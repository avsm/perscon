val init : string -> unit
module Dir :
  sig
    val db : unit -> string
    val log : unit -> string
    val static : unit -> string
    val etc : unit -> string
    val port : unit -> int
  end

module User :
  sig
    val root : unit -> string
  end
