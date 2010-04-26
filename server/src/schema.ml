TYPE_CONV_PATH "Schema"

open Tokyo_common
open Tokyo_cabinet
open Lwt

(* Lwt-safe accessor functions *)
let lwt_wrap1 fn a = try_lwt return (fn a) with e -> fail e
let lwt_wrap2 fn a1 a2 = try_lwt return (fn a1 a2) with e -> fail e
let lwt_wrap3 fn a1 a2 a3 = try_lwt return (fn a1 a2 a3) with e -> fail e
let lwt_wrap4 fn a1 a2 a3 a4 = try_lwt return (fn a1 a2 a3 a4) with e -> fail e
let lwt_wrap5 fn a1 a2 a3 a4 a5 = try_lwt return (fn a1 a2 a3 a4 a5) with e -> fail e

module Person = struct
  type t = {
    uid: string option;
    first_name: string option;
    last_name: string option;
    origin: string option;
    created: float;
    modified: float;
    services: string list;
    atts: string list;
  } with json,type_desc

  let tc = 
    let type_desc = type_desc_t in
    let marshall v = Cstr.of_string (json_of_t v) in
     let unmarshall cstr = t_of_json (Cstr.copy cstr) in
    Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

  let lwt_of_json = lwt_wrap1 t_of_json
end

module Location = struct
  type t = {
    lat: float;
    lon: float;
    speed: float option;
    accuracy: float option;
    woeid: string option;
    url: string option;
    date: float;
  } with json,type_desc

  let tc =
    let type_desc = type_desc_t in
    let marshall v = Cstr.of_string (json_of_t v) in
    let unmarshall cstr = t_of_json (Cstr.copy cstr) in
    Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

  let lwt_of_json = lwt_wrap1 t_of_json
end

module Att = struct
  type t = {
    mime: string;
    body: string;
  } with json,type_desc
  
  let tc =
    let type_desc = type_desc_t in
    let marshall v = Cstr.of_string (json_of_t v) in
    let unmarshall cstr = t_of_json (Cstr.copy cstr) in
    Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare
end

module Service = struct
   type t = {
     ty: string;
     context: string option;
     person: string option;
     value: string option;
     proto: (string * string) option;
   } with json, type_desc
end

module Message = struct
  type t = {
    origin: string;
    frm: (string * string) list list;
    tos: (string * string ) list list;
    atts: string list;
    meta: (string * string) list;
    ctime: float option;
    mtime: float;
    thread: string option;
    thread_count: int option;
    uid: string;
    tags: string list;
  } with json, type_desc

  let tc =
    let type_desc = type_desc_t in
    let marshall v = Cstr.of_string (json_of_t v) in
    let unmarshall cstr = t_of_json (Cstr.copy cstr) in
    Otoky_type.make ~type_desc ~marshall ~unmarshall ~compare

  let lwt_of_json = lwt_wrap1 t_of_json
  let lwt_to_json = lwt_wrap1 json_of_t
end

type skey = string with type_desc

let string_type =
  let type_desc = type_desc_skey in
  let marshall = Cstr.of_string in
  let unmarshall = Cstr.copy in
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

let with_loc_db fn =
  lwt_wrap4 with_bdb (Config.Dir.db () ^ "/loc.db") string_type Location.tc fn

let with_att_db fn =
  lwt_wrap4 with_hdb (Config.Dir.db () ^ "/att.db") string_type Att.tc fn

let with_msg_db fn =
  lwt_wrap4 with_hdb (Config.Dir.db () ^ "/message.db") string_type Message.tc fn
