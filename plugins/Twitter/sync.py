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

import sys, time, os.path
sys.path.append("../../support")
import simplejson

import twitter
import dateutil.parser
sys.path.append("../../perscon")
import config

## mort: keyring, getpass imports from python-keyring-lib,
## <http://bitbucket.org/kang/python-keyring-lib/>
import keyring, getpass

def stash_tweets(service, account, tweets, mode="from"):
    info = { 'origin': 'com.twitter', 'account': account, }
    for tweet in tweets:
        st = tweet['status']
        data = { 'meta': info.copy(), }

        tm = st['created_at']
        time_parsed = dateutil.parser.parse(tm)
        tt = time_parsed.timetuple()
        time_float = time.mktime(tt)
        data['meta']['mtime'] = time_float

        body = st['text']
        data['meta']['text'] = body        

        ## XXX verify this is appropriate uid
        uid = hashlib.sha1(service+account+st['id']).hexdigest()
        data['uid'] = uid

        ## XXX verify correct frm/to interpretation wrt api
        if mode == "to":
            data['frm'] = [tweet['screen_name']]
            data['to'] = [account]
        else:
            data['frm'] = [account]
            if 'in_reply_to_screen_name' in st and st['in_reply_to_screen_name']:
                data['to'] = st['in_reply_to_screen_name']

        dataj = simplejson.dumps(data, indent=2)
        print dataj
        Perscon_utils.rpc("thing/%s" % (uid, ), data=dataj)

def retryOnError(label, c):
   tries = 0
   while True:
      print >> sys.stderr, "attempt #%d: %s" % (tries, label)
      try: return (c ())
      except twitter.api.TwitterError, e:
          print >> sys.stderr, "   error: %s" % str(e)
          if "page parameter out of range" in e.message: return []
          tries += 1
          if tries > 6: raise e
##           time.sleep(60 * 20)  # sleep for 20 minutes
         
def main():
    ## mort: this config stuff is a bit grim - really need a proper
    ## plugin interface
    configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "perscon", "perscon.conf")
    config.parse(configfile)
    service = "twitter.com"
    username = config.user(service)
    password = keyring.get_password(service, username)

    t = twitter.Twitter(username, password)
    tsearch = twitter.Twitter(username, password, domain="search.twitter.com")

    ## global search for all tweets to username (self)
    pg = 1
    while True:
        print >> sys.stderr, "search: pg=%d" % pg
        fs = retryOnError("search",
                          lambda: tsearch.search(rpp=90, page=pg, to=username))
        if len(fs) == 0: break
        stash_tweets(service, username, fs['results'], mode="to")
        pg += 1
  
    ## fill out the list of friends, having seeded it with username
    pg = 1
    friends = [username]
    while True:
        fs = retryOnError("get_friends", lambda: t.statuses.friends(page=pg))
        if len(fs) == 0: break
        for f in retryOnError("get_friends_page_%d" % pg,
                              lambda: t.statuses.friends(page=pg)):
            friends.append(f['screen_name'])
        pg += 1

    ## process all friends tweets, including username == self
    for friend in friends:
        pg = 1
        print >> sys.stderr, "friend: %s   pg: %d" % (friend, pg)
        while True:
            st = retryOnError("timeline_%s_%d" % (friend, pg),
                              lambda: t.statuses.user_timeline(id=friend, page=pg, count=200))
            if len(st) == 0: break
            stash_tweets(service, username, st, mode="from")
            pg += 1
        print >> sys.stderr, "friend: %s done" % friend
        
if __name__ == "__main__": main()
