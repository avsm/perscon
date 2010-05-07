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

import sys, struct, re, string, traceback, os, glob, pprint

_recordsz_re = re.compile("(?P<ty>[^0-9]+)(?P<sz>[0-9]+)\.dbb")

NUL    = '\x00'
NULNUL = NUL+NUL
HDR_SZ = 8

SKR_MARKER     = struct.pack("4B", 0x6c, 0x33, 0x33, 0x6c)
SKR_MARKER_LEN = 4
SKR_RECSZ_LEN  = 4
SKR_HDR_LEN    = SKR_MARKER_LEN+SKR_RECSZ_LEN
SKR_SEQNO_LEN  = 4

Verbose = 0

class Logtype:
    calls    = ('call',)             ## cdr for call initiator
    cdrs     = ('callmember',)       ## cdr for other call members, one incl. duration
    mucs     = ('chat', )            ## chat meta-data for mucs; incl. chat msgs for 1-1 chats 
    messages = ('chatmsg', )         ## chat messages;
    chatmembers = ('chatmember', )   ## chat metadata: speakers
    profiles = ('user', 'profile',)  ## user profiles: others, mine

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
                                                
def btos(bs, ascii=False, sep='.'):
    if bs == None or bs == "": return ""
    def _fmt(b):
        if ascii and isprintable(b): return b
        return '%0.2x' % (ord(b),)
    return sep.join(map(_fmt, bs))

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
        return label, ''.join(bs[i+2:j]), j+1

    except IndexError, ie:
        raise SkrypeExc("bad %s exc:%s i:%s bs:%s" % (
            label, fmtexc(ie), i, fmtbs(bs[i+2:j+2], prefix="#   :")))
                      
class MessageIndicator:
    chatid      = b'\xe0\x03'
    chatid2     = b'\xb8\x03'
    timestamp   = b'\xe5\x03'
    username    = b'\xe8\x03'
    username2   = b'\xc0\x03'
    username3   = b'\xc8\x03'
    displayname = b'\xec\x03'
    message     = b'\xfc\x03'
    message2    = b'\xf4\x03'
    message3    = b'\x03\x37'
    displaymsg  = b'\xd8\x03'

MessageParsers = {
    MessageIndicator.chatid: lambda bs, i: parse_string('chatid', bs,i),
    MessageIndicator.chatid2: lambda bs, i: parse_string('chatid', bs,i),
    MessageIndicator.timestamp: lambda bs, i: parse_number("timestamp", bs, i), 
    MessageIndicator.username: lambda bs, i: parse_string('username', bs,i),
    MessageIndicator.username2: lambda bs, i: parse_string('username', bs,i),
    MessageIndicator.username3: lambda bs, i: parse_string('username', bs,i),
    MessageIndicator.displayname: lambda bs, i: parse_string('displayname', bs,i),
    MessageIndicator.message: lambda bs, i: parse_string('message', bs,i),
    MessageIndicator.message2: lambda bs, i: parse_string('message', bs,i),
    MessageIndicator.message3: lambda bs, i: parse_string('message', bs,i),
    MessageIndicator.displaymsg: lambda bs, i: parse_string('displaymsg', bs,i),
    }

class MucIndicator:
    chatname = b'\xd8\x03'
    actives  = b'\xcc\x03'
    members  = b'\xc8\x03'
    members2 = b'\xd4\x03'
    speaker  = b'\xbc\x06'
    member   = b'\x03\x00'
    chatid   = b'\xb8\x03'
    description = b'\xb8\x06'
    message  = b'\x037'
    timestamp = b'\xb5\x04'

MucParsers = {
    MucIndicator.chatid: lambda bs, i: parse_string('chatid', bs,i),
    MucIndicator.timestamp: lambda bs, i: parse_number('timestamp', bs,i),
    MucIndicator.chatname: lambda bs, i: parse_string('chatname', bs,i),
    MucIndicator.actives: lambda bs, i: parse_string('actives', bs,i),
    MucIndicator.members: lambda bs, i: parse_string('members', bs,i),
##     MucIndicator.members2: lambda bs, i: parse_string('members', bs,i),
    MucIndicator.speaker: lambda bs, i: parse_string('speaker', bs,i),
##     MucIndicator.member: lambda bs, i: parse_string('member', bs,i),
    MucIndicator.description: lambda bs, i: parse_string('description', bs,i),
    MucIndicator.message: lambda bs, i: parse_string('message', bs,i),
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
    pickup      = b'\xe5\x19'
    
CdrParsers = {
    CdrIndicator.duration: lambda bs, i: parse_number("duration", bs, i),
    CdrIndicator.username: lambda bs, i: parse_string("username", bs, i),
    CdrIndicator.displayname: lambda bs, i: parse_string("displayname", bs, i),
    CdrIndicator.cdrid: lambda bs, i: parse_string('cdr-id', bs,i),
    CdrIndicator.forwarder: lambda bs, i: parse_string('forwarder', bs,i),
    CdrIndicator.pickup: lambda bs, i: parse_number('pickup', bs,i),
    }

class ChatmemberIndicator:
    chatid = b'\xc8\x04'
    member = b'\xcc\x04'

ChatmemberParsers = {
    ChatmemberIndicator.chatid: lambda bs,i: parse_string("chatid", bs,i),
    ChatmemberIndicator.member: lambda bs,i: parse_string("member", bs,i),
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

def parse_items(ps, bs, with_junk=False):
    ## skip to recognised indicator
    oi, i, junk = resync(ps, bs, 0)
    d = {}
    if with_junk: d['junk'] = [(oi, btos(junk, ascii=True)),]

    while i < len(bs):
        try:
            (indicator,) = struct.unpack("2s", bs[i:i+2])
            key, value, i = ps[indicator](bs, i)
            if key not in d: d[key] = value
            else:
                if not isinstance(d[key], list): d[key] = [d[key]]
                d[key].append(value)

        except struct.error, se:
            print >>sys.stderr, "# struct.%s" % (fmtexc(se, with_tb=True),)
            oi, i, junk = resync(ps, bs, i+1)
            if with_junk: d['junk'].append((oi, btos(junk, ascii=True)))
            
        except KeyError:
            print >>sys.stderr, "# unknown indicator: i:%s ind:%s" % (
                i, btos(indicator),)
            oi, i, junk = resync(ps, bs, i+1)
            if with_junk: d['junk'].append((oi, btos(junk, ascii=True)))
        
        except SkrypeExc, se:
            print >>sys.stderr, "# %s" % (fmtexc(se, with_tb=True),)
            oi, i, junk = resync(ps, bs, i+1)
            if with_junk: d['junk'].append((oi, btos(junk, ascii=True)))

        except Exception, e:
            print >>sys.stderr, "%s\ni:%s%s" % (
                fmtexc(e, with_tb=True), i, fmtbs(bs[i:]))
            oi, i, junk = resync(ps, bs, i+1)
            if with_junk: d['junk'].append((oi, btos(junk, ascii=True)))
            
    return d

def parse(ps, bs, with_junk=False):
    (seqno, ) = struct.unpack("<L", bs[:SKR_SEQNO_LEN])
    return { 'seqno': seqno,
             'items': parse_items(ps, bs[SKR_SEQNO_LEN:], with_junk),
             }

#
# entry points
#

def record(bs, ps, with_junk=False, with_raw=False):
    (marker, skr_len,) = struct.unpack("<4s L", bs[:SKR_HDR_LEN])
    if marker != SKR_MARKER: raise FormatExc("bad marker")

    record = { 'marker': marker,
               'length': skr_len,
               'value': parse(ps, bs[SKR_HDR_LEN:SKR_HDR_LEN+skr_len],
                              with_junk),
               }
    if with_raw: record['raw'] = bs
    return record

def records(m, ps, with_junk=False, with_raw=False):
    sz = int(m.group('sz'))
    with open(m.string, 'rb') as f:
        while True:
            bs = f.read(HDR_SZ+sz)
            if Verbose > 1:
                print "sz:%d bs:\n%s" % (sz, fmtbs(bs, ascii=True))
            if len(bs) == 0: break

            (marker, skr_len,) = struct.unpack("<4s L", bs[:SKR_HDR_LEN])
            if marker != SKR_MARKER: raise FormatExc("bad marker")
            if skr_len == 0: break
                             
            record = { 'marker': marker,
                       'length': skr_len,
                       'value': parse(ps, bs[SKR_HDR_LEN:SKR_HDR_LEN+skr_len],
                                      with_junk),
                       }
            if with_raw: record['raw'] = bs
            yield record

def messages(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.messages: 
        raise SkrypeExc("bad messages fn:%s" % (fn,))
    ps = MessageParsers
    return records(m, ps, with_junk, with_raw)

def mucs(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.mucs: 
        raise SkrypeExc("bad mucs fn:%s" % (fn,))
    ps = MucParsers
    return records(m, ps, with_junk, with_raw)

def profiles(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.profiles:
        raise SkrypeExc("bad profiles fn:%s" % (fn,))
    ps = ProfileParsers
    return records(m, ps, with_junk, with_raw)

def calls(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.calls: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = CallParsers
    return records(m, ps, with_junk, with_raw)

def cdrs(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.cdrs: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = CdrParsers
    return records(m, ps, with_junk, with_raw)

def chatmembers(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.chatmembers: 
        raise SkrypeExc("bad chatmembers fn:%s" % (fn,))
    ps = ChatmemberParsers
    return records(m, ps, with_junk, with_raw)

def unknown(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty not in Logtype.unknown: 
        raise SkrypeExc("bad calls fn:%s" % (fn,))
    ps = UnknownParsers
    return records(m, ps, with_junk, with_raw)

def process(fn, with_junk=False, with_raw=False):
    m = _recordsz_re.match(fn)
    if not m: raise SkrypeExc("bad log filename")
    
    ty = os.path.basename(m.group("ty"))
    if ty in Logtype.calls: return ("calls", calls(fn, with_junk, with_raw))
    elif ty in Logtype.cdrs: return ("cdrs", cdrs(fn, with_junk, with_raw))
    elif ty in Logtype.messages: return ("messages", messages(fn, with_junk, with_raw))
    elif ty in Logtype.mucs: return ("mucs", mucs(fn, with_junk, with_raw))
    elif ty in Logtype.profiles: return ("profiles", profiles(fn, with_junk, with_raw))
    elif ty in Logtype.chatmembers:
        return ("chatmembers", chatmembers(fn, with_junk, with_raw))
    elif ty in Logtype.unknown: return ("unknown", unknown(fn, with_junk, with_raw))

#
# splice multiple streams together in seqno order
#

class R:
    def __init__(self, ty, rec, stream):
        self.ty = ty
        self.rec = rec
        self.stream = stream
        self.seqno = rec['value']['seqno']

    def __cmp__(self, other):
        if   self.seqno <  other.seqno: return -1
        elif self.seqno == other.seqno: return 0
        else:                           return 1

    def __repr__(self):
        return "%s<%s> [%s]" % (self.ty, self.seqno, pprint.pformat(self.rec))

def splice(fns, with_junk=False, with_raw=False):
    def nex((ty, recs)):
        try: return R(ty, recs.next(), recs)
        except StopIteration: pass
    
    records = filter(None, map(nex, map(
        lambda fn: process(fn, with_junk, with_raw), fns)))
    records.sort()

    while len(records) > 0:
        r = records[0]
        yield (r.ty, r.rec)
        try: records[0] = R(r.ty, records[0].stream.next(), r.stream)
        except StopIteration: del records[0]
        records.sort()

#
# main
#

if __name__ == '__main__':
    if sys.argv[1] == '-v':
        Verbose = 2
        fns = sys.argv[2:]
    else: fns = sys.argv[1:]
    for r in splice(fns): pprint.pprint(r)
  
