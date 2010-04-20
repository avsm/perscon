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
from perscon.drivers import twitter, android

urls = map(
    lambda (p,c): (r'^/drivers/%s' % p, c),    
    [ (r'twitter/login/?$',       twitter.Login),
      (r'twitter/verify/?$',      twitter.Verify),
      (r'twitter/us/?$',          twitter.MentioningUs),
      (r'twitter/ourtweets/?$',   twitter.OurTweets),
      (r'twitter/dm/sent/?$',     twitter.OurDMSent),
      (r'twitter/dm/received/?$', twitter.OurDMReceived),
      
      (r'android/update/?$', android.Location),
      ])
     
application = webapp.WSGIApplication(urls, debug=True)
def main(): run_wsgi_app(application)
if __name__ == '__main__': main()
