# Copyright (C) 2010 Anil Madhavapeddy <anil@recoil.org>
#               2010 Richard Mortier <mort@cantab.net>
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

from google.appengine.api.labs import taskqueue
from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

import django
from django import http
from django.utils import simplejson as json

import time,hashlib
import oauth
import secret
import dateutil.parser

app_key="PZakZTaETAqBIShqg2P1g"
app_secret="9T81OwiZrMGswcK0TXSwO5DT5r4in7SopUq4qP5Bw"

app_uri="http://localhost:8081"
login_url = "%s/twitter/login" % app_uri
callback_url = "%s/twitter/verify" % app_uri
timeline_url = "%s/twitter/timeline" % app_uri
ae = None

def login(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    return http.HttpResponseRedirect(client.get_authorization_url())

def verify(req):      
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    auth_token = req.GET["oauth_token"]
    auth_verifier = req.GET["oauth_verifier"]
    user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
    user_secret = user_info['secret']
    username = user_info['username']
    s = secret.OAuth(service="twitter", token=user_info['token'], secret=user_secret, username=username)
    s.put()
    return http.HttpResponseRedirect(timeline_url)

# import Tweets as perscon objects
class TWTY:
    tweet = 'tweet'
    retweet = 'retweet'
    reply = 'reply'
    direct = 'direct'

import logging

def addr(service, account): return (service, account)

def stash_tweets(account, tweets):
    global ae
    service = 'http://twitter.com'
    info = { 'origin': 'com.twitter', 'account': account, }
    for tw in tweets:
       
        data = { 'origin': 'com.twitter' }
        data['meta'] = { 'type': TWTY.tweet }

        mtime = dateutil.parser.parse(tw['created_at'])
        data['mtime'] = time.mktime(mtime.timetuple())

        uid = "twitter:"+hashlib.sha1(service+account+str(tw['id'])).hexdigest()
        data['uid'] = uid

        auid = uid + ".txt"
        taskqueue.add(url="/att", method="POST", payload=unicode(tw['text']))

        data['atts'] = [ auid ]

        if 'sender' in tw and tw['sender']:
            data['meta']['type'] = TWTY.direct
            data['frm'] = [ addr(service, tw['sender_screen_name']) ]
            data['to'] = [ addr(service, tw['recipient_screen_name']) ]

        else:
            try: data['frm'] = [addr(service, tw['from_user'])]
            except KeyError:
                data['frm'] = [addr(service, tw['user']['screen_name'])]
                
            try: data['to'] = [addr(service, tw['to_user'])]
            except KeyError:
                data['to'] = []
                                              
            if 'in_reply_to_screen_name' in tw and tw['in_reply_to_screen_name']:
                data['meta']['type'] = TWTY.reply
                data['to'] = [addr(service, tw['in_reply_to_screen_name'])]

            if 'retweeted_status' in tw and tw['retweeted_status']:
                data['meta']['type'] = TWTY.retweet
                data['meta']['source'] = tw['retweeted_status']['user']['screen_name']
                ctime = dateutil.parser.parse(tw['retweeted_status']['created_at'])
                data['meta']['ctime'] = time.mktime(ctime.timetuple())
            
        dataj = json.dumps(data, indent=2)
        taskqueue.add(url="/message", method="POST", payload=dataj)

def mentioningUs(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    timeline_url = "http://search.twitter.com/search.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    if s:
        q = '@' + s.username
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'q':q})
        rj = json.loads(rs.content)
        if len(rj['results']) > 0:
            stash_tweets(s.username, rj['results'])
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url)

def ourTweets(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    timeline_url = "http://twitter.com/statuses/user_timeline.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    pg = int(req.GET.get('pg','1'))
    count = 20
    if s:
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'pg':pg,'count':count})
        rj = json.loads(rs.content)
        if len(rj) > 0:
            stash_tweets(s.username, rj)
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url)
  
def ourDMSent(req): 
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    timeline_url = "http://twitter.com/statuses/direct_messages/sent.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    pg = int(req.GET.get('pg','1'))
    count = 20
    if s:
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'pg':pg,'count':count})
        logging.info(rs.content)
        rj = json.loads(rs.content)
        if len(rs) > 0:
            stash_tweets(s.username, rj)
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url)
   
def ourDMReceived(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    timeline_url = "http://twitter.com/statuses/direct_messages.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    pg = int(req.GET.get('pg','1'))
    count = 20
    if s:
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'pg':pg,'count':count})
        logging.info(rs.content)
        rj = json.loads(rs.content)
        if len(rs) > 0:
            stash_tweets(s.username, rj)
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url)
 

#    ## 6. tweets from friends
#    cr = -1
#    friends = []
#    while cr != 0:
#        rs = retryOnError("get_friends cursor=%d" % cr,
#                          lambda: t.friends.ids(cursor=cr))
#        friends.extend(rs['ids'])
#        cr = rs['next_cursor']

#    print >> sys.stderr, "friends:", friends
#    for friend in friends:
#        pg = 1
#        while True:
#            rs = retryOnError(
#                "friend_timeline %s %d" % (friend, pg),
#                lambda: t.statuses.user_timeline(id=friend, page=pg, count=200))
#            if len(rs) == 0: break
#            stash_tweets(service, username, rs)
#            pg += 1
#        print >> sys.stderr, "friend: %s done" % friend

