# Copyright (C) 2010 Anil Madhavapeddy <anil@recoil.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#     
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA.
#   

import sys
sys.path.append ("../support")
from pkg_resources import require
require ("simplejson")

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from db import Person,Thing,Att,Service, get_store
import simplejson,cgi,urllib
import config,perscon

store = None
class PersconHandler(BaseHTTPRequestHandler):

    def output_json(self, x):
        if x:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(simplejson.dumps(x.to_dict(), ensure_ascii=False))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        bits = urllib.unquote(self.path).split('/')
        x = None
        if bits[1] == "people":
            self.output_json(Person.retrieve(bits[2]))
        
        elif bits[1] == "service":
            self.output_json(Service.retrieve(bits[2],bits[3]))
        
        elif bits[1] == "thing":
            self.output_json(Thing.retrieve(bits[2]))
        
        elif bits[1] == "att":
            x = Att.retrieve(bits[2])
            if x:
                self.send_response(200)
                self.send_header('Content-type', x.mime)
                self.send_header('Content-length', x.size)
                self.end_headers()
                self.wfile.write(x.body)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write('404 Not Found')

        elif bits[1] == "credential":
            pass

  def do_POST(self):
      global store
      
      print "POST %s" % self.path
      bits = urllib.unquote(self.path).split('/')
      x = None
      if bits[1] == "people":
          clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
          c = self.rfile.read(int(clen))
          j = simplejson.loads(unicode(c))
          print "POST people: %s" % j
          x = Person.of_dict(j)

      elif bits[1] == 'service':
          clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
          c = self.rfile.read(int(clen))
          j = simplejson.loads(unicode(c))
          print "POST service: %s" % j
          x = Service.of_dict(j)

      elif bits[1] == 'att':
          clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
          mime, pdict = cgi.parse_header(self.headers.getheader('content-type'))
          c = self.rfile.read(int(clen))
          print "POST att: %s" % bits[1]
          x = Att.insert(unicode(bits[2]), c, unicode(mime))

      elif bits[1] == 'thing':
          clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
          c = self.rfile.read(int(clen))
          j = simplejson.loads(unicode(c))
          print "POST thing: %s" % j
          x = Thing.of_dict(j)

      elif bits[1] == 'credential':
          clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
          c = self.rfile.read(int(clen))
          j = simplejson.loads(unicode(c))
          print "POST credential: %s" % j
          x = Credential.of_dict(j)
      
      try: store.commit()
      except:
          store = get_store()
          store.commit()

      if x: self.send_response(200)
      else:
          self.send_response(500)
      
      self.end_headers()
