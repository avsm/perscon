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
  | Transaction of string * string * int64 list (* origin * folder name * deleted msgs *)
  | Update of int64 list

exception Not_implemented

let rec tick ~auth ic oc =
  (* helper input/output functions *)
  let out b       = Lwt_io.write oc (b ^ "\r\n") in
  let out_ok b    = out ("+OK " ^ b) in
  let out_err b   = out ("-ERR " ^ b) in
  let continue st = tick ~auth ic oc st in
  (* tick to advance state after output *)
  let out_ok_tick st b  = out_ok b >> continue st in
  let out_ml_tick st    = out "." >> continue st in
  let out_err_tick st b = out_err b >> continue st in
  (* input cmd and split it, and call callback fn *)
  let rec inp_cmd fn =
    lwt l = Lwt_io.read_line ic in
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
          | "quit" -> out_ok_tick (Update []) "Personal Container signing off"
          |  other -> fn args other
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
                       out_ok_tick (Transaction (origin,folder,[])) "Success"
                     else
                       out_err_tick Authorization "Denied"
                 | c -> out_err_tick Authorization "only PASS valid here; relogin with USER"
               )
           | _ ->
               out_err_tick Authorization "Must be in format Origin/Folder"
        end
        | c -> out_err_tick Authorization "Unknown command"
      )
  | Transaction (origin,folder,del) as st -> 
      logmod "POP3" "state: transaction %s" folder;
      (* handle common commands like quit/noop for this state *)
      let rec inp_trans_cmd fn =
        inp_cmd (fun arg -> function
          | "quit" ->
              out_ok_tick (Update del) "Personal Container signing off"
          | "noop" ->
              out_ok "" >> inp_trans_cmd fn
          | c -> fn arg c
        ) in
      (* parameters for searching the db *)
      let e_origin = Some (`Eq origin) in
      let e_folder = match folder with "" -> None | x -> Some (`Eq x) in
      let e_size e = try Int64.of_string (List.assoc "raw_size" e.O.e_meta) with Not_found -> 0L in
      let e_id s = SingleDB.with_db (fun db -> OD.e_id db s) in
      (* get all messages; TODO will be replaced by a more efficient custom function *)
      let msgs () = SingleDB.with_db (OD.e_get ?e_origin ?e_folder) in
      (* pad lines going out with . if appropriate *)
      let bytestuff l = if String.length l > 0 && (l.[0] = '.') then "." ^ l else l in
      (* retrieve a message and apply fn over it, or transmit error *)
      let with_msg sid fn =
        let uid = try Int64.of_string sid with _ -> (-1L) in
        match SingleDB.with_db (OD.e_get ~id:(`Id uid)) with
        |[m] -> fn m uid (* (try_lwt fn m with _ -> out_err_tick st "error processing message") *)
        |_ -> out_err_tick st "unknown message id" in
      (* check if a msg is in the deleted list *)
      let is_del id = List.mem id del in
      let unless_del id fn = 
        if is_del id then return () else fn id in
      (* begin processing command *)
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
                unless_del (e_id m) (fun id -> out (sprintf "%Lu %Lu" id (e_size m)))
              ) ml >>
              out_ml_tick st
            | arg ->
              with_msg arg (fun m _ -> out_ok_tick st (sprintf "%s %Lu" arg (e_size m)))
        end
        | "uidl" -> begin
            match arg with
            | "" -> (* list add UIDs *)
              let ml = msgs () in
              out_ok "" >>
              Lwt_util.iter_serial (fun m ->
                unless_del (e_id m) (fun id -> out (sprintf "%Lu %s" id m.O.e_uid))
              ) ml >> out_ml_tick st
            | arg -> with_msg arg (fun m id -> out_ok_tick st (sprintf "%Lu %s" id m.O.e_uid))
        end
        | "retr" ->
            with_msg arg (fun m id ->
              if is_del id then
                out_err_tick st "message deleted"
              else begin
                let raw_uuid = List.assoc "raw" m.O.e_meta in
                let fname = Filename.concat (Config.Dir.att ()) (Crypto.Uid.hash raw_uuid) in
                let size = e_size m in
                out_ok (sprintf "%Lu octets" size) >>
                Lwt_stream.iter_s (fun l -> out (bytestuff l)) (Lwt_io.lines_of_file fname) >>
                out_ml_tick st
              end )
        | "dele" ->
           with_msg arg (fun m id ->
             if is_del id then
               out_err_tick st "message already deleted"
             else
               out_ok_tick (Transaction (origin,folder,id::del)) "message deleted"
           )
        | "rset" ->
            out_ok_tick (Transaction (origin,folder,[])) (sprintf "%d messages undeleted" (List.length del))
        | "top" -> begin
            match Pcre.split ~pat:" " ~max:2 arg with
            | [sid; top] ->
              with_msg sid (fun m id ->
                if is_del id then 
                   out_err_tick st "message deleted" 
                else begin
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
                        |None -> return () (* done with file *)
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
                end
              ) >>
              out_ml_tick st
            | _ -> 
                out_err_tick st "bad arguments"
        end
        | c -> out_err_tick st "Unknown command"
      )
  | Update del ->
      let del' = ref 0 in
      SingleDB.with_db (fun db ->
        List.iter (fun id ->
           match OD.e_get ~id:(`Id id) db with
           |[m] -> OD.e_delete db m; incr del'
           |_ -> ()
        ) del
      );
      if !del' = (List.length del) then
        out_ok (sprintf "%d messages deleted. bye!" (List.length del))
      else
        out_err (sprintf "%d deleted out of %d requested. bye!" !del' (List.length del))

let t ~auth ic oc =
  logmod "POP3" "pop3_protocol.t";
  tick ~auth ic oc Greeting
