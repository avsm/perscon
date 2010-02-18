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
    calls    = ('call',)            ## cdr for call initiator
    cdrs     = ('callmember',)      ## cdr for other call members, one incl. duration
    chats    = ('chat', )           ## chat meta-data for mucs; incl. chat msgs for 1-1 chats 
    messages = ('chatmsg', )        ## chat messages
    profiles = ('user', 'profile',) ## user profiles: others, mine

    ## chatmember: uninteresting?  list of chat members for chat session
    ## contactgroup: list of usernames mapping to contact groups
    ## transfer: file transfer metadata (dstpath, sourcename, size, sender)
    ## voicemail: voicemail metadata (filename of local file containing msg you left)
    unknown  = ('call', 'callmember', 'chat', 'chatmsg', 'user', 'profile',
                'chatmember', 'contactgroup', 'transfer', 'voicemail',
                )
    
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

def parse_number(label, bs, i):
    try:
        j = i+2
        shift = n = 0
        while ord(bs[j]) & 0x80:
            n |= ((ord(bs[j]) & 0x7f) << shift)
            shift += 7
            j += 1
        n |= ((ord(bs[j]) & 0x7f) << shift)
        return label, n, j+2
            
    except IndexError, ie:
        raise SkrypeExc("bad %s exc:%s i:%s bs:%s" % (
            label, fmtexc(ie), i, fmtbs(bs[i+2:j+2], prefix="#   :")))
    
def parse_string(label, bs, i):
    try:
        j = i+2
        while bs[j] != NUL: j += 1
        return label, ''.join(bs[i+2:j]), j+2

    except IndexError, ie:
        raise SkrypeExc("bad %s exc:%s i:%s bs:%s" % (
            label, fmtexc(ie), i, fmtbs(bs[i+2:j+2], prefix="#   :")))
                      
class MessageIndicator:
    message_id  = b'\xe0\x03'
    timestamp   = b'\xe5\x03'
    username    = b'\xe8\x03'
    displayname = b'\xec\x03'
    messagez    = b'\xf4\x03'
    message     = b'\xfc\x03'

MessageParsers = {
    MessageIndicator.timestamp: lambda bs, i: parse_number("timestamp", bs, i), 
    MessageIndicator.message_id: lambda bs, i: parse_string('message_id', bs,i),
    MessageIndicator.username: lambda bs, i: parse_string('username', bs,i),
    MessageIndicator.displayname: lambda bs, i: parse_string('displayname', bs,i),
    MessageIndicator.messagez: lambda bs, i: parse_string('message', bs,i),
    MessageIndicator.message: lambda bs, i: parse_string('message', bs,i),
    }

class ProfileIndicator:
    username    = b'\x03\x10'
    displayname = b'\x03\x14'
    country     = b'\x03\x28'
    language    = b'\x03\x24'
    city        = b'\x03\x30'
    phone       = b'\x03\x34'
    office      = b'\x03\x38'
    mobile      = b'\x03\x3c'
    pstn        = b'\x03\x18'
    label       = b'\x84\x01'

ProfileParsers = {
    ProfileIndicator.username: lambda bs, i: parse_string('username', bs,i),
    ProfileIndicator.displayname: lambda bs, i: parse_string('displayname', bs,i),
    ProfileIndicator.language: lambda bs, i: parse_string('language', bs,i),
    ProfileIndicator.country: lambda bs, i: parse_string('country', bs,i),
    ProfileIndicator.city: lambda bs, i: parse_string('city', bs,i),
    ProfileIndicator.phone: lambda bs, i: parse_string('phone', bs,i),
    ProfileIndicator.office: lambda bs, i: parse_string('office', bs,i),
    ProfileIndicator.mobile: lambda bs, i: parse_string('mobile', bs,i),
    ProfileIndicator.pstn: lambda bs, i: parse_string('pstn', bs,i),
    ProfileIndicator.label: lambda bs, i: parse_string('label', bs,i),
    }

class CallIndicator:
    timestamp   = b'\xa1\x01'
    cdrid       = b'\xe4\x06'
    username    = b'\xa4\x01'
    usernamex   = b'\xc8\x06'
    duration    = b'\x85\x02'
    pstn_number = b'\x80\x02'
    pstn_status = b'\x8c\x02'
    chatname    = b'\xfc\x01'

CallParsers = {
    CallIndicator.timestamp: lambda bs, i: parse_number("timestamp", bs, i), 
    CallIndicator.username: lambda bs, i: parse_string('username', bs,i),
    CallIndicator.usernamex: lambda bs, i: parse_string('username', bs,i),
    CallIndicator.pstn_number: lambda bs, i: parse_string('pstn-number', bs,i),
    CallIndicator.pstn_status: lambda bs, i: parse_string('pstn-status', bs,i),
    CallIndicator.cdrid: lambda bs, i: parse_string('cdr-id', bs,i),
    CallIndicator.chatname: lambda bs, i: parse_string('chatname', bs,i),
    }

class CdrIndicator:
    duration    = b'\xa5\x07'
    username    = b'\x98\x07'
    displayname = b'\x9c\x07'
    cdrid       = b'\xb8\x01'
    forwarder   = b'\x84\x07'

CdrParsers = {
    CdrIndicator.duration: lambda bs, i: parse_number("duration", bs, i),
    CdrIndicator.username: lambda bs, i: parse_string("username", bs, i),
    CdrIndicator.displayname: lambda bs, i: parse_string("displayname", bs, i),
    CdrIndicator.cdrid: lambda bs, i: parse_string('cdr-id', bs,i),
    CdrIndicator.forwarder: lambda bs, i: parse_string('forwarder', bs,i),
    }

UnknownParsers = {
    }

#
# parse harness
#

def resync(ps, bs, i):
    j = i
    while j < len(bs) and bs[j:j+2] not in ps.keys():
        j += 1
    return i, j, bs[i:j]

def parse_items(ps, bs):
    ## skip to recognised indicator
    oi, i, junk = resync(ps, bs, 0)
    d = { 'junk': [(oi, btos(junk, ascii=True)),] }

    while i < len(bs):
        try:
            (indicator,) = struct.unpack("2s", bs[i:i+2])
            key, value, i = ps[indicator](bs, i)
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

#
# entry points
#

def records(m, ps):
    sz = int(m.group('sz'))
    with open(m.string, 'rb') as f:
        while True:
            bs = f.read(HDR_SZ+sz)
            if len(bs) == 0: break

            (marker, skr_len,) = struct.unpack("<4s L", bs[:SKR_HDR_LEN])
            if marker != SKR_MARKER: raise FormatExc("bad marker")

            yield { 'marker': marker,
                    'length': skr_len,
                    'value': parse(ps, bs[SKR_HDR_LEN:SKR_HDR_LEN+skr_len]),
                    }

def messages(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.messages: 
        raise SkrypeExc("bad messages fn:%s" % (fn,))
    ps = MessageParsers
    return records(m, ps)

def profiles(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.profiles:
        raise SkrypeExc("bad profiles fn:%s" % (fn,))
    ps = ProfileParsers
    return records(m, ps)

def calls(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.calls: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = CallParsers
    return records(m, ps)

def cdrs(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.cdrs: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = CdrParsers
    return records(m, ps)

def unknown(fn):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.unknown: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = UnknownParsers
    return records(m, ps)

#
# main
#

if __name__ == '__main__':

    import pprint, glob
    try: map(lambda msg: pprint.pprint(msg), messages(sys.argv[1])) ; sys.exit()
    except Exception, e: print >>sys.stderr, fmtexc(e)
    
    try: map(lambda msg: pprint.pprint(msg), profiles(sys.argv[1])) ; sys.exit()
    except Exception, e: print >>sys.stderr, fmtexc(e)
    
    try: map(lambda msg: pprint.pprint(msg), calls(sys.argv[1])) ; sys.exit()
    except Exception, e: print >>sys.stderr, fmtexc(e, with_tb=True)
        
    try: map(lambda msg: pprint.pprint(msg), cdrs(sys.argv[1])) ; sys.exit()
    except Exception, e: print >>sys.stderr, fmtexc(e, with_tb=True)

    ## catch-all
    try: map(lambda msg: pprint.pprint(msg), unknown(sys.argv[1]))
    except Exception, e: print >>sys.stderr, fmtexc(e, with_tb=True)

