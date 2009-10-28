(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log
open Db
open Lwt

module O = Schema.Entry
module OD = Schema.Entry.Orm

exception Serve_static_file of string * string

module Resp = struct
  (* respond to an RPC with an error *)
  let not_found req err = 
    let status = `Client_error `Not_found in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err in
    return (Http_response.init ~body ~headers ~status ())

  (* respond to an RPC with "not enough args" *)
  let bad_args ?(err="") req =
    let status = `Client_error `Bad_request in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = sprintf "<html><body><h1>Bad Request</h1><p>%s</p></body></html>" err in
    logmod "HTTP" "Bad request %s" err;
    return (Http_response.init ~body ~headers ~status ())

  (* debugging response to just dump output *)
  let debug req body =
    logmod "HTTP" "Debug response: %s" body;
    let headers = [ "Cache-control", "no-cache"; "Mime-type", "text/plain" ] in
    let status = `Success `OK in
    return (Http_response.init ~body ~headers ~status ())

  (* blank ok for RPC successes *)
  let ok req =
    let body = "" in
    let headers = [ "Cache-control", "no-cache" ] in
    let status = `Success `OK in
    return (Http_response.init ~body ~headers ~status ())

  (* respond with JSON *)
  let json req js =
    let headers = [ "Mime-type", "application/json" ] in
    let status = `Success `OK in
    let body = Json_io.string_of_json js in
    return (Http_response.init ~body ~headers ~status ())

  (* respond with a query result *)
  let json_result req stringfn res =
    let res = object
       method results = List.length res
       method rows = res
     end in
     json req (stringfn res)

  (* create / read / update / delete functions for a URI *)
  let crud ?get ?post ?delete req (args:string list) =
    let ofn0 args = function 
      | None -> not_found req "unknown method"
      | Some fn -> fn args in
    let ofn1 body args = function
      | None -> not_found req "unknown method"
      | Some fn -> fn body args in
    match Http_request.meth req with
      | `GET | `HEAD -> ofn0 args get
      | `POST ->        ofn1 (Http_request.body req) args post
      | `DELETE ->      ofn0 args delete

  let handle_json req fn =
    try
      fn ()
    with
    | Json_type.Json_error err ->
        bad_args ~err ("Json error: " ^ Printexc.get_backtrace ())
    | Sqlite3.Error err ->  
        bad_args ~err ("Sqlite error: " ^ Printexc.get_backtrace ())
end

module Lookup = struct
  (* given a svc, look it up from the db by its primary keys. *)
  let svc s =
    SingleDB.with_db (fun db ->
      match OD.svc_get ~s_ty:(`Eq s.O.s_ty) ~s_id:(`Eq s.O.s_id) db with
      |[s'] -> logmod "Debug" "Svc hit, id: %Lu" (OD.svc_id db s'); s'
      |[] ->  OD.svc_save db s; s
      | _ ->  failwith "db integrity error"
    )

  (* given an att, look it up from the db *)
  let att a =
    SingleDB.with_db (fun db ->
      match OD.att_get ~a_uid:(`Eq a.O.a_uid) db with
      | [a] -> a
      | []  -> a
      | _   -> failwith "db integrity error"
    )
 
  (* given an entry, remap the svc fields by looking up from db *)
   let entry e =
     SingleDB.with_db (fun db ->
       let e = match OD.e_get ~e_uid:(`Eq e.O.e_uid) db with
        | [e] -> e
        | []  -> e
        | _ -> assert false in
       let e_from = List.map svc e.O.e_from in
       let e_to = List.map svc e.O.e_to in
       let e_atts = List.map att e.O.e_atts in
       e.O.e_from <- e_from;
       e.O.e_to   <- e_to;
       e.O.e_atts <- e_atts;
       e
     )

  (* given a contact, lookup from db or return the same item *)
   let contact c =
     SingleDB.with_db (fun db ->
       let c = match OD.contact_get ~c_uid:(`Eq c.O.c_uid) db with
       | [c] -> c
       | [] -> c
       | _ -> assert false in
       let c_atts = List.map att c.O.c_atts in
       c.O.c_atts <- c_atts; 
       c
     )
end

(* query functions *)
module Query = struct

  let view req =
    let ps = Http_request.params_get req in
    let metaps = List.fold_left (fun a (k,v) ->
        match Pcre.split ~pat:":" ~max:2 k with
        | ["meta";field] -> (field,v) :: a
        | _ -> a
      ) [] ps in
    let mapsl x = String.concat "," (List.map (fun (k,v) -> sprintf "%s=%s" k v) x) in
    logmod "Debug" "View: %s (meta=%s) " (mapsl ps) (mapsl metaps);
    function
      | "doc" :: [] ->
        let e_folder = try Some (`Eq (List.assoc "e_folder" ps)) with Not_found -> None in
        let e_origin = try Some (`Eq (List.assoc "e_origin" ps)) with Not_found -> None in
        SingleDB.with_db (fun db ->
          let rs = OD.e_get ?e_folder ?e_origin db in
          logmod "Debug" "res=%d" (List.length rs);
          Resp.json_result req O.json_of_e_query rs
        )
      | _ -> Resp.not_found req "unknown query"
end

module Methods = struct

  let doc req args =
    let with_doc fn = 
     function
     | uuid :: [] -> 
       SingleDB.with_db (fun db ->
         match OD.e_get ~e_uid:(`Eq uuid) db with
           | [x] -> fn db x
           | _ -> Resp.not_found req "doc not found"
       )
     | _ -> Resp.bad_args req in
    let get = 
      with_doc (fun db d ->
        Resp.json req (O.json_of_e d)
      ) in
    let delete =
      with_doc (fun db c ->
        OD.e_delete db c;
        Resp.ok req
      ) in
    let post body args =
      Resp.handle_json req (fun () ->
        let js = O.e_of_json (Json_io.json_of_string body) in
        let e = Lookup.entry js in
        (* XXX sync update fields here *)
        SingleDB.with_db (fun db -> OD.e_save db e);
        Resp.ok req
      ) in
    Resp.crud ~get ~post ~delete req args

  let contact req args =
    let with_contact fn = 
      function
      | uuid :: [] ->
         SingleDB.with_db (fun db ->
           match OD.contact_get ~c_uid:(`Eq uuid) db with
             | [x] -> fn db x
             | _ -> Resp.not_found req "contact not found"
         )
      | _ -> Resp.bad_args req  in
    let get =
      with_contact (fun db c ->
        Resp.json req (O.json_of_contact c)
      ) in
    let delete =
      with_contact (fun db c -> 
        OD.contact_delete db c;
        Resp.ok req
      ) in
    let post body args =
      Resp.handle_json req (fun () ->
        let js = O.contact_of_json (Json_io.json_of_string body) in
        let e = Lookup.contact js in
        e.O.c_mtime <- js.O.c_mtime;
        e.O.c_meta  <- js.O.c_meta;
        SingleDB.with_db (fun db -> OD.contact_save db e);
        Resp.debug req (Json_io.string_of_json (O.json_of_contact js))
      ) in
    Resp.crud ~get ~post ~delete req args

  let service req args =
    let with_service fn =
      function
      | s_ty :: s_id ->
          let s_id = String.concat "/" s_id in
          SingleDB.with_db (fun db ->
            match OD.svc_get ~s_id:(`Eq s_id) ~s_ty:(`Eq s_ty) db with
            | [s] -> fn db s
            | _ -> Resp.not_found req "service not found" 
          )
      | _ -> Resp.bad_args req in
    let get =
       with_service (fun db s ->
         Resp.json req (O.json_of_svc s)
       ) in
    let delete =
       with_service (fun db s ->
         OD.svc_delete db s;
         Resp.ok req
       ) in
    let post body args =
      Resp.handle_json req (fun () -> 
        let js = O.svc_of_json (Json_io.json_of_string body) in
        let s = Lookup.svc js in
        (match js.O.s_co with |"" -> () |t -> s.O.s_co <- t);
        logmod "Debug" "%s" (Json_io.string_of_json (O.json_of_svc s));
        SingleDB.with_db (fun db -> logmod "Debug3" "s_id: %Lu" (OD.svc_id db s); OD.svc_save db s);
        logmod "Debug2" "%s" (Json_io.string_of_json (O.json_of_svc js));
        Resp.debug req (Json_io.string_of_json (O.json_of_svc js))
      ) in
    Resp.crud ~get ~delete ~post req args

  let att req args =
    let with_att fn = 
      function
      | uuid :: [] ->
         SingleDB.with_db (fun db ->
           match OD.att_get ~a_uid:(`Eq uuid) db with
             | [x] -> fn db x
             | _ -> Resp.not_found req "attachment not found"
         )
      | _ -> Resp.bad_args req  in
    let get =
      with_att (fun db att ->
        let uuid_hash = Crypto.Uid.hash att.O.a_uid in
        fail (Serve_static_file (uuid_hash, att.O.a_mime))
      ) in
    let delete =
      with_att (fun db att ->
        let uuid_hash = Crypto.Uid.hash att.O.a_uid in
        OD.att_delete db att;
        (try
          Unix.unlink (Filename.concat (Config.Dir.att ()) uuid_hash)
        with _ -> ());
        Resp.ok req
      ) in
    let post body args = 
      let mime = 
        match Http_request.header ~name:"content-type" req with 
          | None -> "application/octet-stream"
          | Some m -> m in
      match args with
      | uuid :: [] ->
          let uuid_hash = Crypto.Uid.hash uuid in
          let fname = Filename.concat (Config.Dir.att ()) uuid_hash in
          lwt () = Lwt_io.with_file ~mode:Lwt_io.output fname
            (fun oc -> Lwt_io.write oc body) in
          SingleDB.with_db (fun db ->
            match OD.att_get ~a_uid:(`Eq uuid) db with
            | [] -> OD.att_save db { O.a_uid=uuid; a_mime=mime }
            | [a] -> a.O.a_mime <- mime; OD.att_save db a
            | _ -> assert false
          );
          Resp.ok req
      | _ -> Resp.bad_args req in
    Resp.crud ~post ~get ~delete req args

  let ping req () =
    let pong _ = Resp.debug req "pong" in
    let post _ _ = Resp.debug req (Http_request.body req) in
    let get = pong and delete = pong in
    Resp.crud ~get ~post ~delete req []
end

(* dispatch HTTP requests *)
let dispatch req oc =
  let dyn fn tl = 
    lwt resp = fn req tl in
    Http_daemon.respond_with resp oc in
  let static fname mime_type =
    logmod "HTTP" "Serving static file: %s (%s)" fname mime_type;
    Http_daemon.respond_file ~fname ~droot:(Config.Dir.att ()) ~mime_type oc in
  (* bit of a hack; an exception represents the static
     file since most responses are dynamic and its not worth
     threading through a variant just for the odd static response *)
  let dynstatic fn tl =
    try_lwt 
      dyn fn tl
    with 
      | Serve_static_file (fname, mime) -> static fname mime in
  function
  | "s" :: tl ->  (* static *)
     let path = String.concat "/" tl in
     let mime_type = Magic_mime.lookup path in
     let fname = Filename.concat (Config.Dir.static ()) path in
     logmod "HTTP" "serving file: %s (%s)" fname mime_type;
     static fname mime_type
  | args ->       (* dynamic *)
     match args with
       | "doc"     :: tl -> dyn Methods.doc tl
       | "contact" :: tl -> dyn Methods.contact tl
       | "svc"     :: tl -> dyn Methods.service tl
       | "att"     :: tl -> dynstatic Methods.att tl
       | "ping"    :: [] -> dyn Methods.ping ()
       | "view"    :: tl -> dyn Query.view tl
       | _ ->               dyn Resp.not_found "unknown url"
 
(* main callback function *)
let t req oc =

  (* debug bits *)
  let path = Http_request.path req in
  logmod "HTTP" "%s %s [%s]" (Http_common.string_of_method (Http_request.meth req)) path 
    (String.concat "," (List.map (fun (h,v) -> sprintf "%s=%s" h v) 
      (Http_request.params_get req)));

  (* normalize path to strip out ../. and such *)
  let split_path = Pcre.split ~pat:"/" path in
  let normalized_path = List.filter (function |"."|".." -> false |_ -> true) split_path in
  let path_elem = List.tl normalized_path in
  dispatch req oc path_elem
