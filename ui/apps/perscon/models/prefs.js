// ==========================================================================
// Project:   Perscon.Prefs
// Copyright: ©2010 Anil Madhavapeddy <anil@recoil.org>
// ==========================================================================
/*globals Perscon */

/** @class

  (Document your Model here)

  @extends SC.Record
  @version 0.1
*/
Perscon.Prefs = SC.Record.extend(
/** @scope Perscon.Prefs.prototype */ {

    firstName: SC.Record.attr(String),
    lastName: SC.Record.attr(String),
    email: SC.Record.attr(String),
    passphrase: SC.Record.attr(String)

}) ;
