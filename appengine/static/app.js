Ext.BLANK_IMAGE_URL = 'ext/resources/images/default/s.gif';
// turn on validation errors beside the field globally
Ext.form.Field.prototype.msgTarget = 'side';

origin_icons = {
    'com.twitter' : '/static/twitter_30x30.png',
    'iphone:call' : '/static/phone_30x30.png',
    'iphone:sms' : '/static/sms_30x30.png',
    'com.apple.addressbook': '/static/addressbook_30x30.png',
}
   
Ext.apply(Ext.form.VTypes, {
    password : function(val, field) {
        if (field.initialPassField) {
            var pwd = Ext.getCmp(field.initialPassField);
            return (val == pwd.getValue());
        }
        return true;
    },
    passwordText : 'Passwords do not match'
});

Ext.onReady(function(){

    Ext.QuickTips.init();
    
    // ------ PERSON STORE ----
    var Person = Ext.data.Record.create([
      {name: 'first_name', mapping: 'first_name'},
      {name: 'last_name', mapping: 'last_name'},
      {name: 'modified', mapping: 'modified', type: 'date', dateFormat:'timestamp'},
      {name: 'created', mapping: 'created', type: 'date', dateFormat:'timestamp'},
      {name: 'atts', mapping: 'atts' }
    ])

    var person_store = new Ext.data.GroupingStore({
      proxy: new Ext.data.HttpProxy({ method: 'GET', url: '/person' }),
      reader: new Ext.data.JsonReader({
        totalProperty: 'results',
        idProperty: 'uid',
        root: 'rows',
      }, Person)
    });

    // ------ MESSAGE STORE ----
    var Message = Ext.data.Record.create([
      { name: 'origin', mapping: 'origin' },
      { name: 'frm', mapping: 'frm' },
      { name: 'to', mapping: 'to' },
      { name: 'atts', mapping: 'atts' },
      { name: 'modified', mapping: 'modified', type: 'date', dateFormat:'timestamp' },
      { name: 'created', mapping: 'created', type: 'date', dateFormat:'timestamp' },
      { name: 'atts', mapping: 'atts' },
      { name: 'meta', mapping: 'meta' }
    ])

    var message_store = new Ext.data.GroupingStore({
      proxy: new Ext.data.HttpProxy({ method: 'GET', url: '/message' }),
      reader: new Ext.data.JsonReader({
        totalProperty: 'results',
        idProperty: 'uid',
        root: 'rows',
      }, Message)
    });

    // ------ LOG STORE ----
    var Log = Ext.data.Record.create([
      { name: 'origin', mapping: 'origin' },
      { name: 'entry', mapping: 'entry' },
      { name: 'level', mapping: 'level' },
      { name: 'created', mapping: 'created', type: 'date', dateFormat:'timestamp' },
    ])

    var log_store = new Ext.data.GroupingStore({
      proxy: new Ext.data.HttpProxy({ method: 'GET', url: '/log' }),
      reader: new Ext.data.JsonReader({
        totalProperty: 'results',
        root: 'rows',
      }, Log)
    });

    log_store.load();
    person_store.load();
    message_store.load();

    function renderAtt(value, p, record){
        var img = "ext/resources/images/default/s.gif";
        if (record.data.atts.length > 0)
            img = "/att/"+record.data.atts[0];
        return String.format('<img src="{0}" height="30" />', img);
    }

    function renderContact(value, p, record) {
        var name = String.format('{0} {1}', record.data.first_name, record.data.last_name);
        return name;
    }
    
    var person_grid = new Ext.grid.GridPanel({

        store: person_store,
        title: 'Contacts',
        view: new Ext.grid.GroupingView({ markDirty: false }),
        columns:[
          { header: "Picture",
            dataIndex: "atts",
            width: 60,
            sortable: false,
            renderer: renderAtt,
          },
          { header: "Name",
            dataIndex: "",
            width: 800,
            renderer: renderContact,
          },
        ],
        bbar: new Ext.PagingToolbar({
            store: person_store,
            displayInfo: true,
            displayMsg: 'Displaying contacts {0} - {1} of {2}',
            emptyMsg: "No contacts to display",
            items:[]
        })

    });

    function renderOrigin(value, p, record) {
        var icon = origin_icons[record.data.origin];
        if (!icon)
            icon = Ext.BLANK_IMAGE_URL;
        return String.format("<img src='{0}' width='30' />",icon);
    }
    
    function renderMsgContact(r) {
        var res = "";
        for (var x=0; x < r.length; x++) {
            var p = r[x][2];
            if (p)
                res += String.format ("{0} {1}", p['first_name'], p['last_name']);
            else
                res += r[x][1];
        }
        return res;
    }
        
    function renderFrom(value, p, record) {
        return renderMsgContact(record.data.frm);
    }
    
    function renderTo(value, p, record) {
        return renderMsgContact(record.data.to);
    }
    
    function renderBody(value, p, record) {
        if (record.data.atts.length > 0) {
            var s = "<div id='tmp_"+record.id+"'>...</div>";
            // XXX this races with the DOM creation, probably move the summary into the server JSON
            // and show rest in bigger preview
            Ext.Ajax.request({
                url: '/att/'+record.data.atts[0],
                success: function(resp, options) {
                    Ext.getDom('tmp_'+record.id).innerHTML = resp.responseText;
                },
            });
            return s;
        } else
            return "";
    }

    var message_grid = new Ext.grid.GridPanel({
        store: message_store,
        title: 'Messages',
        view: new Ext.grid.GroupingView({ markDirty: false }),
        columns : [
          { header: "Type",
            dataIndex: "origin",
            width: 35,
            renderer: renderOrigin
          },
          { header: "From",
            dataIndex: "frm",
            width: 100,
            renderer: renderFrom,
          },
         { header: "To",
            dataIndex: "frm",
            width: 100,
            renderer: renderTo,
          },
          { header: "Body",
            dataIndex: "",
            width: 600,
            renderer: renderBody,
          },
          { header: "Date",
            dataIndex: "created",
            width: 150,
          }
        ],
        bbar: new Ext.PagingToolbar({
            store: message_store,
            displayInfo: true,
            displayMsg: 'Displaying messages {0} - {1} of {2}',
            emptyMsg: "No messages to display",
            items:[]
        })        
    });

    var log_grid = new Ext.grid.GridPanel({
        frame: true,
        store: log_store,
        title: 'Recent Activity',
        view: new Ext.grid.GroupingView({ markDirty: false }),
        columns : [
          { header: "Type",
            dataIndex: "origin",
            width: 35,
            renderer: renderOrigin
          },
         { header: "Entry",
            dataIndex: "entry",
            width: 100,
          },
          { header: "Date",
            dataIndex: "created",
            width: 150,
          }
        ],
        bbar: new Ext.PagingToolbar({
            store: log_store,
            displayInfo: true,
            displayMsg: 'Displaying activity {0} - {1} of {2}',
            emptyMsg: "No activity to display",
            items:[]
        })        
    });


    var plugins_grid = new Ext.Panel({
        title: 'Plugins',
        id: 'plugins-panel',
        frame: true,
        contentEl: 'plugin-auth',
    });
    
    var settings_grid = new Ext.FormPanel({
        title: 'Settings',
        id: 'prefs-form',
        width: 600,
        frame: true,
        trackResetOnLoad: true,
        buttons: [ 
            { text:'Reset',
              handler: function(btn,e) {
                Ext.getCmp('prefs-form').getForm().reset();
              }
            },
            { 
              text:'Save', 
              handler: function(btn,e) {
                var vals =  Ext.getCmp('prefs-form').getForm().getValues();
                var js = {'first_name':vals['first_name'], 'last_name':vals['last_name'], 'email':vals['email'] };
                if (vals['pass2'] != vals['passphrase'])  {
                    Ext.MessageBox.alert('Passphrase mismatch', 'Please type in the same passphrase twice to confirm it.');
                    return;
                }
                if (vals['passphrase'].length > 0) 
                    js['passphrase'] = vals['passphrase'];
                 Ext.Ajax.request({
                   url: '/prefs',
                   method: 'POST',
                   jsonData: vals,
                   success: function() {
                       Ext.MessageBox.alert('Passphrase changed', 'Your passphrase has been changed.');
                   },
                   failure: function() {
                       Ext.MessageBox.alert('Passphrase not changed', 'Error communicating with personal container. Your passphrase is not changed.');
                   }
                 });                
              }
            }
        ],
        items: [
                { 'xtype': 'textfield',
                  'name' : 'first_name',
                  'fieldLabel' : 'First Name',
                },
                { 'xtype': 'textfield',
                  'name' : 'last_name',
                  'fieldLabel' : 'Last Name',
                },
                { 'xtype': 'textfield',
                  'name' : 'email',
                  'fieldLabel' : 'EMail',
                },
                { 'xtype': 'textfield',
                  'name' : 'passphrase',
                  'id': 'pass1',
                  'inputType' : 'password',
                  'fieldLabel' : 'Passphrase',
                },
                { 'xtype': 'textfield',
                  'name' : 'pass2',
                  'inputType' : 'password',
                  'fieldLabel' : 'Confirm Passphrase',
                  'vtype': 'password',
                  'initialPassField' : 'pass1'
                },
            ],
        
     }); 
     settings_grid.load({url:'/prefs',method:'GET'});
    var tabs = new Ext.TabPanel({
      activeTab: 0,
      items: [ message_grid, person_grid ],
    });

    new Ext.Viewport({
       layout: 'border',
       title: 'Ext Layout Browser',
       items: [{
            xtype: 'box',
            region: 'north',
            applyTo: 'header',
            height: 30
          },{
            layout: 'accordion',
            region:'west',
            border: false,
            split:true,
            margins: '2 0 5 0',
            width: 275,
            items: [ settings_grid, plugins_grid, log_grid ],
          },
          { xtype:'panel',
            region: 'center',
            layout:'fit',
            border: false,
            id: 'content-panel',
            margins: '2 0 5 0',
            items: [ tabs ]
          },
        ],
        renderTo: Ext.getBody(),
        
    });


});
