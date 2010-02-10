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

import getopt, sys, socket, os, ssl
from SocketServer import BaseServer, ForkingMixIn
from BaseHTTPServer import HTTPServer

import config, db
from perscon import PersconHandler

SSLKeyfile = "perscon.pem"

## from http://code.activestate.com/recipes/442473/ but using base ssl
class SecureHTTPServer(ForkingMixIn, HTTPServer):
    def __init__(self, server_address, HandlerClass):
        BaseServer.__init__(self, server_address, HandlerClass)

        self.socket = ssl.wrap_socket(
            socket.socket(self.address_family, self.socket_type), 
            certfile=SSLKeyfile, keyfile=SSLKeyfile, ssl_version=ssl.PROTOCOL_SSLv23,
            server_side=True, suppress_ragged_eofs=False
            )
        self.server_bind()
        self.server_activate()

def usage():
    print "Usage: %s [-c <config>]" % sys.argv[0]
    sys.exit(2)

def main():
    try: opts, args = getopt.getopt(
        sys.argv[1:], "hsc:", ["help", "secure", "config="])
    except getopt.GetoptError, err:
        print str(err)
        usage()
    
    configfile = "perscon.conf"
    https = False
    for o, a in opts:
        if o in ("-c", "--config"): configfile = a
        elif o in ("-s", "--secure"): https = True
        elif o in ("-h", "--help"): usage()
        else: usage()

    config.parse(configfile)
    db.open()
    port = config.port()
    
    print "Listening on port %d" % port
    if https: server = SecureHTTPServer(('', port), PersconHandler)
    else: server = HTTPServer(('', port), PersconHandler)
    
    server.serve_forever()

if __name__ == '__main__': main()
