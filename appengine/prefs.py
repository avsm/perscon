# Copyright (c) 2010 Anil Madhavapeddy <anil@recoil.org>
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

from google.appengine.ext import db
import django
from django import http
from django import shortcuts
from django.utils import simplejson as json
import logging

class Prefs(db.Model):
    firstName = db.StringProperty()
    lastName = db.StringProperty()
    email = db.StringProperty()
    passphrase = db.StringProperty()

    def to_dict(self):
        return { 'firstName':self.firstName, 'lastName':self.lastName, 'email':self.email}

    def to_json(self): 
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def null_json():
        return json.dumps({'firstName':None, 'lastName':None, 'email':None})

def crud(req):
    meth = req.method
    if meth == 'GET':
        p = Prefs.all().get()
        if p:
           return http.HttpResponse(p.to_json(), mimetype="text/plain")
        else:
           return http.HttpResponse(Prefs.null_json(), mimetype="text/plain")
    elif meth == 'POST':
       np = json.loads(req.raw_post_data)
       logging.info(np)
       p = Prefs.all().get()
       if not p:
           p = Prefs()
       npFN = np.get('firstName', None)
       npLN = np.get('lastName', None)
       npEM = np.get('email', None)
       npPP = np.get('passphrase', None)
       if npFN: p.firstName = npFN
       if npLN: p.lastName = npLN
       if npEM: p.email = npEM
       if npPP: p.passphrase = npPP
       p.put()
       return http.HttpResponse("ok", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")
