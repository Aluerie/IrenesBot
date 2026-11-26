⏰ Reminders
============

Ask the bot to ping you in chat later: start with the time, then say what to remind you of.
The reminder arrives as a reply to your message, even if the bot restarted in between.

* ``!remind 10m stretch``
* ``!remind in 2 hours drink water``
* ``!remind tomorrow 3pm water the plants``
* ``!remind eow to send the report`` (``eod``, ``eow``, ``eom``, ``eoy`` are the ends of the day, the working week, the month and the year)

Durations like ``10m`` or ``1h30m`` work the same for everybody.
Clock times like ``3pm`` or ``friday 18:00`` are in UTC, since Twitch doesn't tell the bot your timezone.
Name your timezone after the time to use your clocks instead: ``!remind 18:00 MSK stretch``, ``!remind 3pm EST lunch``,
``!remind friday 10:00 Europe/Berlin call``, ``!remind 9am UTC+3 standup``.

☝️ Commands
###########

.. autochatcommand:: ext.public.reminders.Reminders.remind_group

.. autochatcommand:: ext.public.reminders.Reminders.remind_list

.. autochatcommand:: ext.public.reminders.Reminders.remind_delete

.. autochatcommand:: ext.public.reminders.Reminders.remind_clear
