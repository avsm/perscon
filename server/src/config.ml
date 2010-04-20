open Lwt
open Lwt_io

type config = {
    db_directory: string;
    log_directory: string;
    port: int;
    static_directory: string;
} with json

let conf = ref None
let cfn fn = match !conf with 
          None -> failwith "configuration not initalized"
        | Some c -> fn c

let rex = Pcre.regexp "\\$HOME"
let itempl = Pcre.subst (Sys.getenv "HOME")
let s = Pcre.replace ~rex ~itempl

let init file =
  let s = Lwt_io.lines_of_file file in
  lwt l = Lwt_stream.fold (fun l a -> a ^ l ) s "" in
  conf := Some (config_of_json l);
  return ()

module Dir = struct
  let db () = cfn (fun c -> s c.db_directory)
  let log () = cfn (fun c -> s c.log_directory)
  let static () = cfn (fun c -> s c.static_directory)
  let port () = cfn (fun c -> c.port)
end

