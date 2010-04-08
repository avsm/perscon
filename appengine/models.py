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

from django.utils import simplejson as json
import time, string
import logging

def Key_to_uid(key):
    return key.name()
  
class DictProperty(db.Property):
    data_type = dict

    def get_value_for_datastore(self, model_instance):
      value = super(DictProperty, self).get_value_for_datastore(model_instance)
      return db.Text(json.dumps(value))

    def make_value_from_datastore(self, value):
      if value is None:
        return dict()
      return json.loads(value)

    def default_value(self):
      if self.default is None:
        return dict()
      else:
        return super(DictProperty, self).default_value().copy()

    def validate(self, value):
      if not isinstance(value, dict):
        raise db.BadValueError('Property %s needs to be convertible to a dict instance (%s) of class dict' % (self.name, value))
      return super(DictProperty, self).validate(value)

    def empty(self, value):
      return value is None

class Location(db.Model):
    loc = db.GeoPtProperty(required=True)
    date = db.DateTimeProperty(required=True)
    accuracy = db.FloatProperty()
    woeid = db.StringProperty()
    url = db.URLProperty()
    speed = db.FloatProperty()

    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)

    def todict (self):
      return { 'lat': self.loc.lat, 'lon': self.loc.lon, 'date': time.mktime(self.date.timetuple()), 'woeid': self.woeid }

    # query the best location fit for this date/time
    @staticmethod
    def nearest_location_at_time(date):
        # just assume a 6 minute window, until we have a quadtree location store
        q = Location.gql("WHERE date < :1 ORDER BY date DESC LIMIT 1", date)
        res = q.fetch(1)
        if len(res) == 0:
            return None
        else:
            return res[0].loc
        
class Att(db.Model):
    mime = db.StringProperty(default="application/octet-stream")
    body = db.BlobProperty()
  
class Person(db.Model):
    first_name = db.StringProperty()
    last_name  = db.StringProperty()
    origin = db.StringProperty()
    created = db.DateTimeProperty(required=True)
    modified = db.DateTimeProperty(auto_now=True)
    services = db.ListProperty(db.IM)
    atts = db.ListProperty(db.Key)
  
    def todict(self):
      return { 'uid': self.key().name(), 'first_name': self.first_name, 
         'last_name': self.last_name, 'modified': time.mktime(self.modified.timetuple()), 
         'atts': map(lambda x: x.name(), self.atts),
         'services': map(lambda x: (x.protocol, x.address), self.services) }

    def tojson(self):
      return json.dumps(self.todict(), indent=2)

    @staticmethod
    def from_service(svc):
        q = Person.gql("WHERE services = :1 LIMIT 1", svc)
        res = q.fetch(1)
        if len(res) == 0:
            return None
        else:
            return res[0]

def IM_to_uid(im):
    p = Person.from_service(im)
    if p: p = p.todict()
    return (im.protocol, im.address, p)

class Message(db.Model):
    origin = db.StringProperty(required=True)
    frm = db.ListProperty(db.IM)
    to  = db.ListProperty(db.IM)
    atts = db.ListProperty(db.Key)
    created = db.DateTimeProperty(required=True)
    meta = DictProperty()
    modified = db.DateTimeProperty(auto_now=True)

    def todict(self):
      return { 'origin': self.origin,
               'frm': map(IM_to_uid, self.frm),
               'to':  map(IM_to_uid, self.to),
               'atts' : map(Key_to_uid, self.atts),
               'uid' : self.key().name(),
               'modified': time.mktime(self.modified.timetuple()),
               'created': time.mktime(self.created.timetuple()),
             }
           
    def tojson(self):
      return json.dumps(self.todict(), indent=2)
   
class Sync(db.Model):
    service = db.StringProperty(required=True)
    username = db.StringProperty()
    status = DictProperty()

    @staticmethod
    def of_service(service, username):
        s = Sync.all().filter('service =',service).filter('username =', username).get()
        if not s:
            s = Sync(service=service, username=username, status={})
            s.put()
        return s
