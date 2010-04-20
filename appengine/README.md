A personal location tracker which runs under Google AppEngine and
keeps track of you (and only you) from various sources.

To install it, just copy 'passwd.py.in' to 'passwd.py' with your
credentials, and deploy the whole lot to AppEngine.

Portions of the findmyiphone web scraper are originally from:
http://code.google.com/p/findmyiphone/
and covered by the Apache 2 license.

In order to use the Flickr API to provide WOEIDs, a Flickr API key is 
required (http://www.flickr.com/services/apps/create/) and needs to be 
added to passwd.py.

The rest is GPLv2 licensed:

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License along
   with this program; if not, write to the Free Software Foundation, Inc.,
   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


--
Anil Madhavapeddy <anil@recoil.org>
