🤩 Further Preparations
=======================

🤯 Initial settings
###################

* The bot's command prefixes are ``!``, ``?``, ``$``. 
  Which means that the bot will respond to all of these commands: ``!hi``, ``?hi``, ``$hi`` with the same response.
  Maybe in future the bot will support custom per channel command prefixes.

* The bot should moderate itself upon joining your channel. If it doesn't for some reason - please, moderate it yourself.
  As it was said in the :ref:`how_to_invite` section -
  :iconify:`logos:twitch` twitch is silly and they rate-limit small bots quite a lot, 
  which is annoying to deal with and it's possible it might break some bots' features.
  So again, please, moderate the bot.

  .. hint::

    You can mod the bot by typing ``/mod @IrenesBot`` in your twitch channel's chat.

🦤 Extra actions
################

If a feature requires you to do extra action (e.g. add the bot account to 7tv editors) then the corresponding page will instruct about it.

💡 Random Tips
##############

I'm not sure where to put this information but why not here.

Features related to channel point rewards
-----------------------------------------

* If, for some reason, the channel points redemption can't be satisfied - the bot will refund the points to the user.
* if the bot goes down for some reason - it will still process redemptions as soon as it goes online. 
  Hence if you see the bot not responding - you don't need to refund the points to users yourself just yet - 
  the bot will try to fix everything on its own.