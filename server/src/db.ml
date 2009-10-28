(*pp camlp4o `ocamlfind query -i-format lwt.syntax type-conv orm` pa_lwt.cmo pa_type_conv.cmo pa_orm.cma *)

open Lwt
open Log
module C = CalendarLib.Calendar

(* Split a database into multiple databases ordered by time *)

module TimeDB = struct

  let dbs = Hashtbl.create 7

  (* convert a unix time into a year/quadrant *)
  let yrqd ~tm =
    let cal = C.from_unixfloat tm in
    let year = C.year cal in
    let quad = match C.month cal with
      |C.Jan |C.Feb |C.Mar -> 0
      |C.Apr |C.May |C.Jun -> 1
      |C.Jul |C.Aug |C.Sep -> 2
      |C.Oct |C.Nov |C.Dec -> 3 in
    year, quad

  (* map a year/quadrant into a full filename *)
  let db_filename ~year ~quad =
    Printf.sprintf "%s/Perscon-date.%04d%0d.db" (Config.Dir.db ()) year quad

  (* locate database with the date and return handle *)
  let get_db ~year ~quad =
   let fname = db_filename ~year ~quad in
   Schema.Entry.Orm.init fname

  (* run a function over a db handle with time tm *)
  let with_db tm fn =
    let year, quad = yrqd ~tm in
    (* look in the cache for the db *)
    let db = 
      try
        let db' = Hashtbl.find dbs (year,quad) in
        logmod "DB" "got handle %d/%d from cache" year quad;
        db'
      with
        Not_found ->
          let db' = get_db ~year ~quad in
          Hashtbl.add dbs (year,quad) db';
          logmod "DB" "new handle %d/%d" year quad;
          db' in
    fn db

end

module SingleDB = struct

  let dbr = ref None 

  let db_filename () = 
    Printf.sprintf "%s/Perscon.db" (Config.Dir.db ())

  let get_db () = 
    match !dbr with
    | None ->
      logmod "DB" "Initialising new DB";
      let db = Schema.Entry.Orm.init (db_filename ()) in
      dbr := Some db;
      db
    | Some db -> 
      logmod "DB" "Returning cached DB";
      db

  let with_db fn =
    fn (get_db ())

end
