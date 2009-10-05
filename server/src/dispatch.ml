(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log

(* respond to an RPC with an error *)
let respond_not_found req err = 
  let status = `Client_error `Not_found in
  let headers = [ "Cache-control", "no-cache" ] in
  let body = sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err in
  Http_response.init ~body ~headers ~status ()

(* respond to an RPC with "not enough args" *)
let respond_bad_args req =
  respond_not_found req "Incorrect number of arguments provided"

module Methods = struct

  (* create / read / update / delete functions for a URI *)
  let crud ?get ?post ?delete req args =
    let ofn args = function 
      | None -> respond_not_found req "unknown method"
      | Some fn -> fn args in
    match Http_request.meth req with
    |`GET |`HEAD -> ofn args get
    |`POST ->       ofn args post
    |`DELETE ->     ofn args delete

  let doc req = 
    function
    | uuid :: [] -> 
        let get args = respond_not_found req "GET" in
        crud ~get req [uuid]
    | _ -> respond_bad_args req

end

(* dispatch dynamic RPC requests *)
let dispatch_rpc req path_elem =
  match path_elem with
  |"d" :: tl -> Methods.doc req tl
  | _ -> respond_not_found req "unknown RPC"   

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
