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

import logging

from google.appengine.ext import db, webapp
from django.utils import simplejson as json

from perscon.models import Person, Service

SERVICES = {
  'aim' : 'http://aim.com',
  'icq' : 'http://icq.com',
  'jabber' : 'xmpp',
  'msn' : 'http://messenger.msn.com',
  'yahoo' : 'http://messenger.yahoo.com',
}

class Sync(webapp.RequestHandler):
    def post(self, client_id):
        np = json.loads(self.request.body)
        set = np.get('set', None)
        if set:
            entity = set['com.apple.syncservices.RecordEntityName']
            uid = np['uid']
            if entity == 'com.apple.contacts.Contact':
                p = Person.find_or_create(uid)
                if set.get('first name',None):
                    p.first_name = set['first name']
                if set.get('last name',None):
                    p.last_name = set['last name']
                p.put()
            else:
                svc = None
                if entity == 'com.apple.contacts.Email Address':
                    email = Service.normalize_email(set['value'])
                    svc = Service.find_or_create('email', db.Email(email), key_name=uid)
                    svc.context = set['type']
                    svc.put()
                elif entity == 'com.apple.contacts.Phone Number':
                    phone = Service.normalize_phone(set['value'])
                    svc = Service.find_or_create('phone', db.PhoneNumber(phone), key_name=uid)
                    svc.context = set['type']
                    svc.put()
                elif entity == 'com.apple.contacts.IM':
                    im = db.IM(SERVICES[set['service']], address=set['user'])
                    svc = Service.find_or_create('im', im, key_name=uid)
                    svc.context = set['type']
                    svc.put()
                elif entity == 'com.apple.contacts.URL':
                    url = set['value']
                    svc = Service.find_or_create('url', url, key_name=uid)
                    if set['type'] == 'other':
                        svc.context = set['label']
                    else:
                        svc.context = set['type']
                    svc.put()
                p = Person.find_or_create(set['contact'])
                if not (svc.key() in p.services):
                    p.services.append(svc.key())
                    svc.person = p
                    svc.put()
                    p.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("ok")
