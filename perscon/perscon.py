# Copyright (C) 2010 Anil Madhavapeddy <anil@recoil.org>
#                                                                                                       
# This program is free software; you can redistribute it and/or modify                                  
# it under the terms of the GNU General Public License as published by                                  
# the Free Software Foundation; either version 2 of the License, or                                     
# (at your option) any later version.                                                                   
#     
# This program is distributed in the hope that it will be useful,                                       
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.                                                          
#                                                                                                       
# You should have received a copy of the GNU General Public License along                               
# with this program; if not, write to the Free Software Foundation, Inc.,                               
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#   

import sys
sys.path.append ("../support")
from pkg_resources import require
require ("simplejson")

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from db import Person,Thing,Att,Service
import simplejson,cgi
import config,perscon

class PersconHandler(BaseHTTPRequestHandler):

  def output_json(self, x):
    if x:
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(x.to_json())
    else:
      self.send_response(404)
      self.end_headers()

  def do_GET(self):
    bits = self.path.split('/')
    x = None
    if bits[1] == "contact":
      self.output_json(Person.retrieve(bits[2]))
    elif bits[1] == "service":
      self.output_json(Service.retrieve(bits[2],bits[3]))
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
     
  def do_POST(self):
    global rootnode
    print "POST %s" % self.path
    bits = self.path.split('/')
    x = None
    if bits[1] == "contact":
      clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
      c = self.rfile.read(int(clen))
      j = simplejson.loads(unicode(c))
      print "POST contact: %s" % j
      x = Person.of_json(j)
    elif bits[1] == 'service':
      clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
      c = self.rfile.read(int(clen))
      j = simplejson.loads(unicode(c))
      print "POST service: %s" % j
      x = Service.of_json(j)
    elif bits[1] == 'att':
      clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
      mime, pdict = cgi.parse_header(self.headers.getheader('content-type'))
      c = self.rfile.read(int(clen))
      print "POST att: %s" % bits[1]
      x = Att.of_json(unicode(bits[2]), c, unicode(mime))
    if x:
      self.send_response(200)
      self.end_headers()
    else:
      self.send_response(500)
      self.end_headers()
