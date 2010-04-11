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
from models import Person,Service
import logging

def crud(req, client_id):
    if req.method == 'POST':
       np = json.loads(req.raw_post_data)
       set = np.get('set', None)
       logging.info(set)
       if set:
           entity=set['com.apple.syncservices.RecordEntityName']
           uid=np['uid']
           if entity == 'com.apple.contacts.Contact':
                p = Person.find_or_create(uid)
                if set.get('first name',None):
                   p.first_name = set['first name']
                if set.get('last name',None):
                   p.last_name = set['last name']
                p.put()
           elif entity == 'com.apple.contacts.Email Address':
                svc = Service.get_by_key_name(uid)
                if not svc:
                    svc = Service(ty="email")
                svc.context = set['type']
                svc.email = set['value']
                svc.put()
                cuid=set['contact']
                p = Person.find_or_create(cuid)
                if not (svc.key() in p.services):
                    p.services.append(svc.key())
                    p.put()
           elif entity == 'com.apple.contacts.Phone Number':
                svc = Service.get_by_key_name(uid)
                if not svc:
                    svc = Service(ty="phone")
                svc.context = set['type']
                svc.phone = set['value']
                svc.put()
                cuid=set['contact']
                p = Person.find_or_create(cuid)
                if not (svc.key() in p.services):
                    p.services.append(svc.key())
                    p.put()
                logging.info(p.services)
#           else:
#                logging.info(set)
       return http.HttpResponse("ok", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")
