(* Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License along
   with this program; if not, write to the Free Software Foundation, Inc.,
   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*)

(* Platform-specific implementations of various functions *)
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

