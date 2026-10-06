7️⃣ 7TV features
================

In this page we will document bot's features for adding / removing / managing `7TV <https://7tv.app/>`_ emotes.
There is quite a few features, so let's get started.

🖊️ Making the bot your 7TV editor
#################################

.. attention::

   For 7TV bot's features to work - you need to add the bot as your 7TV editor.
   So please,

   1. Go to your `7TV editors settings page <https://7tv.app/settings/editors>`_
   2. Add Editor ``@IrenesBot``
   3. Set Editor Permissions - currently, ``Emotes Sets > ✅ Manage`` permission (the default) is enough, 
      but maybe future features will require more.
   4. At the moment, the bot doesn't automatically accept 7TV editor invites. However, you can use ``!7tv editor accept`` 
      command to make the bot accept it
   5. The commands below might be of help.

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_editor_guide

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_editor_accept

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_editor_status


📐 Linking bot 7tv features to an emote set
###########################################

7tv features are mostly performed on 7TV emote sets, links to which the bot saves in its database. 
This documentation will refer to such emote sets as "attached emote set". 
As it was mentioned above - if the streamer uses ``!7tv editor accept`` command then the bot will attach to their currently active emote set by default.

If, in future, the streamer decides to mess around with their 7tv emote sets, e.g. make a new one or select some other emote set as their active - 
the commands here will help to reattach the bot to a proper emote set that the streamer wants the bot to manage.

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_emoteset_status

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_emoteset_attach

🚲 Cycling Emotes Channel Reward
################################

These commands are about managing 7tv cycling emotes.

Cycling emotes are supposed to work as follows. 
A streamer has a channel points redeem (that was setup with the bot's help).
When a chatter redeems it with the text specifying what emote to add - 
the bot adds this emote to the channel but considers it as a "cycling emote".
Eventually, when the total amount of cycling emotes becomes more than a currently set up ``emote_limit`` - 
the bot removes the oldest emote from the channel.
In other words, the bot *cycles out* the oldest emote - hence the name for the feature.

Here is a screenshot of how it works with ``emote_limit = 2``. 

1. I add "🔵Blue" emote with an ``<emote_id>`` - the bot adds it;
2. I add "🟡Yellow" emote with its ``<7tv_link>`` - the bot adds it;
3. I add "🟣Purple" emote with its ``<emote_id>`` and ``<emote_alias>="MaybeOrange"`` 
   (so the emote will be called "MaybeOrange" and not "Purple") - 
   the bot adds it, but this time the limit came to play - it also had to remove the "🔵Blue" emote.

.. image:: /_static/images/cycling-emotes.png

.. attention::

   Sometimes it takes a bot a few seconds to add / remove the requested emotes. 
   7TV sometimes slowly responds to our requests. 
   We all know how 7TV can be laggy and annoying. 
   Well, it's quite the same when developing with it.

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_create

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_status

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_drop

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_limit

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_showemotes

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_cycle_allowcommonwords

🤹🏻 Emote Management
#####################

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_add

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_rename

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_remove

🐦‍⬛ Blacklisting
##################

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_blacklist_create

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_blacklist_duration

🤣 Emote Stats
##############

Coming Soon

🥸 7TV Editors 
###############

.. autochatcommand:: modules.public.seven_tv.SevenTVFeatures.stv_mods