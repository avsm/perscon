OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=platform schema password

SOURCES=config.ml perscon.ml
THREADS=yes
PACKS=pcre lwt lwt.extra orm cryptokit json-static
RESULT=perscon
INCDIRS=$(PERSCON_LIBS:%=../lib/%)
LIBS=platform schema
ANNOTATE=yes

.PHONY: all
all: nc
	@ :

-include $(OCAMLMAKEFILE)
