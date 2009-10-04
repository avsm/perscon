open Printf
open Arg

let _ =
  let config_file = ref "perscon.conf" in
  let spec = [
      "-c", Arg.Set_string config_file, "Name of configuration file to use";
  ] in
  parse spec (fun _ -> ()) "";

  Config.init !config_file;
 
  (* obtain the master passphrase *)
  let _ = match Platform.get_password (Lifedb_config.root_user ()) with
  |None ->
     prerr_endline (sprintf "Unable to retrieve passphrase for user: %s" (Lifedb_config.root_user ()));
     exit 1;
  |Some p ->
     Lifedb_rpc.passphrase := p in
 

