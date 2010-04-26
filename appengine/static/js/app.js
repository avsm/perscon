Ext.BLANK_IMAGE_URL = '/js/ext/resources/images/default/s.gif';
// turn on validation errors beside the field globally
Ext.form.Field.prototype.msgTarget = 'side';

origin_icons = {
    'com.twitter' : '/images/twitter_30x30.png',
    'iphone:call' : '/images/phone_30x30.png',
    'iphone:sms' : '/images/sms_30x30.png',
    'com.adium' : '/images/chat_30x30.png',
    'com.apple.iphoto' : '/images/iphoto_30x30.png',
    'com.apple.addressbook': '/images/addressbook_30x30.png',
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
      { name: 'tos', mapping: 'tos' },
      { name: 'atts', mapping: 'atts' },
      { name: 'modified', mapping: 'modified', type: 'date', dateFormat:'timestamp' },
      { name: 'created', mapping: 'created', type: 'date', dateFormat:'timestamp' },
      { name: 'atts', mapping: 'atts' },
      { name: 'meta', mapping: 'meta' },
      { name: 'thread_count', mapping: 'thread_count' },
      { name: 'loc', mapping: 'loc' }
    ])

    var message_store = new Ext.data.GroupingStore({
      proxy: new Ext.data.HttpProxy({ method: 'GET', url: '/message?threaded=1' }),
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
        var img = "/js/ext/resources/images/default/s.gif";
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
            var p = r[x]['person'];
            if (p)
                res += String.format ("{0} {1}", p['first_name'], p['last_name']);
            else {
                switch (r[x]['ty']) {
                  case 'url':
                      res += r[x]['value'].split('/').pop();
                      break;
                  case 'email':
                      res += String.format("<a href='mailto:{0}'>{0}</a>",r[x]['value']);
                      break;
                  case 'im':
                      res += String.format("{0} <i>({1})</i>",r[x]['proto'][1], r[x]['proto'][0]); 
                      break;
                  default: 
                      res += r[x]['value'];
               }
            }
        }
        return res;
    }
        
    function renderFromTo(value, p, record) {
        return renderMsgContact(record.data.frm) + " &rarr; " + renderMsgContact(record.data.tos);
    }
    
    function renderBody(value, p, record) {
        var s = "";
        if (record.data.atts.length > 0) {
            s = "<span class='messageBody' id='tmp_"+record.id+"'>...</span>";
            if (record.data.atts[0]) {
                var mime = record.data.atts[0]['mimetype'];
                if (mime == 'text/plain') {
                   // XXX this races with the DOM creation, probably move the summary into the server JSON
                   // and show rest in bigger preview
                   Ext.Ajax.request({
                      url: '/att/'+record.data.atts[0]['key'],
                      success: function(resp, options) {
                        Ext.getDom('tmp_'+record.id).innerHTML = resp.responseText;
                       },
                   });
                } else if (mime.match("^image/")) {
                  s = "<span class='messageBody'><img src='/att/"+record.data.atts[0]['key']+"' height=20></span>";
                }
            }
        }
        var tofrom = renderMsgContact(record.data.frm) + " &rarr; " + renderMsgContact(record.data.tos);
        var tc = (record.data.thread_count > 0) ? ("(" + record.data.thread_count + " in thread)") : "";
        return String.format("<div class='messageWrapper'><span class='messageToFrom'>{0}</span><span class='messageDate'>{1}</span><span class='messageThreadCount'>{2}</span><br />{3}</div>", tofrom, record.data.created, tc, s);
    }

    var message_grid = new Ext.grid.GridPanel({
        store: message_store,
        title: 'Messages',
        view: new Ext.grid.GroupingView({ markDirty: false }),
        columns : [
          { header: "Type",
            dataIndex: "origin",
            width: 40,
            renderer: renderOrigin
          },
          { header: "Body",
            dataIndex: "thread_count",
            width: 800,
            renderer: renderBody,
          },
        ],
        bbar: new Ext.PagingToolbar({
            store: message_store,
            displayInfo: true,
            displayMsg: 'Displaying messages {0} - {1} of {2}',
            emptyMsg: "No messages to display",
            items:[]
        })        
    });

    function renderLogEntry(value, p, record) {
        var icon = origin_icons[record.data.origin];
        if (!icon)
            icon = Ext.BLANK_IMAGE_URL;
        return String.format('<div class="logEntry"><img src="{0}" width="15" /><span class="logEntryBody-{1}">{2}</span>, <span class="logEntryDate">{3}</span></div>',icon, record.data.level, record.data.entry, record.data.created);
    }
    
    var log_grid = new Ext.grid.GridPanel({
        frame: true,
        store: log_store,
        title: 'Recent Activity',
        view: new Ext.grid.GroupingView({ markDirty: false }),
        columns : [
          { header: "Entry",
            dataIndex: "origin",
            width: 300,
            renderer: renderLogEntry
          },
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
        contentEl: 'plugin_auth',
    });
    
    var maps_grid = new Ext.Panel({
        title: 'Map',
        id: 'maps-panel',
        frame: true,
        autoHeight: true,
        width: 400,
        items: [{
            xtype: 'gmappanel',
            zoomLevel: 16,
            gmapType: 'map',
            width: 400,
            height: 400,
            id: 'gmap-panel',
            border: true,
            mapConfOpts: ['enableScrollWheelZoom','enableDoubleClickZoom','enableDragging'],
            mapControls: ['GSmallMapControl','GMapTypeControl'],
            setCenter: {
                lat: 42.339641,
                lng: -71.094224
            },
            markers:[]
        }]
    });

    message_grid.on('rowclick', function(grid, rowIndex, e) {
        var row = grid.getView().getRow(rowIndex);
        var record = message_store.getAt(rowIndex);
        console.log(record.data);
        var loc = record.data['loc'];
        console.log(loc);
        if (loc) {
            var pt = new google.maps.LatLng(loc['lat'],loc['lon']);
            var m = Ext.getCmp('gmap-panel');
            console.log(m);
            m.addMarker(pt, {});
            m.getMap().setCenter(pt, 12);
        }
    }, message_grid);

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
            items: [ maps_grid, settings_grid, plugins_grid, log_grid ],
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

   function startSync(plugin) {
      alert('start: ' + plugin);
   }

   function refreshPlugin(plugin) {
       Ext.Ajax.request({
           url: '/sync/'+plugin,
           success: function(resp, options) {
               var j = Ext.decode(resp.responseText);
               var html = "?";
               console.log(j);
               switch (j['status']) {
                 case 'NEEDAUTH':
                    html = String.format('Needs authentication: <a href="/drivers/{0}/login">Login</a>', plugin);
                    break;
                 case 'AUTHORIZED': 
                    // hack.  grim.  sorry.
                    if (j['threads'].length == 0) {
                      html = String.format('Logged in ({0}): <a id="plugin_href_start_{1}" href="#">Start Sync</a>', j['username'], plugin);
                    } else {
html = "";
                      for (var x=0; x < j['threads'].length; x++) {
console.log(x);
                        var t = j['threads'][x];
console.log(t);
                        switch (t['status']) {
                          case 'UNSYNCHRONIZED': 
                            html += String.format('Logged in ({0}): <a id="plugin_href_start_{1}" href="#">Start Sync {2}</a><br />', j['username'], plugin, t['thread']); break;
                          case 'SYNCHRONIZED': 
                            html += String.format('Logged in ({0}): <a id="plugin_href_start_{1}" href="#">Refresh Sync {2}</a><br />', j['username'], plugin, t['thread']); break;
                          case 'INPROGRESS': 
                            html += String.format('Logged in ({0}): <a id="plugin_href_stop_{1}" href="#">Cancel Sync {2}</a><br />', j['username'], plugin, t['thread']); break;
                        }
                      }
                    }
                    break;
               }

               var x = Ext.fly('plugin_'+plugin).update(html);
               var start = x.down('#plugin_href_start_'+plugin);
               var stop  = x.down('#plugin_href_stop_'+plugin);
               if (start)
                 start.on('click', function() {
                     console.log('start');
                     Ext.Ajax.request({url: '/sync/'+plugin+'/start', method:'POST', success: function() { refreshPlugin(plugin); }});
                   });
               if (stop)
                 stop.on('click', function() {
                     console.log('stop');
                     Ext.Ajax.request({url: '/sync/'+plugin+'/stop', method:'POST', success: function() { refreshPlugin(plugin); }});
                   });
           },
       });
   }

   refreshPlugin('twitter');

});
