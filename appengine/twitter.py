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

import os

from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

import django
from django import http

import oauth
import secret

app_key="PZakZTaETAqBIShqg2P1g"
app_secret="9T81OwiZrMGswcK0TXSwO5DT5r4in7SopUq4qP5Bw"

app_uri="http://localhost:8081"
login_url = "%s/twitter/login" % app_uri
callback_url = "%s/twitter/verify" % app_uri
timeline_url = "%s/twitter/timeline" % app_uri

def login(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    return http.HttpResponseRedirect(client.get_authorization_url())

def verify(req):      
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    auth_token = req.GET["oauth_token"]
    auth_verifier = req.GET["oauth_verifier"]
    user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
    s = secret.OAuth(service="twitter", token=user_info['token'], secret=user_info['secret'])
    s.put()
    return http.HttpResponseRedirect(timeline_url)

def timeline(req):      
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    timeline_url = "http://twitter.com/statuses/user_timeline.xml"
    s = secret.OAuth.all().filter('service =','twitter').get()
    if s:
        result = client.make_request(url=timeline_url, token=s.token, secret=s.secret)
        return http.HttpResponse(result.content, mimetype='text/plain')
    return http.HttpResponseRedirect(login_url)
