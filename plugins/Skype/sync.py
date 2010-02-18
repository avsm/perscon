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

import datetime, time, sys, os

sys.path.append("../../perscon")
import config

sys.path.append("../../support")
import Perscon_utils

from pkg_resources import require
require("simplejson")
import simplejson as sj
require("Skype4Py")
import Skype4Py

def main():
##     save_dir = os.getenv("LIFEDB_DIR")
##     if not save_dir:
##         print >> sys.stderr, "no LIFEDB_DIR in env"
##         exit(1)

    skype = Skype4Py.Skype()
    skype.Attach()

    myHandle = skype.CurrentUserHandle

    calls = skype.Calls()
    for call in calls:
        tt = call.Datetime.timetuple()
        tstamp = time.mktime(tt)
        if call.Type == Skype4Py.cltIncomingPSTN or call.Type == Skype4Py.cltOutgoingPSTN:
            ctype = "PhoneCall"
        else:
            ctype = "Skype"
        m = { '_type' : 'com.skype', '_timestamp' : tstamp,
            'duration' : call.Duration, 'type' : call.Type,
            'status' : call.Status,
            '_from' : { 'type' : ctype, 'id' : call.PartnerHandle }, 
            '_to' : [ { 'type' : 'Skype', 'id' : myHandle } ]
          }
        if call.Participants:
            m['participants'] = map(lambda x: x.Handle, call.Participants)
       
        uid = "%s.%s.%s" % (call.Id, tstamp, myHandle)
        guid, subdir = util.split_to_guid(uid)
        dir = os.path.join(save_dir, subdir)
        fname = "%s.lifeentry" % guid
        m['_uid'] = guid
        full_fname = os.path.join(dir, fname)
        if not os.path.isfile(full_fname):
            if not os.path.isdir(dir):
                os.makedirs(dir)
            fout = open(full_fname, 'w')
            simplejson.dump(m, fout, indent=2)
            fout.close()
            print "Written: %s" % full_fname

if __name__ == "__main__": main()
