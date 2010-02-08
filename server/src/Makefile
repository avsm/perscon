OCAMLMAKEFILE=../OCamlMakefile

PERSCON_LIBS=platform schema password
INCDIRS=$(PERSCON_LIBS:%=../lib/%)

SOURCES=log.ml config.ml crypto.ml db.ml dispatch.ml tcp_server.ml \
  render.ml pop3_protocol.ml pop3_daemon.ml perscon.ml 

PACKS=pcre unix lwt lwt.unix orm cryptokit json-tc.syntax ANSITerminal cohttp calendar cryptokit
PACKS+=lwt.syntax

RESULT=perscon
LIBS=platform schema
PREDS=camlp4o


ANNOTATE=yes
.PHONY: all
all: dnc
	@ :

-include $(OCAMLMAKEFILE)
