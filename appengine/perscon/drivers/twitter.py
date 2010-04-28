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

import os, logging, time, hashlib
log = logging.info

from google.appengine.ext import webapp
from google.appengine.api.labs import taskqueue
from django.utils import simplejson as json

from perscon.support.dateutil import parser 
import perscon.support.oauth as oauth
import perscon.support.secret as secret
import perscon.models as models
from perscon.log import linfo

COUNT = 50
app_key="PZakZTaETAqBIShqg2P1g"
app_secret="9T81OwiZrMGswcK0TXSwO5DT5r4in7SopUq4qP5Bw"

def base_url(req):
    bu = "%s://%s:%s/drivers" % (
        req.scheme, req.environ['SERVER_NAME'], req.environ['SERVER_PORT'])
    return bu

def login_url(req):
    return "%s/twitter/login" % base_url(req)

def callback_url(req):
    return "%s/twitter/verify" % base_url(req)
 
class Login(webapp.RequestHandler):
    def get(self):
        client = oauth.TwitterClient(
            app_key, app_secret, callback_url(self.request))
        self.redirect(client.get_authorization_url())

class Verify(webapp.RequestHandler):
    def get(self):
        client = oauth.TwitterClient(app_key, app_secret, callback_url)
        auth_token = self.request.GET.get("oauth_token")
        auth_verifier = self.request.GET.get("oauth_verifier")
        user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)
        user_secret = user_info['secret']
        username = user_info['username']
        s = secret.OAuth(service="twitter", token=user_info['token'],
                         secret=user_secret, username=username)
        s.put()
        self.redirect("/")

# import Tweets as perscon objects
class TWTY:
    tweet = 'tweet'
    retweet = 'retweet'
    reply = 'reply'
    direct = 'direct'

def addr(service, account):
    return ({'ty':'url', 'value': 'http://twitter.com/'+account})

def stash_tweets(account, tweets):
    service = 'http://twitter.com/'
    info = { 'origin': 'com.twitter', 'account': account, }
    for tw in tweets:
        data = { 'origin': 'com.twitter' }
        data['meta'] = { 'type': TWTY.tweet, 'raw': tw }

        mtime = parser.parse(tw['created_at'])
        data['mtime'] = time.mktime(mtime.timetuple())

        uid = "twitter:%d" % tw['id']
        data['uid'] = uid

        auid = "%s.txt" % (uid,)
##         taskqueue.add(url="/att/%s" % auid, method="POST", payload=tw['text'])

        ## XXX hack - taskqueue is reordering stuff when busy, leading
        ## to confusion (att created after message is presumed absent
        ## forever)

        a = models.Att.get_or_insert(auid, mime="text/plain",
                                     body=tw['text'].encode("utf8"))
        a.put()

        ## XXX end hack
        
        data['atts'] = [ auid ]

        if 'sender' in tw and tw['sender']:
            data['meta']['type'] = TWTY.direct
            data['frm'] = [ addr(service, tw['sender_screen_name']) ]
            data['tos'] = [ addr(service, tw['recipient_screen_name']) ]

        else:
            try: data['frm'] = [addr(service, tw['from_user'])]
            except KeyError:
                data['frm'] = [addr(service, tw['user']['screen_name'])]
                
            try: data['tos'] = [addr(service, tw['to_user'])]
            except KeyError:
                data['tos'] = []
        
            if 'in_reply_to_status_id' in tw and tw['in_reply_to_status_id']:
                data['thread'] = 'twitter:' + str(tw['in_reply_to_status_id'])

            if 'in_reply_to_screen_name' in tw and tw['in_reply_to_screen_name']:
                data['meta']['type'] = TWTY.reply
                data['tos'] = [addr(service, tw['in_reply_to_screen_name'])]

            rt = tw['retweeted_status'] if 'retweeted_status' in tw else None
            if rt:
                data['meta']['type'] = TWTY.retweet
                data['meta']['source'] = rt['user']['screen_name']
                ctime = parser.parse(rt['created_at'])
                data['meta']['ctime'] = time.mktime(ctime.timetuple())
            
        dataj = json.dumps(data, indent=2)
        log(dataj)
        taskqueue.add(url="/message/%s" % uid, method="POST", payload=dataj)
                                                                            
    linfo(origin="com.twitter", entry=("Stored %d tweets" % len(tweets)))

class MentioningUs(webapp.RequestHandler):
    def get(self):
        ps = { 'count': COUNT, }
        mi = self.request.GET.get("max_id")
        if mi:
            mi = long(mi)
            ps['max_id'] = mi

        s = secret.OAuth.all().filter('service =', 'twitter').get()
        if not s: self.redirect(login_url(self.request))
        
        client = oauth.TwitterClient(app_key, app_secret, callback_url(self.request))
        url = "http://api.twitter.com/1/statuses/mentions.json"
        rs = client.make_request(url=url, token=s.token, secret=s.secret,
                                 additional_params=ps)

        rj = json.loads(rs.content)
        if len(rj) > 0:
            nmi = reduce(lambda x, y: min(x,y), [ long(tw['id']) for tw in rj ])
            is_sync = True if self.request.GET.get("sync") else False
            if is_sync:
                ss = models.SyncStatus.of_service(s.service, "/drivers/twitter/us?sync=1")
                if nmi == mi:
                    ss.status = models.SYNC_STATUS.synchronized
                    ss.put()
                else:
                    taskqueue.add(url="/drivers/twitter/us", method="GET",
                                  params={'sync': 1, 'max_id': nmi,})

            stash_tweets(s.username, rj)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(rj, indent=2))

class OurTweets(webapp.RequestHandler):
    def get(self):
        ps = { 'count': COUNT, }
        req = self.request
        mi = req.GET.get("max_id")
        if mi:
            mi = long(mi)
            ps['max_id'] = mi

        s = secret.OAuth.all().filter('service =','twitter').get()
        if not s: self.redirect(login_url(req))
                                               
        client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
        url = "http://api.twitter.com/1/statuses/user_timeline.json"
        rs = client.make_request(url=url, token=s.token, secret=s.secret,
                                 additional_params=ps)
        rj = json.loads(rs.content)
        if len(rj) > 0:
            nmi = reduce(lambda x,y: min(x,y), [ long(tw['id']) for tw in rj ])
            is_sync = True if req.GET.get("sync") else False
            if is_sync:
                ss = models.SyncStatus.of_service(s.service, "/drivers/twitter/ourtweets?sync=1")
                if nmi == mi:
                    ss.status = models.SYNC_STATUS.synchronized
                    ss.put()
                else:
                    taskqueue.add(url="/drivers/twitter/ourtweets", method="GET",
                                  params={'sync': 1, 'max_id': nmi,})
                    
            stash_tweets(s.username, rj)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(rj,indent=2))

class OurDMSent(webapp.RequestHandler):
    def get(self):
        ps = { 'count': COUNT, }
        req = self.request
        mi = req.GET.get("max_id")
        if mi:
            mi = long(mi)
            ps['max_id'] = mi

        s = secret.OAuth.all().filter('service =','twitter').get()
        if not s: self.redirect(login_url(req))
        
        client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
        url = "http://api.twitter.com/1/direct_messages/sent.json"
        rs = client.make_request(url=url, token=s.token, secret=s.secret,
                                 additional_params=ps)
        rj = json.loads(rs.content)
        if len(rj) > 0:
            nmi = reduce(lambda x,y: min(x,y), [ long(tw['id']) for tw in rj ])
            is_sync = True if req.GET.get("sync") else False
            if is_sync:
                ss = models.SyncStatus.of_service(
                    s.service, "/drivers/twitter/dm/sent?sync=1")
                if nmi == mi:
                    ss.status = models.SYNC_STATUS.synchronized
                    ss.put()
                else:
                    taskqueue.add(url="/drivers/twitter/dm/sent", method="GET",
                                  params={'sync': 1, 'max_id': nmi,})
                    
            stash_tweets(s.username, rj)
        
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(rj,indent=2))

class OurDMReceived(webapp.RequestHandler):
    def get(self):
        ps = { 'count': COUNT, }
        req = self.request
        mi = req.GET.get("max_id")
        if mi:
            mi = long(mi)
            ps['max_id'] = mi

        s = secret.OAuth.all().filter('service =','twitter').get()
        if not s: self.redirect(login_url(req))

        client = oauth.TwitterClient(app_key, app_secret, callback_url(req))
        url = "http://api.twitter.com/1/direct_messages.json"
        rs = client.make_request(url=url, token=s.token, secret=s.secret,
                                 additional_params=ps)
        rj = json.loads(rs.content)
        if len(rj) > 0:
            nmi = reduce(lambda x,y: min(x,y), [ long(tw['id']) for tw in rj ])
            is_sync = True if req.GET.get("sync") else False
            if is_sync:
                ss = models.SyncStatus.of_service(
                    s.service, "/drivers/twitter/dm/received?sync=1")
                if nmi == mi:
                    ss.status = models.SYNC_STATUS.synchronized
                    ss.put()
                else:
                    taskqueue.add(url="/drivers/twitter/dm/received", method="GET",
                                  params={'sync': 1, 'max_id': nmi,})
                    
            stash_tweets(s.username, rj)
        
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(rj,indent=2))
 
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
    
class Sync(webapp.RequestHandler):
    def get(self, cmd):
        ss = models.SyncService.of_service("twitter")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(ss.tojson())

    def post(self, cmd):
        ss = models.SyncService.of_service("twitter")
        if not ss or ss.status == models.SVC_STATUS.needauth:
            self.response.set_status(400)
            return
        
        urls = map(lambda u: "/drivers/twitter/%s?sync=1" % u,
                   [ 'us', 'ourtweets', 'dm/sent', 'dm/received', ])
        if cmd == "start":
            for u in urls:
                s = models.SyncStatus.all().filter(
                    "service =", ss).filter("thread =", u).get()
                if not s: s = models.SyncStatus(service=ss, thread=u)

                if s.status != models.SYNC_STATUS.inprogress:
                    taskqueue.add(url=u, method="GET")
                    s.status = models.SYNC_STATUS.inprogress
                
                s.put()

        elif cmd == "stop":
            for u in urls:
                s = models.SyncStatus.all().filter(
                    "service =", ss).filter("thread =", u).get()
                if not s: continue
                
                if s.status == models.SYNC_STATUS.inprogress:
                    s.status = models.SYNC_STATUS.unsynchronized
                    s.put()

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(ss.tojson())

class Cron(webapp.RequestHandler):
    def get(self):
        taskqueue.add(url="/sync/twitter/start", method="POST")
