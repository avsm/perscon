import sys,objc
from SyncServices import *

if __name__ == "__main__":
  if not ISyncManager.isEnabled:
    print "sync manager not enabled"
    sys.exit(1)
  manager = ISyncManager.sharedManager ()
  clientId = NSString.stringWithString_(u'org.recoil.test')
  client = manager.clientWithIdentifier_(clientId)
  if not client:
    print "registering client"
    bundle = NSBundle.bundleWithPath_(".")
    pl = bundle.pathForResource_ofType_("PersCon", "plist")
    client = manager.registerClientWithIdentifier_descriptionFilePath_(clientId, pl)
    print client
  print client
