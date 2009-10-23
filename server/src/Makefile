OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=platform schema password

SOURCES=log.ml config.ml crypto.ml db.ml dispatch.ml tcp_server.ml pop3_daemon.ml perscon.ml 
THREADS=yes
PACKS=pcre lwt lwt.extra orm cryptokit json-static ANSITerminal cohttp calendar cryptokit
RESULT=perscon
INCDIRS=$(PERSCON_LIBS:%=../lib/%)
LIBS=platform schema
ANNOTATE=yes

.PHONY: all
all: nc
	@ :

-include $(OCAMLMAKEFILE)
