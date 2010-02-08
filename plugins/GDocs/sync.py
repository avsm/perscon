#!/usr/bin/python
# Copyright (C) 2010 Malte Schwarzkopf <malte@malteschwarzkopf.de>
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
sys.path.append ("../../support")
sys.path.append ("../../perscon")
from pkg_resources import require
require ("simplejson")

import Perscon_utils
import simplejson
from datetime import *
#import urllib2
import hashlib
import config

import gdata.docs
import gdata.docs.service

import keyring, getpass

def parseObject(entry, client):
    """Parses a Google Docs entry (document) and stores it."""
    m = { 'origin':'com.google.docs' }

    # Parse the date stamp returned by the GDocs API
    # in the format 2010-01-31T17:07:39.183Z
    d = datetime.strptime(entry.updated.text, "%Y-%m-%dT%H:%M:%S.%fZ")
    m['mtime'] = time.mktime(d.timetuple())

    info = { 'type': entry.GetDocumentType(), 'uri': entry.id.text }

    acl_feed = client.GetDocumentListAclFeed(entry.GetAclLink().href)
    readers = []
    writers = [] 
    for acl_entry in acl_feed.entry:
      # Set 'from' to be the document owner
      if (acl_entry.role.value == 'owner'):
        m['frm'] = [{ 'ty' : entry.GetDocumentType(), 'id': acl_entry.scope.value }]
      # Gather readers and writers
      elif (acl_entry.role.value == 'writer'):
        writers.append(acl_entry.scope.value)
      elif (acl_entry.role.value == 'reader'):
        readers.append(acl_entry.scope.value)
      else:
        print "ERROR: unrecognised ACL detected"
      print '%s - %s (%s)' % (acl_entry.role.value, acl_entry.scope.value, acl_entry.scope.type)

    # Map writers to 'to' field
    m['to'] = map(lambda x: { 'ty': entry.GetDocumentType(), 'id' : x }, writers)

    # Map readers to 'cc' field
    #m['cc'] = map(lambda x: { 'ty': entry.GetDocumentType(), 'id' : x }, readers)

    meta={}
    meta.update(info)
    m['meta'] = meta 

    h = hashlib.sha1()
    h.update(entry.title.text)
    h.update(entry.resourceId.text)
    uid = h.hexdigest()
    m['uid'] = uid
    mj = simplejson.dumps(m,indent=2)
#    print mj
    Perscon_utils.rpc('thing/' + uid, data=mj)

# TODO: store document contents as attachments
#   Perscon_utils.rpc('att/'+uid, headers={'Content-type':mime,'Content-length':len(data)}, data=data)

def main(argv = None):
    """ main entry point """

    configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "perscon", "perscon.conf")
    config.parse(configfile)
    service = "google.com"
    username = config.user(service)
    password = keyring.get_password(service, username)

    gd_client = gdata.docs.service.DocsService(source='py-perscon-v01')
    gd_client.ClientLogin(username, password)

    uri = "http://localhost:5985/"
    Perscon_utils.init_url (uri)

    feed = gd_client.GetDocumentListFeed()
    if not feed.entry:
      print 'No items found.\n'
    for entry in feed.entry:
      parseObject(entry, gd_client)

    
if __name__ == "__main__":
    main()
