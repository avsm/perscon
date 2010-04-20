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

import sys
sys.path.append ("../../support")
from pkg_resources import require
require ("simplejson")

import plistlib, os, shutil, mimetypes
import sqlite3, EXIF
import simplejson
from datetime import datetime
from CoreFoundation import kCFAbsoluteTimeIntervalSince1970
from AppKit import *
import AddressBook,hashlib
import tempfile,filecmp
import Perscon_utils

def relpath(path, start):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = os.path.abspath(start).split(os.path.sep)
    path_list = os.path.abspath(path).split(os.path.sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    return os.path.join(*rel_list)

def ti_to_tt(ti):
    tstamp = ti + kCFAbsoluteTimeIntervalSince1970
    tt = datetime.fromtimestamp(tstamp).timetuple()
    return (tstamp,tt)

def DmsToDecimal(degree_num, degree_den, minute_num, minute_den,
                 second_num, second_den):
  """Converts the Degree/Minute/Second formatted GPS data to decimal degrees.

  Args:
    degree_num: The numerator of the degree object.
    degree_den: The denominator of the degree object.
    minute_num: The numerator of the minute object.
    minute_den: The denominator of the minute object.
    second_num: The numerator of the second object.
    second_den: The denominator of the second object.

  Returns:
    A deciminal degree.
  """

  degree = float(degree_num)/float(degree_den)
  minute = float(minute_num)/float(minute_den)/60
  second = float(second_num)/float(second_den)/3600
  return degree + minute + second


def GetGps(data):
  """Parses out the GPS coordinates from the file.

  Args:
    data: A dict object representing the Exif headers of the photo.

  Returns:
    A tuple representing the latitude, longitude, and altitude of the photo.
  """

  lat_dms = data['GPS GPSLatitude'].values
  long_dms = data['GPS GPSLongitude'].values
  latitude = DmsToDecimal(lat_dms[0].num, lat_dms[0].den,
                          lat_dms[1].num, lat_dms[1].den,
                          lat_dms[2].num, lat_dms[2].den)
  longitude = DmsToDecimal(long_dms[0].num, long_dms[0].den,
                           long_dms[1].num, long_dms[1].den,
                           long_dms[2].num, long_dms[2].den)
  if data['GPS GPSLatitudeRef'].printable == 'S': latitude *= -1
  if data['GPS GPSLongitudeRef'].printable == 'W': longitude *= -1
  altitude = None

  try:
    alt = data['GPS GPSAltitude'].values[0]
    altitude = alt.num/alt.den
    if data['GPS GPSAltitudeRef'] == 1: altitude *= -1

  except KeyError:
    altitude = 0

  return latitude, longitude, altitude

def parse_photos():
    ae = Perscon_utils.RPC()
    home = os.getenv("HOME") or exit(1)
    book = AddressBook.ABAddressBook.sharedAddressBook()
    addrs = book.me().valueForProperty_(AddressBook.kABEmailProperty)
    myemail = addrs.valueAtIndex_(addrs.indexForIdentifier_(addrs.primaryIdentifier()))
    fname = book.me().valueForProperty_(AddressBook.kABFirstNameProperty)
    lname = book.me().valueForProperty_(AddressBook.kABLastNameProperty)
    name = "%s %s" % (fname, lname)
    from_info = [ {'ty':'email', 'value':myemail } ]
    base = os.path.join(home, "Pictures/iPhoto Library")
    idb = os.path.join(base, 'iPhotoMain.db')
    fdb = os.path.join(base, 'face.db')
    conn = sqlite3.connect('')
    c = conn.cursor()
    c.execute("attach database '%s' as i" % idb)
    c.execute("attach database '%s' as f" % fdb)
    sql = "select f.face_name.name,f.face_name.email,relativePath from i.SqFileInfo inner join i.SqFileImage on (i.SqFileImage.primaryKey = i.SqFileInfo.primaryKey) inner join i.SqPhotoInfo on (i.SqFileImage.photoKey = i.SqPhotoInfo.primaryKey) inner join f.detected_face on (f.detected_face.image_key = i.SqFileImage.photoKey) inner join f.face_name on (f.detected_face.face_key = f.face_name.face_key) where f.face_name.name != '' and relativePath=?"
    fname = "%s/Pictures/iPhoto Library/AlbumData.xml" % os.getenv("HOME")
    pl = plistlib.readPlist(fname)

    version="%s.%s" % (pl['Major Version'], pl['Minor Version'])
    app_version = pl['Application Version']
    if not (app_version.startswith('8.1')):
        print >> sys.stderr, "This script only works with iPhoto 8.1, found version %s" % app_version
        exit(1)
    images = pl['Master Image List']
    keywords = pl['List of Keywords']
    rolls = pl['List of Rolls']

    for roll in rolls:
        roll_id = roll['RollID']
        thread_msg = None
        for img_id in roll['KeyList']:
            img = images[img_id]
            thumb_path = img['ThumbPath']
            if 'OriginalPath' in img:
                img_path = img['OriginalPath']
            else:
                img_path = img['ImagePath']
            tstamp,tt = ti_to_tt(img['DateAsTimerInterval'])
            if tt.tm_year > 2009:
                fin = open(img_path, 'rb')
                meta={}
                try:
                    mtags = EXIF.process_file(fin)
                    gps = GetGps(mtags)
                    meta['lat'] = str(gps[0])
                    meta['lon'] = str(gps[1])
                except:
                    pass
                fin.close()
                if 'lat' in meta:
                    loc = { 'lat': meta['lat'], 'lon': meta['lon'], 'url':'http://apple.com/iphoto', 'date':tstamp }
                    locj = simplejson.dumps(loc, indent=2)
                    ae.rpc('loc', data=locj)
                rel_path = (relpath(img_path, base),)
                root,ext = os.path.splitext(img_path)
                uid = img['GUID'] + ext
                if thread_msg:
                    thread = thread_msg
                else:
                    thread = None
                    thread_msg = uid
                mime,mime_enc = mimetypes.guess_type(img_path)
                if not mime:
                   mime = 'application/octet-stream'
                fin = open(thumb_path, 'rb')
                data = fin.read()
                fin.close()
                m = {'origin':'com.apple.iphoto', 'mtime':tstamp, 'atts': [uid], 'uid': uid,  'thread': thread, 'tags':[] }
                if 'Rating' in img:
                    meta['rating'] = str(img['Rating'])
                if 'Comment' in img and img['Comment'] != '':
                    meta['comment'] = img['Comment']
                if 'Keywords' in img:
                    kw = map(lambda x: keywords[x], img['Keywords'])
                    m['tags'] = kw
                if 'Caption' in img:
                    meta['caption'] = img['Caption']
                meta['file_path'] = relpath(img_path, base)
                c.execute(sql, rel_path)
                m['frm'] = from_info
                m['to'] = []
                for row in c:
                   fname=row[0]
                   email=row[1]
                   if email:
                      m['to'].append({'ty':'email', 'value':email})
                m['meta'] = meta
                mj = simplejson.dumps(m, indent=2)
                print mj
                ae.att(uid, data, mime)
                ae.rpc('message/'+uid, data=mj)

def main():
    parse_photos()

if __name__ == "__main__":
    main()
