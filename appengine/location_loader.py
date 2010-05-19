import time
from datetime import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader
from perscon.models import Location

def str_or_none(x):
  if str(x) == '':
    return None
  else:
    return str(x)

def float_or_none(x):
  try:
      if float(x) >= 0.0:
          return float(x)
  except:
       pass
  return None

class LocationLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'Location',
            [ ('loc', str),
              ('date', lambda x: datetime.fromtimestamp(float(x))),
              ('accuracy', float),
              ('woeid', str_or_none),
              ('url', str),
              ('speed', float_or_none),
            ])

class LocationExporter(bulkloader.Exporter):
    def __init__(self):
        bulkloader.Exporter.__init__(self, 'Location',
            [ ('loc', str, None),
              ('date', lambda x: time.mktime(x.timetuple()), None),
              ('accuracy', str, None),
              ('woeid', str, ''),
              ('url', str, None),
              ('speed', str, "-1.0")
            ])

exporters = [LocationExporter]
loaders = [LocationLoader]
