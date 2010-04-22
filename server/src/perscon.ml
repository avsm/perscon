open Printf
open Arg
open Lwt
open Log
open Cohttpserver

module Dirs = struct
  exception Unable_to_make_dirs of string * string
  let make dir =
    let rec fn dir accum = 
      match dir with
      |"/"|""|"." -> raise (Unable_to_make_dirs (dir, String.concat "/" accum))
      |_ when try Sys.is_directory dir with Sys_error _ -> false ->
        ignore(List.fold_left (fun a b ->
          let c = Filename.concat a b in
          Unix.handle_unix_error Unix.mkdir c 0o755;
          c) dir accum)
      |_ ->
        fn (Filename.dirname dir) ((Filename.basename dir) :: accum)
    in fn dir []
end

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
    List.iter Dirs.make [ Config.Dir.db () ; Config.Dir.log () ];
    let http =
      logmod "Server" "listening to HTTP on port %d" http_port;
      Http_daemon.main http_spec in
    join [ http ]

  )
