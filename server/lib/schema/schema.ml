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
      c_origin: string;
      mutable c_mtime: float;
      c_uid: string;
      mutable c_meta: (string * string) list
   }
 and
   svc = {
     s_ty: string;
     s_id: string;
     s_co: string option
   }
 and
   e = {
     source: string;
     mtime: float;
     uid: string;
     _from: svc list;
     _to: svc list;
     meta: (string * string) list;
   }
 with 
   json, 
   orm ( debug: all; 
         dot: "schema.dot"; 
         unique: contact<c_uid>, e<uid>, svc<s_ty,s_id> )

end
