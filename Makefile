.PHONY: all run scan clean

PYTHON=/usr/bin/python

# build everything
all: 
	cd support && $(MAKE) all

# run server
run:
	cd perscon && $(PYTHON) main.py

# run plugins, once each
scan:
	cd plugins && $(MAKE) run

clean:
	cd support && $(MAKE) clean
