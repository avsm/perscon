OCAMLMAKEFILE=../OCamlMakefile

SOURCES=config.ml perscon.ml
THREADS=yes
PACKS=pcre lwt lwt.extra orm json-static
RESULT=perscon
INCDIRS=../lib/platform ../lib/schema
LIBS=platform schema
ANNOTATE=yes

.PHONY: all
all: nc
	@ :

-include $(OCAMLMAKEFILE)
