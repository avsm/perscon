(*pp camlp4o `ocamlfind query -i-format type-conv orm.syntax json-static` pa_type_conv.cmo pa_orm.cma pa_json_tc.cmo *)


module Config = struct
  type c = {
    db_directory: string;
    log_directory: string;
    static_directory: string;
    etc_directory: string;
    port: int
  } with json
end
 
module Entry = struct
  type 
    contact = {
      first_name: string option;
      last_name: string option;
      abrec: string option;
      uid: string;
   }
 and
   svc = {
     name: string;
     path: string;
     contact: contact option
   }
 and
   meta = {
     k: string;
     v: string
   }
 and
   e = {
     _source: string;
     _timestamp: float;
     _uid: string;
     _from: svc list;
     _to: svc list;
     _meta: meta list;
   }
 with 
   json, 
   orm ( debug: all; 
         dot: "schema.dot"; 
         unique: contact<uid>, e<_uid> )

end
