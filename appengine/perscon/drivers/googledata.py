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

## useful links:
##   http://code.google.com/apis/accounts/docs/OAuth.html
##   http://code.google.com/apis/gdata/docs/auth/oauth.html
##   http://code.google.com/appengine/articles/gdata.html
##   http://code.google.com/apis/contacts/docs/1.0/developers_guide_python.html

## to register your domain:
##   http://code.google.com/apis/accounts/docs/RegistrationForWebAppsAuto.html
##   https://www.google.com/accounts/ManageDomains

## sample code:
##   http://code.google.com/p/gdata-python-client/source/browse/trunk/samples/oauth/oauth_on_appengine/

import sys, logging, pprint
log = logging.info
ppf = pprint.pformat

import gdata.auth, gdata.contacts, gdata.contacts.service, gdata.alt.appengine
from appengine_utilities.sessions import Session
from django.utils import simplejson as json
from google.appengine.ext import webapp
import perscon.passwd as passwd

SETTINGS = {
  'APP_NAME': 'Personal Container', ## 'google-GDataOAuthAppEngine-v1',
  'CONSUMER_KEY': passwd.google_oauth_key, ## 'YOUR_CONSUMER_KEY',
  'CONSUMER_SECRET': passwd.google_oauth_secret, ## 'YOUR_CONSUMER_SECRET',
  
  'SIG_METHOD': gdata.auth.OAuthSignatureMethod.HMAC_SHA1,
  'SCOPES': [ 'http://www.google.com/m8/feeds/',
              'https://www.google.com/m8/feeds/', 
##              'http://docs.google.com/feeds/',
##              'https://docs.google.com/feeds/'
              ]
  }

Gcontacts = gdata.contacts.service.ContactsService(source=SETTINGS['APP_NAME'])
Gcontacts.SetOAuthInputParameters(SETTINGS['SIG_METHOD'], SETTINGS['CONSUMER_KEY'],
                                  consumer_secret=SETTINGS['CONSUMER_SECRET'])
gdata.alt.appengine.run_on_appengine(Gcontacts)

def base_url(req):
    bu = "%s://%s:%s/drivers" % (
        req.scheme, req.environ['SERVER_NAME'], req.environ['SERVER_PORT'])
    return bu

def login_url(req): return "%s/googledata/login" % (base_url(req),)
def contacts_url(req):return "%s/googledata/contacts" % (base_url(req),)

class Login(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        
        ## 2b.  get authorized request token from redirected request
        oauth_token = gdata.auth.OAuthTokenFromUrl(self.request.uri)
        log(oauth_token)
        if not oauth_token: self.redirect("/")

        oauth_token.secret = self.session['oauth_token_secret']
        oauth_token.oauth_input_params = Gcontacts.GetOAuthInputParameters()
        Gcontacts.SetOAuthToken(oauth_token)

        ## 3a.  exchange the authorized request token for an access token
        oauth_verifier = self.request.get('oauth_verifier', default_value='')
        access_token = Gcontacts.UpgradeToOAuthAccessToken(
            oauth_verifier=oauth_verifier)

        ## 3b.  store access token
        if access_token: Gcontacts.token_store.add_token(access_token)

        self.redirect(self.request.uri)

    def post(self):
        self.session = Session()

        ## 1a. request token for given scopes.  after user grants
        ## access, redirect GET back to this page
        req_token = Gcontacts.FetchOAuthRequestToken(
            scopes=SETTINGS['SCOPES'], oauth_callback=login_url(self.request))
                                           
        ## 1b. persist token secret so we can re-create the OAuthToken
        ## returned from approval page.
        self.session['oauth_token_secret'] = req_token.secret
        
        ## 1c. generate redirection uri.  dropping hd param gives user
        ## choice of google vs. google apps account to login with.
        domain = self.request.get('domain', default_value='default')
        approval_page_url = Gcontacts.GenerateOAuthAuthorizationURL(
            extra_params={'hd': domain})
                                                       
        ## 2. redirect to google oauth approval page
        self.redirect(approval_page_url)

def process_contact(entry):
    i = 1
    log("%s %s" % (i, entry))
    emails = map(lambda e:e.address, entry.email)
    log("%s email: %s" % (i, emails))

    if entry.content:
        log("%s content: %s" % (i, entry.content.text))

    groups = map(lambda e:e.href, entry.group_membership_info)
    log("%s groups: %s" % (i, groups))

    for (j, ep) in enumerate(entry.extended_property):
        v = ep.value if ep.value else ep.GetXmlBlobString()
        log("%s-%s %s: %s" % (i, j, ep.name, v))


    for (j, link) in enumerate(entry.link):
        log("%s-%s link: %s" % (i, j, link))
        log("%s-%s text: %s" % (i, j, link.text))
        log("%s-%s title: %s" % (i, j, link.title))
        log("%s-%s type: %s" % (i, j, link.type))

    ns = entry.title.text.split(" ") if entry.title.text else ['']
    if len(ns) <= 1: firstname, lastname = '', ns[0]
    else:
        firstname, lastname = ns[0], " ".join(ns[1:])

    log("%s firstname:'%s' lastname:'%s'" % (i, firstname, lastname))

    phones = map(lambda e: { 'label': e.label, 'number': e.text }, entry.phone_number)
    for (j, phone) in enumerate(entry.phone_number):
        log("%s-%s %s: %s %s" % (
            i, j, phone.label, phone.text,
            "***" if phone.primary == "true" else ''))


##                     log("%s nickname: %s" % (i, entry.nickname))
##                     log("%s relation: %s" % (i, entry.relation))
##                     log("%s im: %s" % (i, entry.im))
##                     log("%s content: %s" % (i, entry.content))
##                     log("%s groups: %s" % (i, entry.group_membership_info))

                                                      
##                     log("%s addr: %s" % (i, entry.postal_address))
##                     log("%s struct addr: %s" % (i, entry.structured_pstal_address))

    return { 'firstname': firstname,
             'lastname': lastname,
             'phones': phones,
             'emails': emails,
             }

class Contacts(Login):
    def get(self):
        access_token = Gcontacts.token_store.find_token(
            '%20'.join(SETTINGS['SCOPES']))
        if not isinstance(access_token, gdata.auth.OAuthToken):
            Login.post(self)

        else:
            try:
                cs = []
                finished = False

                query = gdata.contacts.service.ContactsQuery()
                query.max_results = 100
                query.start_index = 1
                while not finished:
                    feed = Gcontacts.GetContactsFeed(query.ToUri())
                    cs.extend(map(process_contact, feed.entry))
                    query.start_index = int(query.start_index)+int(query.max_results)
                    finished = (int(feed.start_index.text)+int(feed.items_per_page.text)
                                > int(feed.total_results.text))
                              
                self.response.out.write(json.dumps(cs))
            
            except gdata.service.RequestError, error:
                log("EXC: %s" % (error,))
                Login.post(self)

'''
def EraseStoredTokens(self):
    gdata.alt.appengine.save_auth_tokens({})


def PrintFeed(feed):
    for i, entry in enumerate(feed.entry):
        print '\n%s %s' % (i+1, entry.title.text)
        if entry.content:
            print '    %s' % (entry.content.text)
        # Display the primary email address for the contact.
        for email in entry.email:
            if email.primary and email.primary == 'true':
                print '    %s' % (email.address)
        # Show the contact groups that this contact is a member of.
        for group in entry.group_membership_info:
            print '    Member of group: %s' % (group.href)
        # Display extended properties.
        for extended_property in entry.extended_property:
            if extended_property.value:
                value = extended_property.value
            else:
                value = extended_property.GetXmlBlobString()
            print '    Extended Property - %s: %s' % (extended_property.name, value)
feed = gd_client.GetContactsFeed()
PrintFeed(feed)


{'_GDataEntry__id': <atom.Id object at 0x10309a390>,
 'author': [],
 'batch_id': None,
 'batch_operation': None,
 'batch_status': None,
 'birthday': None,
 'category': [<atom.Category object at 0x10309a450>],
 'content': <atom.Content object at 0x10309a4d0>,
 'contributor': [],
 'control': None,
 'deleted': None,
 'email': [<gdata.contacts.Email object at 0x10309a650>,
           <gdata.contacts.Email object at 0x10309a690>,
           <gdata.contacts.Email object at 0x10309a6d0>,
           <gdata.contacts.Email object at 0x10309a710>,
           <gdata.contacts.Email object at 0x10309a790>],
 'etag': None,
 'event': [],
 'extended_property': [],
 'extension_attributes': {},
 'extension_elements': [],
 'external_id': [],
 'gender': None,
 'group_membership_info': [<gdata.contacts.GroupMembershipInfo object at 0x10309a850>,
                           <gdata.contacts.GroupMembershipInfo object at 0x10309a890>],
 'im': [],
 'link': [<atom.Link object at 0x10309a510>,
          <atom.Link object at 0x10309a550>,
          <atom.Link object at 0x10309a5d0>],
 'nickname': None,
 'occupation': None,
 'organization': [],
 'phone_number': [<gdata.contacts.PhoneNumber object at 0x10309a7d0>,
                  <gdata.contacts.PhoneNumber object at 0x10309a810>],
 'postal_address': [],
 'published': None,
 'relation': [],
 'rights': None,
 'source': None,
 'structured_pstal_address': [],
 'summary': None,
 'text': None,
 'title': <atom.Title object at 0x10309a490>,
 'updated': <atom.Updated object at 0x10309a3d0>,
 'user_defined_field': [],
 'website': []}


 'author',
 'batch_id',
 'batch_operation',
 'batch_status',
 'birthday',
 'category',
 'content',
 'contributor',
 'control',
 'deleted',
 'email',
 'etag',
 'event',
 'extended_property',
 'extension_attributes',
 'extension_elements',
 'external_id',
 'gender',
 'group_membership_info',
 'id',
 'im',
 'link',
 'nickname',
 'occupation',
 'organization',
 'phone_number',
 'postal_address',
 'published',
 'relation',
 'rights',
 'source',
 'structured_pstal_address',
 'summary',
 'text',
 'title',
 'updated',
 'user_defined_field',
 'website']


'''
