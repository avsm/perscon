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

import datetime, time, sys, os, hashlib, pprint, glob, re

sys.path.append("../../support")
from pkg_resources import require
require("simplejson")
import simplejson as sj
import Perscon_utils, Perscon_config

import skrype

INFO = { 'account': Perscon_config.skype_username,
         'service': 'skype',
         }

MIN_TIME = 100000000
MAX_TIME = 10000000000
           
Displaynames = {} ## username: displayname
Usernames = {}    ## displayname: username
Members = {}      ## chatid: chatmembers

def safe_encode(v):
    if isinstance(v, str):
        while True:
            try: v = v.decode("utf8").encode("utf8")
            except UnicodeDecodeError, e:
                v = v[:e.start]+v[e.end:]
                continue
            break
    
    elif isinstance(v, dict):
        v = dict([ (key,safe_encode(val)) for (key,val) in v.items() ])
    
    return v

def extract_chatid(cs):
    def _validate(s):
        return (s.startswith('#') and "$" in s and ";" in s)

    if isinstance(cs, str):
        if _validate(cs): return cs
    elif isinstance(cs, list):
        cs = filter(_validate, cs)
        if len(cs) == 1: return cs[0]

def extract_body(bs):
    def _validate(s):
        try: s.decode("utf8").encode("utf8")
        except UnicodeDecodeError:
            return False
        return True
    
    if isinstance(bs, str): return safe_encode(bs)
    elif isinstance(bs, list):
        bs = filter(_validate, bs)
        if len(bs) == 1: return safe_encode(bs[0])

def extract_timestamp(ts):
    def _validate(s): return (MIN_TIME <= s <= MAX_TIME)

    if isinstance(ts, int):
        if _validate(ts): return ts
    elif isinstance(ts, list):
        ts = filter(_validate, ts)
        if len(ts) == 1: return ts[0]

def extract_name(ns):
    if not ns: return
    return extract_body(ns)

_cid_re = re.compile("^#(.*)/\$(.*);\w+$")
def split_chatid(c):
    m = _cid_re.match(c)
    if not m: return [ 'unknown' ]
    else:
        return list(m.groups())

def process_message(record):
    rec = record['value']['items']
    if 'message' not in rec: return
    if 'chatid' not in rec: return
    if 'timestamp' not in rec: return

    raw = record['raw']    

    chatid = extract_chatid(rec['chatid'])
    if not chatid:
        print >>sys.stderr, "bad chatid!  record:%s" % (pprint.pformat(record),)
        return
    
    body = extract_body(rec['message'])
    if not body:
        print >>sys.stderr, "bad body!  record:%s" % (pprint.pformat(record),)
        return
        
    ts = extract_timestamp(rec['timestamp'])
    if not ts:
        print >>sys.stderr, "bad timestamp!  record:%s" % (pprint.pformat(record),)
        return

    ## sender
    un = extract_name(rec.get('username'))
    dn = extract_name(rec.get('displayname'))
    if un and dn:
        Usernames[dn] = un
        Displaynames[un] = dn

    if un: sender = un
    else:
        if dn and dn in Usernames: sender = Usernames[dn]
        else: return

    ## receiver
    if chatid in Members: receivers = Members[chatid][:]
    else:
        receivers = split_chatid(chatid)
        print >>sys.stderr, "unknown chatid!  chatid:%s  extracted:%s" % (
            chatid, receivers)
        Members[chatid] = receivers[:]
    if sender in receivers: receivers.remove(sender)

    ## data for posting
    data = { 'meta': INFO.copy(),
             'origin': 'com.skype',
             }
    data['frm'] = [{ 'ty': 'im', 'proto': [ 'http://skype.com', sender ], } ]
    data['tos'] = map(lambda receiver:
                      { 'ty': 'im', 'proto': [ 'http://skype.com', receiver ], },
                      receivers)
    data['mtime'] = ts

    uid = hashlib.sha1("%s:%s:%s:%s" % (
        INFO['account'], INFO['service'],
        chatid, record['value']['seqno'])).hexdigest()
    data['uid'] = uid

    thread = hashlib.sha1("%s:%s:%s" % (
        INFO['account'], INFO['service'], chatid)).hexdigest()
    data['thread'] = thread

    ruid = "%s.raw" % (uid,)
    ae.att(ruid, raw, "application/octet-stream")
    
    auid = "%s.txt" % (uid,)
    ae.att(auid, body, "text/plain")
    
    data['atts'] = [auid, ruid]
    dataj = sj.dumps(data, indent=2)
##     print "data: %s" % (dataj,)
    ae.rpc('message/%s' % uid, data=dataj)

def process_member(record):
    rec = record['value']['items']
    chatid = rec['chatid']
    member = rec['member']

    if chatid not in Members: Members[chatid] = []
    Members[chatid].append(member)

def main():
    logdir = "%s/Library/Application Support/Skype/%s" % (
        os.getenv("HOME"), Perscon_config.skype_username,)
    if not os.path.isdir(logdir):
        print >> sys.stderr, "Unable to find Skype log dir in: %s" % logdir
        sys.exit(1)
    
    global ae
    ae = Perscon_utils.RPC()
    fns = glob.glob("%s/*.dbb" % (logdir))

    for (ty, rec) in skrype.splice(fns, with_junk=False, with_raw=True):
        if ty in ('unknown', 'profiles', ):
            continue

        if ty in ('mucs', ):
            pprint.pprint((ty, rec))
        try:
            if ty in ('messages', 'mucs', ):
                process_message(rec)
            elif ty in ('chatmembers', ):
                process_member(rec)
                                   
        except:
            pprint.pprint((ty, rec))
            raise

if __name__ == "__main__": main()
