
open Cryptokit

module Uid = struct

  let hash = hash_string (Hash.sha1 ())

end
