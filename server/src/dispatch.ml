(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log
open Db

module O = Schema.Entry
module OD = Schema.Entry.Orm

module Resp = struct
  (* respond to an RPC with an error *)
  let not_found req err = 
    let status = `Client_error `Not_found in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err in
    Http_response.init ~body ~headers ~status ()

  (* respond to an RPC with "not enough args" *)
  let bad_args ?(err="") req =
    let status = `Client_error `Bad_request in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = sprintf "<html><body><h1>Bad Request</h1><p>%s</p></body></html>" err in
    logmod "HTTP" "Bad request %s" err;
    Http_response.init ~body ~headers ~status ()

  (* debugging response to just dump output *)
  let debug req body =
    logmod "HTTP" "Debug response: %s" body;
    let headers = [ "Cache-control", "no-cache"; "Mime-type", "text/plain" ] in
    let status = `Success `OK in
    Http_response.init ~body ~headers ~status ()

  (* blank ok for RPC successes *)
  let ok req =
    let body = "" in
    let headers = [ "Cache-control", "no-cache" ] in
    let status = `Success `OK in
    Http_response.init ~body ~headers ~status ()

  (* respond with JSON *)
  let json req js =
    let headers = [ "Mime-type", "application/json" ] in
    let status = `Success `OK in
    let body = Json_io.string_of_json js in
    Http_response.init ~body ~headers ~status ()

  (* create / read / update / delete functions for a URI *)
  let crud ?get ?post ?delete req args =
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

(* query functions *)
module Views = struct

  let uid = ()

end

module Lookup = struct
  (* given a svc, look it up from the db by its primary keys. *)
  let svc s =
    SingleDB.with_db (fun db ->
      match OD.svc_get ~s_ty:(`Eq s.O.s_ty) ~s_id:(`Eq s.O.s_id) db with
      |[s] -> s
      |[] ->  s
      | _ ->  failwith "db integrity error"
    )

  (* given an att, look it up from the db *)
  let att a =
    SingleDB.with_db (fun db ->
      match OD.att_get ~a_uid:(`Eq a.O.a_uid) db with
      |[a] -> a
      |[]  -> a
      |_   -> failwith "db integrity error"
    )
 
  (* given an entry, remap the svc fields by looking up from db *)
   let entry e =
     SingleDB.with_db (fun db ->
       let e = match OD.e_get ~e_uid:(`Eq e.O.e_uid) db with
        |[e] -> e
        |[] -> e
        |_ -> assert false in
       let e_from = List.map svc e.O.e_from in
       let e_to = List.map svc e.O.e_to in
       let e_atts = List.map att e.O.e_atts in
       { e with O.e_from=e_from; e_to=e_to; e_atts=e_atts }
     )

  (* given a contact, lookup from db or return the same item *)
   let contact c =
     SingleDB.with_db (fun db ->
       match OD.contact_get ~c_uid:(`Eq c.O.c_uid) db with
       |[c] -> c
       |[] -> c
       |_ -> assert false
     )
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
        SingleDB.with_db (fun db ->
           match OD.e_get ~e_uid:(`Eq js.O.e_uid) db with
            | [e] -> failwith "todo"
            | [] -> OD.e_save db js
            | _ -> assert false
        );
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
        s.O.s_co <- js.O.s_co;
        SingleDB.with_db (fun db -> OD.svc_save db s);
        Resp.debug req (Json_io.string_of_json (O.json_of_svc js))
      ) in
    Resp.crud ~get ~delete ~post req args

  let att req args =
    let mime = 
      match Http_request.header ~name:"mime-type" req with 
        | None -> "application/octet-stream"
        | Some m -> m in
    let post body = function
      | uuid :: [] ->
          let uuid_hash = Crypto.Uid.hash uuid in
          let fname = Filename.concat (Config.Dir.att ()) uuid_hash in
          Resp.ok req
      | _ -> Resp.bad_args req in
    Resp.crud ~post req args

  let ping req  =
    let pong _ = Resp.debug req "pong" in
    let post _ _ = Resp.debug req (Http_request.body req) in
    let get = pong and delete = pong in
    Resp.crud ~get ~post ~delete req []
end

(* dispatch dynamic RPC requests *)
let dispatch_rpc req path_elem =
  match path_elem with
  |"d" :: tl -> Methods.doc req tl
  |"c" :: tl -> Methods.contact req tl
  |"svc" :: tl -> Methods.service req tl
  |"a" :: tl -> Methods.att req tl
  |"ping" :: [] -> Methods.ping req 
  | _ -> Resp.not_found req "unknown RPC"   

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

  (* determine if it is static or dynamic content *)
  match path_elem with
  | "s" :: tl -> (* static file *)
     let path = String.concat "/" tl in
     let mime_type = Magic_mime.lookup path in
     let fname = Filename.concat (Config.Dir.static ()) path in
     logmod "HTTP" "serving file: %s (%s)" fname mime_type;
     Http_daemon.respond_file ~fname ~mime_type oc
  | _ -> (* dynamic *)
     Http_daemon.respond_with (dispatch_rpc req path_elem) oc
