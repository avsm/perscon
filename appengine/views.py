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

from models import Location,Att,Person,Message,Service

def message(request, uid):
    meth = request.method
    if meth == 'POST':
        j = json.loads(request.raw_post_data)
        created = datetime.fromtimestamp(float(j['mtime']))
        frm = map(Service.key_ofdict, j['frm'])
        to = map(Service.key_ofdict, j['to'])
        atts = filter(None, map(lambda x: Att.get_by_key_name(x), j['atts']))
        atts = map(lambda x: x.key(), atts)
        thread=None
        if j.get('thread',None):
            parent_msg = Message.get_by_key_name(j['thread'])
            if parent_msg:
                if parent_msg.thread:
                    thread=parent_msg.thread
                else:
                    thread=parent_msg.key().name()
        meta = j.get('meta',{})
        m = Message.get_or_insert(uid, origin=j['origin'], frm=frm, to=to, 
                                  atts=atts, created=created, meta=meta, thread=thread)
        return http.HttpResponse("ok", mimetype="text/plain")
    elif meth == 'GET':
        m = Message.get_by_key_name(uid)
        if m:
            return http.HttpResponse(m.tojson(), mimetype='text/plain')
        else:
            return http.HttpResponseNotFound("not found", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")

def messages(req):
    if req.method == 'GET':
        offset = int(req.GET.get('start', '0'))
        limit = int(req.GET.get('limit','20'))
        threaded = int(req.GET.get('threaded',0))
        rq = Message.all().order('-created')
        rc = rq.count(1000)
        # XXX hack, need to iterate more cleverly to fill in threads
        if threaded:
            rs = rq.fetch(1000, offset=offset)
            outl = []
            outd = {}
            for r in rs:
                if len(outl) >= limit: break
                if r.thread:
                    if r.thread not in outd:
                        # threaded and not seen before
                        outl.append(r)
                        outd[r.thread] = 1
                    else:
                        # threaded and seen before, discard
                        pass
                else:
                    if r.key().name() in outd:
                        # this root message is in a thread so skip
                        pass
                    else:
                        outl.append(r)
                        outd[r.key().name()] = 1
            for r in outl:
                if r.thread:
                    q = db.GqlQuery("SELECT __key__ FROM Message WHERE thread=:1", r.thread)
                    num = q.count(1000)
                    r.thread_count = num
            rs = outl
            rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
            return http.HttpResponse(json.dumps(rsd,indent=2), mimetype='text/plain')
        else:
            rs = rq.fetch(limit, offset=offset)
            rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
            return http.HttpResponse(json.dumps(rsd,indent=2), mimetype='text/plain')
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
        atts = filter(None, map(lambda x: Att.get_by_key_name(x), j['atts']))
        atts = map(lambda x: x.key(), atts)
        p = Person.get_or_insert(uid, 
                   first_name = j.get('first_name', None), 
                   last_name = j.get('last_name', None), 
                   origin = j.get('origin', None),
                   services = [],
                   created = created, atts=atts)
        return http.HttpResponse("ok", mimetype="text/plain")
    elif meth == 'GET':
        p = Person.get_by_key_name(uid)
        if p:
           return http.HttpResponse(p.tojson(), mimetype="text/plain")
        else:
           return http.HttpResponseNotFound("not found", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")

def people(req):
    offset = int(req.GET.get('start', '0'))
    limit = int(req.GET.get('limit','20'))
    if req.method == 'GET':
        rq = Person.all().order('-created')
        rc = rq.count(1000)
        rs = rq.fetch(limit, offset=offset)
        rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
        return http.HttpResponse(json.dumps(rsd,indent=2), mimetype='text/plain')
    return http.HttpResponseServerError("not implemented")

def service_im(req, svc, uid):
    if req.method == 'GET':
        s = Service.ofdict({'ty': 'im', 'value': [svc,uid]},create=False)
        if s:
            return http.HttpResponse(json.dumps(s.todict(),indent=2), mimetype='text/plain')
        else:
            return http.HttpResponseNotFound("not found", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")
    
def service_generic(req, ty, val):
    if req.method == 'GET':
        s = Service.ofdict({'ty': ty, 'value': val},create=False)
        if s:
            return http.HttpResponse(json.dumps(s.todict(),indent=2), mimetype='text/plain')
        else:
            return http.HttpResponseNotFound("not found", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")
  
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
    meth = request.method
    if meth == 'GET':
        query = Location.all()
        recent = query.order('-date').fetch(10)
        j = json.dumps(map(lambda x: x.todict(), recent), indent=2)
        return http.HttpResponse(j, mimetype="text/plain")
    elif meth == 'POST':
        resp = json.loads(request.raw_post_data)
        loc = db.GeoPt(resp['lat'], resp['lon'])
        wid = woeid.resolve_latlon(loc.lat, loc.lon)
        acc = resp.get('accuracy', None)
        if acc:
            acc = float(acc)
        ctime = datetime.fromtimestamp(float(resp['date']))
        l = Location(loc=loc, date=ctime, accuracy=acc, url=resp.get('url',None), woeid=wid)
        l.put()
        return http.HttpResponse("ok", mimetype="text/plain")
    return http.HttpResponseServerError("not implemented")

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
        all_atts = map(Att.get, msg.atts)
        atts = filter(lambda x: x and x.mime == 'text/plain', all_atts)
        imgs = filter(lambda x: x and x.mime != 'text/plain', all_atts)
        atts_text = string.join(map(lambda x: linebreaks(escape(x.body)), atts), '\n')
        imgs_txt = string.join(map(lambda x: "<a href='/att/%s'><img width='30%%' height='30%%' src='/att/%s' /></a>" % (x.key().name(), x.key().name()), imgs), '\n')
        nearest = Location.nearest_location_at_time(msg.created)
        frm=' '.join(map(msg_person_html, msg.frm))
        to=' '.join(map(msg_person_html, msg.to))
        if to != '':
           to = "to " + to
        info_html = "<div class='info_popup'><img src='/static/%s.png'>%s%s<br />%s %s<br />%s</div>" % (icon, imgs_txt, msg.created, frm, to, atts_text)
        if nearest:
            return 'x%d = new GMarker(new GLatLng(%f,%f), %s); map.addOverlay(x%d); GEvent.addListener(x%d, "click", function() { x%d.openInfoWindowHtml("%s"); })' % (n, nearest.lat, nearest.lon, marker, n, n, n, info_html)
        else:
            return None
    return string.join(filter(None, map(lambda x: msg_to_loc(marker, x), res)), '\n');

def index(request):
    return http.HttpResponseRedirect("/static/index.html")

def indexold(request):
    global n
    n = 0
    query = Location.all()
    points = query.order('-date').fetch(1000)
    # center on the most recent result
    centerx = points[0].loc.lat
    centery = points[0].loc.lon
    points_js = string.join(map(lambda x: "new GLatLng(%f,%f)" % (x.loc.lat,x.loc.lon), points), ',')
    limit = 20
    sms_markers_js = message_type_to_js("iphone:sms","smsMarker", "sms_30x30", limit=limit)
    call_markers_js = message_type_to_js("iphone:call", "phoneMarker", "phone_30x30", limit=limit)
    twitter_markers_js = message_type_to_js("com.twitter", "twitterMarker", "twitter_30x30", limit=limit)
    photo_markers_js = message_type_to_js("com.apple.iphoto", "photoMarker", "photo_30x30", limit)
    chat_markers_js = message_type_to_js("com.adium", "chatMarker", "chat_30x30", limit)
    p = { 'google_maps_appid': passwd.google_maps_appid,
          'centerx':centerx, 'centery':centery,
          'points': points_js,
          'sms_markers': sms_markers_js, 'call_markers': call_markers_js, 
          'twitter_markers': twitter_markers_js, 'photo_markers': photo_markers_js,
          'chat_markers': chat_markers_js
        }
    return shortcuts.render_to_response("map.html", p)
