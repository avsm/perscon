open Printf
open Lwt
open Lwt_process

let set_pass ~user ~pass =
    let cmd = shell (
      sprintf "/usr/bin/security add-generic-password -U -s Perscon -a '%s' -p '%s'"
       (String.escaped user) (String.escaped pass)) in
    lwt status = exec cmd in
    match status with
    | Unix.WEXITED 0 -> return true
    | _ -> return false

let get_pass ~user = 
    let c = sprintf "/usr/bin/security find-generic-password -s Perscon -a '%s' -g 2>&1| grep ^password | sed -e 's/password: \"//' -e 's/\"$//g'"
        (String.escaped user) in 
    let cmd = shell c in
    try_lwt
      lwt password = pread_line cmd in
      return (Some password)
    with _ -> return None
