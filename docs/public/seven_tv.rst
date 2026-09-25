7️⃣ 7TV features
================

7TV public features.

🖊️ Making the bot your 7TV editor
#################################

.. important::

   For 7tv bot's features to work - you need to add the bot as your 7TV editor.
   So please,

   1. Go to your `7TV editors settings page <https://7tv.app/settings/editors>`_
   2. Add Editor ``@IrenesBot``
   3. Set Editor Permissions - currently, ``Emotes Sets > ✅ Manage`` permission (the default) is enough, 
      but maybe future features will require more.
   4. At the moment, the bot doesn't automatically accept 7TV editor invites. However, you can use ``!7tv editor accept`` 
      to make the bot accept it
   5. The commands below might be of help.

``!7tv editor guide``
---------------------

* **Arguments**: ``None``.
* **Usage Example(-s)**: ``!7tv editor guide``

   Sends a small guide on how to make the bot your 7TV editor (practically a TL;DR of the "important" admonition from above)

``!7tv editor accept``
----------------------

* **Arguments**: ``None``.
* **Usage Example(-s)**: ``!7tv editor accept``

   Make the bot accept a pending 7TV editor request from the streamer.

   .. note::

      Invoking this command also makes the bot attach to to your currently active 7tv emote set.
      Which is identical to performing ``!7tv emoteset link`` with no arguments.

``!7tv editor status``
----------------------

* **Arguments**: ``None``.
* **Usage Example(-s)**: ``!7tv editor status``

   Show some debug information about state of 7TV editor request for the streamer.

📐 Linking bot 7tv features to an emote set
###########################################

The bot 7tv emote features are mostly performed on 7tv emote sets. 
This documentation will refer to such emote as "attached emote set". 
As it was mentioned above - if the streamer uses ``!7tv editor accept`` command then the bot will attach to their currently active emote set by default.
If, in future, the streamer decides to mess around with their 7tv emote sets, e.g. make a new one or select some other emote set as their active - 
the commands here will help to reattach the bot to a proper emote set that the streamer wants the bot to manage.

``!7tv emoteset status``
------------------------

* **Arguments**: ``None``.
* **Usage Example(-s)**: ``!7tv emoteset status``

   Show some debug information about currently attached 7tv emote set, if any.

``!7tv emoteset attach``
------------------------

* **Arguments**:
   * ``<emote_set_id>`` (optional, text) - emote set id for the bot to attach to. If not provided - 
     the bot will attach to streamer's currently 7tv active emote set.
* **Usage Example(-s)**: ``!7tv emoteset status``

   Attach bot's 7tv features to the emote set.

🤣 Emote Stats
##############

Coming Soon

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

The list of commands:

``!7tv cycle create``
---------------------

* **Arguments**: 
   * ``<emote_limit>`` (optional, integer, 10 by default) - an upper limit for total amount of cycling emotes.
* **Usage Example(-s)**: ``!7tv cycle create 10``

   Create a channel points reward, redeems for which the bot will listen to and process them to add/remove 7tv emotes to the channel.

   .. admonition:: Notes
      :class: note
      
      * After creating a channel points reward with this command - 
        streamers are able to edit the resulting channel points reward in their streamer dashboard (https://dashboard.twitch.tv/u/your-twitch-tv-name/viewer-rewards/channel-points/rewards).
      * Please, don't disable ``Require Viewer to Enter Text`` as the bot won't be able to get anything, obviously.
      * It's not possible to attach to already created channel point rewards because the bots can manage only those chanel point rewards
        that were created by the bot itself.

``!7tv cycle status``
---------------------
* **Arguments**: ``None``.
* **Usage Example(-s)**: ``!7tv cycle status``

   Get some information about your cycling-emotes channel points reward.
   Mostly some information useful for the developer.

``!7tv cycle remove``
---------------------
* **Arguments**: 
    * ``emote_id`` (text, emote_alias or emote_id formats are supported) - 7TV emote id.
* **Usage Example(-s)**: ``!7tv cycle remove Blue``, ``!7tv cycle remove 01J8FC6EN0000DNWJ3ST67HH38``

   Remove an emote from the cycling list.
   Useful, when streamer wants to elevate an emote from cycling list into a "permanent" one.
   In other words, to prevent the emote from being eventually cycled out.

``!7tv cycle limit``
---------------------
* **Arguments**: 
   * ``new_limit`` (integer) - new limit to set.
* **Usage Example(-s)**: ``!7tv cycle limit 20``

   Set a new limit for cycling emote list.
