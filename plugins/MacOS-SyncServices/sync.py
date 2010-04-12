import sys
sys.path.append ("../../support")
from pkg_resources import require
require ("simplejson")

from Foundation import *
from AppKit import *
from SyncServices import *

import Perscon_utils
import Perscon_config
import simplejson

class SyncRecord:
    def __init__(self, change):
        self.set_fields = {}
        self.uid = change.recordIdentifier()
        for c in change.changes():
            self.applyAction(c)

    def applyAction(self,change):
        if change['ISyncChangePropertyActionKey'] == 'set':
            v = change['ISyncChangePropertyNameKey']
            if v == 'contact':
                cs = change['ISyncChangePropertyValueKey'][0]
            else:
                cs = change['ISyncChangePropertyValueKey']
                if isinstance(cs, NSDate):
                   cs = float(cs.timeIntervalSince1970())
                elif isinstance(cs, NSURL):
                   cs = cs.absoluteString()
            self.set_fields[change['ISyncChangePropertyNameKey']] = cs
        else:
            print "unknown action: a"

    def __str__(self):
         return simplejson.dumps({'set': self.set_fields, 'uid': self.uid}, indent=2)

class ContactSync:
    def __init__(self, client_name, ae):
        self.ae = ae
        self.client_name = client_name
        desired_entities = [ "Contact", "Phone Number", "Email Address", "IM", "URL" ]
        self.entar = NSArray.arrayWithArray_(map(lambda x: NSString.stringWithString_("com.apple.contacts."+x), desired_entities))

        plist_file =  "PersCon.plist"

        self.manager = ISyncManager.sharedManager()
        if self.manager.isEnabled() != 1:
            print("SyncManager is not enabled. Bailing out")
            sys.exit(1) # XXX exception

        # get the client object    
        client_name = NSString.stringWithString_(client_name)
        bundle = NSBundle.bundleWithPath_(".")
        pl = bundle.pathForResource_ofType_("PersCon", "plist")
        self.client = self.manager.registerClientWithIdentifier_descriptionFilePath_(client_name, pl)

        print "the client supports the entities: %s" % (",".join(self.client.supportedEntityNames()))
        # set the client to pull the truth (i.e. do not save any records into the sync system)
        self.session = ISyncSession.beginSessionWithClient_entityNames_beforeDate_(self.client,self.entar,NSDate.distantFuture())
        self.client.setShouldReplaceClientRecords_forEntityNames_(True,self.entar)


    def pull(self):
        print "pulling"
        self.session.prepareToPullChangesForEntityNames_beforeDate_(self.entar,NSDate.distantFuture())
        changes_enum = self.session.changeEnumeratorForEntityNames_(self.entar)
        changes = changes_enum.allObjects()
        for change in changes:
            r = SyncRecord(change)
            print str(r)
            self.ae.rpc('sync/macos/change/%s' % self.client_name, data=str(r))
        self.session.clientCommittedAcceptedChanges()
    
    def finish(self):
        self.session.finishSyncing()

def main():
    c = ContactSync("net.perscon."+Perscon_config.app_name, Perscon_utils.AppEngineRPC())
    c.pull()
    c.finish()

if __name__ == "__main__":
    main()
