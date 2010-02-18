# Copyright (C) 2010 Richard Mortier <mort@cantab.net>
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

import sys, struct, re, string, traceback, os

_recordsz_re = re.compile("(?P<ty>[^0-9]+)(?P<sz>[0-9]+)\.dbb")

NUL    = '\x00'
NULNUL = NUL+NUL
HDR_SZ = 8

SKR_MARKER     = struct.pack("4B", 0x6c, 0x33, 0x33, 0x6c)
SKR_MARKER_LEN = 4
SKR_RECSZ_LEN  = 4
SKR_HDR_LEN    = SKR_MARKER_LEN+SKR_RECSZ_LEN
SKR_SEQNO_LEN  = 4

class Logtype:
    messages = ('chatmsg', 'msg', )
    profiles = ('user', 'profile',)
                                  
class MessageIndicator:
    message_id  = b'\xe0\x03'
    timestamp   = b'\xe5\x03'
    username    = b'\xe8\x03'
    displayname = b'\xec\x03'
    messagez    = b'\xf4\x03'
    message     = b'\xfc\x03'

class ProfileIndicator:
    username = b'\x03\x10'
    displayname = b'\x03\x14'
    country = b'\x03\x28'
    language = b'\x03\x24'
    city = b'\x03\x30'
    phone = b'\x03\x34'
    office = b'\x03\x38'
    mobile = b'\x03\x3c'
    
class SkrypeExc(Exception): pass

def fmtexc(e, with_tb=False):
    tb = traceback.extract_tb(sys.exc_info()[2])
    s = '%s: %s' % (e.__class__.__name__, str(e))
    if with_tb:
        s += '\n%s' % ('\n'.join([ '#   %s@%s:%s' % (filename, lineno, func)
                                   for (filename,lineno,func,_) in tb ]),)
    return s

def isprintable(b):
    return ((b in string.printable)
            and (b == " " or b not in string.whitespace))
                                                
def btos(bs, ascii=False):
    if bs == None or bs == "": return ""
    def _fmt(b):
        if ascii and isprintable(b): return b
        return '%0.2x' % (ord(b),)
    return '.'.join(map(_fmt, bs))

def fmtbs(bs, prefix="  : ", ascii=False):
    def _fmt():
        for i in range(0, len(bs), 16):
            yield '\n%s0x%s' % (prefix, btos(bs[i:i+16], ascii))
    return "".join(_fmt())

#
# item parsers
#

def parse_timestamp(bs, i):
    ## wierd.  just plain wierd.
    try:
        tsb = bs[i+2:i+7]
        b31_28 = ord(tsb[-1]) & 0x0f
        b27_21 = ord(tsb[-2]) & 0x7f
        b20_14 = ord(tsb[-3]) & 0x7f
        b13_07 = ord(tsb[-4]) & 0x7f
        b06_00 = ord(tsb[-5]) & 0x7f

        b3 =  (b31_28         << 4) + ((b27_21 & 0x78) >> 3)
        b2 = ((b27_21 & 0x07) << 5) + ((b20_14 & 0x7c) >> 2)
        b1 = ((b20_14 & 0x03) << 6) + ((b13_07 & 0x7e) >> 1)
        b0 = ((b13_07 & 0x01) << 7) +  (b06_00 & 0x7f)

        (ts,) = struct.unpack(">L", ''.join(map(chr, [b3, b2, b1, b0])))
        return 'ts', ts, bs[i+7], i+8

    except IndexError, ie:
        raise SkrypeExc("bad timestamp exc:%s i:%s bs:%s" % (
            fmtexc(ie), i, fmtbs(bs[i+2:i+7], prefix="#   :")))

def parse_string(label, bs, i):
    try:
        j = i+2
        while bs[j] != NUL: j += 1
        return label, ''.join(bs[i+2:j]), bs[j+1:j+2], j+2

    except IndexError, ie:
        raise SkrypeExc("bad %s exc:%s i:%s bs:%s" % (
            label, fmtexc(ie), i, fmtbs(bs[i+2:j], prefix="#   :")))
    
MessageParsers = {
    MessageIndicator.timestamp: parse_timestamp,
    MessageIndicator.message_id: lambda bs, i: parse_string('message_id', bs,i),
    MessageIndicator.username: lambda bs, i: parse_string('username', bs,i),
    MessageIndicator.displayname: lambda bs, i: parse_string('displayname', bs,i),
    MessageIndicator.messagez: lambda bs, i: parse_string('message', bs,i),
    MessageIndicator.message: lambda bs, i: parse_string('message', bs,i),
    }

ProfileParsers = {
    ProfileIndicator.username: lambda bs, i: parse_string('username', bs,i),
    ProfileIndicator.displayname: lambda bs, i: parse_string('displayname', bs,i),
    ProfileIndicator.language: lambda bs, i: parse_string('language', bs,i),
    ProfileIndicator.country: lambda bs, i: parse_string('country', bs,i),
    ProfileIndicator.city: lambda bs, i: parse_string('city', bs,i),
    ProfileIndicator.phone: lambda bs, i: parse_string('phone', bs,i),
    ProfileIndicator.office: lambda bs, i: parse_string('office', bs,i),
    ProfileIndicator.mobile: lambda bs, i: parse_string('mobile', bs,i),
    }

#
# parse harness
#

def resync(ps, bs, i):
    j = i
    while j < len(bs) and bs[j:j+2] not in ps.keys(): j += 1
    return i, j, bs[i:j]

def parse_items(ps, bs):
    ## skip to recognised indicator
    oi, i, junk = resync(ps, bs, 0)
    d = { 'junk': [(oi, btos(junk, ascii=True)),] }

    while i < len(bs):
        try:
            (indicator,) = struct.unpack("2s", bs[i:i+2])
            key, value, status, i = ps[indicator](bs, i)
            d[key] = value

        except struct.error, se:
            print >>sys.stderr, "# struct.%s" % (fmtexc(se, with_tb=True),)
            oi, i, junk = resync(ps, bs, i+1)
            d['junk'].append((oi, btos(junk, ascii=True)))
            
        except KeyError:
            print >>sys.stderr, "# unknown indicator: i:%s ind:%s" % (i, btos(indicator),)
            oi, i, junk = resync(ps, bs, i+1)
            d['junk'].append((oi, btos(junk, ascii=True)))
        
        except SkrypeExc, se:
            print >>sys.stderr, "# %s" % (fmtexc(se, with_tb=True),)
            oi, i, junk = resync(ps, bs, i+1)
            d['junk'].append((oi, btos(junk, ascii=True)))

        except Exception, e:
            print >>sys.stderr, "%s\ni:%s%s" % (fmtexc(e, with_tb=True), i, fmtbs(bs[i:]))
            oi, i, junk = resync(ps, bs, i+1)
            d['junk'].append((oi, btos(junk, ascii=True)))
            
    return d

def parse(ps, bs):
    (seqno, ) = struct.unpack("<L", bs[:SKR_SEQNO_LEN])
    return { 'seqno': seqno,
             'items': parse_items(ps, bs[SKR_SEQNO_LEN:]),
             }

def messages(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.messages: return
    ps = MessageParsers

    sz = int(m.group('sz'))
    with open(fn, 'rb') as f:
        while True:
            bs = f.read(HDR_SZ+sz)
            if len(bs) == 0: break

            (marker, skr_len,) = struct.unpack("<4s L", bs[:SKR_HDR_LEN])
            if marker != SKR_MARKER: raise FormatExc("bad marker")

            yield { 'marker': marker,
                    'length': skr_len,
                    'value': parse(ps, bs[SKR_HDR_LEN:SKR_HDR_LEN+skr_len]),
                    }

def profiles(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.profiles: return
    ps = ProfileParsers

    sz = int(m.group('sz'))
    with open(fn, 'rb') as f:
        while True:
            bs = f.read(HDR_SZ+sz)
            if len(bs) == 0: break

            (marker, skr_len,) = struct.unpack("<4s L", bs[:SKR_HDR_LEN])
            if marker != SKR_MARKER: raise FormatExc("bad marker")

            yield { 'marker': marker,
                    'length': skr_len,
                    'value': parse(ps, bs[SKR_HDR_LEN:SKR_HDR_LEN+skr_len]),
                    }

if __name__ == '__main__':

    import pprint, glob
    map(lambda msg: pprint.pprint(msg), messages(sys.argv[1]))
    map(lambda msg: pprint.pprint(msg), profiles(sys.argv[1]))
        
