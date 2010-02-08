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
    store.execute("""CREATE TABLE IF NOT EXISTS att (
        uid TEXT PRIMARY KEY,
        mime TEXT,
        size INTEGER,
        body BLOB
        )""", noresult=True)

  @staticmethod
  def insert(uid, body, mime):
    global store
    x = store.get(Att, unicode(uid))
    if x:
      print "Att exists %s: skipping" % uid
    else:
      x = Att(uid, body, mime)
      store.add(x)
      print "Att new: %s" % uid
##     store.commit()
    return x

  @staticmethod
  def retrieve(uid):
    global store
    return store.get(Att, unicode(uid))

class PersonAtt(object):
  __storm_table__ = "person_att"
  __storm_primary__ = "person_uid", "att_uid"
  person_uid = Unicode()
  att_uid = Unicode()

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS person_att (
        person_uid TEXT,
        att_uid TEXT,

        PRIMARY KEY(person_uid, att_uid)
        )""", noresult=True)

class Person(object):
  __storm_table__ = "person"
  uid = Unicode(primary=True)
  meta = Unicode()
  atts = ReferenceSet(uid, PersonAtt.person_uid, PersonAtt.att_uid, Att.uid)

  def __init__(self, uid, meta, atts=[]):
    self.uid = uid
    self.meta = simplejson.dumps(meta, ensure_ascii=False)
    for i in atts:
      a = Att.retrieve(i['uid'])
      self.atts.add(a)

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS person (
        uid TEXT PRIMARY KEY,
        meta TEXT
        )""", noresult=True)

  # convert object to dict
  def to_dict(self):
    attuids = map(lambda x: x.uid, self.atts)
    meta = simplejson.loads(self.meta)
    return {'uid': self.uid, 'meta': meta, 'atts': attuids }

  # convert from dict to object
  @staticmethod 
  def of_dict(p):
    global store
    x = store.get(Person, p['uid'])
    if x:
      x.uid = p['uid']
      x.meta = simplejson.dumps(p['meta'], ensure_ascii=False)
      x.atts = p['atts']
      print "Person update: %s" % p
    else:
      x = Person(uid=p['uid'],meta=p['meta'],atts=p['atts'])
      store.add(x)
      print "Person new: %s" % p
##     store.commit()
    return x

  @staticmethod
  def retrieve(uid):
    global store
    return store.get(Person, unicode(uid))

class Service(object):
  __storm_table__ = "service"
  id = Int(primary=True)
  sty = Unicode()
  sid = Unicode()
  person_uid = Unicode()
  co = Reference(person_uid, Person.uid)

  def __init__(self, sty, sid, co=None):
    self.sty = sty
    self.sid = sid
    if co:
      self.co = store.get(Person, co)

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS service (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sty TEXT,
        sid TEXT,
        person_uid INTEGER
        )""")
    store.execute("CREATE UNIQUE INDEX IF NOT EXISTS service_sty_sid on service (sty, sid)")

  @staticmethod
  def of_dict(s):
    global store
    x = store.find(Service, (Service.sid == s['id']) & (Service.sty == s['ty'])).one()
    if x:
      if s.get('co',None):
        x.co = store.get(Person, s['co'])
        print "Service update: %s" % s
    else:
      x = Service(s['ty'], s['id'], s.get('co',None))
      store.add(x)
      print "Service new: %s" % s
##     store.commit()
    return x

  @staticmethod
  def retrieve(ty,id):
    global store
    return store.get(Service, (unicode(ty), unicode(id)))

  def to_dict(self):
    s = { 'ty' : self.sty, 'id' : self.sid }
    if self.co:
      s['co'] = self.co.uid
    return s

class ThingAtt(object):
  __storm_table__ = "thing_att"
  __storm_primary__ = "thing_uid", "att_uid"
  thing_uid = Unicode()
  att_uid = Unicode()

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS thing_att (
        thing_uid TEXT,
        att_uid TEXT,

        PRIMARY KEY(thing_uid, att_uid)
        )""", noresult=True)

class ThingTo(object):
  __storm_table__ = "thing_to"
  __storm_primary__ = "thing_uid", "service_id"
  thing_uid = Unicode()
  service_id = Int()
  
  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS thing_to (
        thing_uid TEXT,
        service_id INTEGER,

        PRIMARY KEY(thing_uid, service_id)
        )""", noresult=True)

class ThingFrom(object):
  __storm_table__ = "thing_from"
  __storm_primary__ = "thing_uid", "service_id"
  thing_uid = Unicode()
  service_id = Int()
  
  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS thing_from (
        thing_uid TEXT,
        service_id INTEGER,

        PRIMARY KEY(thing_uid, service_id)
        )""", noresult=True)

class Tag(object):
  __storm_table__ = "tag"
  id = Int(primary=True)
  name = Unicode()
 
  def __init__(self, name):
    self.name = name 

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS tag (
        id INTEGER PRIMARY KEY,
        name TEXT
        )""")
    store.execute("CREATE UNIQUE INDEX IF NOT EXISTS tag_name_index on tag (name)")

  @staticmethod
  def update(name):
    global store
    t = store.find(Tag, Tag.name == name).one()
    if not t:
      t = Tag(name)
      store.add(t)
##       store.commit()
    return t

class ThingTag(object):
  __storm_table__ = "thing_tag"
  __storm_primary__ = "tag_id", "thing_uid"
  thing_uid = Unicode()
  tag_id = Int()
  
  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS thing_tag (
        thing_uid TEXT,
        tag_id INTEGER,

        PRIMARY KEY(thing_uid, tag_id)
        )""", noresult=True)

class Thing(object):
  __storm_table__ = "thing"
  uid = Unicode(primary=True)
  atts = ReferenceSet(uid, ThingAtt.thing_uid, ThingAtt.att_uid, Att.uid)
  frm  = ReferenceSet(uid, ThingFrom.thing_uid, ThingFrom.service_id, Service.id)
  to   = ReferenceSet(uid, ThingTo.thing_uid, ThingTo.service_id, Service.id)
  tags = ReferenceSet(uid, ThingTag.thing_uid, ThingTag.tag_id, Tag.id)
  folder = Unicode()
  meta = Unicode()

  def __init__(self, uid, meta, frm=[], to=[], atts=[], tags=[],folder=""):
    self.uid = uid
    for i in frm:
      self.frm.add(i)
    for i in to:
      self.to.add(i)
    for i in atts:
      self.atts.add(i)
    for i in tags:
      self.tags.add(i)
    self.meta = simplejson.dumps(meta, ensure_ascii=False)
    self.folder=folder

  @staticmethod
  def createTable(store):
    store.execute("""CREATE TABLE IF NOT EXISTS thing (
        uid TEXT,
        folder TEXT,
        meta TEXT
        )""", noresult=True)

  @staticmethod
  def of_dict(t):
    global store
    x = store.get(Thing, t['uid'])
    frm = map(lambda f: Service.of_dict(f), t['frm'])
    to = map(lambda f: Service.of_dict(f), t['to'])
    tags = map(lambda f: Tag.update(f), t.get('tags',[]))
    atts = map(lambda a: Att.retrieve(a['uid']), t.get('atts',[]))
    if x:
      print "updating Thing %s" % t['uid']
      x.folder = t.get('folder',u'')
      x.frm = frm
      x.to = to
      x.tags = tags 
      x.atts = atts
      x.meta = simplejson.dumps(t['meta'], ensure_ascii=False) 
    else:
      print "new Thing %s" % t['uid']
      x = Thing(t['uid'], t['meta'], frm=frm, to=to, tags=tags, atts=atts,folder=t.get('folder',u''))
      store.add(x)
##     store.commit()
    return x

  def to_dict(self):
    frm = map(lambda f: Service.to_dict(f), self.frm)
    to = map(lambda f: Service.to_dict(f), self.to)
    tags = map(lambda f: f.name, self.tags)
    atts = map(lambda a: Att.to_dict(a), self.atts)
    meta = simplejson.loads(self.meta)
    return { 'uid': self.uid, 'frm':frm, 'to':to, 'tags':tags, 'atts':atts, 'folder': self.folder, 'meta':meta  }

  @staticmethod
  def retrieve(uid):
    global store
    print "Thing: retrieve %s" % uid
    return store.get(Thing, unicode(uid))

class Credential(object):
    __storm_table__ = "credential"
    uid = Unicode(primary=True)
    svc = Unicode()
    usr = Unicode()
    pwd = Unicode()  
          
    def __init__(self, uid, svc, usr, pwd):
        self.uid = uid
        self.svc = svc
        self.usr = usr
        self.pwd = pwd

    @staticmethod
    def createTable(store):
        store.execute("""CREATE TABLE IF NOT EXISTS credential (
            uid TEXT,
            svc TEXT,
            usr TEXT,
            pwd TEXT
            )""", noresult=True)

    @staticmethod
    def of_dict(d):
        global store
        x = store.get(Credential, d['uid'])
        x.svc = svc
        x.usr = usr
        x.pwd = pwd
        return x

def get_store(): return store

def open():
  global store
  database = create_database("sqlite:"+config.db())
  store = Store(database)
  Person.createTable(store)
  PersonAtt.createTable(store)
  Att.createTable(store)
  Tag.createTable(store)
  Thing.createTable(store)
  ThingAtt.createTable(store)
  ThingFrom.createTable(store)
  ThingTo.createTable(store)
  ThingTag.createTable(store)
  Service.createTable(store)
  Credential.createTable(store)
  store.commit()

def test():
  p = Person(u"persuid")
  a = Att(u"attuid", u"attobody")
  b = Att(u"attuid2", u"attobody2")
  t = Thing(u"thinguid", frm=[a,b], to=[b])
  store.add(t)
  store.add(p)
  store.commit()
