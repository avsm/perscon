open Printf
open Lwt
open Log
open Tcp_server

type authfn = (user:string -> pass:string -> bool)

type spec = {
  address: string;
  port: int;
  timeout: int option;
  auth: authfn;
  cb: (clisockaddr:Unix.sockaddr ->
       srvsockaddr:Unix.sockaddr ->
       auth:authfn ->
       Lwt_io.input Lwt_io.channel -> 
       Lwt_io.output Lwt_io.channel ->
       unit Lwt.t)
}

(* callback for a new pop3 connection *)
let cb ~clisockaddr ~srvsockaddr ~auth ic oc =
  Pop3_protocol.t ~auth ic oc

(* start the server loop *)
let main spec =
  lwt sockaddr = build_sockaddr spec.address spec.port in
  let auth = spec.auth in
  let cb ~clisockaddr ~srvsockaddr inchan outchan =
    try_lwt
      logmod "POP3"  "invoking callback";
      spec.cb ~clisockaddr ~srvsockaddr ~auth inchan outchan
    with
      | End_of_file -> 
        logmod "POP3" "done with connection"; return ()
      | e ->
        logmod "POP3" "uncaught exception: %s" (Printexc.to_string e);
        fail e
  in
  let timeout = spec.timeout in
  Tcp_server.t ~sockaddr ?timeout cb
