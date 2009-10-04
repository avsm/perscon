(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Cohttp
open Log

(* main callback function *)
let t req oc =
  List.iter (fun (h,v) -> eprintf "%s=%s\n" h v) (Http_request.params_get req);
  let res = Http_response.init
    ~body:"<html><body>hello</body></html>"
    ~headers:[ ("Mime-Type", "text/html") ]
    ~version:`HTTP_1_1
    ~status:(`Success `OK) () in
  Http_daemon.respond_with res oc

