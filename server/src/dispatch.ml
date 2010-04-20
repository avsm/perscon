open Printf
open Cohttp
open Cohttpserver
open Log
open Lwt

exception Serve_static_file of string * string

module Resp = struct
  (* respond to an RPC with an error *)
  let not_found req err = 
    let status = `Status (`Client_error `Not_found) in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = [`String (sprintf "<html><body><h1>Error</h1><p>%s</p></body></html>" err)] in
    return (Http_response.init ~body ~headers ~status ())

  (* respond to an RPC with "not enough args" *)
  let bad_args ?(err="") req =
    let status = `Status (`Client_error `Bad_request) in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = [`String (sprintf "<html><body><h1>Bad Request</h1><p>%s</p></body></html>" err)] in
    logmod "HTTP" "Bad request %s" err;
    return (Http_response.init ~body ~headers ~status ())

  (* debugging response to just dump output *)
  let debug req body =
    logmod "HTTP" "Debug response: %s" body;
    let headers = [ "Cache-control", "no-cache"; "Mime-type", "text/plain" ] in
    let status = `Status (`Success `OK) in
    let body = [`String body] in
    return (Http_response.init ~body ~headers ~status ())

  (* blank ok for RPC successes *)
  let ok req =
    let status = `Status (`Success `OK) in
    let headers = [ "Cache-control", "no-cache" ] in
    let body = [`String ""] in
    return (Http_response.init ~body ~headers ~status ())

  (* respond with JSON *)
  let json req js =
    let headers = [ "Mime-type", "application/json" ] in
    let status = `Status (`Success `OK) in
    let body = [`String js] in
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
    try  fn ()
    with e ->
      let err = Printexc.to_string e in
      bad_args ~err ("Json error: " ^ Printexc.get_backtrace ())
end

module Person = struct

  let crud req args =
    let get = function
       |[uid] -> Resp.debug req "foo"
       | _ -> Resp.not_found req "not found"
    in
    Resp.crud ~get req args 
end

let safe_try fn arg =
  try return (fn arg)
  with e -> fail e

module Loc = struct
  let crud req args =
    let post doc = function
      | [] -> 
          lwt body = Http_message.string_of_body doc in
          lwt j = try_lwt return (Schema.location_of_json body) with e -> fail e in
          Resp.ok req
      | _ -> Resp.not_found req "unknown post"
  in
  Resp.crud ~post req args    
end

(* dispatch HTTP requests *)
let dispatch req oc =
  let dyn fn tl = 
    lwt resp = fn req tl in
    logmod "HTTP" "Dynamic response";
    Http_daemon.respond_with resp oc in
  let static fname mime_type =
    logmod "HTTP" "Serving static file: %s (%s)" fname mime_type;
    Http_daemon.respond_file ~fname ~droot:("todo") ~mime_type oc in
  function
  | "" :: "static" :: tl -> (* static *)
      let path = String.concat "/" tl in
      let mime_type = Magic_mime.lookup path in
      let fname = Filename.concat (Config.Dir.static ()) path in
      logmod "HTTP" "serving file: %s (%s)" fname mime_type;
      static fname mime_type
  | "" :: args -> begin (* dynamic *)
      match args with
        | "person" :: x -> dyn Person.crud x
        | "loc" :: x -> dyn Loc.crud x
        | _ -> dyn Resp.not_found "unknown url"
  end
  | _ -> dyn Resp.not_found "unknown url"
 
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
  logmod "HTTP" "normalized_path: %d" (List.length normalized_path);
  try_lwt
      dispatch req oc normalized_path
  with e -> begin
      print_endline "exception:";
      print_endline (Printexc.to_string e);
      lwt resp = Resp.bad_args "internal server error" in
      Http_daemon.respond_with resp oc
  end
