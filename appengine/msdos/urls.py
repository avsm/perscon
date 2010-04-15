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

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import views

urls = [
    (r'^message(:P/(.+))?/?$',    views.Message),
    (r'^att(:P/(.+))?/?$',        views.Att),
    (r'^person(:P/(.+))?/?$',     views.Person),    
    (r'^service/im/(.+)/(.+)/?$', views.IMService),
    (r'^service/(.+)/(.+)/?$',    views.Service),
    (r'^loc/?$',                  views.Loc),
    (r'^prefs/?$',                views.Prefs),
    (r'^log/?$',                  views.Log),
    ]

## application is defined as a list of (URL, handler object) pairs.
## run the application, via a main() function to take advantage of
## GAE's application caching behaviour
application = webapp.WSGIApplication(urls, debug=True)
def main(): run_wsgi_app(application)
if __name__ == '__main__': main()
