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
  |`Debug l -> printf "[%s] %s\n" (datetime ()) l;
  |`Module (m,l) ->
      printf "[%s]" (datetime ());
      printf "%.10s: " m;
      print_endline l

let logmod m fmt =
  let xfn f = log_request (`Module (m, f)) in
  kprintf xfn fmt

let logdbg fmt =
  let xfn f = log_request (`Debug f) in
  kprintf xfn fmt
