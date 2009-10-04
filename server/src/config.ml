open Schema.Config
let conf = ref None

let cfn fn = match !conf with 
          None -> failwith "configuration not initalized"
        | Some c -> fn c

let rex = Pcre.regexp "\\$HOME"
let itempl = Pcre.subst (Sys.getenv "HOME")
let s = Pcre.replace ~rex ~itempl

let init file =
  conf := Some (c_of_json (Json_io.load_json file))

module Dir = struct
  let db () = cfn (fun c -> s c.db_directory)
  let log () = cfn (fun c -> s c.log_directory)
  let static () = cfn (fun c -> s c.static_directory)
  let port () = cfn (fun c -> c.port)
end

module User = struct
  let root () = "root"
end
