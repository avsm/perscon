module AT=ANSITerminal
open Printf

type log_request = [
  |`Module of (string * string)
  |`Debug of string
]

let datetime () =
    let tm = Unix.gmtime (Unix.gettimeofday ()) in
    Printf.sprintf "%.4d/%.2d/%.2d %.2d:%.2d:%.2d"
      (1900+tm.Unix.tm_year) tm.Unix.tm_mon
      tm.Unix.tm_mday tm.Unix.tm_hour tm.Unix.tm_min tm.Unix.tm_sec

let log_request = function
  |`Debug l -> AT.printf [AT.Foreground AT.Cyan] "[%s] %s\n" (datetime ()) l;
  |`Module (m,l) ->
      let col_of_module = function
        |"HTTP" -> AT.Red
        |"POP3" -> AT.Yellow
        |"Debug" -> AT.Cyan
        |"Sync" -> AT.Blue
        |_ -> AT.Magenta in
      AT.printf [AT.Foreground AT.Cyan] "[%s]" (datetime ());
      AT.printf [AT.Foreground (col_of_module m)] "%.10s: " m;
      print_endline l

let logmod m fmt =
  let xfn f = log_request (`Module (m, f)) in
  kprintf xfn fmt

let logdbg fmt =
  let xfn f = log_request (`Debug f) in
  kprintf xfn fmt
