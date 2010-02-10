# Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>
#               2010 Richard Mortier <mort@cantab.net>
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

import sys, urllib2, urllib, commands, hashlib
import config

sys.path.append("../../support")
from pkg_resources import require
require("simplejson")
import simplejson as sj
                       
script = "../scripts/get_passphrase.sh"

localuri = None

def get_perscon_password():
    status, passwd = commands.getstatusoutput(script)
    if status == 0:
        return passwd
    else:
        return ''

def init_url (uri):
    global localuri
    passwd = get_perscon_password ()
    ah = urllib2.HTTPBasicAuthHandler()
    ah.add_password(realm='Personal Container',
                    uri=uri,
                    user='root',
                    passwd=passwd)
    op = urllib2.build_opener(ah)
    urllib2.install_opener(op)
    localuri = uri

def rpc(urifrag, delete=False, args=None, data=None, headers={}):
    if not headers.get('content-type', None):
        headers['content-type'] = 'application/json'
    uri = localuri + urllib.quote(urifrag)
    if args:
        uri += "?" + urllib.urlencode(args)
    print "rpc: " + uri
    if delete:
        meth="DELETE"
    else:
        if data:
            meth="POST"
        else:
            meth="GET"
    req = urllib2.Request(uri, data=data, headers=headers)
    req.get_method = lambda: meth
    return urllib2.urlopen(req)

def get_credentials(service):
    username = config.user(service)
    uid = hashlib.sha1("%s:%s" % (service, username)).hexdigest()
    c = rpc("credential/%s" % (uid,))
    dj = sj.loads(''.join(c.readlines()))
    return (dj['usr'], dj['pwd'])
