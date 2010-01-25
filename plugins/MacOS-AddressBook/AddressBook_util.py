import AddressBook

def addressbook_name(person):
    fname = person.valueForProperty_(AddressBook.kABFirstNameProperty) or ""
    lname = person.valueForProperty_(AddressBook.kABLastNameProperty) or ""
    cname = person.valueForProperty_(AddressBook.kABOrganizationProperty) or ""
    if cname != "":
        cname = "(%s)" % cname
    return ("%s %s %s" % (fname, lname, cname)).strip()

def normalize_phone(p):
    import re
    if len(p) < 1:
        return p
    pn = re.sub('[^0-9|\+]','',p)
    if len(pn) < 1:
        return pn
    if pn[0:1] == "00" and len(pn) > 2:
        pn = "+%s" % pn[2:]
    elif pn[0]  == '0':
        pn = "+44%s" % pn[1:]
    return pn

def map_service_to_property(service):
    label = None
    prop = None
    if service == "Twitter":
        label = "LDB:twitter"
        prop = AddressBook.kABURLsProperty
    elif service == "PhoneSMS" or service == "PhoneCall":
        prop = AddressBook.kABPhoneProperty
    elif service == "Jabber" or service == "GTalk":
        prop = AddressBook.kABJabberInstantProperty
    elif service == "MSN":
        prop = AddressBook.kABMSNInstantProperty
    elif service == "Yahoo!":
        prop = AddressBook.kABYahooInstantProperty
    elif service == "AIM":
        prop = AddressBook.kABAIMInstantProperty
    elif service == "email":
        prop = AddressBook.kABEmailProperty
    elif service == "Skype":
        label = "LDB:skype"
        prop = AddressBook.kABURLsProperty
    elif service == "Facebook":
        label = "LDB:facebook"
        prop = AddressBook.kABURLsProperty
    if not prop:
        print "Unknown service: %s" % service
        raise NotImplemented
    return (label, prop)
        
