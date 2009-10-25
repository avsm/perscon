import urllib2,urllib
import commands

script = "../../scripts/get_passphrase.sh"

localuri = None

def get_perscon_password():
    status, passwd = commands.getstatusoutput(script)
    if status == 0:
        return passwd
    else:
        return ''

def init_url (uri):
    global localuri
    passwd = get_perscon_password ()
    ah = urllib2.HTTPBasicAuthHandler()
    ah.add_password(realm='Personal Container',
                    uri=uri,
                    user='root',
                    passwd=passwd)
    op = urllib2.build_opener(ah)
    urllib2.install_opener(op)
    localuri = uri

def rpc(urifrag, delete=False, args=None, data=None, headers={}):
    headers['content-type'] = 'application/json'
    uri = localuri + urllib.quote(urifrag)
    if args:
      uri += "?" + urllib.urlencode(args)
    print "rpc: " + uri
    if delete:
      meth="DELETE"
    else:
      if data:
        meth="POST"
      else:
        meth="GET"
    req = urllib2.Request(uri, data=data, headers=headers)
    req.get_method = lambda: meth
    return urllib2.urlopen(req)
