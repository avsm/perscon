# Copyright (C) 2010 Richard Mortier <mort@cantab.net>
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

import logging, time, hashlib, datetime
log = logging.info

from django import http
from django.utils import simplejson as json
from google.appengine.api.labs import taskqueue
from google.appengine.api import users
from google.appengine.ext import db, webapp

import perscon.support
import atom.url
import gdata.service
import gdata.alt.appengine

from perscon.log import linfo

def init(req):
    client = gdata.service.GDataService()
    gdata.alt.appengine.run_on_appengine(client)

    feed_url = req.GET.get("feed_url")
    session_token = None
    
    # Find the AuthSub token and upgrade it to a session token.
    auth_token = gdata.auth.extract_auth_sub_token_from_url(self.request.uri)

    if auth_token:
        # Upgrade the single-use AuthSub token to a multi-use session
        # token.
        session_token = client.upgrade_to_session_token(auth_token)
    
    if session_token and users.get_current_user():
        # If there is a current user, store the token in the datastore
        # and associate it with the current user. Since we told the
        # client to run_on_appengine, the add_token call will
        # automatically store the session token if there is a
        # current_user.
        client.token_store.add_token(session_token)

    elif session_token:
        ## XXX never reached
        
        # Since there is no current user, we will put the session
        # token in a property of the client. We will not store the
        # token in the datastore, since we wouldn't know which user it
        # belongs to.  Since a new client object is created with each
        # get call, we don't need to worry about the anonymous token
        # being used by other users.  client.current_token =
        # session_token

        pass
    
    self.fetch_feed(client, feed_url)

    ## authsub url
    authsub_url = client.GenerateAuthSubURL(
        next_url, ('http://docs.google.com/feeds/',), secure=False, session=True)

    ## sample feed url
    example_url = atom.url.Url(
        'http', settings.HOST_NAME, path='/step3', 
        params={'feed_url': 'http://docs.google.com/feeds/documents/private/full'}
        ).to_string()

    try:
        response = client.Get(feed_url, converter=str)
        self.response.out.write(cgi.escape(response))
    except gdata.service.RequestError, request_error:
        # If fetching fails, then tell the user that they need to
        # login to authorize this app by logging in at the following
        # URL.
        if request_error[0]['status'] == 401:
            # Get the URL of the current page so that our AuthSub
            # request will send the user back to here.
            next = atom.url.Url('http', settings.HOST_NAME, path='/step3', 
              params={'feed_url': feed_url})
            # If there is a current user, we can request a session
            # token, otherwise we should ask for a single use token.
            auth_sub_url = client.GenerateAuthSubURL(next, feed_url,
                secure=False, session=True)
            self.response.out.write('<a href="%s">' % (auth_sub_url))
            self.response.out.write(
                'Click here to authorize this application to view the feed</a>')
        else:
            self.response.out.write(
                'Something went wrong, here is the error object: %s ' % (
                    str(request_error[0])))
def get_tokens():
    tokens = gdata.alt.appengine.load_auth_tokens()

def EraseStoredTokens(self):
    gdata.alt.appengine.save_auth_tokens({})
