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
sys.path.append ("support")
from pkg_resources import require
require ("simplejson")

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from db import Person,Thing,Att
import simplejson,cgi
import config,perscon

class PersconHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    bits = self.path.split('/')
    if bits[0] == "contact":
      print "contact"
    if self.path.endswith(".esp"):   #our dynamic content
      self.send_response(200)
      self.send_header('Content-type',    'text/html')
      self.end_headers()
      self.wfile.write("hey, today is the" + str(time.localtime()[7]))
      self.wfile.write(" day in the year " + str(time.localtime()[0]))
      return

  def do_POST(self):
    global rootnode
    print "POST %s" % self.path
    bits = self.path.split('/')
    print bits
    if bits[1] == "contact":
      clen, pdict = cgi.parse_header(self.headers.getheader('content-length'))
      c = self.rfile.read(int(clen))
      j = simplejson.loads(unicode(c))
      print "POST contact: %s" % j
      Person.update(j)
      self.send_response(200)
      self.end_headers()
