:iconify:`thesvg-color:dota-2` Dota 2 features
==============================================

📚 Commands table
#################

The command list is pretty much a homage to :iconify:`logos:twitch` `@9kmmrbot <https://twitch.tv/9kmmrbot>`_. 
The commands below work exactly in the same fashion as :iconify:`logos:twitch` `@9kmmrbot <https://twitch.tv/9kmmrbot>`_ worked long ago.

.. list-table::
    :widths: 4, 4, 20, 20
    :header-rows: 1

    * - Command Name
      - Chat Aliases
      - Description
      - Showcase (`7tv emote set <https://7tv.app/emote-sets/01JS1XW1PAAKP34984FDYZVDR7>`_ on)
    * - Game Medals
      - !gm
      - Show rank medal for each players in the match.
      - .. image:: /_static/images/dota2/gm.png
    * - Lifetime Games
      - !smurfs !lifetime
      - Show total games played for each player in the match.
      - .. image:: /_static/images/dota2/lifetime.png
    * - Live Match Player Stats
      - !stats !items !kda
      - Fetch live stats and items for a player in the current match (2 minutes delay).
        
        Note, you need to provide an argument for the command such as hero name, hero alias, player slot or player color.
        I.e. "!stats pa", "!stats blue", "!stats mireska", "!stats Templar Assassin".
      - .. image:: /_static/images/dota2/stats.png
    * - Lead
      - !lead
      - Show which team has a gold lead and by how much.
      - .. image:: /_static/images/dota2/lead.png
    * - Player Stats Profiles
      - !profile !player
      - Show link to stats profile for a player.
        Similarly to above, you need to provide an argument for the command such as hero name, alias; player slot or color.
      - .. image:: /_static/images/dota2/player.png 
    * - Notable players
      - !notable !np
      - Show notable players in the match.
        This includes streamers, twitch chatters and pro-players.
        Honestly, everybody is welcome to be added as a notable player.
      - .. image:: /_static/images/dota2/notable.png
    * - Ranked
      - !ranked
      - Show whether the current match is ranked or not.
      - .. image:: /_static/images/dota2/ranked.png
    * - Match ID
      - !match_id !matchid
      - Show match id for the current game.
      - .. image:: /_static/images/dota2/matchid.png
    * - Played with in Last Game
      - !lg !lm !played
      - Show recurring players from the last game present in the current game.
      - .. image:: /_static/images/dota2/last-game.png
    * - Previous Match Results
      - !pm
      - Show a short summary for the previous match results.
      - .. image:: /_static/images/dota2/pm.png
    * - Win Loss Ratio
      - !wl !score !winloss
      - Show streamer's win-loss score ratio during the live-stream.
      - .. image:: /_static/images/dota2/score.png
    * - Offline Win Loss Ratio
      - !wl offline
      - Show win-loss ratio for the last streamer's gaming session but also include offline games.
      - .. image:: /_static/images/dota2/score.png
    * - MMR
      - !mmr
      - Show streamer's mmr tracked in the bot database (according to their match history).
        It is not accurate.
      - .. image:: /_static/images/dota2/mmr.png
    * - Set MMR
      - !mmr set
      - (Streamer's only command) Allows for streamers to manually update their MMR in the bot's database.
      - .. image:: /_static/images/dota2/mmr-set.png
    * - Stats Profile
      - !dotabuff !stratz !opendota
      - Show link to the streamer's stats profile page.
      - .. image:: /_static/images/dota2/dotabuff.png
    * - Last Seen
      - !lastseen !status
      - Show which account the bot has spotted you playing Dota 2 last on.
        The bot considers that account as "active" for the purposes of the commands above.
      - .. image:: /_static/images/dota2/lastseen.png
    * - D2PT Hero Builds
      - !d2pt
      - Show Dota 2 ProTracker page for the currently selected hero.
      - .. image:: /_static/images/dota2/d2pt.png
    * - Party Members
      - !d2pt
      - Show known members from the current party.
      - .. image:: /_static/images/dota2/party.png

🖖 Tip for merging 7tv emote sets
#################################

To make bot responses look like in the "Showcase" column you can add those emotes quickly to your channel by merging your main 7tv emote set with 
the `Dota 2 hero icons emote set <https://7tv.app/emote-sets/01JS1XW1PAAKP34984FDYZVDR7>`_ using a tool/bot like `potat.app/help/mergeset <https://potat.app/help/mergeset>`_. 
Some short instructions for :iconify:`logos:twitch` `@PotatBotat <https://www.twitch.tv/PotatBotat>`_ specifically:

* Add :iconify:`logos:twitch` `@PotatBotat <https://www.twitch.tv/PotatBotat>`_ to your channel;
* Give it 7tv editor role, allow it to ``Create Emote Sets`` in addition to default permissions;
* Use ``#mergeset <Primary set ID> 01JS1XW1PAAKP34984FDYZVDR7`` where the second argument is the ID for the Dota 2 emote set from the showcase column;
* You can find your ``<Primary set ID>`` (the first argument) by copying the last part of the URL to your own main emote set;
* :iconify:`logos:twitch` `@PotatBotat <https://www.twitch.tv/PotatBotat>`_ will create a new emote set trying to merge the provided ones; if there is more then 1000 emotes in total - some emotes from the 2nd set won't make it;
* Now you can switch between your main set and a merged version;

⚠️ Functionality restrictions
#############################################

.. caution::
    
    Unfortunately, due to implementation specifics and Valve being stupid - currently for the Dota 2 features to work:

1. You need to add the :iconify:`bi:steam` `bot's steam account <https://steamcommunity.com/id/irenesbot>`_ to friends (tell me so I can accept the friend request).
2. You also need to be green-online 🟢 in :iconify:`thesvg-color:dota-2` Dota 2 (and have rich presence visible to friends in your privacy settings) for the bot to be able to see your status live.

.. note::
    
    PS. Another implementation for these features (using :iconify:`thesvg-color:dota-2` Dota 2 Game State Integration) is coming soon™️. 
    It won't have mentioned restrictions but you will have to put a ``.cfg`` file into the :iconify:`thesvg-color:dota-2` Dota 2 directory.
