(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Arg
open Lwt
open Log
open Cohttp

let _ =
  let config_file = ref "perscon.conf" in
  let spec = [
      "-c", Arg.Set_string config_file, "Name of configuration file to use";
  ] in
  parse spec (fun _ -> ()) "";

  logmod "Server" "reading config from %s" !config_file;
  Config.init !config_file;

  Lwt_main.run ( 
    (* obtain the master passphrase *)
    logmod "Server" "obtaining root passphrase";
    let user = Config.User.root () in
    lwt p = Platform.get_pass ~user in
    let phrase = match p with
      |None ->
        prerr_endline "Unable to retrieve passphrase for root user";
        exit 1;
      |Some p -> p
    in
    let port = Config.Dir.port () in
    let spec = {  Http_daemon.default_spec with
      Http_daemon.auth = Some ("Personal Container", `Basic ("root", phrase));
      callback = Dispatch.t;
      port = port } in
   
    logmod "Server" "initializing MIME types";
    Mime.init (Filename.concat (Config.Dir.etc ()) "mime.types") >>

    (logmod "Server" "listening to HTTP on port %d" port;
    Http_daemon.main spec)
  )
