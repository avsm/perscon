# Copyright (C) 2009,2010 Anil Madhavapeddy <anil@recoil.org>
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
# Parse and sync Adium logs with a LifeDB

import os, sys, time, hashlib, base64, xml, dateutil.parser
from xml.dom import minidom 

sys.path.append("../../support")
from pkg_resources import require
require("simplejson")
require("lxml")
import lxml.html, simplejson
import Perscon_utils

ae = None

SERVICES={
    'aim':('im','http://aim.com'),
    'gtalk':('im','xmpp'),
    'jabber':('im','xmpp'),
    'msn' : ('im', 'http://messenger.msn.com'),
    'yahoo!': ('im','http://messenger.yahoo.com'),
    'icq' : ('im','http://icq.com'),
    'facebook' : ('url','fb://profile/'),
    'irc' : ('url','irc://'),
    'twitter' : ('url','http://twitter.com/'),
}

def addr(service, sender):
    ty,va = SERVICES[service]
    if ty == 'im':
      return {'ty':ty, 'proto' : [va, sender]}
    else:
      return {'ty':ty, 'value': va+sender }

def parseLog(chatlog):
    global ae
    try: tree = minidom.parse(chatlog)
    except xml.parsers.expat.ExpatError, err:
        print >> sys.stderr, "Warning: %s is not XML, skipping" % chatlog
        return

    chats = tree.getElementsByTagName('chat')
    for chat in chats:
        thread = None
        account = chat.getAttribute('account')
        service = chat.getAttribute('service').lower()
        version = chat.getAttribute('version')
        transport = chat.getAttribute('transport')
        uri = chat.namespaceURI

        info = { 'account': account,
                 'service': service,
                 'uri': uri
                }        
        if version != "": info['version'] = version
        if transport != "": info['transport'] = transport

        msgs = chat.getElementsByTagName('message')
        # need to accumulate the list of participants in the chat based on who
        # talks that isnt the sender
        participants = []
        for msg in msgs:
            sender = msg.getAttribute('sender')
            if sender != account and sender not in participants:
               participants.append(sender)
        
        for msg in msgs:
            data = { 'meta': info.copy(), 'origin': 'com.adium' }
            
            sender = msg.getAttribute('sender')
            
            tm = msg.getAttribute('time')
            time_parsed = dateutil.parser.parse(tm)
            tt = time_parsed.timetuple()
            time_float = time.mktime(tt)
            data['mtime'] = time_float
            
            # very dodgily ignoring unicode errors here, but copes
            # with some malformed messages
            body = u''.join(
                map(lambda x: unicode(x.toxml(encoding='utf-8'), errors='ignore'),
                    msg.childNodes))
            body = lxml.html.fromstring(body).text_content()

            # this message originated from the current user, so its from us
            # and to the participants
            data['frm'] = [ addr(service,sender) ]
            if sender == account:
                data['tos'] = map(lambda x: addr(service,x), participants)
            else:
                data['tos'] = [ addr(service, account)]

            uid = hashlib.sha1(service+account+sender+tm+body).hexdigest()
            data['uid'] = uid
            if not thread: thread = uid
            data['thread'] = thread
            auid = uid + ".txt"
            data['atts'] = [auid]
            # XXX only 2010 so far
            if tt.tm_year > 2009 and body != '':
                dataj = simplejson.dumps(data, indent=2)
                ae.att(auid, body, "text/plain")
                ae.rpc('message/%s' % uid, data=dataj)

def main():
    logdir = "%s/Library/Application Support/Adium 2.0/Users/Default/Logs/" % os.getenv("HOME")
    global ae
    ae = Perscon_utils.RPC()
    if not os.path.isdir(logdir):
        print >> sys.stderr, "Unable to find Adium log dir in: %s" % logdir
        sys.exit(1)
    for root, dirs, files in os.walk(logdir):
        for f in files:
            logfile = os.path.join(root, f)
            parseLog(logfile)
    
if __name__ == "__main__":
    main()
