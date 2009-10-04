(* Platform-specific implementations of various functions *)
(* XXX broken currently, needs porting to LWT *)
open Printf
open Str
open Utils

let get_passwdfile () =
    let homedir=Sys.getenv "HOME" in
    Printf.sprintf "%s/.lifedb_password" homedir

let set_password username password =
    let passwdfile = get_passwdfile () in
    let fd = Unix.openfile passwdfile [Unix.O_APPEND; Unix.O_CREAT] 0o600 in
    let str = Printf.sprintf "%s %s\n" username password in
    Unix.write fd str 0 (String.length str);
    true

let get_password username = 
    let passwdfile = get_passwdfile () in
    let fh = open_in passwdfile in
    let map = ref [] in
    try_final (fun () ->
      repeat_until_eof (fun () ->
        let line = input_line fh in
        match Str.split (Str.regexp_string " ") line with
        |[username; password] ->
          map := (username,password):: !map
        |_ -> ()
      )
    ) (fun () -> close_in fh);
    try
    Some (List.assoc username !map)
    with _ -> None

