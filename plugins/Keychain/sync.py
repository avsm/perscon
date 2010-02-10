# Copyright (C) 2010 Richard Mortier <mort@cantab.net>
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

import sys, time, os.path, hashlib, ConfigParser

sys.path.append("../../support")
import Perscon_utils
from pkg_resources import require
require("simplejson")
import simplejson as sj
require("keyring")
import keyring

Global_cf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "perscon", "perscon.conf")
Local_cf = "keychain.conf"

def register_credential(svc, usr):
    pwd = keyring.get_password(svc, usr)
    uid = hashlib.sha1("%s:%s" % (svc, usr)).hexdigest()
    data = { 'uid': uid, 'svc': svc, 'usr': usr, 'pwd': pwd, }
    print >>sys.stderr, "register_credential:", svc, usr, uid
    Perscon_utils.rpc("credential/%s" % (uid, ), data=sj.dumps(data, indent=2))

def main():
    gconfig = ConfigParser.ConfigParser()
    gconfig.read(Global_cf)
    uri = "http://localhost:%d/" % (gconfig.getint("network", "port"),)
    Perscon_utils.init_url(uri)

    lconfig = ConfigParser.ConfigParser()
    lconfig.read(Local_cf)

    map(lambda (s,u): register_credential(s,u), lconfig.items("services"))
    
if __name__ == '__main__': main()
