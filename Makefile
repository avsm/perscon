.PHONY: all run scan clean

# build everything
all: 
	cd support && $(MAKE) all

# run server
run:
	cd perscon && /usr/bin/python main.py

# run plugins, once each
scan:
	cd plugins && $(MAKE) run

clean:
	cd support && $(MAKE) clean
