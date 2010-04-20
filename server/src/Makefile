OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=password
INCDIRS=$(PERSCON_LIBS:%=../lib/%)

SOURCES=log.ml config.ml crypto.ml schema.ml dispatch.ml perscon.ml 

PACKS=pcre unix lwt lwt.unix orm shelf.json cryptokit cohttp cohttpserver
PACKS+=lwt.syntax shelf.syntax

RESULT=perscon
PREDS=camlp4o

ANNOTATE=yes
.PHONY: all
all: dnc
	@ :

-include $(OCAMLMAKEFILE)
