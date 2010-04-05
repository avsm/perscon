// ==========================================================================
// Project:   Perscon - mainPage
// Copyright: ©2010 Anil Madhavapeddy <anil@recoil.org>
// ==========================================================================
/*globals Perscon */

// This page describes the main user interface for your application.  
Perscon.mainPage = SC.Page.design({


  mainPane: SC.MainPane.design({
    childViews: 'middleView topView bottomView'.w(),
         
    topView: SC.ToolbarView.design({
      layout: { top: 0, left: 0, right: 0, height: 36 },
      childViews: 'labelView settingsButton'.w(),
      anchorLocation: SC.ANCHOR_TOP,
      
      labelView: SC.LabelView.design({
          layout: { centerY: 0, height: 24, left: 8, width: 200 },
          controlSize: SC.LARGE_CONTROL_SIZE,
          fontWeight: SC.BOLD_WEIGHT,
          value:   'Personal Container'
      }),
      
      settingsButton: SC.ButtonView.design({
        layout: { centerY: 0, height: 24, right: 12, width: 100 },
        title:  "Settings",
        action: "showPane",
        target: "Perscon.prefsController",
      })

    }),
    
    middleView: SC.ScrollView.design({
      hasHorizontalScroller: NO,
      layout: { top: 36, bottom: 32, left: 0, right: 0 },
      backgroundColor: 'white',
 
      contentView: SC.ListView.design({
      })
    }),
    
    bottomView: SC.ToolbarView.design({
      layout: { bottom: 0, left: 0, right: 0, height: 32 },
      anchorLocation: SC.ANCHOR_BOTTOM
    })
  }),
  
  settingsView: SC.SheetPane.design({
    layout: { width: 400, height: 240, centerX: 0, centerY: 0 },
    classNames: 'settings',
    childViews: 'contentView'.w(),

    contentView: SC.View.extend({
        childViews: 'firstNameView lastNameView emailView headingView passphraseView passphrase2View passphraseButton doneButton'.w(),
        
        firstNameView: SC.TextFieldView.design({
            hint: 'First Name',
            valueBinding: 'Perscon.prefsController.firstName',
            layout: { height: 24, width: 100, left: 20, top: 50 }
        }),
        
        lastNameView: SC.TextFieldView.design({
            hint: 'Last Name',
            valueBinding: 'Perscon.prefsController.lastName',
            layout: { height: 24, width: 130, left: 140, top: 50 }
        }),
        
        emailView: SC.TextFieldView.design({
            hint: 'E-Mail',
            valueBinding: 'Perscon.prefsController.email',
            layout: { height: 24, width: 250, left: 20, top: 80 }
        }),
        
        passphraseView: SC.TextFieldView.design({
            hint: 'Passphrase',
            valueBinding: 'Perscon.prefsController.passphrase',
            isPassword: true,
            layout: { height: 24, width: 250, left: 20, top: 120 }
        }),
        
        passphrase2View: SC.TextFieldView.design({
            hint: 'Repeat Passphrase',
            valueBinding: 'Perscon.prefsController.passphrase2',
            isPassword: true,
            layout: { height: 24, width: 250, left: 20, top: 150 }
        }),

        headingView: SC.LabelView.design({
            layout: { left: 20, top: 5, width: 200 },
            controlSize: SC.LARGE_CONTROL_SIZE,
            fontWeight: SC.BOLD_WEIGHT,
            value: 'Settings',
        }),
        
        passphraseButton: SC.ButtonView.design({
            layout: { width: 160, left: 20, top: 185 },
            buttonBehaviour: SC.PUSH_BEHAVIOR,
            target: "Perscon.prefsController",
            action: "changePassphrase",
            title: "Change Passphrase",
        }),

        doneButton: SC.ButtonView.design({
            layout: { width: 80, left: 190, top: 185 },
            isDefault: true,
            buttonBehaviour: SC.PUSH_BEHAVIOR,
            target: "Perscon.prefsController",
            action: "hidePane",
            title: "Done",
        }),

    })
}),


});
