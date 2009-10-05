(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log

(* respond to an RPC with an error *)
let respond_unknown req err = 
  let status = `Client_error `Not_found in
  let headers = [ "Cache-control", "no-cache" ] in
  let body = sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err in
  Http_response.init ~body ~headers ~status ()

(* dispatch dynamic RPC requests *)
let dispatch_rpc req path_elem =
  match path_elem with
  |"d" :: tl -> respond_unknown req "d"
  | _ -> respond_unknown req "unknown RPC"   

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
  logmod "HTTP" "path_elem = %s" (String.concat " ; " path_elem);
  match path_elem with
  | "s" :: tl -> (* static file *)
     let path = String.concat "/" tl in
     let mime_type = Mime.lookup (get_extension path) in
     let fname = Filename.concat (Config.Dir.static ()) path in
     logmod "HTTP" "serving file: %s (%s)" fname mime_type;
     Http_daemon.respond_file ~fname ~mime_type oc
  | _ -> (* dynamic *)
     Http_daemon.respond_with (dispatch_rpc req path_elem) oc
