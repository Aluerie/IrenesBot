🤩 F.A.Q.
=======================

🤯 What is the bot's prefix?
############################

* The bot's command prefixes are ``!``, ``?``, ``$``. 
  Which means that the bot will respond to all of these commands: ``!hi``, ``?hi``, ``$hi`` with the same response.
  Maybe in future the bot will support custom per channel command prefixes.
* To be short, this documentation will just write one command prefix (``!``) when mentioning a command.

🤔 Should streamers give the bot moderator role?
#################################################

* The bot should give itself a moderator role upon joining your channel. If it doesn't for some reason - please, mod it yourself.
  As it was said in the :ref:`how_to_invite` section -
  :iconify:`logos:twitch` twitch is silly and they rate-limit small bots quite a lot, 
  which is annoying to deal with and it's possible it might break some of the bot's features.
  So again, please, moderate the bot.

  .. hint::

    You can mod the bot by typing ``/mod @IrenesBot`` in your twitch channel's chat.

🦤 Do streamers need to do something beyond inviting the bot?
#############################################################

* If a feature requires you to do extra action (e.g. add the bot account to 7tv editors) 
  then the corresponding page in this documentation will instruct about it.

💡 More random tips?
####################

.. _channel_points_reward_tips:

🥎 Features related to channel point rewards
---------------------------------------------


* After creating a channel points reward with bot commands -
  streamers are able to edit the resulting channel points reward in their :iconify:`logos:twitch` `streamer dashboard
  <https://dashboard.twitch.tv/viewer-rewards/channel-points/rewards>`_.
* However, please, don't disable ``Require Viewer to Enter Text`` for rewards that require user input as 
  the bot won't be able to get anything, obviously.
* If the bot sets a max amount of redeems per stream or cooldown for channel points redeem - then it's probably needed 
  (e.g. for "First!" redeems).
* The bot is not able to attach to previously created channel point rewards that were created by other accounts 
  (e.g. by broadcaster or other bots). 
  It's a twitch restriction - the bots can manage only those channel point rewards that were created by the bot itself.
* If, for some reason, the channel points redemption can't be satisfied - the bot will try to refund the points to the user.
* if the bot goes down for some reason - it will still process redemptions queue as soon as it goes online. 
  Hence if you see the bot not responding - you don't need to refund the points to users yourself just yet - 
  the bot will try to fix everything on its own.
