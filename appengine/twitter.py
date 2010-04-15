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
from perscon_log import linfo
import logging
log = logging.info

app_key="PZakZTaETAqBIShqg2P1g"
app_secret="9T81OwiZrMGswcK0TXSwO5DT5r4in7SopUq4qP5Bw"

def base_url(req):
    svc = "https" if req.is_secure() else "http"
    return "%s://%s:%s" % (svc, req.META['SERVER_NAME'], req.META['SERVER_PORT'])

def login_url(req):
    return "%s/twitter/login" % base_url(req)

def callback_url(req):
    return "%s/twitter/verify" % base_url(req)
 
def login(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
    return http.HttpResponseRedirect(client.get_authorization_url())

def verify(req):      
    client = oauth.TwitterClient(app_key, app_secret, callback_url)
    auth_token = req.GET["oauth_token"]
    auth_verifier = req.GET["oauth_verifier"]
    user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
    user_secret = user_info['secret']
    username = user_info['username']
    s = secret.OAuth(service="twitter", token=user_info['token'], 
       secret=user_secret, username=username)
    s.put()
    return http.HttpResponseRedirect("/static/index.html")

# import Tweets as perscon objects
class TWTY:
    tweet = 'tweet'
    retweet = 'retweet'
    reply = 'reply'
    direct = 'direct'


def addr(service, account): return ({'ty':'url', 'value': 'http://twitter.com/'+account})

def stash_tweets(account, tweets):
    service = 'http://twitter.com/'
    info = { 'origin': 'com.twitter', 'account': account, }
    for tw in tweets:
        data = { 'origin': 'com.twitter' }
        data['meta'] = { 'type': TWTY.tweet, 'raw': tw }

        mtime = dateutil.parser.parse(tw['created_at'])
        data['mtime'] = time.mktime(mtime.timetuple())

        uid = "twitter:%d" % tw['id']
        data['uid'] = uid

        auid = "%s.txt" % (uid,)
##         taskqueue.add(url="/att/%s" % auid, method="POST", payload=tw['text'])

        ## XXX hack - taskqueue is reordering stuff when busy, leading
        ## to confusion (att created after message is presumed absent
        ## forever)

        a = models.Att.get_or_insert(auid, mime="text/plain", body=tw['text'].encode("utf8"))
        a.put()

        ## XXX end hack
        
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
        
            if 'in_reply_to_status_id' in tw and tw['in_reply_to_status_id']:
                data['thread'] = 'twitter:' + str(tw['in_reply_to_status_id'])

            if 'in_reply_to_screen_name' in tw and tw['in_reply_to_screen_name']:
                data['meta']['type'] = TWTY.reply
                data['to'] = [addr(service, tw['in_reply_to_screen_name'])]

            if 'retweeted_status' in tw and tw['retweeted_status']:
                data['meta']['type'] = TWTY.retweet
                data['meta']['source'] = tw['retweeted_status']['user']['screen_name']
                ctime = dateutil.parser.parse(tw['retweeted_status']['created_at'])
                data['meta']['ctime'] = time.mktime(ctime.timetuple())
            
        dataj = json.dumps(data, indent=2)
        log(dataj)
        taskqueue.add(url="/message/%s" % uid, method="POST", payload=dataj)
    linfo(origin="com.twitter", entry=("Stored %d tweets" % len(tweets)))

def mentioningUs(req):
    ps = { 'count': 20, }
    mi = req.GET.get("max_id")
    if mi:
        mi = long(mi)
        ps['max_id'] = mi
           
    s = secret.OAuth.all().filter('service =', 'twitter').get()
    if not s: return http.HttpResponseRedirect(login_url(req))
    client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
    url = "http://api.twitter.com/1/statuses/mentions.json"
    rs = client.make_request(url=url, token=s.token, secret=s.secret,
                             additional_params=ps)
    
    rj = json.loads(rs.content)
    if len(rj) > 0:
        is_sync = True if req.GET.get("sync") else False
        nmi = reduce(lambda x, y: min(x,y), [ long(tw['id']) for tw in rj ])
        if is_sync:
            if nmi != mi:
                taskqueue.add(url="/twitter/us", method="GET",
                              params={'sync': 1, 'max_id': nmi,})
            else:
                ss = models.Sync.of_service(s.service, s.username)
                ss.status = models.SYNC_STATUS.synchronized
                ss.put()

        else: log("NO SYNC")
        stash_tweets(s.username, rj)
        
    return http.HttpResponse(json.dumps(rj, indent=2), mimetype='text/plain')

def ourTweets(req):
    ps = { 'count': 20, }
    mi = req.GET.get("max_id")
    if mi:
        mi = long(mi)
        ps['max_id'] = mi
        
    s = secret.OAuth.all().filter('service =','twitter').get()
    if not s: return http.HttpResponseRedirect(login_url(req))
    client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
    url = "http://api.twitter.com/1/statuses/user_timeline.json"
    rs = client.make_request(url=url, token=s.token, secret=s.secret,
                             additional_params=ps)
    rj = json.loads(rs.content)
    if len(rj) > 0:
        is_sync = True if req.GET.get("sync") else False
        nmi = reduce(lambda x,y: min(x,y), [ long(tw['id']) for tw in rj ])
        if is_sync:
            if nmi != mi:
                taskqueue.add(url="/twitter/ourtweets", method="GET",
                              params={'sync':1, 'max_id': nmi,})
            else:
                ss = models.Sync.of_service(s.service, s.username)
                ss.status = models.SYNC_STATUS.synchronized
                ss.put()

        else: log("NO SYNC")
        stash_tweets(s.username, rj)
        
    return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
  
def ourDMSent(req): 
    client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
    timeline_url = "http://api.twitter.com/1/direct_messages/sent.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    pg = int(req.GET.get('pg','1'))
    count = 20
    if s:
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'pg':pg,'count':count})
        rj = json.loads(rs.content)
        if len(rj) > 0:
            stash_tweets(s.username, rj)
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url(req))
   
def ourDMReceived(req):
    client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
    timeline_url = "http://api.twitter.com/1/direct_messages.json"
    s = secret.OAuth.all().filter('service =','twitter').get()
    pg = int(req.GET.get('pg','1'))
    count = 20
    if s:
        rs = client.make_request(url=timeline_url, token=s.token, secret=s.secret, additional_params={'pg':pg,'count':count})
        log(rs.content)
        rj = json.loads(rs.content)
        if len(rj) > 0:
            stash_tweets(s.username, rj)
        return http.HttpResponse(json.dumps(rj,indent=2), mimetype='text/plain')
    return http.HttpResponseRedirect(login_url(req))
 

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

import models
def sync(req, cmd):
    ## XXX assumes oauth tokens already there!
    s = secret.OAuth.all().filter("service =", "twitter").get()
    if not s:
        ss = models.Sync.new_sync('twitter')
    else: 
        svc, usr = s.service, s.username
        ss = models.Sync.of_service(svc, usr)

    if not cmd and req.method == 'GET': pass ## default return
    elif req.method in ("POST", "GET"):
        if cmd == "start":
            if ss.status != models.SYNC_STATUS.inprogress:
                # starting syncing twitter: set syncstate; get first page;
                # unless all old, add next fetch to taskqueue
                ss.status = models.SYNC_STATUS.inprogress
                ss.put()
                taskqueue.add(url='/twitter/us?sync=1', method="GET")
                taskqueue.add(url='/twitter/ourtweets?sync=1', method="GET")
        
        elif cmd == "stop":
            # stop syncing twitter - set syncstate
            # clear up taskqueue?
            pass

    return http.HttpResponse(ss.tojson(), mimetype='text/plain')
