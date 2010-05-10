from google.appengine.api import urlfetch
import sys

import cgi
import getpass
from django.utils import simplejson as json
import re
import time
import urllib
import Cookie

from google.appengine.ext import webapp
from google.appengine.ext import db
import perscon.passwd as passwd
import perscon.support.woeid as woeid
import perscon.models as models
from datetime import datetime

initial_payload=urllib.urlencode({'service': 'account', 'ssoNamespace': 'primary-me', 'returnURL': 'https://secure.me.com/account/#findmyiphone'.encode('base64'), 'anchor': 'findmyiphone', 'formID': 'loginForm', 'username': passwd.mobileme_username, 'password': passwd.mobileme_password})

def parse_poll(p):
	# format is:
	# accuracy                1178
	# date                    February 14, 2010
	# isAccurate              False
	# isLocateFinished        False
	# isLocationAvailable     True
	# isOldLocationResult     True
	# isRecent                True
	# latitude                51.521776
	# longitude               -0.108779
	# status                  1
	# statusString            locate status available
	# time                    8:17 AM
	
    month,day,year = re.search('(\w+) (\d+), (\d+)', p['date']).groups()
    month = month[0:3].lower()
    pdate = datetime.strptime("%s %s %s %s" % (month, day, year, p['time']), "%b %d %Y %I:%M %p")
    ctime = time.mktime(pdate.timetuple())
    accuracy = float(p['accuracy'])
    latitude = float(p['latitude'])
    longitude = float(p['longitude'])
    return { 'accuracy': accuracy, 'lat': latitude, 'lon':longitude, 'date': ctime }

def poll():
    r = urlfetch.fetch("https://auth.me.com/authenticate", method="POST", payload=initial_payload, headers={'Content-Type': 'application/x-www-form-urlencoded'}, follow_redirects=False)
    if r.status_code != 302 and 'set-cookie' not in r.headers:
      print >> sys.stderr, 'Incorrect name or password.'
      return None
    cookie1 = r.headers['set-cookie']
    r2 = urlfetch.fetch('https://secure.me.com/wo/WebObjects/Account2.woa?lang=en&anchor=findmyiphone', method='GET', headers={'Cookie': cookie1, 'X-Mobileme-Version': '1.0'})
    cookie2 = r2.headers['set-cookie']
    lsc, = re.search('isc-secure\\.me\\.com=(.*?);', cookie2).groups()
    c1 = Cookie.SimpleCookie(cookie1)
    c2 = Cookie.SimpleCookie(cookie2)
    for k in c2: c1[k] = c2[k].value
    ck= c1.output({},"",", ")

    r3 = urlfetch.fetch('https://secure.me.com/wo/WebObjects/DeviceMgmt.woa', method='POST', headers={'Cookie': ck, 'X-Mobileme-Version': '1.0', 'X-Mobileme-Isc': lsc})
    if json.loads(r3.content)['status'] == 0:
       print >> sys.stderr, 'Find My iPhone is unavailable.'
       return None
    id, os_version = re.search('new Device\\([0-9]+, \'(.*?)\', \'.*?\', \'.*?\', \'(.*?)\', \'(?:false|true)\', \'(?:false|true)\'\\)', r3.content).groups()
    r4 = urlfetch.fetch('https://secure.me.com/wo/WebObjects/DeviceMgmt.woa/wa/LocateAction/locateStatus', method='POST', payload='postBody=' + json.dumps({'deviceId': id, 'deviceOsVersion': os_version}), headers={'Cookie': ck, 'X-Mobileme-Version': '1.0', 'X-Mobileme-Isc': lsc})
    return parse_poll(json.loads(r4.content))

def poll_test():
	return parse_poll({"status": 1, "isAccurate": False, "isLocateFinished": False, "isLocationAvailable": True, "isOldLocationResult": True, "date": "February 14, 2010", "longitude": -0.108779, "time": "8:17 AM", "latitude": 51.521776000000003, "isRecent": True, "statusString": "locate status available", "accuracy": 1178})

class Cron(webapp.RequestHandler):
    def get(self):
        resp = poll()
        if resp:
            loc = db.GeoPt(resp['lat'], resp['lon'])
            try: wid = woeid.resolve_latlon(loc.lat, loc.lon)
            except: wid = None
            acc = resp.get('accuracy')
            if acc: acc = float(acc)
            ctime = datetime.fromtimestamp(float(resp['date']))
            l = models.Location(loc=loc, date=ctime, accuracy=acc, url='http://me.com', woeid=wid)
            l.put()
            self.response.out.write("ok")
        else:
            self.response.set_status(400)
            self.response.out.write("error")

