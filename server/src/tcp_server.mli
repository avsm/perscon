val build_sockaddr : addr:string -> port:int -> Unix.sockaddr Lwt.t

val t :
  sockaddr:Unix.sockaddr ->
  ?timeout:int ->
  (clisockaddr:Unix.sockaddr ->
   srvsockaddr:Unix.sockaddr ->
   Lwt_io.input Lwt_io.channel -> Lwt_io.output Lwt_io.channel -> unit Lwt.t) ->
  'a Lwt.t
