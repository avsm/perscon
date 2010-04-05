// ==========================================================================
// Project:   Perscon.prefsController
// Copyright: ©2010 My Company, Inc.
// ==========================================================================
/*globals Perscon */

/** @class

  (Document Your Controller Here)

  @extends SC.Object
*/
Perscon.prefsController = SC.ObjectController.create(
/** @scope Perscon.prefsController.prototype */ {
    email:'',
    firstName:'',
    lastName:'',
    passphrase:'',
    passphrase2:'',
    
    settingsChanged: function() {
        var s = {
            'firstName': this.get('firstName'),
            'lastName': this.get('lastName'),
            'email': this.get('email')
        };
        SC.Request.postUrl('/prefs', s).json().send();
    }.observes('email','firstName','lastName'),
    
    refreshPane: function() {
        SC.Request.getUrl('/prefs').json().notify(this, 'refreshPaneDone').send();
    },
    refreshPaneDone: function(response) {
        if (SC.ok(response)) {
            var r = response.get('body');
            if (r['email']) this.set('email', r['email']);
            if (r['firstName']) this.set('firstName', r['firstName']);
            if (r['lastName']) this.set('lastName', r['lastName']);
        }
    },
    
    changePassphrase: function() {
        var p1 = this.get('passphrase').toString();
        var p2 = this.get('passphrase2').toString();
        var minLen = 4;
        if (p1.length < minLen || p2.length < minLen) 
            SC.AlertPane.error("Passphrase too short", "Your passphrase must be at least " + minLen + " characters in length.");
        else if (p1 != p2) 
            SC.AlertPane.error("Passphrases do not match", "Please enter the same passphrase in both text fields, and ensure they are the same");
        else {
            var s = { 'passphrase': p1 };
            SC.Request.postUrl('/prefs', s).json().send();
            SC.AlertPane.info("Passphrase updated","Your passphrase has been updated. This will remove any old saved passwords you might have had.");
        } 
    },
    
    paneIsVisible: NO,
    showPane: function() {
        this.set('paneIsVisible', YES);
    },
    hidePane: function() {
        this.set('paneIsVisible', NO);
    },
            
    paneHasChanged: function() {
        var panel = Perscon.mainPage.get('settingsView');
        if (this.get('paneIsVisible')) {
            this.refreshPane();
            panel.append();
        }
        else
            panel.remove();
    }.observes('paneIsVisible'),
    
}) ;
