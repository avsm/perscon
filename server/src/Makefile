OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=platform schema password

SOURCES=log.ml config.ml perscon.ml
THREADS=yes
PACKS=pcre lwt lwt.extra orm cryptokit json-static ANSITerminal
RESULT=perscon
INCDIRS=$(PERSCON_LIBS:%=../lib/%)
LIBS=platform schema
ANNOTATE=yes

.PHONY: all
all: nc
	@ :

-include $(OCAMLMAKEFILE)
