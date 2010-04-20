module Config = struct
  type c = {
    db_directory: string;
    att_directory: string;
    log_directory: string;
    static_directory: string;
    etc_directory: string;
    port: int
  } with json
end
 
module Entry = struct
  type 
    contact = <
      origin: string;
      mtime: float;
      uid: string;
      meta: (string * string) list;
      atts: att list
   >
 and
   svc = <
     ty: string;
     id: string;
     co: string
   >
 and
   att = <
     uid: string;
     mime: string
   >
 and
   e = <
     origin: string;
     mtime: float;
     uid: string;
     frm: svc list;
     eto: svc list;
     meta: (string * string) list;
     folder: string;
     tags: string list;
     atts: att list;
   >
 with 
   json, 
   orm

 type e_query = <
     results: int;
     rows: e list
 > with json

end
