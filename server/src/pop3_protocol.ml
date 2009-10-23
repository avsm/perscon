(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Lwt
open Log
open Db

module O = Schema.Entry
module OD = Schema.Entry.Orm

type state =
  | Greeting
  | Authorization
  | Transaction of string * string (* origin * folder name *)
  | Update

exception Not_implemented

let rec tick ~auth ic oc =
  (* helper input/output functions *)
  let out b = 
    Lwt_io.write oc (b ^ "\r\n") in
  let out_ok b = out ("+OK " ^ b) in
  let continue st = tick ~auth ic oc st in
  let out_ok_tick st b = out_ok b >> continue st in
  let out_ml_tick st = out "." >> continue st in
  let out_err b = out ("-ERR " ^ b) in
  let out_err_tick st b = out_err b >> continue st in
  let inp () = Lwt_io.read_line ic in
  let rec inp_cmd fn =
    lwt l = inp () in
    logmod "Debug" "In : %s" l;
    match Pcre.split ~pat:" " ~max:2 l with
    | [cmd; rest] -> fn rest (String.lowercase cmd)
    | [cmd] -> fn "" (String.lowercase cmd)
    | _ -> out_err "Unknown command" >> inp_cmd fn in
  (* pattern match the protocol based on state *)
  function
  | Greeting ->
      out_ok_tick Authorization "Personal Container POP3 ready"
  | Authorization ->
      (* handle common commands like quit for this state *)
      let rec inp_auth_cmd fn =
        inp_cmd (fun args -> function
          | "quit" ->
              out_ok_tick Update "Personal Container signing off"
          |  other ->
              fn args other
        ) in

      inp_auth_cmd (fun arg1 -> function
        | "user" -> begin
            (* split username into origin/folder *)
            match Pcre.split ~pat:"/" ~max:2 arg1 with
            | [ origin; folder ] ->
                out_ok (origin ^ " " ^ folder) >>
                inp_auth_cmd (fun arg2 -> function
                  |"pass" ->
                     if auth ~user:arg1 ~pass:arg2 then
                       out_ok_tick (Transaction (origin,folder)) "Success"
                     else
                       out_err_tick Authorization "Denied"
                 | c -> out_err_tick Authorization "only PASS valid here; relogin with USER"
               )
           | _ ->
               out_err_tick Authorization "Must be in format Origin/Folder"
        end
        | c -> out_err_tick Authorization "Unknown command"
      )
  | Transaction (origin,folder) as st -> 
      logmod "POP3" "state: transaction %s" folder;
      (* handle common commands like quit/noop for this state *)
      let rec inp_trans_cmd fn =
        inp_cmd (fun arg -> function
          | "quit" ->
              out_ok_tick Update "Personal Container signing off"
          | "noop" ->
              out_ok "" >> inp_trans_cmd fn
          | c -> fn arg c
        ) in
      let e_origin = Some (`Eq origin) in
      let e_folder = match folder with "" -> None | x -> Some (`Eq x) in
      let msgs () = SingleDB.with_db (OD.e_get ?e_origin ?e_folder) in
      let e_size e =
        try Int64.of_string (List.assoc "raw_size" e.O.e_meta)
        with Not_found -> 0L in
      let e_id s = SingleDB.with_db (fun db -> OD.e_id db s) in
      let bytestuff l = if String.length l > 0 && (l.[0] = '.') then "." ^ l else l in
      let with_msg sid fn =
        let id = try Some (`Id (Int64.of_string sid)) with Not_found -> Some (`Id (-1L)) in
        match SingleDB.with_db (OD.e_get ?id) with
        |[m] -> fn m (* (try_lwt fn m with _ -> out_err_tick st "error processing message") *)
        |_ -> out_err_tick st "unknown message id"
      in
      inp_trans_cmd (fun arg -> function
        | "stat" ->
            let ml = msgs () in
            let size = List.fold_left (fun a b -> Int64.add a (e_size b)) 0L ml in
            let num = List.length ml in (* TODO: custom fun to only get size? *)
            out_ok_tick st (sprintf "%d %Lu" num size)
        | "list" -> begin
            match arg with
            | "" ->  (* list all messages *)
              let ml = msgs () in
              let size = List.fold_left (fun a b -> Int64.add a (e_size b)) 0L ml in
              out_ok (sprintf "%d messages (%Lu octets)" (List.length ml) size) >>
              Lwt_util.iter_serial (fun m ->
                out (sprintf "%Lu %Lu" (e_id m) (e_size m))
              ) ml
              >>
              out_ml_tick st
            | arg ->
              with_msg arg (fun m -> out_ok_tick st (sprintf "%s %Lu" arg (e_size m)))
        end
        | "retr" ->
            with_msg arg (fun m ->
              let raw_uuid = List.assoc "raw" m.O.e_meta in
              let fname = Filename.concat (Config.Dir.att ()) (Crypto.Uid.hash raw_uuid) in
              let size = e_size m in
              out_ok (sprintf "%Lu octets" size) >>
              Lwt_stream.iter_s (fun l -> out (bytestuff l)) 
                (Lwt_io.lines_of_file fname)
            ) >>
            out_ml_tick st
        | "top" -> begin
            match Pcre.split ~pat:" " ~max:2 arg with
            | [sid; top] ->
                with_msg sid (fun m ->
                  let top = int_of_string top in
                  let linenum = ref 0 in
                  let headers = ref true in
                  let raw_uuid = List.assoc "raw" m.O.e_meta in
                  let fname = Filename.concat (Config.Dir.att ()) (Crypto.Uid.hash raw_uuid) in
                  Lwt_io.with_file ~mode:Lwt_io.input fname
                    (fun ic ->
                      let rec fn () =
                        lwt line = Lwt_io.read_line_opt ic in
                        match line with
                        |None -> return ()
                        |Some l -> begin
                          match !headers, l with
                          | true, "" -> (* end of headers *)
                             headers := false;
                             out "" >>= fn
                          | true, _ ->  (* still in headers *)
                             out (bytestuff l) >>= fn
                          | false, _ -> (* in body *)
                             incr linenum;
                             if !linenum > top then 
                               return ()
                             else
                               out (bytestuff l) >>= fn
                         end
                      in fn ()
                  )
                ) >>
                out_ml_tick st
            | _ -> 
                out_err_tick st "bad arguments"
        end
        | c -> out_err_tick st "Unknown command"
      )
  | Update -> return ()

let t ~auth ic oc =
  logmod "POP3" "pop3_protocol.t";
  tick ~auth ic oc Greeting
