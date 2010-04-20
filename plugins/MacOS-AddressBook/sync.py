#!/usr/bin/python
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

import sys
sys.path.append ("../../support")
from pkg_resources import require
require ("simplejson")

import Perscon_utils
import simplejson
from datetime import datetime
import urllib2

from AppKit import *
import AddressBook
import objc
from AddressBook_util import *

# The names of fields in the export, and the corresponding property.
FIELD_NAMES=(
    ('last_name',   AddressBook.kABLastNameProperty),
    ('first_name',  AddressBook.kABFirstNameProperty),
    ('birthday',   AddressBook.kABBirthdayProperty),
    ('company',    AddressBook.kABOrganizationProperty),
    ('job',        AddressBook.kABJobTitleProperty),
    ('calendar',   AddressBook.kABCalendarURIsProperty),
    ('note',       AddressBook.kABNoteProperty),
    ('middle_name', AddressBook.kABMiddleNameProperty),
    ('title',      AddressBook.kABTitleProperty),
)

FIELD_NAMES_ARRAY=(
    ('address',    AddressBook.kABAddressProperty),
)

SERVICES=(
    ('http://aim.com/', AddressBook.kABAIMInstantProperty, None),
    ('xmpp', AddressBook.kABJabberInstantProperty, None),
    ('http://messenger.msn.com/', AddressBook.kABMSNInstantProperty, None),
    ('http://messenger.yahoo.com/', AddressBook.kABYahooInstantProperty, None),
    ('http://icq.com/', AddressBook.kABICQInstantProperty, None),
    ('http://www.ietf.org/rfc/rfc2368.txt', AddressBook.kABEmailProperty, None),
    ('sip', AddressBook.kABPhoneProperty, normalize_phone),
)

SERVICES_URL_LABELS=(
    ('http://twitter.com/', 'LDB:twitter'),
    ('http://skype.com/', 'LDB:skype'),
    ('http://facebook.com/', 'LDB:facebook'),
)

def encodeField(value):
    if value is None:
        return None
    
    if isinstance(value, AddressBook.NSDate):
        return float(value.timeIntervalSince1970())
    elif isinstance(value, AddressBook.NSCFDictionary):
        d = {}
        for k in value:
            d[k] = encodeField(value[k])
        return d
    elif isinstance(value, AddressBook.ABMultiValue):
        # A multi-valued property, merge them into a single string
        result = { }
        for i in range(len(value)):
            l = encodeField(value.labelAtIndex_(i))
            if not l or l == "":
               raise ValueError(l)
            if not l in result:
                result[l] = []
            result[l].append(encodeField(value.valueAtIndex_(i)))
        return result
    elif type(value) == objc.pyobjc_unicode:
        return unicode(value)
    else:
        print type(value)
        raise NotImplemented

def getField(p, fieldName):
    return encodeField(p.valueForProperty_(fieldName))

def writeRecord(p, uid, mtime):
    print "NEW: %s" % unicode(addressbook_name(p))
    m = { 'origin' : 'com.apple.addressbook', 'mtime' : mtime, 'uid' : uid, 'atts' : [] }
    for (fieldname, fieldkey) in FIELD_NAMES:
        v = getField(p, fieldkey)
        if v:
            m[fieldname] = unicode(v)
    for (fieldname, fieldkey) in FIELD_NAMES_ARRAY:
        def fn (p):
          for a in p:
            for x in a.keys():
              m[fieldname + "_" + x.lower()] = unicode(a[x])
        v = getField(p, fieldkey)
        if v:   
            if type(v) == dict:
                for k in v:
                   fn(v[k])
            else:
                fn(v)
           
    services = []
    for (fieldname, fieldkey, cb) in SERVICES:
        v = getField(p, fieldkey)
        def rc(f,i,c):
          return ( f, i )
        def fn(p, fname, cb):
          if not cb:
            cb = lambda x: x
          return map(lambda x: rc(fname,cb(x.lower()),uid) , p)
        if v:   
            if type(v) == dict:
                for k in v:
                    services.extend(fn(v[k], fieldname, cb))
            else:
                services.extend( fn(v[k], fieldname, cb))
        urls = getField(p, AddressBook.kABURLsProperty)
        for (fieldname, fieldkey) in SERVICES_URL_LABELS:
            if urls and fieldkey in urls:
               services.extend (map (lambda x: rc(fieldname, x, uid ), urls[fieldkey]) )
    m['services'] = services
    att=None
    imgdata = p.imageData()
    if imgdata:
        tiffData = NSImage.alloc().initWithData_(imgdata).TIFFRepresentation()
        bitmap = NSBitmapImageRep.alloc().initWithData_(tiffData)
        fileType = NSPNGFileType
        imageData = bitmap.representationUsingType_properties_(fileType, None)
        imageStr=str(imageData.bytes())
        auid = uid + ".png"
        ameta={ 'uid': auid, 'mime' : 'image/png' }
        att = (imageStr, ameta) 
        m['atts'] = [ auid ]
        
    return m, att

def main(argv = None):
    """ main entry point """

    ae = Perscon_utils.RPC ()
    book = AddressBook.ABAddressBook.sharedAddressBook()
    ae.log('com.apple.addressbook', 'Started contacts sync')
    for p in book.people():
        mtime_ts = getField(p, AddressBook.kABModificationDateProperty)
        mtime = datetime.fromtimestamp(mtime_ts)
        uid = getField(p, AddressBook.kABUIDProperty)
        tt = mtime.timetuple()
        m, att = writeRecord(p, uid, mtime_ts)
        mj = simplejson.dumps(m, indent=2)
        # upload attachment first
        if att:
          ae.att(att[1]['uid'], att[0], att[1]['mime'])
        # then contacts
        try:
         print mj
         r = ae.rpc ("person/%s" % uid, data=mj)
         print r.read()
        except urllib2.HTTPError as e: 
          print e.read ()
          print mj
          sys.exit(1)
    ae.log('com.apple.addressbook', 'Done contacts sync')
    
if __name__ == "__main__":
    main()
