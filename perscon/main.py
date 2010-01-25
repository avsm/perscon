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

import getopt, sys
from perscon import PersconHandler
import config,db
from BaseHTTPServer import HTTPServer


def usage():
  print "Usage: %s [-c <config>]" % sys.argv[0]
  sys.exit(2)

def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:", ["help", "config="])
  except getopt.GetoptError, err:
     print str(err)
     usage()
  configfile = "perscon.conf"
  for o, a in opts:
    if o == "-c":
      configfile = a
    elif o == "-h":
      usage()
 
  config.parse(configfile)
  db.open()
  port = config.port()
  print "Listening on port %d" % port
  server = HTTPServer(('', port), PersconHandler)
  server.serve_forever()

if __name__ == '__main__':
    main()
