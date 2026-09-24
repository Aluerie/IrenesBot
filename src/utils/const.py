# ruff: noqa: N815
from __future__ import annotations

from enum import StrEnum

__all__ = (
    "BTTV",
    "FFZ",
    "STV",
    "BotsLowerName",
    "Global",
    "Logo",
    "LowerName",
    "SevenTV",
    "UserID",
)


class UserID(StrEnum):
    """Known/special user IDs."""

    Irene = "180499648"  # @Irene_Adler__
    Bot = "1277023540"  # @IrenesBot
    Test = "1543411482"  # @IrenesTest

    # Not me
    Xas = "101998257"  # @Xasthurize


class LowerName(StrEnum):
    """Known/special user names."""

    Irene = "irene_adler__"


class Global(StrEnum):
    """Global emotes that are usable everywhere."""

    # Twitch Native ones
    D4Head = "4Head"  # idk let's think better name?
    CaitThinking = "CaitThinking"

    # BTTV
    monkaS = "monkaS"

    # FFZ
    # None - no good ones?..

    # STV
    EZ = "EZ"
    FeelsDankMan = "FeelsDankMan"


class BTTV(StrEnum):
    """Some of BTTV emotes enabled on the channel."""

    DankG = "DankG"
    Offline = "Offline"
    peepoHey = "peepoHey"
    PogU = "PogU"
    Smoge = "Smoge"
    weirdChamp = "weirdChamp"


class FFZ(StrEnum):
    """Some of FFZ emotes enabled on the channel."""

    Weirdge = "Weirdge"
    monkaGIGA = "monkaGIGA"
    monkaGIGAGUN = "monkaGIGAGUN"
    monkaH = "monkaH"
    peepoPolice = "peepoPolice"
    peepoWTF = "peepoWTF"
    PepoG = "PepoG"
    sadKEK = "sadKEK"
    WTFF = "WTFF"


class SevenTV(StrEnum):
    """Some often used 7TV snowflakes."""

    IRENE_EMOTE_SET_ID = "01FAQVCS500002EV4FV330P46A"  # also irene seven tv id
    IRENESBOT_USER_ID = "01KFF67D46PJPD1S6DPFFT06E3"


class STV(StrEnum):
    """Some of 7TV emotes enabled on the channel."""

    actually = "actually"
    Adge = "Adge"
    ALERT = "ALERT"
    ApuBritish = "ApuBritish"
    AYAYA = "AYAYA"
    Boink = "Boink"
    buenoSuccess = "buenoSuccess"
    buenoFail = "buenoFail"
    Cinema = "Cinema"
    catFU = "catFU"
    classic = "classic"
    DankApprove = "DankApprove"
    dankFix = "dankFix"
    dankHey = "dankHey"
    DankL = "DankL"
    DankMods = "DankMods"
    DankDolmes = "DankDolmes"
    DANKHACKERMANS = "DANKHACKERMANS"
    dankJAM = "dankJAM"
    DankLurk = "DankLurk"
    DankReading = "DankReading"
    DankThink = "DankThink"
    Deadge = "Deadge"
    discord = "discord"
    DonkCrayon = "DonkCrayon"
    donkDetective = "donkDetective"
    donkHappy = "donkHappy"
    donkHey = "donkHey"
    donkJam = "donkJam"
    donkSad = "donkSad"
    Donki = "Donki"
    DonkPrime = "DonkPrime"
    ermtosis = "ermtosis"
    Erm = "Erm"
    EZdodge = "EZdodge"
    FeelsBingMan = "FeelsBingMan"
    FirstTimeChadder = "FirstTimeChadder"
    FirstTimeDentge = "FirstTimeDentge"
    forsenCD = "forsenCD"
    fridayNight = "fridayNight"
    gg = "gg"
    GroupScoots = "GroupScoots"
    hello = "hello"
    Hey = "Hey"
    heyinoticedyouhaveaprimegamingbadgenexttoyourname = "heyinoticedyouhaveaprimegamingbadgenexttoyourname"
    hi = "hi"
    How2Read = "How2Read"
    LastTimeChatter = "LastTimeChatter"
    OVERWORKING = "OVERWORKING"
    peepoAds = "peepoAds"
    peepoDapper = "peepoDapper"
    please = "please"
    plink = "plink"
    PogChampPepe = "PogChampPepe"
    POGCRAZY = "POGCRAZY"
    POLICE = "POLICE"
    science = "science"
    Speedge = "Speedge"
    Spotify = "Spotify"
    Timeloth = "Timeloth"
    yo = "yo"
    uuh = "uuh"
    uuhAcktshucally = "uuhAcktshucally"
    wickedchad = "wickedchad"
    widepeepoHappyRightHeart = "widepeepoHappyRightHeart"
    wow = "wow"
    UltraMad = "UltraMad"
    YouTube = "YouTube"


class BotsLowerName(StrEnum):
    """List of known bot names.

    Used to identify other bots' messages.
    Variable name is supposed to be their display name while
    the value is lowercase name for easier comparing.
    """

    # Invited to Irene's channel;
    IrenesBot = "irenesbot"
    PotatBotat = "potatbotat"
    Supibot = "supibot"
    WizeBot = "wizebot"

    # Not invited to Irene's channel currently;
    # d9kmmrbot = "9kmmrbot"
    # dotabod = "dotabod"
    # Fossabot = "fossabot"
    # LolRankBot = "lolrankbot"
    # Moobot = "moobot"
    # Nightbot = "nightbot"
    # Sery_Bot = "sery_bot"
    # StreamLabs = "streamlabs"
    # Streamelements = "streamelements"
    # poggSpin = "poggspin"  # https://bot.itsbr0dyy.dev/


class Logo(StrEnum):
    """Images for brands and logos."""

    Twitch = (
        "https://cdn3.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
    )
