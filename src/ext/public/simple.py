"""Meta.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
import random
from typing import TYPE_CHECKING, Annotated, TypedDict

import twitchio  # ruff: ignore[typing-only-third-party-import]
from twitchio.ext import commands

from core import Component
from shared import errors, globs, translate
from utils import const, guards
from utils.converters import TranslateArguments, TranslateConverter

if TYPE_CHECKING:
    from core import Bot, Context

    class RunDict(TypedDict):
        keywords: list[str]
        game: str
        desc: str


__all__ = ("Simple",)


class Simple(Component):
    """Meta commands."""

    @guards.is_online()
    @commands.command()
    async def clip(self, ctx: Context, *, title: str | None = None) -> None:
        """Create a clip."""
        # TODO: include `duration` argument
        # I guess we have to use some regex converter cause twitchio doesnt have duration = None, *, title: str support
        # TODO: try to experiment with edit_url
        clip = await ctx.broadcaster.create_clip(token_for=const.UserID.Bot, title=title)
        await ctx.send(f"clips.twitch.tv/{clip.id}")
        # await ctx.send(f"Editing Link: {clip.edit_url}")

    @clip.error
    async def clip_error(self, payload: commands.CommandErrorPayload) -> None:
        """Error handler for !clip command."""
        error = payload.exception
        if isinstance(error, ValueError):
            # clip duration is bad value
            await payload.context.send(str(error))
            return
        # Unresolved
        raise error

    @commands.command(name="coin-flip")
    async def coin_flip(self, ctx: Context) -> None:
        """🪙 Flip a coin: Heads or Tails?"""  # ruff: ignore[missing-trailing-period]
        word = random.choice(["⚪ Heads", "⚫ Tails"])
        await ctx.send(content=word)

    @commands.command(name="commands", aliases=["help", "irenesbot", "docs"])
    async def command_list(self, ctx: Context) -> None:
        """Get link to the bot's documentation (this web-page)."""
        await ctx.send("irenesbot.readthedocs.io")

    @commands.command(aliases=["hi", "yo", "hallo"])
    async def hello(self, ctx: Context) -> None:
        """Respond with "hello Hello" response.

        Simple command.
        """
        await ctx.send(f"{const.Stv.hello} Hello!")

    @commands.command()
    async def irene(self, ctx: Context) -> None:
        """Just a random command that is unlikely to be in other bots."""
        await ctx.send(globs.TwitchEmote.FeelsDankMan)

    @commands.command()
    async def ping(self, ctx: Context) -> None:
        """Ping the bot.

        Currently doesn't provide any useful info.
        """
        await ctx.send("\N{TABLE TENNIS PADDLE AND BALL} Pong!")

    @commands.command()
    async def source(self, ctx: Context) -> None:
        """Get link to the bot's GitHub repository."""
        await ctx.send("github.com/Aluerie/IreBot")

    @commands.command(aliases=["id", "twitchid"])
    async def twitch_id(self, ctx: Context, *, user: twitchio.User | None = None) -> None:
        """Get mentioned @user numeric twitch_id."""
        who = user or ctx.author
        await ctx.send(f"Twitch ID for {who.mention}: {who.id} {const.Stv.donkDetective}")

    TRANSLATE_ARGUMENT_DEFAULT = TranslateArguments("")

    @commands.cooldown(rate=1, per=dt.timedelta(seconds=5), key=commands.BucketType.channel)
    @commands.command()
    async def translate(
        self,
        ctx: Context,
        *,
        translate_arguments: Annotated[TranslateArguments, TranslateConverter] = TRANSLATE_ARGUMENT_DEFAULT,
    ) -> None:
        """Translate given text.

        Uses Google Translate.

        Nice tip: you can reply to a person's message with ``!translate`` and the bot will translate their message.
        E.g. some chatter comes and says "Hola te amo" - you can reply to it with ``!translate``
        and the bot will use the text of that message to translate it into "Hello I love you".

        Parameters
        ----------
        translate_arguments
            The formatting for this argument: ``<text_to_translate> --to <target_language> --from <source_language>``.
            Both flag arguments (``--to`` and ``--from``) are optional.

            * By default, ``--to <target_language>`` is assumed to be ``en`` (English).
            * If ``--from <source_language>`` is not provided then the bot autodetect the used language.

            The languages needs to be passed as a 2-letters code (some languages use 3 letters though),
            e.g. ``fr`` for French, ``de`` for German.
            You can see the list of supported languages with ``!languages`` command or in the table below.

            .. list-table::
               :widths: 1, 1, 1, 1, 1, 1, 1, 1
               :header-rows: 1

               * - Code
                 - Language
                 - Code
                 - Language
                 - Code
                 - Language
                 - Code
                 - Language
               * - af
                 - Afrikaans
                 - gl
                 - Galician
                 - lv
                 - Latvian
                 - si
                 - Sinhala
               * - sq
                 - Albanian
                 - ka
                 - Georgian
                 - lt
                 - Lithuanian
                 - sk
                 - Slovak
               * - am
                 - Amharic
                 - de
                 - German
                 - lb
                 - Luxembourgish
                 - sl
                 - Slovenian
               * - ar
                 - Arabic
                 - el
                 - Greek
                 - mk
                 - Macedonian
                 - so
                 - Somali
               * - hy
                 - Armenian
                 - gu
                 - Gujarati
                 - mg
                 - Malagasy
                 - es
                 - Spanish
               * - az
                 - Azerbaijani
                 - ht
                 - Haitian creole
                 - ms
                 - Malay
                 - su
                 - Sundanese
               * - eu
                 - Basque
                 - ha
                 - Hausa
                 - ml
                 - Malayalam
                 - sw
                 - Swahili
               * - be
                 - Belarusian
                 - haw
                 - Hawaiian
                 - mt
                 - Maltese
                 - sv
                 - Swedish
               * - bn
                 - Bengali
                 - iw
                 - Hebrew
                 - mi
                 - Maori
                 - tg
                 - Tajik
               * - bs
                 - Bosnian
                 - he
                 - Hebrew
                 - mr
                 - Marathi
                 - ta
                 - Tamil
               * - bg
                 - Bulgarian
                 - hi
                 - Hindi
                 - mn
                 - Mongolian
                 - tt
                 - Tatar
               * - ca
                 - Catalan
                 - hmn
                 - Hmong
                 - my
                 - Myanmar (burmese)
                 - te
                 - Telugu
               * - ceb
                 - Cebuano
                 - hu
                 - Hungarian
                 - ne
                 - Nepali
                 - th
                 - Thai
               * - ny
                 - Chichewa
                 - is
                 - Icelandic
                 - no
                 - Norwegian
                 - tr
                 - Turkish
               * - zh-cn
                 - Chinese (simplified)
                 - ig
                 - Igbo
                 - or
                 - Odia
                 - tk
                 - Turkmen
               * - zh-tw
                 - Chinese (traditional)
                 - id
                 - Indonesian
                 - ps
                 - Pashto
                 - uk
                 - Ukrainian
               * - co
                 - Corsican
                 - ga
                 - Irish
                 - fa
                 - Persian
                 - ur
                 - Urdu
               * - hr
                 - Croatian
                 - it
                 - Italian
                 - pl
                 - Polish
                 - ug
                 - Uyghur
               * - cs
                 - Czech
                 - ja
                 - Japanese
                 - pt
                 - Portuguese
                 - uz
                 - Uzbek
               * - da
                 - Danish
                 - jw
                 - Javanese
                 - pa
                 - Punjabi
                 - vi
                 - Vietnamese
               * - nl
                 - Dutch
                 - kn
                 - Kannada
                 - ro
                 - Romanian
                 - cy
                 - Welsh
               * - en
                 - English
                 - kk
                 - Kazakh
                 - ru
                 - Russian
                 - xh
                 - Xhosa
               * - eo
                 - Esperanto
                 - km
                 - Khmer
                 - sm
                 - Samoan
                 - yi
                 - Yiddish
               * - et
                 - Estonian
                 - ko
                 - Korean
                 - gd
                 - Scots gaelic
                 - yo
                 - Yoruba
               * - tl
                 - Filipino
                 - ku
                 - Kurdish (kurmanji)
                 - sr
                 - Serbian
                 - zu
                 - Zulu
               * - fi
                 - Finnish
                 - ky
                 - Kyrgyz
                 - st
                 - Sesotho
                 -
                 -
               * - fr
                 - French
                 - lo
                 - Lao
                 - sn
                 - Shona
                 -
                 -
               * - fy
                 - Frisian
                 - la
                 - Latin
                 - sd
                 - Sindhi
                 -
                 -

        Examples
        --------
        * ``!translate Je t'aime``
        * ``!translate Ich liebe dich --to fr``
        * ``!translate  i love you --to fr --from en``
        * ``!translate`` (but as a reply to somebody's message "Hola te amo")
        """
        text = ctx.message.reply.parent_message_body if ctx.message.reply else translate_arguments.text
        if not text:
            msg = "You need to provide text to translate"
            raise errors.RespondWithError(msg)

        result = await translate.translate(
            text,
            source_language=translate_arguments.from_,
            target_language=translate_arguments.to,
            session=self.bot.session,
        )
        answer = f"{const.Stv.ApuBritish} [{result.source_language} to {result.target_language}] {result.translated}"
        await ctx.send(answer)

    @commands.command()
    async def languages(self, ctx: Context) -> None:
        """Get list of supported languages for the ``!translate`` command.

        The language codes from this command are supposed to be used in ``to:``, ``from:`` argument flags of the said
        command.
        """
        answer = f"{const.Stv.ApuBritish} Supported languages: {' '.join(translate.LANGUAGES)}"
        await ctx.send(answer)


async def setup(bot: Bot) -> None:
    """Load the module (twitchio entry point)."""
    await bot.add_component(Simple(bot))
