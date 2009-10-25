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

from xml.etree import ElementTree
import base64, os, sys
import tempfile, getopt, plistlib
import datetime, time, uuid, shutil

sys.path.append ("../support")
from pkg_resources import require
require ("simplejson")

import Perscon_utils
import simplejson

def stripData(pl, attachments):
    if type(pl) == plistlib._InternalDict:
        d={}
        for k in pl.keys():
            d[k] = stripData(pl[k], attachments)
        return d
    elif isinstance(pl, plistlib.Data):
        if pl.data[0:6] == 'bplist':
            fout = tempfile.NamedTemporaryFile()
            fout.write(pl.data)
            fout.flush()
            status = os.system("plutil -convert xml1 %s" % fout.name)
            if not status == 0:
                fout.close()
                print >> sys.stderr, "error parsing binary plist"
                sys.exit(2)
            p = plistlib.readPlist(fout.name)
            fout.close()
            return stripData(p, attachments)
        else:
            uid = uuid.uuid4().hex
            attachments[uid] = pl.data
            return {'_uuid': unicode(uid) }
    elif type(pl) == str:
        return unicode(pl)  
    elif type(pl) == int:
        return int(pl)
    elif type(pl) == datetime.datetime:
        try:
            return time.mktime(pl.timetuple())
        except OverflowError, err:
            return None
    elif type(pl) == list:
        return map(lambda x: stripData(x, attachments), pl)
    elif type(pl) == bool:
        return pl
    elif type(pl) == unicode:
        return pl
    elif type(pl) == float:
        return pl
    elif type(pl) == long:
        return pl
    else:
        print pl
        print type(pl)
        sys.exit(2)

def get_plist(pfname):
    fin = open(pfname, 'rb')
    xml1_tmp = tempfile.NamedTemporaryFile()
    xml1_tmp.write(fin.read())
    fin.close()
    xml1_tmp.flush()
    status = os.system("plutil -convert xml1 %s" % xml1_tmp.name)
    if not status == 0:
       xml1_tmp.close()
       print >> sys.stderr, "error parsing binary plist"
       sys.exit(2)
    p = plistlib.readPlist(xml1_tmp.name)
    xml1_tmp.close()
    return p

def get_plist_of_string(pl):
    xml1_tmp = tempfile.NamedTemporaryFile()
    xml1_tmp.write(pl)
    xml1_tmp.flush()
    status = os.system("plutil -convert xml1 %s" % xml1_tmp.name)
    if not status == 0:
       xml1_tmp.close()
       print >> sys.stderr, "error parsing binary plist"
       sys.exit(2)
    p = plistlib.readPlist(xml1_tmp.name)
    xml1_tmp.close()
    return p

def usage():
    print "Usage: %s [-v] [-h] [-x <extract prefix>] -o <output directory> <backup directory>" % sys.argv[0]
    print "  -v : verbose output (default: False)"
    print "  -x : prefix to filter extracted files by (default: extract all files)"
    print "  -o : directory to output extracted files to"

def main(argv=None):
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvx:o:")
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    outputdir = None
    extract_filter = None
    verbose = False
    for o,a in opts:
        if o == '-h':
            usage()
            sys.exit()
        elif o == '-o':
            outputdir = a
        elif o == '-x':
            extract_filter = a
        elif o == '-v':
            verbose = True
    if len(args) != 1:
        usage()
        sys.exit()
    if not outputdir:
        print "No output directory specified"
        sys.exit()
        usage()
    basedir = args[0]
    if os.path.isdir(outputdir):
        print "%s: output directory already exists" % outputdir
        usage()
        sys.exit(1)
    if not os.path.isdir(basedir):
        print "%s: not a directory" % basedir
        usage()
        sys.exit(1)
    manifest_name = "%s/Manifest.plist" % basedir
    if not os.path.isfile(manifest_name):
        print "%s: does not contain a Manifest.plist, not a valid iPhone backup directory" % basedir
        usage()
        sys.exit(1)
    atts={}
    pl = stripData(plistlib.readPlist(manifest_name), atts)
    #import simplejson
    #print simplejson.dumps(pl, indent=2)
    home={}
    for k in pl['Data']['Files']:
        if 'AppId' in pl['Data']['Files'][k]:
            pass
        else:
            home[k] = pl['Data']['Files'][k]
    
    os.makedirs(outputdir)
   
    def init_output_path(plistname):
        p = get_plist(plistname)
        print str(p)
        if p['Version'] == "3.0":
          if p['IsEncrypted']:
            print "Backup is encrypted, cannot parse it."
            sys.exit(1)
          p = get_plist_of_string(p['Metadata'].data)
        if (extract_filter and p['Path'].startswith(extract_filter)) or not extract_filter:
            fullpath = "%s/%s" % (outputdir, p['Path'])
            basepath, fl = os.path.split(fullpath)
            if not os.path.exists(basepath):
                os.makedirs(basepath)
            return (fullpath, p)
        else:
            return (None, None)

    for mdbackup_file in home:
        mdpath = "%s/%s.mdbackup" % (basedir, mdbackup_file)
        if not os.path.isfile(mdpath):
            # look for an mddata file instead
            mddata = "%s/%s.mddata" % (basedir,mdbackup_file)
            mdinfo = "%s/%s.mdinfo" % (basedir,mdbackup_file)
            fullpath,p = init_output_path(mdinfo)
            if fullpath:
                shutil.copyfile(mddata, fullpath)
        else:
            fullpath, p = init_output_path(mdpath)
            atts={}
            #print simplejson.dumps(phonedata, indent=2)
            if fullpath:
                phonedata = stripData(p, atts)
                ofile = open(fullpath, 'wb')
                if type(phonedata['Data']) == dict and '_uuid' in phonedata['Data']:
                    data = atts[phonedata['Data']['_uuid']]
                else:
                    data = simplejson.dumps(phonedata['Data'], indent=2)
                ofile.write(data)
                ofile.close()
                if verbose: print "X %s" % phonedata['Path']
            else:
                if verbose: print "- %s" % phonedata['Path']

if __name__ == "__main__":
    main()
