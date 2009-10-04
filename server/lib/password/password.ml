(* module to manage passwords securely.
   encryption scheme is:
      * pass in a 64-bit time (e.g. when the password was entered by the user) with passwd
      * time is converted to a string and MD5 hashed into a 16-byte string (acts as iv). 
      * passphrase is SHA-256 hashed into a 32-byte string (acts as key).
      * use AES block encryption with CBC (iv/key from above), padding provided
      * result is hex encoded as a string
 *)
open Cryptokit
open Printf

let hash_of_string hfn s =
    let hash = hfn () in
    hash#add_string s;
    let r = hash#result in
    hash#wipe;
    r

(* the AES key is obtained by taking the SHA1 hash of the input passphrase.
   the IV for the CBC is obtained from the SHA1 hash of the string representation
   of the time the password was stored.  this is the "salt" *)
let key_of_passphrase ~time ~passphrase =
    let passhash = hash_of_string Hash.sha256 passphrase in
    let timehash = hash_of_string Hash.md5 (sprintf "%.0f" time) in
    passhash, timehash

(* encrypt the password using the key and AES *)
let encrypt_password ~time ~passphrase ~password =
    try 
      let key, iv = key_of_passphrase time passphrase in
      let hexenc = Hexa.encode () in
      let aes = Cipher.aes ~mode:Cipher.CBC ~pad:Padding.length ~iv:iv key Cipher.Encrypt in
      let t = compose aes hexenc in
      t#put_string password;
      t#finish;
      let r = t#get_string in
      t#wipe;
      Some r
    with Error _ -> None
   
let decrypt_password ~time ~passphrase ~enc_password =
    try 
      let key, iv = key_of_passphrase time passphrase in
      let hexdec = Hexa.decode () in
      let aes = Cipher.aes ~mode:Cipher.CBC ~pad:Padding.length ~iv:iv key Cipher.Decrypt in
      let t = compose hexdec aes in
      t#put_string enc_password;
      t#finish;
      let r = t#get_string in
      t#wipe;
      Some r
    with Error _ -> None
