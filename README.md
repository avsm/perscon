Personal container
==================

Only works on Google AppEngine at the moment, with an OCaml version in-development.
Please see http://perscon.net for more information.

TODO list
---------

Items currently assigned indicated by github ID in **bold**.

### App Engine

- web UI currently only fetches the first 1000 messages
- **mort** finish sync/twitter (fix start, add stop)
- **avsm** shift location WOEID resolution to be async to improve reliability if Flickr is unavailable (iterate over WOEID entries that are blank, try to resolve and fill in)
- threading + extjs paging is broken due to result set being inaccurate
    
### Plugins

- add skip-ahead to eg., Adium:sync.py
- robustify eg., Adium:sync.py to things like CONNRESET
- resurrect Skype plugin
- **mort** add Google Contacts plugin

