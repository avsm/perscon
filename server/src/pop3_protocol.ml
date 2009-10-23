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
exception Connection_done
exception Unknown_cmd of string

let tick ~auth ic oc =
  (* helper input/output functions *)
  let out b = 
    logmod "Debug" "Out: %s" b;
    Lwt_io.write_line oc b in
  let out_ok b = out ("+OK " ^ b) in
  let out_ok_tick st b = out_ok b >> return st in
  let out_ml_tick st = out "." >> return st in
  let out_err b = out ("-ERR " ^ b) in
  let out_err_tick st b = out_err b >> return st in
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
              out_ok "Personal Container signing off" >>
              return Update
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

      inp_trans_cmd (fun arg -> function
        | "stat" ->
            SingleDB.with_db (fun db ->
              let ml = msgs () in
              let size = List.fold_left (fun a b -> Int64.add a (e_size b)) 0L ml in
              let num = List.length ml in (* TODO: custom fun to only get size? *)
              out_ok_tick st (sprintf "%d %Lu" num size)
            )
        | "list" -> begin
            match arg with
            |"" ->  (* list all messages *)
              let ml = msgs () in
              let size = List.fold_left (fun a b -> Int64.add a (e_size b)) 0L ml in
              out_ok (sprintf "%d messages (%Lu octets)" (List.length ml) size) >>
              SingleDB.with_db (fun db ->
                Lwt_util.iter_serial (fun m ->
                  out (sprintf "%Lu %Lu" (OD.e_id db m) (e_size m))
                ) ml
              ) >>
              out_ml_tick st
            |arg ->
              let id = Int64.of_string arg in
              SingleDB.with_db (fun db ->       
                match OD.e_get ?e_origin ?e_folder ~id:(`Id id) db with
                | [m] -> 
                    out_ok_tick st (sprintf "%Lu %Lu" id (e_size m))
                | [] ->
                    out_err_tick st "unknown message id"
                | _ -> assert false
              )
        end
        | c -> out_err_tick st "Unknown command"
      )
  | Update ->
      logmod "POP3" "state: update";
      fail Connection_done

let t ~auth ic oc =
  logmod "POP3" "pop3_protocol.t";
  let rec loop s =
    try_lwt 
      lwt s' = tick ~auth ic oc s in
      loop s'
    with 
    | Connection_done ->
        return Update
    | Not_implemented ->
        logmod "POP3" "Not implemented";
        Lwt_io.write_line oc "-ERR Not implemented yet, sorry!" >>
        return Update
    | Unknown_cmd c ->
        Lwt_io.write_line oc "-ERR Unknown command, aborting connection" >>
        return Update
    | e -> fail e
  in
  loop Greeting >>= fun _ ->
  return ()
