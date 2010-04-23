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
sys.path.append ("../../perscon")
from pkg_resources import require
require ("simplejson")

import plistlib, os, shutil, mimetypes, time, hashlib
import sqlite3, EXIF, mimetypes
import simplejson
from datetime import datetime
import dateutil.parser
import Perscon_utils, config

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


def main():
    uri = "http://localhost:5985/"
    Perscon_utils.init_url (uri)

    configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "perscon", "perscon.conf")
    config.parse(configfile)
    base = config.get('photofiles', 'base')
    print "base dir is %s" % base

    for root, dirs, files in os.walk(base):
      for f in files:
        skip = False
        fname = os.path.join(root, f)
        meta = {}
        root_name,ext = os.path.splitext(fname)
        fin = open(fname, 'rb')
        try:
          print "reading %s" % fname
          data = fin.read()
          fin.seek(0)
          exif_tags = EXIF.process_file(fin)
        except:
          print >> sys.stderr, "error reading: %s" % fname
          skip = True
        finally:
          fin.close()
        if skip or (exif_tags == {}):
          print "skipping"
          continue
        if exif_tags.has_key('EXIF DateTimeOriginal'):
          raw = str(exif_tags['EXIF DateTimeOriginal'])
          tm = dateutil.parser.parse(raw)
          tt = tm.timetuple()
        else:
          tt = datetime.fromtimestamp(os.path.getmtime(fname)).timetuple()
        tstamp = time.mktime(tt)
        guid = hashlib.md5(file(fname).read()).hexdigest()
        uid = guid + ext
        m = { 'type':'org.perscon.photofiles', 'mtime':tstamp, 'att': [uid], 'uid': guid, 'frm': [], 'tos':[] }
#        rpath = relpath(root,base)
        print base
        print fname
        m['caption'] = os.path.join(base, os.path.basename(fname))
        mime,mime_enc = mimetypes.guess_type(fname)
        Perscon_utils.rpc('att/'+uid, headers={'content-type': mime,'content-length': len(data)}, data=data)
        meta['file_path'] = fname
        m['meta'] = meta
        mj = simplejson.dumps(m, indent=2)
        print mj
        Perscon_utils.rpc('thing/' + uid, data=mj)
        


if __name__ == "__main__":
    main()
