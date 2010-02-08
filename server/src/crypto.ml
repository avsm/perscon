open Cryptokit

module Uid = struct

  let hash x = transform_string (Hexa.encode ()) (hash_string (Hash.sha1 ()) x)

end
