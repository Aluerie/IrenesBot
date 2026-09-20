from __future__ import annotations

import asyncio
import datetime
import logging
import random
from typing import TYPE_CHECKING, NamedTuple, TypedDict

import twitchio  # noqa: TC002
from twitchio.ext import commands

from config import env
from core import IreBot, IrePersonalComponent
from shared import common_const, errors, fmt
from utils import const, guards

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from core import IreBot, IreContext


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TranslatedSentence(TypedDict):
    """TranslatedSentence."""

    trans: str
    orig: str


class TranslateResult(NamedTuple):
    """TranslatedResult."""

    original: str
    translated: str
    source_lang: str
    target_lang: str


class TranslateError(errors.CustomError):
    """Raised when there is an error in translate functionality."""

    def __init__(self, status_code: int, text: str) -> None:
        self.status_code: int = status_code
        self.text: str = text
        super().__init__(f"Google Translate responded with HTTP Status Code {status_code}")


async def translate(
    text: str, *, source_lang: str = "auto", target_lang: str = "en", session: ClientSession
) -> TranslateResult:
    """Google Translate."""
    query = {
        "dj": "1",
        "dt": ["sp", "t", "ld", "bd"],
        "client": "dict-chrome-ex",  # Needs to be dict-chrome-ex or else you'll get a 403 error.
        "sl": source_lang,
        "tl": target_lang,
        "q": text,
    }

    headers = {
        "User-Agent": (  # cSpell: ignore KHTML
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        )
    }

    async with session.get("https://clients5.google.com/translate_a/single", params=query, headers=headers) as resp:
        if resp.status != 200:
            raise TranslateError(resp.status, text=await resp.text())

        data = await resp.json()
        src = data.get("src", "Unknown")
        sentences: list[TranslatedSentence] = data.get("sentences", [])
        if not sentences:
            msg = "Google translate returned no information"
            raise RuntimeError(msg)

        return TranslateResult(
            original="".join(sentence.get("orig", "") for sentence in sentences),
            translated="".join(sentence.get("trans", "") for sentence in sentences),
            source_lang=src.upper(),
            target_lang=target_lang.upper(),
        )


class StableCommands(IrePersonalComponent):
    """Stable commands.

    Stable in a sense that unlike commands in `temporary.py`
    these commands are unlikely to be deleted from my channel for a long time.

    Notes
    -----
    * Commands in this file are sorted alphabetically.
    """

    def __init__(self, bot: IreBot) -> None:
        super().__init__(bot)
        self.yt_music_on: asyncio.Event = asyncio.Event()

    @commands.group(name="ads", aliases=["ad", "commercial"])
    async def ads_group(self, ctx: IreContext) -> None:
        """A group command !ads."""

    @ads_group.command(name="start", aliases=["run"])
    async def ads_start(self, ctx: IreContext, length: int = 180) -> None:
        """Run ads."""
        await ctx.broadcaster.start_commercial(length=length)
        await ctx.send("Running ads in 3 2 1 (if possible)")

    @ads_group.command(name="snooze")
    async def ads_snooze(self, ctx: IreContext) -> None:
        """Snooze next ad."""
        await ctx.broadcaster.snooze_next_ad()
        await ctx.send(f"Snoozing next ad for 5 min {const.STV.DankApprove}")

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @guards.is_owner_channel()
    @commands.command()
    async def boink(self, ctx: IreContext) -> None:
        """Send an announcement for an obligatory boink."""
        await ctx.send_announcement(content=f"it's time to boink {const.STV.Boink}", color="purple")

    @commands.command()
    async def controller(self, ctx: IreContext) -> None:
        """Get Irene's current controller model."""
        await ctx.send("Razer Wolverine V3 Tournament Edition Xbox Black")

    @commands.command()
    async def discord(self, ctx: IreContext) -> None:
        """Link to my discord community server."""
        await ctx.send(f"{const.STV.discord} discord.gg/K8FuDeP")

    @commands.command()
    async def donate(self, ctx: IreContext) -> None:
        """Link to my Donation page."""
        await ctx.send("donationalerts.com/r/irene_adler__")  # cSpell: ignore donationalerts

    @commands.command()
    async def followage(self, ctx: IreContext) -> None:  # cSpell: ignore followage
        """Get your follow age."""
        # just a small joke to teach people
        await ctx.send("Just click your name 4Head")

    @commands.command(aliases=["lorem", "ipsum"])
    async def loremipsum(self, ctx: IreContext) -> None:
        """Lorem ipsum."""
        await ctx.send(  # cSpell:disable
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. "
            "Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. "
            "Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. "
            "Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, "
            "per inceptos himenaeos. Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. "
            "Pellentesque nibh."
        )  # cSpell:enable

    @commands.command()
    async def love(self, ctx: IreContext, *, arg: str) -> None:
        """Measure love between chatter and `arg`.

        arg can be a user or anything else.
        """

        def choose_love_emote() -> tuple[int, str]:
            love = random.randint(0, 100)
            if love < 10:
                emote = const.STV.donkSad
            if love < 33:
                emote = const.FFZ.sadKEK
            elif love < 66:
                emote = const.STV.donkHappy
            elif love < 88:
                emote = const.STV.widepeepoHappyRightHeart
            else:
                emote = const.STV.DankL
            return love, emote

        # chr(917504) is a weird "unknown" invisible symbol 7tv appends to the message
        # and the rest is just to get a possible clear name in case chatter was mentioning one
        potential_name = arg.replace(chr(917504), "").strip().removeprefix("@").lower()
        if potential_name in const.BotsLowerName:
            await ctx.send("Silly organic, bots cannot know love BibleThump")
        elif potential_name == ctx.chatter.name:
            await ctx.send("pls")
        elif potential_name == const.LowerName.Irene:
            await ctx.send(f"The {ctx.chatter.mention}'s love for our beloved Irene transcends all")
        else:
            love, emote = choose_love_emote()
            await ctx.send(f"{love}% love between {ctx.chatter.mention} and {arg} {emote}")

    @commands.command()
    async def lurk(self, ctx: IreContext) -> None:
        """Make it clear to the chat that you are lurking."""
        await ctx.send(f"{ctx.chatter.mention} is now lurking {const.STV.DankLurk} Have fun {const.STV.donkHappy}")

    @commands.command(name="decide", aliases=["ball", "8ball", "answer", "question", "yesno"])
    async def magic_ball(self, ctx: IreContext, *, text: str | None = None) -> None:
        """Get a random answer from a Magic Ball.

        Better than ChatGPT.
        """
        if not text:
            await ctx.send(f"Wrong command usage! You need to ask the bot yes/no question with it {const.FFZ.peepoWTF}")
            return

        options = [
            "69% for sure",
            "Are you kidding?!",
            "Ask again",
            "Better not tell you now",
            "Definitely... not",
            "Don't bet on it",
            "don't count on it",
            "Doubtful",
            "For sure",
            "Forget about it",
            "Hah!",
            "Hells no.",
            "If the Twitch gods grant it",
            "Impossible!In due time",
            "Indubitably!",
            "It is certain",
            "It is so",
            "Leaning towards no",
            "Look deep in your heart and you will see the answer",
            "Most definitely",
            "Most likely",
            "My sources say yes",
            "Never",
            "No way!",
            "No.",
            "Of course!",
            "Outlook good",
            "Outlook not so good",
            "Perhaps",
            "Possibly",
            "Please.",
            "That's a tough one",
            "That's like totally a yes. Duh!",
            "The answer might not be not no",
            "The answer to that isn't pretty",
            "The heavens point to yes",
            "Who knows?",
            "Without a doubt",
            "Yesterday it would've been a yes, but today it's a yep",
            "You will have to wait",
        ]
        await ctx.send(random.choice(options))

    @commands.command()
    async def nomic(self, ctx: IreContext) -> None:
        """No mic."""
        await ctx.send("Please read info below the stream, specifically, FAQ")

    @commands.command()
    async def oversight(self, ctx: IreContext) -> None:
        """Give me the famous Oversight Dark Willow copypaste."""
        await ctx.send(
            "The biggest🙌💯oversight🔭🔍with Dark✊🏾Willow🌳is that she's unbelievably sexy🤤💦🍆. "
            "I can't go on a hour🕐of my day🌞without thinking💭💦about plowing👉👌🚜that tight😳wooden🌳ass💦🍑. "
            "I'd kill🔫😱a man👨 in cold❄️blood😈just to spend💷a minute⏱️with her crotch🍑😫grinding against "
            "my throbbing💦🍆💦manhood💦🍆💦as she whispers🙊😫terribly dirty💩💩things to me in her "
            "geographically🌍🌎ambiguous🌏🗺️accent 🇮🇪"
        )

    @commands.command(aliases=["pcparts", "specs"])  # cSpell: ignore pcparts
    async def pc(self, ctx: IreContext) -> None:
        """Get Irene's current PC setup."""
        await ctx.send("pcpartpicker.com/user/aluerie/saved/dY497P")  # cSpell: ignore pcpartpicker

    @commands.command()
    async def playlist(self, ctx: IreContext) -> None:
        """Get the link to my Spotify playlist."""
        await ctx.send("open.spotify.com/playlist/7fVAcuDPLVAUL8555vy8Kz?si=b26cecab2cf24608")  # cSpell: ignore DPLVAUL

    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    @guards.is_owner_channel()
    @commands.command(aliases=["rr", "russianroulette"])  # cSpell: ignore russianroulette
    async def roulette(self, ctx: IreContext) -> None:
        """Play russian roulette."""
        mention = ctx.chatter.mention

        for phrase in [
            f"/me places the revolver to {mention}'s head {const.FFZ.monkaGIGAGUN}",
            f"{common_const.DIGITS[3]} {const.Global.monkaS} ... ",
            f"{common_const.DIGITS[2]} {const.FFZ.monkaH} ... ",
            f"{common_const.DIGITS[1]} {const.FFZ.monkaGIGA} ... The trigger is pulled... ",
        ]:
            await ctx.send(phrase)
            await asyncio.sleep(0.87)

        if ctx.chatter.moderator:
            # Special case: we will not kill any moderators
            await ctx.send(f"Revolver malfunctions! {mention} is miraculously alive! {const.STV.PogChampPepe}")
        elif random.randint(0, 1):
            await ctx.send(f"Revolver clicks! {mention} has lived to survive roulette! {const.STV.POGCRAZY}")
        else:
            await ctx.send(f"Revolver fires! {mention} lies dead in chat {const.STV.Deadge}")

            await ctx.broadcaster.timeout_user(
                moderator=const.UserID.Bot, user=ctx.chatter.id, duration=30, reason="Lost in !russianroulette"
            )

    @guards.is_online()
    @commands.is_moderator()
    @guards.is_owner_channel()
    @commands.command(aliases=["so"])
    async def shoutout(self, ctx: IreContext, user: twitchio.User) -> None:
        """Do /shoutout to a user."""
        await ctx.broadcaster.send_shoutout(to_broadcaster=user.id, moderator=const.UserID.Bot)

    async def check_youtube_music(self) -> None:
        """Waits if StreamerBot responds to the message indicating that I'm probably listening to YT Music atm."""

        async def predicate(payload: twitchio.ChatMessage) -> bool:
            """Checks whether the message is likely to be a response from StreamerBot !song request functionality.

            * They are sent by @IrenesBot
            * All such messages should start with `dankJAM`.
            """
            return payload.chatter.id == const.UserID.Bot and payload.text.startswith(const.STV.YouTube)

        try:
            _: twitchio.ChatMessage = await self.bot.wait_for("message", predicate=predicate, timeout=5.0)
        except TimeoutError:
            return
        else:
            self.yt_music_on.set()

    async def check_spotify(self, ctx: IreContext) -> None:
        """Checks my spotify status, if there is none - it tries to wait for YT Music status."""
        url = f"https://spotify.aidenwallis.co.uk/u/{env.SPOTIFY_AIDENWALLIS}"
        async with self.bot.session.get(url) as resp:
            resp_text = await resp.text()

        if not resp.ok:
            await ctx.send(f"{const.STV.Spotify} Irene needs to login + authorize for the tool to work {const.STV.dankFix}")
            return

        if resp_text.startswith("Error:"):
            # not sure how else to handle "Error: Request failed with status code 429" and such
            # if this keeps happening - we can scrape the overlay page for the song title / artist lol;
            # but we need selenium bcs the text is generated by JavaScript which is extremely over
            # the top to include as dependency for this
            # f"https://nowplaying.aidenwallis.co.uk/{env.SPOTIFY_AIDENWALLIS}"
            await ctx.send(
                f"{const.STV.Spotify} {resp_text} {const.STV.DankThink} "
                "You can probably look the song title on the screen in one of the corners."
            )
            return

        # Sometimes it's `"No song playing"`, sometimes it's `"No song playing."` with a dot hence `in resp_text`.
        if "No song playing" in resp_text:
            # In this case we should probably check whether
            # StreamerBot with YouTube Music Song Request functionality is active

            try:
                async with asyncio.timeout(5.0):
                    await self.yt_music_on.wait()
            except TimeoutError:
                # No YT Music
                await ctx.send(f"{const.STV.Spotify} No song playing {const.STV.donkJam}")
                return
            else:
                # Yes YT Music
                return

        await ctx.send(f"{const.STV.Spotify} {resp_text} {const.STV.donkJam}")

    # @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    @guards.is_owner_channel()
    @commands.command()
    async def song(self, ctx: IreContext) -> None:
        """Get currently played song on Spotify."""
        self.yt_music_on.clear()
        await asyncio.gather(
            self.check_spotify(ctx),
            self.check_youtube_music(),
        )

    @commands.command()
    async def translate(self, ctx: IreContext, *, text: str) -> None:
        """Translate given text to English.

        Uses Google Translate. Autodetects source language.

        Sources
        -------
        * My own discord bot (but the code there is also taken from other places)
            https://github.com/Aluerie/AluBot/blob/main/ext/educational/language/translation.py
        """
        result = await translate(text, session=self.bot.session)
        answer = f"{const.STV.ApuBritish} [{result.source_lang} to {result.target_lang}] {result.translated}"
        await ctx.send(answer)

    @commands.command()
    async def uptime(self, ctx: IreContext) -> None:
        """Get stream uptime."""
        stream = next(iter(await self.bot.fetch_streams(user_ids=[ctx.broadcaster.id])), None)
        if stream is None:
            await ctx.send(f"Stream is offline {const.BTTV.Offline}")
        else:
            uptime = datetime.datetime.now(datetime.UTC) - stream.started_at
            await ctx.send(f"{fmt.timedelta_to_words(uptime)} {const.STV.peepoDapper}")

    @commands.command(aliases=["seppuku"])
    async def vanish(self, ctx: IreContext) -> None:
        """Allows for chatters to vanish from the chat by time-outing themselves."""
        if ctx.chatter.moderator:
            if "seppuku" in ctx.message.text:
                msg = f"Emperor Kappa does not allow you this honour, {ctx.chatter.mention} (bcs you're a moderator)"
            else:
                msg = "Moderators can't vanish"
            await ctx.send(msg)
        else:
            await ctx.broadcaster.timeout_user(
                moderator=const.UserID.Bot, user=ctx.chatter.id, duration=1, reason="Used !vanish"
            )

    @commands.command()
    async def vods(self, ctx: IreContext) -> None:
        """Get the link to youtube vods archive."""
        await ctx.send(f"youtube.com/@AluerieVODS/ {const.STV.Cinema}")


async def setup(bot: IreBot) -> None:
    """Load IreBot module. Framework of twitchio."""
    await bot.add_component(StableCommands(bot))
