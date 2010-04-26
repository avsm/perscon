OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=password
INCDIRS=$(PERSCON_LIBS:%=../lib/%)

SOURCES=log.ml config.ml crypto.ml schema.ml dispatch.ml perscon.ml 

PACKS=pcre unix lwt lwt.unix dyntype shelf.json cryptokit cohttp cohttpserver otoky
PACKS+=lwt.syntax shelf.syntax type_desc.syntax 

RESULT=perscon
PREDS=camlp4o

ANNOTATE=yes
.PHONY: all
all: dnc
	@ :

-include $(OCAMLMAKEFILE)
