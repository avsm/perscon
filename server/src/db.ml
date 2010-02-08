open Lwt
open Log
module C = CalendarLib.Calendar

(* Split a database into multiple databases ordered by time *)

module SingleDB = struct

  let dbr = ref None 

  let db_filename () = 
    Printf.sprintf "%s/Perscon.db" (Config.Dir.db ())

  let get_db () = 
    match !dbr with
    | None ->
      let db = Schema.Entry.init (db_filename ()) in
      dbr := Some db;
      db
    | Some db -> 
      db

  let with_db fn =
    fn (get_db ())

end
