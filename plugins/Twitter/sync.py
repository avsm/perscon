# Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>
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

import sys, time, os.path, pprint, hashlib

import twitter
import dateutil.parser

sys.path.append("../../support")
from pkg_resources import require
require("simplejson")

import simplejson as sj
import Perscon_utils, Perscon_config

Verbose = True

class TWTY:
    tweet = 'tweet'
    retweet = 'retweet'
    reply = 'reply'
    direct = 'direct'

def addr(service, account): return (service, account)

def stash_tweets(service, account, tweets):
    global ae
    info = { 'origin': 'com.twitter', 'account': account, }
    for tw in tweets:
        if Verbose:
            print >>sys.stderr, "raw:", sj.dumps(tw, indent=2)
       
        data = { 'origin': 'com.twitter' }
        data['meta'] = { 'type': TWTY.tweet }

        mtime = dateutil.parser.parse(tw['created_at'])
        data['mtime'] = time.mktime(mtime.timetuple())

        uid = "twitter:"+hashlib.sha1(service+account+str(tw['id'])).hexdigest()
        data['uid'] = uid

        auid = uid + ".txt"
        ae.att(auid, unicode(tw['text']), "text/plain")
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
            
        dataj = sj.dumps(data, indent=2)
        if Verbose: print >>sys.stderr, dataj
        ae.rpc('message/' + uid, data=dataj)

def retryOnError(label, c):
   tries = 0
   while True:
      print >> sys.stderr, "attempt #%d: %s" % (tries, label)
      try: return (c ())
      except Exception, e:
          print >> sys.stderr, "   error: %s" % str(e)
          tries += 1
          if tries > 6: raise
          time.sleep(60 * 20)  # sleep for 20 minutes

ae = Perscon_utils.AppEngineRPC()

def main():
    global Verbose
    

    service = "http://twitter.com/"
    username = Perscon_config.twitter_username
    password = Perscon_config.twitter_password

    ## mort: also note that by using Basic authentication the
    ## username/password pair are essentially being passed in the clear
    t = twitter.Twitter(username, password)

    ## 1. tweets mentioning us
#    tsearch = twitter.Twitter(username, password, domain="search.twitter.com")
#    pg = 1
#    while True:
#        rs = retryOnError("search pg=%d" % pg,
#                          lambda: tsearch.search(rpp=90, page=pg, q=username))
#        if len(rs['results']) == 0: break
#        stash_tweets(service, username, rs['results'])
#        pg += 1
  
    ## 2. our own tweets
    pg = 1
    while True:
        rs = retryOnError("own_tweets %d" % (pg,),
                          lambda: t.statuses.user_timeline(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs)
        pg += 1

    ## 3. our own retweets (stupid api - not included in above)
#    pg = 1
#    Verbose = True
#    while True:
#        rs = retryOnError("own_retweets %d" % (pg,),
#                          lambda: t.statuses.retweeted_by_me(page=pg, count=200))
#        if len(rs) == 0: break
#        stash_tweets(service, username, rs)
#        pg += 1
        
    ## 4. direct messages we sent 
    pg = 1
    while True:
        rs = retryOnError("direct_messages_sent %d" % (pg,),
                          lambda: t.direct_messages.sent(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs)
        pg += 1
        
    ## 5. direct messages we received
    pg = 1
    while True:
        rs = retryOnError("direct_messages_received %d" % (pg,),
                          lambda: t.direct_messages(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs)
        pg += 1

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

if __name__ == "__main__": main()
