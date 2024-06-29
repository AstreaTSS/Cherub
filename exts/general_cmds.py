import asyncio
import importlib
import subprocess
import time

import interactions as ipy

import common.utils as utils


class GeneralCMDS(utils.Extension):
    def __init__(self, bot: utils.CherubBase):
        self.name = "General"
        self.bot: utils.CherubBase = bot
        self.invite_link = ""

        asyncio.create_task(self.when_ready())

    async def when_ready(self) -> None:
        await self.bot.wait_until_ready()
        self.invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.owner.id}&permissions=9312563227712&scope=bot%20applications.commands"

    def _get_commit_hash(self):
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )

    async def get_commit_hash(self):
        return await asyncio.to_thread(self._get_commit_hash)

    @ipy.slash_command(
        "ping",
        description=(
            "Pings the bot. Great way of finding out if the bot's working correctly,"
            " but has no real use."
        ),
    )
    @ipy.integration_types(guild=True, user=True)
    async def ping(self, ctx: utils.CherubSlashContext) -> None:
        """
        Pings the bot. Great way of finding out if the bot's working correctly, but has no real use.
        """

        start_time = time.perf_counter()
        average_ping = round((self.bot.latency * 1000), 2)

        embed = ipy.Embed(
            "Pong!", color=self.bot.color, timestamp=ipy.Timestamp.utcnow()
        )
        embed.set_footer("As of")
        embed.description = f"Average Ping: `{average_ping}` ms\nCalculating RTT..."

        mes = await ctx.send(embed=embed)

        end_time = time.perf_counter()
        # not really rtt ping but shh
        rtt_ping = round(((end_time - start_time) * 1000), 2)
        embed.description = (
            f"Average Ping: `{average_ping}` ms\nRTT Ping: `{rtt_ping}` ms"
        )

        await ctx.edit(mes, embed=embed)

    @ipy.slash_command(
        name="invite",
        description="Sends the link to invite the bot to your server.",
    )
    @ipy.integration_types(guild=True, user=True)
    async def invite(self, ctx: utils.CherubSlashContext) -> None:
        embed = utils.make_embed(
            "If you want to invite me to your server, use the Invite Link below!",
            title="Invite Bot",
        )
        button = ipy.Button(
            style=ipy.ButtonStyle.URL,
            label="Invite Link",
            url=self.invite_link,
        )

        await ctx.send(embeds=embed, components=button)

    @ipy.slash_command(
        "support", description="Gives an invite link to the support server."
    )
    @ipy.integration_types(guild=True, user=True)
    async def support(self, ctx: ipy.InteractionContext) -> None:
        embed = utils.make_embed(
            "If you need help with the bot, or just want to hang out, join the"
            " support server!",
            title="Support Server",
        )
        button = ipy.Button(
            style=ipy.ButtonStyle.URL,
            label="Join Support Server",
            url="https://discord.gg/NSdetwGjpK",
        )
        await ctx.send(embeds=embed, components=button)

    @ipy.slash_command("about", description="Gives information about the bot.")
    @ipy.integration_types(guild=True, user=True)
    async def about(self, ctx: utils.CherubSlashContext):
        msg_list = [
            (
                "I'm **Cherub**, an experimental utility bot. I'm the successor to"
                " Seraphim, an old bot of my owner, and am meant to implement the best"
                " features from that bot."
            ),
            (
                "Right now, I only have emoji-related commands - I can get the emoji"
                " URL of any Discord emoji, and I have a variety of commands to add"
                " emojis in an easy way."
            ),
        ]

        about_embed = ipy.Embed(
            title="About",
            color=self.bot.color,
            description="\n".join(msg_list),
        )
        about_embed.set_thumbnail(
            ctx.guild.me.display_avatar.url
            if ctx.guild
            else self.bot.user.display_avatar.url
        )

        commit_hash = await self.get_commit_hash()
        command_num = len(self.bot.application_commands) + len(
            self.bot.prefixed.commands
        )

        about_embed.add_field(
            name="Stats",
            value="\n".join(
                (
                    f"Servers: {len(self.bot.guilds)}",
                    f"Commands: {command_num} ",
                    (
                        "Startup Time:"
                        f" {ipy.Timestamp.fromdatetime(self.bot.start_time).format(ipy.TimestampStyles.RelativeTime)}"
                    ),
                    (
                        "Commit Hash:"
                        f" [{commit_hash}](https://github.com/AstreaTSS/Cherub/commit/{commit_hash})"
                    ),
                    (
                        "Interactions.py Version:"
                        f" [{ipy.__version__}](https://github.com/interactions-py/interactions.py/tree/{ipy.__version__})"
                    ),
                    "Made By: [AstreaTSS](https://github.com/AstreaTSS)",
                )
            ),
            inline=True,
        )

        links = [
            f"Invite Bot: [Link]({self.invite_link})",
            "Support Server: [Link](https://discord.gg/NSdetwGjpK)",
            "Source Code: [Link](https://github.com/AstreaTSS/Cherub)",
        ]

        about_embed.add_field(
            name="Links:",
            value="\n".join(links),
            inline=True,
        )
        about_embed.timestamp = ipy.Timestamp.utcnow()

        await ctx.send(embed=about_embed)


def setup(bot):
    importlib.reload(utils)
    GeneralCMDS(bot)
