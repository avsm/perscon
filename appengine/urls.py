# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from django.conf.urls.defaults import *

urlpatterns = patterns(
    '',
    (r'^$', 'views.index'),
    (r'^tasks/fmi$', 'views.fmi_cron'),
    (r'^update/android$', 'views.android_update'),
    (r'^loc$', 'views.loc'),
    (r'^log$', 'perscon_log.crud'),
    (r'^prefs/?$', 'prefs.crud'),
    (r'^service/(.+)/(.+)$', 'views.service'),
    (r'^person/?$', 'views.people'),
    (r'^person/(.+)$', 'views.person'),
    (r'^att/(.+)$', 'views.att'),
    (r'^message/(.+)$', 'views.message'),
    (r'^message/?$', 'views.messages'),
    (r'^twitter/login$', 'twitter.login'),
    (r'^twitter/verify$', 'twitter.verify'),
    (r'^twitter/us$', 'twitter.mentioningUs'),
    (r'^twitter/ourtweets$', 'twitter.ourTweets'),
    (r'^twitter/dm/sent$', 'twitter.ourDMSent'),
    (r'^twitter/dm/received$', 'twitter.ourDMReceived'),
    )
