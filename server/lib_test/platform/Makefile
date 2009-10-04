OCAMLMAKEFILE = OCamlMakefile

ANNOTATE = yes
export ANNOTATE

OCAMLRUNPARAM=b
export OCAMLRUNPARAM

SOURCES=platform_macos.ml platform_macos_test.ml
THREADS=yes
RESULT=mactest
PACKS=lwt lwt.extra

.PHONY: all
all: dnc
	@ :

include $(OCAMLMAKEFILE)
