7️⃣ 7TV features
================

.. important::

    For most administrative 7tv bot's features to work - you need to add the bot as your 7TV editor `here <https://7tv.app/settings/editors>`_.
    Currently, ``Emotes > Manage`` permission is enough, but maybe future features will require more.

🤣 Emote Stats
##############

Coming Soon

🚲 Cycling Emotes Channel Reward
################################

These commands are about managing 7tv cycling emotes.

Cycling emotes are supposed to work as follows. 
A streamer has a channel points redeem (that was setup with the bot's help).
When a user redeems it and specifies an emote to add - the bot adds this emote to the channel but considers it as a "cycling emote".
Eventually, when the total amount of cycling emotes becomes more than a currently set up ``emote_limit`` - the bot removes the oldest emote from the channel.
In other words, the bot cycles out the oldest emote - hence the name for the feature.

Here is a screenshot of how it works with ``emote_limit = 2``. 

1. I add "🔵Blue" emote with an ``<emote_id>`` - the bot adds it;
2. I add "🟡Yellow" emote with its ``<7tv_link>`` - the bot adds it;
3. I add "🟣Purple" emote with its ``<emote_id>`` and "MaybeOrange" as its ``<emote_alias>`` 
   (so the emote will be called "MaybeOrange" and not "Purple") - 
   the bot adds it, but this time the limit came to play - it also had to remove "🔵Blue" emote.

.. image:: /_static/images/cycling-emotes.png

.. attention::

   Sometimes it takes a bot a few seconds to add / remove the requested emotes. 
   7TV sometimes slowly responds to our requests.

The list of commands:

``!7tv cycle create``
---------------------

* Arguments: 
   * **emote_limit** (integer, 10 by default) - an upper limit for total amount of cycling emotes.

* Usage Example(-s): ``!7tv cycle create 10``

   Create a channel points reward, redeems for which the bot will listen to and process them to add/remove 7tv emotes to the channel.

   PS. Streamers are able to edit the resulting channel points reward in their streamer dashboard (https://dashboard.twitch.tv/u/your-twitch-tv-name/viewer-rewards/channel-points/rewards).
   Please, don't disable ``Require Viewer to Enter Text`` as the bot won't be able to get anything, obviously.

``!7tv cycle status``
---------------------
* Arguments: 
   * **None**.

* Usage Example(-s): ``!7tv cycle status``

   Get some information about your cycling-emotes channel points reward.
   Mostly some information useful for the developer.

``!7tv cycle remove``
---------------------
* Arguments: 
    * **emote_id** (text, emote_alias or emote_id formats are supported) - 7TV emote id.

* Usage Example(-s): ``!7tv cycle remove Blue``, ``!7tv cycle remove 01J8FC6EN0000DNWJ3ST67HH38``

   Remove an emote from the cycling list.
   Useful, when streamer wants to elevate an emote from cycling list into a "permanent" one.
   In other words, to prevent the emote from being eventually cycled out.

``!7tv cycle limit``
---------------------
* Arguments: 
   * **new_limit** (text, emote_alias or emote_id formats are supported) - 7TV emote id.

* Usage Example(-s): ``!7tv cycle limit 20``

   Set a new limit for cycling emote list.


``!7tv cycle attach``
---------------------
* Arguments: 
   * **reward_name** (text) - a name of existing channel points reward for the bot to start listening to.

* Usage Example(-s): ``!7tv cycle attach add 7tv emote lol``

   Instead of creating a new channel points reward with ``!7tv cycle create`` you can attach an existing reward for the bot to listen to.

