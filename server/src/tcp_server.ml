(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Lwt
open Unix
open Lwt_unix
open Lwt_io
open Log

let build_sockaddr ~addr ~port =
  try_lwt
    lwt hent = Lwt_lib.gethostbyname addr in
    return (ADDR_INET (hent.h_addr_list.(0), port))
  with _ ->
    fail (Failure ("Cannot resolve hostname: " ^ addr))

let close chan =
  try_lwt Lwt_io.close chan
  with _ -> return ()

let init ?(backlog=15) sockaddr =
  let s = socket PF_INET SOCK_STREAM 0 in
  setsockopt s SO_REUSEADDR true;
  bind s sockaddr;
  listen s backlog;
  s

let process ~sockaddr ?timeout callback (client,_) =
  let inch = of_fd input client in
  let outch = of_fd output client in

  let unixfd = unix_file_descr client in 
  let clisockaddr = getpeername unixfd in
  let srvsockaddr = getsockname unixfd in

  let c = 
    try_lwt 
      callback ~clisockaddr ~srvsockaddr inch outch 
    with e ->
      logmod "TCP" "ignoring uncaught exception in TCP server: %s" (Printexc.to_string e);
       return ()
    in
  let events = match timeout with
    |None -> [ c ]
    |Some t -> [ c ; (sleep (float_of_int t) >> return ()) ] in
  Lwt.select events >>
  close outch >>
  close inch
  
let t ~sockaddr ?timeout cb =
  let s = init sockaddr in
  let rec handle_connection () =
     lwt x = accept s in
     let _ = process ~sockaddr ?timeout cb x in
     handle_connection ()
  in
  handle_connection ()
