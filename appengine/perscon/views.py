# Copyright (c) 2010 Anil Madhavapeddy <anil@recoil.org>
#                    Richard Mortier <mort@cantab.net>
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

import os, time, string, logging, urllib
log = logging.info

from datetime import datetime

from google.appengine.ext import webapp, db
from google.appengine.api import users
from django.utils import simplejson as json
from django.utils.html import escape, linebreaks

import models
from perscon.log import dolog
from perscon.support import woeid

class Message(webapp.RequestHandler):
    def get(self, uid):
        self.response.headers['Content-Type'] = 'application/json'
        if uid:
            m = models.Message.get_by_key_name(uid)
            if m: self.response.out.write(m.tojson())
            else: self.response.set_status(404)
                                               
        else:
            req = self.request
            offset = int(req.get('start', '0'))
            limit = int(req.get('limit','20'))
            threaded = int(req.get('threaded', '0'))

            rq = models.Message.all().order('-created')            
            rc = rq.count(1000)
            
            # XXX hack, need to iterate more cleverly to fill in threads
            if not threaded: rs = rq.fetch(limit, offset=offset)
            else:
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
                        q = db.GqlQuery(
                            "SELECT __key__ FROM Message WHERE thread=:1", r.thread)
                        num = q.count(1000)
                        r.thread_count = num
                rs = outl

            rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
            self.response.out.write(json.dumps(rsd,indent=2))

    def post(self, uid):
##         log(self.request.body)
        j = json.loads(self.request.body)
        created = datetime.fromtimestamp(float(j['mtime']))
        frm = map(models.Service.key_ofdict, j['frm'])
        tos = map(models.Service.key_ofdict, j['tos'])
        atts = filter(None, map(lambda x: models.Att.get_by_key_name(x), j['atts']))
        atts = map(lambda x: x.key(), atts)
        
        thread = j.get("thread")
        if thread: ## fixup for adium threading
            parent_msg = models.Message.get_by_key_name(thread)
            if parent_msg:
                thread = (parent_msg.thread if parent_msg.thread
                          else parent_msg.key().name())
                
        meta = j.get('meta', {})
        m = models.Message.get_or_insert(
            uid, origin=j['origin'], frm=frm, tos=tos, 
            atts=atts, created=created, meta=meta, thread=thread)

class Att(webapp.RequestHandler):
    def get(self, uid):
        uid = urllib.unquote(uid)
        a = models.Att.get_by_key_name(uid)
        if not a: self.response.set_status(404)
        else:
            self.response.headers['Content-Type'] = a.mime
            self.response.out.write(a.body)

    def post(self, uid):
        mime = self.request.headers.get('Content-Type')
        models.Att.get_or_insert(uid, mime=mime, body=self.request.body)

class Person(webapp.RequestHandler):
    def get(self, uid):
        self.response.headers['Content-Type'] = 'application/json'
        if uid:
            p = models.Person.get_by_key_name(uid)
            if p: self.response.out(p.tojson())
            else: self.response.set_status(404)

        else:
            req = self.request
            offset = int(req.get('start', '0'))
            limit = int(req.get('limit','20'))

            rq = models.Person.all().order('-created')
            rc = rq.count(1000)
            rs = rq.fetch(limit, offset=offset)
            rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
            self.response.out.write(json.dumps(rsd,indent=2))

    def post(self, uid):
        j = json.loads(self.request.body)
        created = datetime.fromtimestamp(float(j['mtime']))
        atts = filter(None, map(lambda x: models.Att.get_by_key_name(x), j['atts']))
        atts = map(lambda x: x.key(), atts)
        p = models.Person.get_or_insert(
            uid, first_name = j.get('first_name'), last_name = j.get('last_name'), 
            origin = j.get('origin'), services = [], created = created, atts=atts)

class IMService(webapp.RequestHandler):
    def get(self, svc, uid):
        s = Service.ofdict({'ty': 'im', 'value': [svc,uid]},create=False)
        if not s: self.response.set_status(404)
        else:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(json.dumps(s.todict(),indent=2))

class Service(webapp.RequestHandler):
    def get(self, ty, val):
        s = Service.ofdict({'ty': ty, 'value': val},create=False)
        if not s: self.response.set_status(404)
        else:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(json.dumps(s.todict(),indent=2))

class Loc(webapp.RequestHandler):
    def get(self):
        query = models.Location.all()
        recent = query.order('-date').fetch(10)
        j = json.dumps(map(lambda x: x.todict(), recent), indent=2)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(j)

    def post(self):
        resp = json.loads(self.request.body)
        loc = db.GeoPt(resp['lat'], resp['lon'])
        wid = woeid.resolve_latlon(loc.lat, loc.lon)
        acc = resp.get('accuracy')
        if acc: acc = float(acc)
        ctime = datetime.fromtimestamp(float(resp['date']))
        l = models.Location(loc=loc, date=ctime, accuracy=acc,
                     url=resp.get('url',None), woeid=wid)
        l.put()

class Prefs(webapp.RequestHandler):
    def get(self):
        p = models.Prefs.all().get()
        self.response.headers['Content-Type'] = 'application/json'
        if not p: self.response.out.write(models.Prefs.null_json())
        else:
           r = json.dumps({ 'success': True, 'data': p.to_dict() })
           self.response.out.write(r)

    def post(self):
        p = models.Prefs.all().get()
        if not p: p = models.Prefs()

        np = json.loads(self.request.body)
        npFN = np.get('first_name', None)
        npLN = np.get('last_name', None)
        npEM = np.get('email', None)
        npPP = np.get('passphrase', None)
        if npFN: p.firstName = npFN
        if npLN: p.lastName = npLN
        if npEM: p.email = npEM
        if npPP: p.passphrase = npPP

        p.put()

class Log(webapp.RequestHandler):
    def get(self, **kwargs):
        req = self.request
        offset = int(req.get('start', '0'))
        limit = int(req.get('limit','20'))
        rq = models.LogEntry.all().order('-created')
        rc = rq.count(1000)
        rs = rq.fetch(limit, offset=offset)
        rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(rsd,indent=2))

    def post(self):
        j = json.loads(self.request.body)
        l = dolog(level=j.get('level','info'),
                  origin=j.get('origin',''), entry=j['entry'])

class Login(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user: self.redirect("/")
        else:
            self.redirect(users.create_login_url("/"))

class Logout(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user: self.redirect("/")
        else:
            self.redirect(users.create_logout_url("/"))

## def msg_person_html(svc):
##     p = Person.from_service(svc)
##     if p:
##         return "%s %s" % (p.first_name, p.last_name)
##     else:
##         return svc.address
        
## n=0
## def message_type_to_js(cl, marker, icon, limit=10):
##     q = Message.gql("WHERE origin=:1 ORDER BY created DESC LIMIT %d" % limit, cl)
##     res = q.fetch(limit)
##     def msg_to_loc(marker, msg):
##         global n
##         n = n + 1
##         all_atts = map(Att.get, msg.atts)
##         atts = filter(lambda x: x and x.mime == 'text/plain', all_atts)
##         imgs = filter(lambda x: x and x.mime != 'text/plain', all_atts)
##         atts_text = string.join(map(lambda x: linebreaks(escape(x.body)), atts), '\n')
##         imgs_txt = string.join(map(lambda x: "<a href='/att/%s'><img width='30%%' height='30%%' src='/att/%s' /></a>" % (x.key().name(), x.key().name()), imgs), '\n')
##         nearest = Location.nearest_location_at_time(msg.created)
##         frm=' '.join(map(msg_person_html, msg.frm))
##         to=' '.join(map(msg_person_html, msg.to))
##         if to != '':
##            to = "to " + to
##         info_html = "<div class='info_popup'><img src='/static/%s.png'>%s%s<br />%s %s<br />%s</div>" % (icon, imgs_txt, msg.created, frm, to, atts_text)
##         if nearest:
##             return 'x%d = new GMarker(new GLatLng(%f,%f), %s); map.addOverlay(x%d); GEvent.addListener(x%d, "click", function() { x%d.openInfoWindowHtml("%s"); })' % (n, nearest.lat, nearest.lon, marker, n, n, n, info_html)
##         else:
##             return None
##     return string.join(filter(None, map(lambda x: msg_to_loc(marker, x), res)), '\n');

## def index(request):
##     return http.HttpResponseRedirect("/static/index.html")

## def indexold(request):
##     global n
##     n = 0
##     query = Location.all()
##     points = query.order('-date').fetch(1000)
##     # center on the most recent result
##     centerx = points[0].loc.lat
##     centery = points[0].loc.lon
##     points_js = string.join(map(lambda x: "new GLatLng(%f,%f)" % (x.loc.lat,x.loc.lon), points), ',')
##     limit = 20
##     sms_markers_js = message_type_to_js("iphone:sms","smsMarker", "sms_30x30", limit=limit)
##     call_markers_js = message_type_to_js("iphone:call", "phoneMarker", "phone_30x30", limit=limit)
##     twitter_markers_js = message_type_to_js("com.twitter", "twitterMarker", "twitter_30x30", limit=limit)
##     photo_markers_js = message_type_to_js("com.apple.iphoto", "photoMarker", "photo_30x30", limit)
##     chat_markers_js = message_type_to_js("com.adium", "chatMarker", "chat_30x30", limit)
##     p = { 'google_maps_appid': passwd.google_maps_appid,
##           'centerx':centerx, 'centery':centery,
##           'points': points_js,
##           'sms_markers': sms_markers_js, 'call_markers': call_markers_js, 
##           'twitter_markers': twitter_markers_js, 'photo_markers': photo_markers_js,
##           'chat_markers': chat_markers_js
##         }
##     return shortcuts.render_to_response("map.html", p)
