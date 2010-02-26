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
from django.utils.html import escape
from django.utils.html import linebreaks
from datetime import datetime
import time, string
import fmi
import passwd
import woeid
import logging

def IM_to_uid(im):
    return (im.protocol, im.address)

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
      return { 'first_name': self.first_name, 'last_name': self.last_name }

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
               'atts' : map(Key_to_uid, self.atts)
             }
           
    def tojson(self):
      return json.dumps(self.todict(), indent=2)
    
def message(request, uid):
    meth = request.method
    logging.info
    if meth == 'POST':
        j = json.loads(request.raw_post_data)
        created = datetime.fromtimestamp(float(j['mtime']))
        frm = map(lambda x: db.IM(x[0], address=x[1]), j['frm'])
        to = map(lambda x: db.IM(x[0], address=x[1]), j['to'])
        atts = filter(None, map(lambda x: Att.get_by_key_name(x), j['atts']))
        meta = j.get('meta',{})
        logging.info(atts)
        atts = map(lambda x: x.key(), atts)
        m = Message.get_or_insert(uid, origin=j['origin'], frm=frm, to=to, atts=atts, created=created, meta=meta)
        return http.HttpResponse("ok", mimetype="text/plain")
    elif meth == 'GET':
        m = Message.get_by_key_name(uid)
        if m:
            return http.HttpResponse(m.tojson(), mimetype='text/plain')
        else:
            return http.HttpResponseNotFound("not found", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")

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
        atts = filter(None, map(lambda x: Att.get_by_key_name(x), j['atts']))
        logging.info(atts)
        atts = map(lambda x: x.key(), atts)
        p = Person.get_or_insert(uid, 
                   first_name = j.get('first_name', None), 
                   last_name = j.get('last_name', None), 
                   origin = j.get('origin', None),
                   services = services,
                   created = created, atts=atts)
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

def msg_person_html(svc):
    p = Person.from_service(svc)
    if p:
        return "%s %s" % (p.first_name, p.last_name)
    else:
        return svc.address
        
n=0
def message_type_to_js(cl, marker, icon, limit=10):
    q = Message.gql("WHERE origin=:1 ORDER BY created DESC LIMIT %d" % limit, cl)
    res = q.fetch(limit)
    def msg_to_loc(marker, msg):
        global n
        n = n + 1
        atts = filter(lambda x: x and x.mime == 'text/plain', map(Att.get, msg.atts))
        atts_text = string.join(map(lambda x: linebreaks(escape(x.body)), atts), '\n')
        nearest = Location.nearest_location_at_time(msg.created)
        frm=' '.join(map(msg_person_html, msg.frm))
        to=' '.join(map(msg_person_html, msg.to))
        info_html = "<div class='info_popup'><img src='/static/%s.png'>%s<br />%s to %s<br />%s</div>" % (icon, msg.created, frm, to, atts_text)
        if nearest:
            return 'x%d = new GMarker(new GLatLng(%f,%f), %s); map.addOverlay(x%d); GEvent.addListener(x%d, "click", function() { x%d.openInfoWindowHtml("%s"); })' % (n, nearest.lat, nearest.lon, marker, n, n, n, info_html)
        else:
            return None
    
    return string.join(filter(None, map(lambda x: msg_to_loc(marker, x), res)), '\n');

def index(request):
    global n
    n = 0
    query = Location.all()
    points = query.order('-date').fetch(1000)
    # center on the most recent result
    centerx = points[0].loc.lat
    centery = points[0].loc.lon
    points_js = string.join(map(lambda x: "new GLatLng(%f,%f)" % (x.loc.lat,x.loc.lon), points), ',')
    # get all the SMS messages
    limit = 1
    sms_markers_js = message_type_to_js("iphone:sms","blueMarker", "phone_30x30", limit=limit)
    call_markers_js = message_type_to_js("iphone:call", "greenMarker", "sms_30x30", limit=limit)
    twitter_markers_js = message_type_to_js("com.twitter", "purpleMarker", "twitter_30x30", limit=limit)
    p = { 'google_maps_appid': passwd.google_maps_appid,
          'centerx':centerx, 'centery':centery,
          'points': points_js,
          'sms_markers': sms_markers_js, 'call_markers': call_markers_js, 'twitter_markers': twitter_markers_js
        }
    return shortcuts.render_to_response("map.html", p)
