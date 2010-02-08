# Copyright (C) 2009 Anil Madhavapeddy <anil@recoil.org>
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
sys.path.append("../../perscon")
import config

sys.path.append("../../support")
from pkg_resources import require
require("simplejson")
require("keyring")
import keyring
import simplejson as sj
import Perscon_utils

def addr(service, account): return { 'ty': service, 'id': account, }

def stash_tweets(service, account, tweets, mode):
    info = { 'origin': 'com.twitter', 'account': account, }
    for tw in tweets:
        print >>sys.stderr, "raw:", sj.dumps(tw, indent=2)
        
        data = { 'meta': info.copy(), }

        tm = dateutil.parser.parse(tw['created_at'])
        data['meta']['mtime'] = time.mktime(tm.timetuple())
        data['meta']['text'] = tw['text']

        uid = hashlib.sha1(service+account+str(tw['id'])).hexdigest()
        data['uid'] = uid

        if mode == "to":
            try: data['frm'] = [addr(service, tw['from_user'])]
            except KeyError:
                data['frm'] = [addr(service, tw['user']['screen_name'])]
                
            try: data['to'] = [addr(service, tw['to_user'])]
            except KeyError:
                data['to'] = [addr(service, None)] ## XXX
        
        else:
            data['frm'] = [addr(service, account)]
            if 'in_reply_to_screen_name' in tw and tw['in_reply_to_screen_name']:
                data['to'] = [addr(service, tw['in_reply_to_screen_name'])]

        dataj = sj.dumps(data, indent=2)
        print dataj
        Perscon_utils.rpc("thing/%s" % (uid, ), data=dataj)

def retryOnError(label, c):
   tries = 0
   while True:
      print >> sys.stderr, "attempt #%d: %s" % (tries, label)
      try: return (c ())
      except twitter.api.TwitterError, e:
          print >> sys.stderr, "   error: %s" % str(e)
          tries += 1
          if tries > 6: raise e
          time.sleep(60 * 20)  # sleep for 20 minutes
         
def main():
    ## mort: this config stuff is a bit grim - really need a proper
    ## plugin interface
    configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "perscon", "perscon.conf")
    config.parse(configfile)
    uri = "http://localhost:%d/" % (config.port(),)
    Perscon_utils.init_url(uri)

    service = "twitter.com"
    username = config.user(service)
    password = keyring.get_password(service, username)

    ## mort: also note that by using Basic authentication the
    ## username/password pair are essentially being passed in the clear
    t = twitter.Twitter(username, password)

    ## 1. tweets mentioning us
    tsearch = twitter.Twitter(username, password, domain="search.twitter.com")
    pg = 1
    while True:
        rs = retryOnError("search pg=%d" % pg,
                          lambda: tsearch.search(rpp=90, page=pg, q=username))
        if len(rs['results']) == 0: break
        stash_tweets(service, username, rs['results'], mode="to")
        pg += 1
  
    ## 2. our own tweets
    pg = 1
    while True:
        rs = retryOnError("own_tweets %d" % (pg,),
                          lambda: t.statuses.user_timeline(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs, mode="to")
        pg += 1

    ## 3. our own retweets (stupid api - not included in above)
    pg = 1
    while True:
        rs = retryOnError("own_retweets %d" % (pg,),
                          lambda: t.statuses.retweeted_by_me(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs, mode="to") ## XXX mark as retweets?
        pg += 1
        
    ## 4. direct messages we sent 
    pg = 1
    while True:
        rs = retryOnError("direct_messages_sent %d" % (pg,),
                          lambda: t.direct_messages.sent(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs, mode="to") ## XXX mark as DMs?
        pg += 1
        
    ## 5. direct messages we received
    pg = 1
    while True:
        rs = retryOnError("direct_messages_received %d" % (pg,),
                          lambda: t.direct_messages(page=pg, count=200))
        if len(rs) == 0: break
        stash_tweets(service, username, rs, mode="to") ## XXX mark as DMs
        pg += 1

    ## 6. tweets from friends
    cr = -1
    friends = []
    while cr != 0:
        rs = retryOnError("get_friends cursor=%d" % cr,
                          lambda: t.friends.ids(cursor=cr))
        friends.extend(rs['ids'])
        cr = rs['next_cursor']

    print >> sys.stderr, "friends:", friends
    for friend in friends:
        pg = 1
        while True:
            rs = retryOnError(
                "friend_timeline %s %d" % (friend, pg),
                lambda: t.statuses.user_timeline(id=friend, page=pg, count=200))
            if len(rs) == 0: break
            stash_tweets(service, username, rs, mode="from")
            pg += 1
        print >> sys.stderr, "friend: %s done" % friend

if __name__ == "__main__": main()
