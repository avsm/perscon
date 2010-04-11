from Foundation import *
from AppKit import *
from SyncServices import *
import sys

class SyncRecord:
    def __init__(self):
        self.fields = {}

    def applyAction(self,change):
        if change['ISyncChangePropertyActionKey'] == 'set':
            self.fields[change['ISyncChangePropertyNameKey']] = change['ISyncChangePropertyValueKey'] 
        else:
            print "unknown action: a"

    def __str__(self):
         return str(self.fields)

class ContactSync:
    def __init__(self, client_name):
        desired_entities = [ "Contact", "Phone Number", "Email Address", "IM" ]
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

        #set the session to pull mode (pull to client from truth)
        self.session.prepareToPullChangesForEntityNames_beforeDate_(self.entar,NSDate.distantFuture())

    def pull(self):
        print "getting"
        changes_enum = self.session.changeEnumeratorForEntityNames_(self.entar)
        changes = changes_enum.allObjects()

        for change in changes:
            #print str(change.record())
            r = SyncRecord()
            for action in change.changes():
                r.applyAction(action)
            print str(r)
            print ""
    #enc_change_text = change.record()["text"]
    # decode
    #attr_txt = NSUnarchiver.unarchiveObjectWithData_(enc_change_text)
    # get the string value and print it
    #print "Sticky text is %s" % (attr_txt.string())
    
#finish the session
    def finish(self):
        self.session.finishSyncing()

def main():
    c = ContactSync("net.perscon.test3")
    c.pull()
    c.finish()

if __name__ == "__main__":
    main()








