(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Platform
open Printf
open Lwt

let _ =
   Lwt_main.run (
   lwt p = set_pass ~user:"floozie" ~pass:"wibbles" in
   (if p then
       printf "set_password: true\n"
   else
       printf "set_password: FAIL\n");
   lwt r = get_pass ~user:"floozie" in
   ( match r with
   |Some x -> printf "get_password: %s\n" x
   |None -> printf "get_password: FAIL\n");
   print_endline "done";
   return 0)
   
