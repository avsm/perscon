OCAMLMAKEFILE = ../../OCamlMakefile

ANNOTATE = yes

SOURCES=test.ml
THREADS=yes
RESULT=test
PACKS=lwt lwt.extra
INCDIRS=../../lib/platform
LIBS=platform

.PHONY: all test
all: dnc
	@ :

test: all
	./$(RESULT)

include $(OCAMLMAKEFILE)
