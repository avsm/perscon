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
from django import http
from django.utils import simplejson as json
import logging
import time

class LogLevel:
    info = 'info'
    debug = 'debug'
    error = 'error'

class LogEntry(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    level = db.StringProperty(required=True)
    source = db.StringProperty()
    entry = db.TextProperty()

    def todict(self):
        return {'created': time.mktime(self.created.timetuple()), 'level':self.level,
                'source':self.source, 'entry':self.entry }

def dolog(level="info", source=None, entry=""):
    LogEntry(level=level, source=source, entry=entry).put()
    source = source or "unknown"
    e = "%s: %s" % (source, entry)
    if level == "info":
      logging.info(e)
    elif level == "debug":
      logging.debug(e)
    elif level == "error":
      logging.error(e)

def ldebug(source=None, entry=""):
    dolog(level="debug", source=source, entry=entry)

def linfo(source=None, entry=""):
    dolog(level="info", source=source, entry=entry)

def crud(req):
    offset = int(req.GET.get('start', '0'))
    limit = int(req.GET.get('limit','20'))
    if req.method == 'GET':
        rq = LogEntry.all().order('-created')
        rc = rq.count(1000)
        rs = rq.fetch(limit, offset=offset)
        rsd = {'results': rc, 'rows': map(lambda x: x.todict(), rs)}
        return http.HttpResponse(json.dumps(rsd,indent=2), mimetype='text/plain')
    return http.HttpResponseServerError("not implemented")
