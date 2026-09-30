.. _how_to_invite:

:iconify:`logos:twitch` How to invite the bot
=============================================

.. .. attention::

..     I've currently disabled the web-app with the bot's invite link.
..     If you want to add the bot - write to me, I guess.

💌 Invite Link
##############

Use this link:

.. highlights::
    
    https://parrot-thankful-trivially.ngrok-free.app/oauth?scopes=channel:bot+channel:read:redemptions+channel:manage:redemptions+channel:manage:moderators&force_verify=true

Yes, I'm sorry. I know the link looks ugly and the host ``parrot-thankful-trivially.ngrok-free.app`` looks suspicious as hell, 
but I don't really care to pay money to get a proper domain name.
Unfortunately, :iconify:`logos:twitch` twitch is dumb and they don't provide any convenient for everybody way to do this. 

From the developer side, it's quite a headache to set up the authorization process. 
But without much explanations - 
even pleb developers like me need to have a running web-app with a public facing URL that :iconify:`logos:twitch` twitch will use to callback after authorization.
A normal looking domain costs some money, but as I said -  I'm a bit stingy.
However, I assure you, it's safe to click. Me and a few people have already authorized the bot this way.

So, the link will redirect you to a normal `twitch.tv <https://www.twitch.tv>`_ authorization page like a screenshot below. 
Here, you read what permissions my bot is asking and press "Authorize" if you are okay with giving my bot those permissions.

.. image:: /_static/images/authorize.png
    :align: center
    :width: 400

.. caution::

    The link asks for "Grant or remove the moderator role from users in your channel" permission only in order to moderate itself.
    It won't remove/add anybody else.
    Sadly, the bot itself needs the moderator role because :iconify:`logos:twitch` twitch is stupid (common theme, huh) and they rate-limit 
    small bot accounts with 

    * ``Your message was not sent because you are sending messages too quickly`` 
    * ``Your message was not sent because it is identical to the previous one you sent, less than 30 seconds ago``

    even when the bot is not trying to be a bad actor.


💔 Troubleshooting
##################

In most cases - just contact me (:iconify:`logos:twitch` `@Irene_Adler__ <https://www.twitch.tv/Irene_Adler__>`_) and we will solve the problem.

* If the page doesn't load at all - I probably turned off the web-app for some reason. Contact me.
* If the page loads but it is showing some error (e.g. recently I stumbled upon ``ERR_NGROK_8012``) then also contact me.
* If your browser shows something like "Secure Connection Failed", "PR_END_OF_FILE_ERROR" then you can try visiting the website with some VPN. 
  Probably, your provider blocks my suspiciously looking web-app.

🚩 Postscript
#############

Thanks for adding the bot.

.. warning::

    If I add more public features or if you ask me to add some feature - I might add more permissions to the link. 
    In that case you will have to reauthorize the bot order to have access to the new features.

.. _invite_link: https://parrot-thankful-trivially.ngrok-free.app/oauth?scopes=channel:bot+channel:read:redemptions+channel:manage:redemptions&force_verify=true