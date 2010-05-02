Personal container
==================

Only works on Google AppEngine at the moment, with an OCaml version in-development.
Please see [http://perscon.net][] for more information.

TODO list for a 0.1 preview release
-----------------------------------

Items currently assigned indicated by github ID in **bold**.

### App Engine

- **avsm** shift location WOEID resolution to be async to improve reliability if Flickr is unavailable (iterate over WOEID entries that are blank, try to resolve and fill in)
- **avsm** threading + extjs paging is broken due to result set being inaccurate
- **avsm** passwd.py.in has to die, and use the passphrase stuff to store plugins
- configurable cron for plugins so that cron.yaml doesnt need editing all the time
- add foursquare plugin
- add gowalla plugin
    
### Plugins

- add skip-ahead to eg., Adium:sync.py
- robustify eg., Adium:sync.py to things like CONNRESET
- **mor1** finish Google Contacts plugin

### Clients

- **ms705** package up Android client

