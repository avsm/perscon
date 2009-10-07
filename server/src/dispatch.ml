(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log
open Db

module O = Schema.Entry

module Resp = struct
  (* respond to an RPC with an error *)
  let not_found req err = 
    let status = `Client_error `Not_found in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err in
    Http_response.init ~body ~headers ~status ()

  (* respond to an RPC with "not enough args" *)
  let bad_args ?(err="") req =
    not_found req ("Incorrect arguments provided\n" ^ err)

  (* debugging response to just dump output *)
  let debug req body =
    let headers = [ "Cache-control", "no-cache"; "Mime-type", "text/plain" ] in
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

module Methods = struct

  let doc req = function
    | uuid :: [] -> 
        let get args = Resp.not_found req "GET" in
        let post body args =
          Resp.handle_json req (fun () ->
            let js = O.e_of_json (Json_io.json_of_string body) in
            Resp.debug req (Json_io.string_of_json (O.json_of_e js)) 
          )
        in
        Resp.crud ~get ~post req [uuid]
    | _ -> Resp.bad_args req

  let contact req = function
    | uuid :: [] ->
       let get = function
         | uuid :: [] ->
            SingleDB.with_db (fun db ->
              match O.Orm.contact_get ~c_uid:(`Eq uuid) db with
              | [x] -> Resp.json req (O.json_of_contact x)
              | _ -> Resp.not_found req "contact not found"
            )
         | _ -> Resp.bad_args req in  
       let post body args =
         Resp.handle_json req (fun () ->
           let js = O.contact_of_json (Json_io.json_of_string body) in
           SingleDB.with_db (fun db ->
             match O.Orm.contact_get ~c_uid:(`Eq js.O.c_uid) db with
              | [x] -> 
                 x.O.c_mtime <- js.O.c_mtime;
                 x.O.c_meta  <- js.O.c_meta;
                 O.Orm.contact_save db x
              | [] -> O.Orm.contact_save db js
              | _ -> assert false
           );
           Resp.debug req (Json_io.string_of_json (O.json_of_contact js))
         ) in
       Resp.crud ~get ~post req [uuid]
    | _ -> Resp.bad_args req
 
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
  |"ping" :: [] -> Methods.ping req 
  | _ -> Resp.not_found req "unknown RPC"   

(* Retrieve file extension , if any, or blank string otherwise *)
let get_extension name =
  let rec search_dot i =
    if i < 1 || name.[i] = '/' then ""
    else if name.[i] = '.' then String.sub name (i+1) (String.length name - i - 1)
    else search_dot (i - 1) in
  search_dot (String.length name - 1)

(* main callback function *)
let t req oc =
  (* debug bits *)
  let path = Http_request.path req in
  logmod "HTTP" "%s %s [%s]" (Http_common.string_of_method (Http_request.meth req)) path 
    (String.concat "," (List.map (fun (h,v) -> sprintf "%s=%s" h v) 
      (Http_request.params_get req)));

  (* normalize path to strip out ../. and such *)
  let path_elem = List.tl (Neturl.norm_path (Pcre.split ~pat:"/" path)) in

  (* determine if it is static or dynamic content *)
  match path_elem with
  | "s" :: tl -> (* static file *)
     let path = String.concat "/" tl in
     let mime_type = Mime.lookup (get_extension path) in
     let fname = Filename.concat (Config.Dir.static ()) path in
     logmod "HTTP" "serving file: %s (%s)" fname mime_type;
     Http_daemon.respond_file ~fname ~mime_type oc
  | _ -> (* dynamic *)
     Http_daemon.respond_with (dispatch_rpc req path_elem) oc
