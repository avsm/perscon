(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Lwt
open Log
open Tcp_server

type spec = {
  address: string;
  port: int;
  timeout: int option;
  cb: (clisockaddr:Unix.sockaddr ->
       srvsockaddr:Unix.sockaddr ->
       Lwt_io.input Lwt_io.channel -> 
       Lwt_io.output Lwt_io.channel ->
       unit Lwt.t)
}

(* callback for a new pop3 connection *)
let cb ~clisockaddr ~srvsockaddr ic oc =
  Lwt_io.write_line oc "hello" >>
  return ()

(* start the server loop *)
let main spec =
  lwt sockaddr = build_sockaddr spec.address spec.port in
  let cb ~clisockaddr ~srvsockaddr inchan outchan =
    try_lwt
      logmod "POP3"  "invoking callback";
      spec.cb ~clisockaddr ~srvsockaddr inchan outchan
    with
      | End_of_file -> 
        logmod "POP3" "done with connection"; return ()
      | e ->
        logmod "POP3" "uncaught exception: %s" (Printexc.to_string e);
        fail e
  in
  let timeout = spec.timeout in
  Tcp_server.t ~sockaddr ?timeout cb
