import urllib2
import commands

script = "../../scripts/get_passphrase.sh"

def get_perscon_password():
    status, passwd = commands.getstatusoutput(script)
    if status == 0:
        return passwd
    else:
        return ''

def init_url (uri):
    passwd = get_perscon_password ()
    ah = urllib2.HTTPBasicAuthHandler()
    ah.add_password(realm='Personal Container',
                    uri=uri,
                    user='root',
                    passwd=passwd)
    op = urllib2.build_opener(ah)
    urllib2.install_opener(op)
