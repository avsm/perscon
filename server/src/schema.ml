TYPE_CONV_PATH "Schema"

type person = {
    uid: string option;
    first_name: string option;
    last_name: string option;
    origin: string option;
    created: float;
    modified: float;
    services: string list;
    atts: string list;
} with json,type_desc

type location = {
    lat: float;
    lon: float;
    speed: float option;
    accuracy: float option;
    woeid: string option;
    url: string option;
    date: float;
} with json,type_desc

type att = {
    mime: string;
    body: string;
} with json,type_desc

type skey = string with type_desc

open Lwt
open Tokyo_common
open Tokyo_cabinet

let string_type =
  let type_desc = type_desc_skey in
  let marshall = Cstr.of_string in
  let unmarshall = Cstr.copy in
  Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

let location_type =
  let type_desc = type_desc_location in
  let marshall v = Cstr.of_string (json_of_location v) in
  let unmarshall cstr = location_of_json (Cstr.copy cstr) in
  Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

let att_type =
  let type_desc = type_desc_att in
  let marshall v = Cstr.of_string (json_of_att v) in
  let unmarshall cstr = att_of_json (Cstr.copy cstr) in
  Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

let with_bdb file ktype vtype fn =
  let db = Otoky_bdb.open_ ~omode:[Oreader;Owriter;Ocreat] ktype vtype file in
  try
    let x = fn db in
    Otoky_bdb.close db;
    x
  with
  e -> (Otoky_bdb.close db; raise e)

let with_hdb file ktype vtype fn =
  let db = Otoky_hdb.open_ ~omode:[Oreader;Owriter;Ocreat] ktype vtype file in
  try
    let x = fn db in
    Otoky_hdb.close db;
    x
  with
  e -> (Otoky_hdb.close db; raise e)

(* Lwt-safe accessor functions *)
let lwt_wrap1 fn a = try_lwt return (fn a) with e -> fail e
let lwt_wrap2 fn a1 a2 = try_lwt return (fn a1 a2) with e -> fail e
let lwt_wrap3 fn a1 a2 a3 = try_lwt return (fn a1 a2 a3) with e -> fail e
let lwt_wrap4 fn a1 a2 a3 a4 = try_lwt return (fn a1 a2 a3 a4) with e -> fail e
let lwt_wrap5 fn a1 a2 a3 a4 a5 = try_lwt return (fn a1 a2 a3 a4 a5) with e -> fail e
let lwt_location_of_json = lwt_wrap1 location_of_json

let with_loc_db fn =
  lwt_wrap4 with_bdb (Config.Dir.db () ^ "/loc.db") string_type location_type fn

let with_att_db fn =
  lwt_wrap4 with_hdb (Config.Dir.db () ^ "/att.db") string_type att_type fn
