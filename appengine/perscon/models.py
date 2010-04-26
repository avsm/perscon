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

import time, string, datetime, logging
log = logging.info

from google.appengine.ext import db
from google.appengine.ext.db import NotSavedError
from django.utils import simplejson as json

import perscon.support.secret as secret

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
      return { 'lat': self.loc.lat, 'lon': self.loc.lon, 
               'date': time.mktime(self.date.timetuple()), 'woeid': self.woeid }

    # query the best location fit for this date/time
    @staticmethod
    def nearest_location_at_time(date):
        # just pick nearest one until we have a quadtree store
        q = Location.gql("WHERE date < :1 ORDER BY date DESC LIMIT 1", date)
        return q.get()

class Att(db.Model):
    mime = db.StringProperty(default="application/octet-stream")
    body = db.BlobProperty()

    def todict(self):
        return {'key': self.key().name(), 'mimetype': self.mime }

class Person(db.Model):
    first_name = db.StringProperty()
    last_name  = db.StringProperty()
    origin = db.StringProperty()
    created = db.DateTimeProperty()
    modified = db.DateTimeProperty(auto_now=True)
    services = db.ListProperty(db.Key)
    atts = db.ListProperty(db.Key)
    
    def todict(self):
      return {
          'uid': self.key().name(),
          'first_name': self.first_name, 'last_name': self.last_name,
          'modified': time.mktime(self.modified.timetuple()), 
          'atts': map(lambda x: Att.get(x).todict(), self.atts),
          'services': map(lambda x: Service.get(x).todict(), self.services)
          }

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

    @staticmethod
    def find_or_create(key):
        q = Person.get_by_key_name(key)
        if not q:
            q = Person(key_name=key)
        return q
 
class Service(db.Expando):
    ty = db.StringProperty(required=True)
    context = db.StringProperty()
    person = db.ReferenceProperty(Person)

    def todict(self, withPerson=False):
        if self.ty == 'im':
            k = 'proto'
            v = [ self.value.protocol, self.value.address ]
        else:
            k = 'value'
            v = self.value
        if withPerson:
            person = self.person
            if person: person = person.todict()
            return {'ty':self.ty, 'context':self.context, k: v, 'person': person }
        else:
            return {'ty':self.ty, 'context':self.context, k: v}

    @staticmethod
    def ofdict(d,create=True):
        ty = d['ty']
        if ty == 'im': 
            v = db.IM(d['proto'][0], address=d['proto'][1])
        elif ty == 'email':
            v = db.Email(Service.normalize_email(d['value']))
        elif ty == 'url':
            v = d['value']
        elif ty == 'phone':
            v = db.PhoneNumber(Service.normalize_phone(d['value']))
        elif ty == 'postal':
            v = db.PostalAddress(d['value'])
        else:
            v = d['value']
        if create:
            return Service.find_or_create(ty, v)
        else:
            return Service.gql('WHERE ty=:1 AND value=:2 LIMIT 1', ty, v).get()
  
    @staticmethod
    def key_ofdict(d):
        d = Service.ofdict(d)
        try:
            d.key()
        except NotSavedError:
            d.put()
        return d.key()

    @staticmethod
    def ofjson(j):
        return Service.ofdict(simplejson.loads(j))

    @staticmethod
    def normalize_email(e):
        return e.lower()

    @staticmethod
    def normalize_phone(p):
        # XXX only works with UK numbers at the moment -avsm
        import re
        if len(p) < 1: return p
        pn = re.sub('[^0-9|\+]','',p)
        if len(pn) < 1: return pn
        if pn[0:1] == "00" and len(pn) > 2:
            pn = "+%s" % pn[2:]
        elif pn[0]  == '0':
            pn = "+44%s" % pn[1:]
        return pn

    @staticmethod
    def find_or_create(ty, v, key_name=None):
        q = Service.gql('WHERE ty=:1 AND value=:2 LIMIT 1', ty, v).get()
        if not q:
            if key_name:
                q = Service(key_name=key_name, ty=ty, value=v)
            else:
                q = Service(ty=ty,value=v)
        # XXX also need to check for dup services here if one exists already
        # or just implement multiple UIDs -avsm
        return q
    
class Message(db.Model):
    origin = db.StringProperty(required=True)
    frm = db.ListProperty(db.Key)
    tos = db.ListProperty(db.Key)
    atts = db.ListProperty(db.Key)
    created = db.DateTimeProperty(required=True)
    meta = DictProperty()
    modified = db.DateTimeProperty(auto_now=True)
    thread = db.StringProperty()
    thread_count = 0

    def todict(self):
        loc = Location.nearest_location_at_time(self.created)
        return { 'origin': self.origin,
                 'frm': map(lambda x: Service.get(x).todict(withPerson=True), self.frm),
                 'tos': map(lambda x: Service.get(x).todict(withPerson=True), self.tos),
                 'atts' : map(lambda x: Att.get(x).todict(), self.atts),
                 'uid' : self.key().name(),
                 'modified': time.mktime(self.modified.timetuple()),
                 'created': time.mktime(self.created.timetuple()),
                 'loc': loc and loc.todict(),
                 'thread': self.thread,
                 'thread_count': self.thread_count
                 }

    def tojson(self):
        return json.dumps(self.todict(), indent=2)

class SVC_STATUS:
    needauth = 'NEEDAUTH'
    authorized = 'AUTHORIZED'
    
class SYNC_STATUS:
    unsynchronized = 'UNSYNCHRONIZED'
    inprogress = 'INPROGRESS'
    halting = 'HALTING'
    synchronized = 'SYNCHRONIZED'

class SyncService(db.Model):
    svcname = db.StringProperty()
    username = db.StringProperty()
    status = db.StringProperty(default=SVC_STATUS.needauth)
    
    def todict(self):
        return { 'svcname': self.svcname,
                 'username': self.username,
                 'status': self.status,
                 'threads': map(lambda x:x.todict(), self.threads),
                 }
    def tojson(self):
        return json.dumps(self.todict(), indent=2)

    @staticmethod
    def of_service(svcname):
        s = secret.OAuth.all().filter("service =", svcname).get()
        username = s.username if s else None
        status = SVC_STATUS.authorized if s else SVC_STATUS.needauth
        
        ss = db.GqlQuery("SELECT * FROM SyncService WHERE svcname=:s AND username=:u",
                         s=svcname, u=username).get()
        if not ss:
            ss = SyncService(svcname=svcname, username=username, status=status)
        ss.username = username
        ss.status = status
        ss.put()
        return ss
            
def datetime_as_float(dt):
    '''Convert a datetime.datetime into a microsecond-precision float.'''
    return time.mktime(dt.timetuple())+(dt.microsecond/1e6)

class SyncStatus(db.Model):
    service = db.ReferenceProperty(
        SyncService, collection_name="threads", required=True)
    thread = db.StringProperty(required=True)
    status = db.StringProperty(default=SYNC_STATUS.unsynchronized, required=True)
    last_sync = db.DateTimeProperty()

    def todict(self):
        ## hack: mutual recursion ahoy.  bah.
        return { 'service': self.service.key().id_or_name(),
                 'thread': self.thread,
                 'status': self.status,
                 'last_sync': (datetime_as_float(self.last_sync)
                               if self.last_sync else None),
                 }
    def tojson(self):
        return json.dumps(self.todict(), indent=2)

    @staticmethod
    def of_service(service, thread):
        svc = SyncService.of_service(service)
        s = SyncStatus.all().filter('service =', svc).filter('thread =', thread).get()
        if not s:
            s = SyncStatus(service=svc, thread=thread,
                           status=SYNC_STATUS.unsynchronized)
            s.put()
        return s

##     @staticmethod
##     def new_sync(service):
##         s = SyncStatus.all().filter('service =', service).get()
##         if not s: s = SyncStatus(service=service, status=SYNC_STATUS.needauth)
##         else:
##             s.username = None
##             s.service = service
##             s.status = SYNC_STATUS.needauth
##             s.last_sync = None

##         s.put()
##         return s

    def put(self):
        if self.status == SYNC_STATUS.synchronized:
            s = db.GqlQuery("SELECT * FROM SyncStatus WHERE service=:s AND thread=:t",
                            s=self.service, u=self.thread).get()
            if (not s or (s and s.status != self.status)):
                self.last_sync = datetime.datetime.now()
        super(SyncStatus, self).put()

class Prefs(db.Model):
    firstName = db.StringProperty()
    lastName = db.StringProperty()
    email = db.StringProperty()
    passphrase = db.StringProperty()

    def to_dict(self):
        return { 'first_name':self.firstName, 'last_name':self.lastName, 'email':self.email}

    def to_json(self): 
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def null_json():
        return json.dumps({'first_name':None, 'last_name':None, 'email':None})

class LogLevel:
    info  = 'info'
    debug = 'debug'
    error = 'error'

class LogEntry(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    level = db.StringProperty(required=True)
    origin = db.StringProperty()
    entry = db.TextProperty()

    def todict(self):
        return {'created': time.mktime(self.created.timetuple()), 'level':self.level,
                'origin':self.origin, 'entry':self.entry }
