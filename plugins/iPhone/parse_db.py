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
# parse the SQLITE3 database in the iPhone into JSON for the LifeDB

import sqlite3
import sys, os

sys.path.append ("../../support")
from pkg_resources import require
require ("simplejson")
import simplejson
from datetime import datetime
import getopt, urllib2
import Perscon_utils

# CREATE TABLE message (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, 
# address TEXT, date INTEGER, text TEXT, flags INTEGER, replace INTEGER, 
# svc_center TEXT, group_id INTEGER, association_id INTEGER, height INTEGER, 
# UIFlags INTEGER, version INTEGER);

from AppKit import *
import AddressBook

def my_number():
    book = AddressBook.ABAddressBook.sharedAddressBook()
    phones = book.me().valueForProperty_(AddressBook.kABPhoneProperty)
    mob_res = []
    other_res = []
    if phones:
        for i in range(len(phones)):
            num = phones.valueAtIndex_(i)
            lab = phones.labelAtIndex_(i)
            if lab == AddressBook.kABPhoneMobileLabel:
                mob_res.append(num)
            else:
                other_res.append(num)

    if len(mob_res) > 0:
        return mob_res[0]
    elif len(other_res) > 0:
        return other_res[0]
    raise ValueError, "couldnt determine your phone number from address book"

def usage(ret=2):
    print "Usage: %s [-u <IPhone UUID>] -m [call|sms] <SMS sqlite.db>" % sys.argv[0]
    sys.exit(ret)
    
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:m:o:")
    except getopt.GetoptError, err:
        print str(err)
        usage(2)
    ae = Perscon_utils.AppEngineRPC()
    uid_prefix = "Default_iPhone"
    mode=None
    for o,a in opts:
        if o == '-h':
            usage(0)
        elif o == '-u':
            uid_prefix=a
        elif o == '-m':
            if a == 'sms':
                mode = 'SMS'
            elif a== 'call':
                mode = 'Call'
            else:
                usage()
    if len(args) != 1 or not mode:
        usage()
    conn = sqlite3.connect(args[0])
    c = conn.cursor()
    if mode == 'SMS':
        res,atts = parseSMS(c, uid_prefix)
        for uid in atts:
            ae.att(uid, atts[uid], "text/plain")
    elif mode == 'Call':
        res = parseCall(c, uid_prefix)
    for uid in res:
        mj = simplejson.dumps(res[uid], indent=2)
        try:
          ae.rpc ('message/' + uid, data=mj)
        except urllib2.HTTPError as e: 
          print e.read ()
          print mj
          sys.exit(1)

def normalize_phone(p):
    import re
    if len(p) < 1:
        return p
    pn = re.sub('[^0-9|\+]','',p)
    if len(pn) < 1:
        return pn
    if pn[0:1] == "00" and len(pn) > 2:
        pn = "+%s" % pn[2:]
    elif pn[0]  == '0':
        pn = "+44%s" % pn[1:]
    return pn

def parseSMS(c, uid_prefix):
    mynum = normalize_phone(my_number())
    c.execute('''
        SELECT group_member.address,text,flags,replace,version,date
        FROM message INNER JOIN group_member ON group_member.group_id = message.group_id;
    ''')
    sms={}
    atts={}
    for row in c:
        e = {}
        m = {}
        if row[1]:
          m['number'] = normalize_phone(row[0])
          m['flags'] = str(row[2])
          m['replace'] = str(row[3])
          m['version'] = str(row[4])
          e['mtime'] = float(row[5])
          e['origin'] = 'iphone:sms'
          if m['flags'] == "2":
            e['frm'] = [ {'ty':'phone', 'value':m['number']} ]
            e['to'] = [ {'ty':'phone', 'value':mynum} ]
          elif m['flags'] == "3":
            e['frm'] = [ {'ty':'phone', 'value':mynum} ]
            e['to'] = [ {'ty':'phone', 'value':m['number']} ]
          else:
            e['frm'] = []
            e['to'] = []
          uid = "%s.SMS.%s" % (uid_prefix, m['number'])
          auid = "%s.txt" % uid
          e['atts'] = [ auid ]
          e['meta'] = m
          e['uid'] = uid
          e['tags'] = ['phone','sms']
          if len(m['number']) > 6:
              atts[auid] = unicode(row[1])
              sms[uid] = e
    return sms, atts

def parseCall(c, uid_prefix):
    mynum = normalize_phone(my_number())
    c.execute('''
        SELECT * from call
    ''')
    call={}
    for row in c:
        # XXX needs to include the phone UUID as well
        e = {}
        m = {}
        m['number'] = normalize_phone(row[1])
        e['mtime'] = float(row[2])
        m['duration'] = str(row[3])
        m['flags'] = str(row[4])
        m['weirdid'] = str(row[5])
        e['origin'] = 'iphone:call'
        e['atts'] = []
        if m['flags'] == "4":
            e['frm'] = [ {'ty':'phone', 'value':m['number']} ]
            e['to'] = [ {'ty':'phone', 'value':mynum} ]
        elif m['flags'] == "5":
            e['frm'] = [ {'ty':'phone', 'value':mynum} ]
            e['to'] = [ {'ty':'phone', 'value':m['number']} ]
        else:
            e['frm'] = []
            e['to'] = []
        uid = "%s.Call.%s" % (uid_prefix, row[0])
        e['meta'] = m
        e['uid'] = uid
        e['atts'] = []
        e['tags'] = ['phone','call']
        if len(m['number']) > 6:
            call[uid] = e
    return call
    
if __name__ == "__main__":
    main()

