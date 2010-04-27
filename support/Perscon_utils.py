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

import Perscon_config
import cookielib
from pkg_resources import require
require ("simplejson")
import simplejson

class BaseRPC:

  def rpc(self, urifrag, delete=False, args=None, data=None, headers={}):
    if not headers.get('content-type', None):
        headers['content-type'] = 'application/json'
    uri = self.baseuri + urllib.quote(urifrag)
    if args:
        uri += "?" + urllib.urlencode(args)
    if delete:
        meth="DELETE"
    else:
        if data:
            meth="POST"
        else:
            meth="GET"
    print "rpc: %s %s " % (meth, uri)
    req = urllib2.Request(uri, data=data, headers=headers)
    req.get_method = lambda: meth
    tries = 0
    while True:
        tries = tries + 1
        try:
            return urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            print e.fp.read()
            if tries > 3: raise

  def log(self, origin, entry, level='info'):
      l = {'origin':origin, 'entry':entry, 'level':level}
      j = simplejson.dumps(l,indent=2)
      print >> sys.stderr, j
      self.rpc('log', data=j)

  def att(self, uid, body, mime):
    l = len(body)
    r = self.rpc("att/" + uid, data=body, headers={'content-type':mime, 'content-length':l})
    return r

class PersconRPC(BaseRPC):
  def __init__(self):
    self.baseuri = 'http://localhost:5985/'

class AppEngineRPC(BaseRPC):

  def __init__(self):
    self.username = Perscon_config.google_username
    self.password = Perscon_config.google_password
    self.app_name = Perscon_config.app_name
    self.dev_mode = Perscon_config.dev_mode
    self.dev_port = Perscon_config.dev_port
    if self.dev_mode:
        self.baseuri = "http://localhost:%d/" % self.dev_port
    else:
        self.baseuri = "https://%s.appspot.com/" % self.app_name
    self.do_auth()

  def do_auth(self):

    # we use a cookie to authenticate with Google App Engine
    #  by registering a cookie handler here, this will automatically store the 
    #  cookie returned when we use urllib2 to open http://%.appspot.com/_ah/login
    cookiejar = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
    urllib2.install_opener(opener)

    # get an AuthToken from Google accounts or the dev server
    #
    if self.dev_mode:
        continue_uri = 'http://localhost:%d/' % self.dev_port
        authreq_data = urllib.urlencode({'email': 'test@example.com',
                                         'admin': True,
                                         'continue': continue_uri,
                                         'action': 'Login'})
        auth_uri = 'http://localhost:%d/_ah/login?%s' % (self.dev_port, authreq_data)
        auth_req = urllib2.Request(auth_uri, data=authreq_data)
        auth_resp = None
        try:
          auth_resp = urllib2.urlopen(auth_req)
        except:
          pass
    else:
        auth_uri = 'https://www.google.com/accounts/ClientLogin'
        authreq_data = urllib.urlencode({ "Email":   self.username,
                                          "Passwd":  self.password,
                                          "service": "ah",
                                          "source":  self.app_name,
                                          "accountType": "HOSTED_OR_GOOGLE" })
        auth_req = urllib2.Request(auth_uri, data=authreq_data)
        auth_resp = urllib2.urlopen(auth_req)
        auth_resp_body = auth_resp.read()

        # auth response includes several fields - we're interested in the bit after Auth= 
        auth_resp_dict = dict(x.split("=") for x in auth_resp_body.split("\n") if x)
        authtoken = auth_resp_dict["Auth"]

        # get a cookie
        # 
        #  the call to request a cookie will also automatically redirect us to the page that we want to go to
        #  the cookie jar will automatically provide the cookie when we reach the redirected location

        serv_args = {}
        serv_args['continue'] = self.baseuri
        serv_args['auth']     = authtoken

        full_serv_uri = "%s_ah/login?%s" % (self.baseuri, urllib.urlencode(serv_args))

        serv_req = urllib2.Request(full_serv_uri)
        serv_resp = urllib2.urlopen(serv_req)
        return serv_resp

def RPC():
    if Perscon_config.mode == 'perscon': return PersconRPC()
    elif Perscon_config.mode == 'appengine': return AppEngineRPC()
    else:
       import sys
       print "unknown config mode, should be perscon/appengine in Perscon_config.py"
       sys.exit(1)
