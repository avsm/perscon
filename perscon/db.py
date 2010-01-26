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
                                                                                                        
import sqlite3
import config
import os,sys
sys.path.append ("../support")
from pkg_resources import require
require ("storm")
require("simplejson")

from storm.locals import *
import simplejson

store = None

class Person(object):
  __storm_table__ = "person"
  uid = Unicode(primary=True)
  meta = Unicode()

  def __init__(self, uid, meta):
    self.uid = uid
    self.meta = simplejson.dumps(meta, ensure_ascii=False)

  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS person (uid TEXT PRIMARY KEY, meta TEXT)", noresult=True)

  def to_json(self):
    return simplejson.dumps({'uid': self.uid, 'meta': simplejson.loads(self.meta)})

  @staticmethod 
  def of_json(p):
    global store
    x = store.get(Person, p['uid'])
    if x:
      x.uid = p['uid']
      x.meta = simplejson.dumps(p['meta'], ensure_ascii=False)
      print "Person update: %s" % p
    else:
      x = Person(uid=p['uid'],meta=p['meta'])
      store.add(x)
      print "Person new: %s" % p
    store.commit()
    return x

  @staticmethod
  def retrieve(uid):
    global store
    return store.get(Person, unicode(uid))

class Service(object):
  __storm_table__ = "service"
  __storm_primary__ = "ty", "id"
  ty = Unicode()
  id = Unicode()
  person_uid = Unicode()
  co = Reference(person_uid, Person.uid)

  def __init__(self, ty, id, co=None):
    self.ty = ty
    self.id = id
    if co:
      self.co = store.get(Person, co)

  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS service (ty TEXT, id TEXT, person_uid INTEGER, PRIMARY KEY(ty, id))")

  @staticmethod
  def of_json(s):
    global store
    x = store.get(Service, (s['ty'], s['id']))
    if x and s['co']:
      x.co = store.get(Person, s['co'])
      print "Service update: %s" % s
    else:
      x = Service(s['ty'], s['id'], s['co'])
      store.add(x)
      print "Service new: %s" % s
    store.commit()
    return x

  @staticmethod
  def retrieve(ty,id):
    global store
    return store.get(Service, (unicode(ty), unicode(id)))

class Att(object):
  __storm_table__ = "att"
  uid = Unicode(primary=True)
  mime = Unicode()
  size = Int()
  body = RawStr()

  def __init__(self, uid, body, mime=u"application/binary"):
    self.uid = uid
    self.size = len(body)
    self.body = body
    self.mime = mime

  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS att (uid TEXT PRIMARY KEY, mime TEXT, size INTEGER, body BLOB)", noresult=True)

  @staticmethod
  def of_json(uid, body, mime):
    global store
    x = store.get(Att, uid)
    if x:
      print "Att exists %s: skipping" % uid
    else:
      x = Att(uid, body, mime)
      store.add(x)
      print "Att new: %s" % uid
    store.commit()
    return x

  @staticmethod
  def retrieve(uid):
    global store
    return store.get(Att, uid)

class ThingAtt(object):
  __storm_table__ = "thing_att"
  __storm_primary__ = "thing_uid", "att_uid"
  thing_uid = Unicode()
  att_uid = Unicode()

  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS thing_att (thing_uid TEXT, att_uid TEXT, PRIMARY KEY(thing_uid, att_uid))", noresult=True)

class ThingTo(object):
  __storm_table__ = "thing_to"
  __storm_primary__ = "thing_uid", "person_uid"
  thing_uid = Unicode()
  person_uid = Unicode()
  
  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS thing_to (thing_uid TEXT, person_uid TEXT, PRIMARY KEY(thing_uid, person_uid))", noresult=True)

class ThingFrom(object):
  __storm_table__ = "thing_from"
  __storm_primary__ = "thing_uid", "person_uid"
  thing_uid = Unicode()
  person_uid = Unicode()
  
  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS thing_from (thing_uid TEXT, person_uid TEXT, PRIMARY KEY(thing_uid, person_uid))", noresult=True)

class Thing(object):
  __storm_table__ = "thing"
  uid = Unicode(primary=True)
  atts = ReferenceSet(uid, ThingAtt.thing_uid, ThingAtt.att_uid, Att.uid)
  frm  = ReferenceSet(uid, ThingFrom.thing_uid, ThingFrom.person_uid, Att.uid)
  to   = ReferenceSet(uid, ThingTo.thing_uid, ThingTo.person_uid, Att.uid)
  meta = Unicode()

  def __init__(self, uid, frm=[], to=[], atts=[]):
    self.uid = uid
    for i in frm:
      self.frm.add(i)
    for i in to:
      self.to.add(i)
    for i in atts:
      self.atts.add(i)

  @staticmethod
  def createTable(store):
    store.execute("CREATE TABLE IF NOT EXISTS thing (uid TEXT)", noresult=True)

def open():
  global store
  database = create_database("sqlite:"+config.db())
  store = Store(database)
  Person.createTable(store)
  Att.createTable(store)
  Thing.createTable(store)
  ThingAtt.createTable(store)
  ThingFrom.createTable(store)
  ThingTo.createTable(store)
  Service.createTable(store)

def test():
  p = Person(u"persuid")
  a = Att(u"attuid", u"attobody")
  b = Att(u"attuid2", u"attobody2")
  t = Thing(u"thinguid", frm=[a,b], to=[b])
  store.add(t)
  store.add(p)
  store.commit()
