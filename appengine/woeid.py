import flickrapi
import passwd
from flickrapi.tokencache import SimpleTokenCache
from django.utils import simplejson as json

key = passwd.flickr_appid
flickr = flickrapi.FlickrAPI(key)
flickr.token_cache = SimpleTokenCache()

def resolve_latlon(lat, lon):
  p = flickr.places_findByLatLon(lat=lat, lon=lon, format='etree')
  w = p.find('places').find('place')
  woeid = w.attrib['woeid']
  return woeid
