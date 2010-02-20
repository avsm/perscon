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
