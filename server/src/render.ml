open Schema.Entry
open Db
open Lwt
open Printf

module C = CalendarLib.Calendar

let add_header k v = 
  sprintf "%s: %s" k v

let add_date e =
  let c = C.from_unixfloat e.e_mtime in
  let rfc822_date = sprintf "%s, %02d %s %d %02d:%02d:%02d +0000"
   (match C.day_of_week c with 
    |C.Mon -> "Mon" |C.Tue -> "Tue" |C.Wed -> "Wed"
    |C.Thu -> "Thu" |C.Fri -> "Fri" |C.Sat -> "Sat" |C.Sun -> "Sun")
   (C.day_of_month c)
   (match C.month c with
    |C.Jan -> "Jan" |C.Feb -> "Feb" |C.Mar -> "Mar"
    |C.Apr -> "Apr" |C.May -> "May" |C.Jun -> "Jun"
    |C.Jul -> "Jul" |C.Aug -> "Aug" |C.Sep -> "Sep"
    |C.Oct -> "Oct" |C.Nov -> "Nov" |C.Dec -> "Dec")
   (C.year c)
   (C.hour c) (C.minute c) (C.second c) in
  add_header "Date" rfc822_date

let person s =
  let contact_name c =
    let fname = try List.assoc "first_name" c.c_meta with Not_found -> "" in
    let lname = try List.assoc "last_name" c.c_meta with Not_found -> "" in
    String.concat " " [fname; lname] in
  let mail_name c s =
    sprintf "%s <%s>" (contact_name c) s.s_id in
  let default = sprintf "%s via %s" s.s_id s.s_ty in
  SingleDB.with_db (fun db ->
    match s.s_co with
    |"" -> default
    |c_id -> begin
      match Orm.contact_get ~c_uid:(`Eq c_id) db with
      |[c] -> 
        (* XXX look up email address also, not just s_id for any service *)
        mail_name c s
      |_ -> default
    end
  ) 

let add_from e =
  match e.e_from with
  |s::_ -> add_header "From" (person s)
  |_ -> add_header "From" "Unknown"

let add_id e =
  add_header "Message-ID" (sprintf "<%s>" e.e_uid)

let add_to e =
  let tos = String.concat "," (List.map person e.e_to) in
  add_header "To" tos

let add_subject s =
  let subj = if String.length s > 255 then
    String.sub s 0 252 ^ "..." else s in
  add_header "Subject" subj

let add_body b = 
  "" :: b

let std_headers e =
  [ add_from e; add_to e; add_date e; add_id e ]

module POP3 = struct

  let imap e =
    let raw_uuid = List.assoc "raw" e.e_meta in
    let fname = Filename.concat (Config.Dir.att ()) (Crypto.Uid.hash raw_uuid) in
    let size = Int64.of_string (List.assoc "raw_size" e.e_meta) in
    (* XXX temporary hack to read into a string, since if you only partially
       read a Lwt_stream it will leak the FD.  Some backends like the POP3
       one will only read a portion in order to service TOP requests *)
    let s = Lwt_io.lines_of_file fname in
    lwt b = Lwt_stream.fold (fun l a -> l :: a) s [] in
    let body = Lwt_stream.of_list (List.rev b) in
    return (body, size)

  let of_dynamic lines =
    let size = Int64.of_int (List.fold_left (fun a b -> String.length b + a + 2) 0 lines) in
    let b = Lwt_stream.of_list lines in
    Log.logmod "Debug" "dyn: size=%Lu" size;
    return (b, size)
    
  let phone e =
    let subj = try List.assoc "text" e.e_meta with Not_found -> "???" in
    let body = [ sprintf "Tags: %s" (String.concat ", " e.e_tags) ] in
    let lines = add_subject subj :: (std_headers e) @ (add_body body) in
    of_dynamic lines

  let call e =
    let subj = try
      sprintf "Phone call, %s seconds" (List.assoc "duration" e.e_meta)
     with Not_found -> "Phone call" in
    let body = [ sprintf "Tags: %s" (String.concat ", " e.e_tags) ] in
    let lines = add_subject subj :: (std_headers e) @ (add_body body) in
    of_dynamic lines

  let t e =
    match String.lowercase (e.e_origin) with
    |"imap" ->
      imap e
    |"iphone:sms" ->
      phone e
    |"iphone:call" ->
      call e
    |_ -> 
      imap e 

end
