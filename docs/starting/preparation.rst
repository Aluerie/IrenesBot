🤩 Preparations
===============

❓ Should the streamer mod the bot
##################################

TL;DR answer: yes, it will help the bot.

Longer answer: the bot doesn't need to be a moderator for its features to work. 
However, :iconify:`logos:twitch` twitch.tv is stupid - the bots get same rate-limits on messages, redeems and other requests 
as normal people's accounts. 

But example: what if the bot *needs* to send a few messages in a row as a part of their features? 
or what if the bot chats in gazillion chats? 
It will get quickly rate-limited and blocked by :iconify:`logos:twitch` twitch.tv (especially non-partnered bots), 
which is really stupid.

This is why all the bots (even the big ones) ask or demand the streamers to mod their mod. 
I could change the invite link to include a special permission that would allow the bot to moderate itself in your channel,
but I think it's unfair and invasive. So for a time being I just ask the streamers to mod the bot on their own volition.

.. hint::

    You can mod the bot by typing ``/mod @IrenesBot`` in your twitch channel's chat.

🤯 Initial settings
###################

* The bot's command prefixes are ``!``, ``?``, ``$``. 
  Which means that the bot will respond to all of these commands: ``!hi``, ``?hi``, ``$hi`` with the same response.
  Maybe in future the bot will support channel custom prefixes.

🦤 Extra actions
################

If a feature requires you to do extra action (e.g. add the bot account to 7tv editors) then the corresponding page will instruct about it.