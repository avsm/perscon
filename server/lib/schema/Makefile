OCAMLMAKEFILE=../../OCamlMakefile

SOURCES=schema.ml 
PACKS=orm json-static
RESULT=schema
ANNOTATE=yes

.PHONY: all
all: dcl dncl
	@ :

.PHONY: debug
debug:
	camlp4orf `ocamlfind query -i-format type-conv orm json-static` pa_type_conv.cmo pa_json_tc.cmo pa_orm.cma schema.ml

-include $(OCAMLMAKEFILE)
