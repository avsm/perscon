# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

import django
from django import http
from django import shortcuts

from django.utils import simplejson as json
from datetime import datetime
import time, string
import fmi
import passwd
import woeid

class DictProperty(db.Property):
  data_type = dict

  def get_value_for_datastore(self, model_instance):
    value = super(DictProperty, self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return dict()
    return pickle.loads(value)

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

class Person(db.Model):
  first_name = db.StringProperty()
  last_name  = db.StringProperty()
  origin = db.StringProperty()
  created = db.DateTimeProperty(required=True)
  modified = db.DateTimeProperty(auto_now=True)
  services = db.ListProperty(db.IM)
  
  def todict(self):
    return { 'first_name': self.first_name, 'last_name': self.last_name }

  def tojson(self):
    return json.dumps(self.todict(), indent=2)

class Att(db.Model):
  mime = db.StringProperty(default="application/octet-stream")
  body = db.BlobProperty()
  
def att(request, uid):
  meth = request.method
  if meth == 'POST':
      mime = request.META.get('CONTENT_TYPE', None)
      a = Att.get_or_insert(uid, mime=mime, body=request.raw_post_data)
      return http.HttpResponse("ok", mimetype="text/plain")
  elif meth == 'GET':
      a = Att.get_by_key_name(uid)
      if a:         
          return http.HttpResponse(a.body, mimetype=a.mime)
      else:
          return http.HttpResponseNotFound("not found", mimetype="text/plain")
  return http.HttpResponseServerError("not implemented")
      
def person(request, uid):
  meth = request.method
  if meth == 'POST':
      j = json.loads(request.raw_post_data)
      created = datetime.fromtimestamp(float(j['mtime']))
      services = map(lambda x: db.IM(x[0], address=x[1]), j['services'])
      p = Person.get_or_insert(uid, 
                 first_name = j.get('first_name', None), 
                 last_name = j.get('last_name', None), 
                 origin = j.get('origin', None),
                 services = services,
                 created = created)
      return http.HttpResponse("ok", mimetype="text/plain")
  elif meth == 'GET':
      p = Person.get_by_key_name(uid)
      if p:
         return http.HttpResponse(p.tojson(), mimetype="text/plain")
      else:
         return http.HttpResponseNotFound("not found", mimetype="text/plain")
  return http.HttpResponseServerError("not implemented")

def person_keys(request):
  ps = Person.all(keys_only=True).fetch(1000)
  p = json.dumps(map(lambda x: x.name(), ps), indent=2)
  return http.HttpResponse(p, mimetype="text/plain")
  
def fmi_cron(request):
  resp = fmi.poll()
  if resp:
      loc = db.GeoPt(resp['lat'], resp['lon'])
      wid = woeid.resolve_latlon(loc.lat, loc.lon)
      acc = resp.get('accuracy', None)
      if acc:
         acc = float(acc)
      ctime = datetime.fromtimestamp(float(resp['date']))
      l = Location(loc=loc, date=ctime, accuracy=acc, url='http://me.com', woeid=wid)
      l.put()
      return http.HttpResponse("ok", mimetype="text/plain")
  else:
      return http.HttpResponseServerError("error", mimetype="text/plain")

def android_update(request):
  resp = json.loads(request.raw_post_data)
  loc = db.GeoPt(resp['lat'], resp['lon'])
  wid = woeid.resolve_latlon(loc.lat, loc.lon)
  acc = resp.get('accuracy', None)
  if acc:
    acc = float(acc)
  ctime = datetime.fromtimestamp(float(resp['date']))
  l = Location(loc=loc, date=ctime, accuracy=acc, url='http://google.com/android', woeid=wid)
  l.put()
  return http.HttpResponse(request.raw_post_data, mimetype="text/plain")

def loc(request):
  query = Location.all()
  recent = query.order('-date').fetch(10)
  j = json.dumps(map(lambda x: x.todict(), recent), indent=2)
  return http.HttpResponse(j, mimetype="text/plain")

def index(request):
  query = Location.all()
  points = query.order('-date').fetch(1000)
  # center on the most recent result
  centerx = points[0].loc.lat
  centery = points[0].loc.lon
  points_js = string.join(map(lambda x: "new GLatLng(%f,%f)" % (x.loc.lat,x.loc.lon), points), ', ')
  p = { 'google_maps_appid': passwd.google_maps_appid, 'centerx':centerx, 'centery':centery, 'points': points_js }
  return shortcuts.render_to_response("map.html", p)
