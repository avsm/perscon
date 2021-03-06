# Copyright (c) 2010 Anil Madhavapeddy <anil@recoil.org>
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

import logging, time
from perscon import models

def dolog(level="info", origin=None, entry=""):
    models.LogEntry(level=level, origin=origin, entry=entry).put()
    origin = origin or "unknown"

    e = "%s: %s" % (origin, entry)
    if   level == "info": logging.info(e)
    elif level == "debug": logging.debug(e)
    elif level == "error": logging.error(e)

def ldebug(origin=None, entry=""):
    dolog(level="debug", origin=origin, entry=entry)

def linfo(origin=None, entry=""):
    dolog(level="info", origin=origin, entry=entry)
