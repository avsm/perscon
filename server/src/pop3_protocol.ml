(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Lwt
open Log

type state =
  | Greeting
  | Authorization
  | Transaction of string (* folder name *)
  | Update

exception Not_implemented
exception Connection_done
exception Unknown_cmd of string

let tick ~auth ic oc =
  (* helper input/output functions *)
  let out b = Lwt_io.write_line oc b in
  let out_ok b = out ("+OK " ^ b) in
  let out_err b = out ("-ERR " ^ b) in
  let inp () = Lwt_io.read_line ic in
  let inp_cmd fn =
    lwt l = inp () in
    match Pcre.split ~pat:" " ~max:2 l with
    | [cmd; rest] -> fn rest (String.lowercase cmd)
    | [cmd] -> fn "" (String.lowercase cmd)
    | _ -> fail (Unknown_cmd l) in
  let unknown c = fail (Unknown_cmd c) in
  (* pattern match the protocol based on state *)
  function
  | Greeting ->
      out_ok "Personal Container POP3 ready" >>
      return Authorization
  | Authorization ->
      (* handle common commands like quit/noop *)
      let rec inp_auth_cmd fn =

        inp_cmd (fun args -> function
          | "quit" ->
              out_ok "Personal Container signing off" >>
              return Update
          | "noop" ->
              out_ok "" >>
              inp_auth_cmd fn
         |  other ->
              fn args other
        ) in

      inp_auth_cmd (fun arg1 -> function
        | "user" ->
            out_ok "" >>
            inp_auth_cmd (fun arg2 -> function
              |"pass" ->
                 if auth ~user:arg1 ~pass:arg2 then begin
                   out_ok "success" >> return (Transaction arg1)
                 end else begin
                   out_err "denied" >> return Authorization
                 end
             | c -> unknown c
            )
        | c -> unknown c
      )
  | Transaction folder -> 
      logmod "POP3" "state: transaction %s" folder;
      fail Not_implemented
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
        Lwt_io.write_line oc "-ERR Not implemented yet, sorry!" >>
        return Update
    | Unknown_cmd c ->
        Lwt_io.write_line oc "-ERR Unknown command, aborting connection" >>
        return Update
    | e -> fail e
  in
  loop Greeting >>= fun _ ->
  return ()
