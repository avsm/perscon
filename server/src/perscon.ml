open Printf
open Arg
open Lwt
open Log
open Cohttpserver

let _ = Sys.set_signal Sys.sigpipe Sys.Signal_ignore

let _ =
  let config_file = ref "perscon.conf" in
  let spec = [
      "-c", Arg.Set_string config_file, "Name of configuration file to use";
  ] in
  parse spec (fun _ -> ()) "";

  logmod "Server" "reading config from %s" !config_file;

  Lwt_main.run ( 
    Config.init !config_file >>
    let http_port = Config.Dir.port () in
    let http_spec = { Http_daemon.default_spec with
      Http_daemon.auth = `None;
      callback = Dispatch.t;
      port = http_port } in
    let http =
      logmod "Server" "listening to HTTP on port %d" http_port;
      Http_daemon.main http_spec in
    join [ http ]

  )
