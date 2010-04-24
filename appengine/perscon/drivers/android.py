# Copyright (C) 2010 Anil Madhavapeddy <anil@recoil.org>
#               2010 Richard Mortier <mort@cantab.net>
#		2010 Malte Schwarzkopf <ms705@cl.cam.ac.uk>
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
from django.utils import simplejson as json

import logging
log = logging.info

from google.appengine.ext import webapp

class Location(webapp.RequestHandler):
    def post(self):
        resp = json.loads(request.raw_post_data)
        loc = db.GeoPt(resp['lat'], resp['lon'])
        wid = woeid.resolve_latlon(loc.lat, loc.lon)
        acc = resp.get('accuracy', None)
        if acc: acc = float(acc)
        ctime = datetime.fromtimestamp(float(resp['date']))
        l = Location(loc=loc, date=ctime, accuracy=acc, url='http://google.com/android', woeid=wid)
        l.put()
        return http.HttpResponse(request.raw_post_data, mimetype="text/plain")
