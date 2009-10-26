(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Schema.Entry
open Lwt

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

  let t e =
    match e.e_origin with
    |"IMAP" ->
      imap e
    |_ -> 
      imap e 

end
