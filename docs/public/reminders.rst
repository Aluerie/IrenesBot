⏰ Reminders
============

Ask the bot to ping you in chat later: start with the time, then say what to remind you of.
The reminder arrives as a reply to your message, even if the bot restarted in between.

* ``!remind 10m stretch``
* ``!remind in 2 hours drink water``
* ``!remind tomorrow 3pm water the plants``
* ``!remind eow to send the report`` (``eod``, ``eow``, ``eom``, ``eoy`` are the ends of the day, the working week, the month and the year)

🔁 Repeating reminders
######################

Start with "every" (or ``daily``, ``weekly``, ``monthly``) to be reminded again and again,
until you stop it with ``!remind delete <id>``:

* ``!remind every day 9am stretch``
* ``!remind every friday 18:00 water the plants``
* ``!remind every mon and thu 20:00 gym``
* ``!remind every 2 weeks on friday 18:00 pay the bills``
* ``!remind every month on the 15th 10:00 rent``
* ``!remind every 3 hours drink water`` (hours count from now)

🔴 When the stream starts
#########################

``!remind live watch the start`` pings you as soon as this channel goes live
(if it does within 30 days).

🌍 Timezones
############

Durations like ``10m`` or ``1h30m`` work the same for everybody.
Clock times like ``3pm`` or ``friday 18:00`` are in UTC, since Twitch doesn't tell the bot your timezone.
Two ways to use your own clocks instead:

* Save your timezone once: ``!remind tz MSK`` (or ``EST``, ``CET``, ``UTC+3``, ``Europe/Berlin``...).
  ``!remind tz`` shows it, ``!remind tz clear`` forgets it.
* Or name it after the time: ``!remind 18:00 MSK stretch``, ``!remind 3pm EST lunch``,
  ``!remind friday 10:00 Europe/Berlin call``, ``!remind 9am UTC+3 standup``.

☝️ Commands
###########

.. autochatcommand:: ext.public.reminders.Reminders.remind_group

.. autochatcommand:: ext.public.reminders.Reminders.remind_live

.. autochatcommand:: ext.public.reminders.Reminders.remind_list

.. autochatcommand:: ext.public.reminders.Reminders.remind_delete

.. autochatcommand:: ext.public.reminders.Reminders.remind_clear

.. autochatcommand:: ext.public.reminders.Reminders.remind_timezone
