class Update(webapp.RequestHandler):
    def post(self):
        resp = json.loads(request.raw_post_data)
        loc = db.GeoPt(resp['lat'], resp['lon'])
        wid = woeid.resolve_latlon(loc.lat, loc.lon)
        acc = resp.get('accuracy', None)
        if acc:
            acc = float(acc)
        ctime = datetime.fromtimestamp(float(resp['date']))
        l = Location(loc=loc, date=ctime, accuracy=acc, url='http://google.com/android', woeid=wid)
        l.put()
        return http.HttpResponse(request.raw_post_data, mimetype="text/plain")
