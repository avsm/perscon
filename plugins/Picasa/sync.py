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
import urllib2
import hashlib
import config
import mimetypes

import gdata.photos
import gdata.photos.service

import keyring, getpass


def check_exists(photo_id):
  
  pass

def main(argv = None):
  """ main entry point """

  configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "perscon", "perscon.conf")
  config.parse(configfile)
  service = "google.com"
  username = config.user(service)
  password = keyring.get_password(service, username)

  gd_client = gdata.photos.service.PhotosService()
  gd_client.email = username
  gd_client.password = password
  gd_client.source = 'py-perscon-v01'
  gd_client.ProgrammaticLogin()

  uri = "http://localhost:5985/"
  Perscon_utils.init_url(uri)

  #####
  # Get pictures from Picasa
  #####

  albums = gd_client.GetUserFeed(user=username)
  # iterate over albums
  for album in albums.entry:
    print 'title: %s, number of photos: %s, id: %s' % (album.title.text,
      album.numphotos.text, album.gphoto_id.text)
    album_id = album.gphoto_id.text
    # iterate over pictures
    photos = gd_client.GetFeed('/data/feed/api/user/%s/albumid/%s?kind=photo' % 
      (username, album_id))
    for photo in photos.entry:
      print 'Photo title:', photo.title.text
      image_url = photo.content.src
      uid = photo.gphoto_id.text
      mime,mime_enc = mimetypes.guess_type(photo.content.src)
      if not mime:
         mime = 'application/octet-stream'
      fin = urllib2.urlopen(image_url)
      data = fin.read()
      fin.close()
      Perscon_utils.rpc('att/'+uid, headers={'Content-type':mime,'Content-length':len(data)}, data=data)
      tstamp = photo.timestamp.text
      m = {'origin':'com.google.picasa', 'mtime':tstamp, 'att': [uid], 'uid': uid, 'tags':[] }
      meta={}
#      if 'Rating' in img:
#          meta['rating'] = img['Rating']
#      if 'Comment' in img and img['Comment'] != '':
#          meta['comment'] = img['Comment']
#      if 'Keywords' in img:
#          kw = map(lambda x: keywords[x], img['Keywords'])
#          m['tags'] = kw
#      if 'Caption' in img:
#          meta['caption'] = img['Caption']
#      meta['file_path'] = relpath(img_path, base)

  #####
  # Push pictures to Picasa
  #####

  


if __name__ == "__main__":
    main()
