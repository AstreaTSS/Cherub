import importlib

import interactions as ipy
import tansy

import common.utils as utils


class Pinboard(utils.Extension):
    pinboard = tansy.SlashCommand(
        name="pinboard",
        description="Pinboard-related commands.",
        dm_permission=False,
        default_member_permissions=ipy.Permissions.MANAGE_MESSAGES,
    )

    @pinboard.subcommand(sub_cmd_name="list", sub_cmd_description="List all pinboards.")
    async def pinboard_list(self, ctx: utils.CherubSlashContext):
        config = await utils.fetch_config(ctx.guild_id)

        if not config.pinboards:
            raise utils.CustomCheckFailure("There are no pinboards on this server.")

        entries = [
            f"{f'<#{k}>' if k != '0' else 'Global'} -> <#{v}>"
            for k, v in config.pinboards.items()
        ]
        await ctx.send(embed=utils.make_embed("\n".join(entries), title="Pinboards"))

    @pinboard.subcommand(sub_cmd_name="add", sub_cmd_description="Adds a pinboard.")
    async def pinboard_add(
        self,
        ctx: utils.CherubSlashContext,
        entry: ipy.GuildText = tansy.Option("The channel to watch for pins."),
        destination: ipy.GuildText = tansy.Option("The channel to send pins to."),
    ):
        config = await utils.fetch_config(ctx.guild_id)
        config.pinboards[str(entry.id)] = str(destination.id)
        await config.save()

        await ctx.send("Pinboard added.")

    @pinboard.subcommand(
        sub_cmd_name="remove", sub_cmd_description="Removes a pinboard."
    )
    async def pinboard_remove(
        self,
        ctx: utils.CherubSlashContext,
        entry: ipy.GuildText = tansy.Option("The entry channel to remove."),
    ):
        config = await utils.fetch_config(ctx.guild_id)

        if not config.pinboards.get(str(entry.id)):
            raise utils.CustomCheckFailure("That channel is not a pinboard.")

        config.pinboards.pop(str(entry.id))
        await config.save()

        await ctx.send("Pinboard removed.")

    @ipy.listen(ipy.events.MessageCreate)
    async def pinboard_listen(self, event: ipy.events.MessageCreate):
        if (
            event.message.type != ipy.MessageType.CHANNEL_PINNED_MESSAGE
            or event.message._guild_id is None
        ):
            return

        config = await utils.fetch_config(event.message._guild_id)
        destination_id = config.pinboards.get(
            str(event.message._channel_id), config.pinboards.get("0")
        )
        if not destination_id:
            return

        pins: list[ipy.Message] = await event.message.channel.fetch_pinned_messages()
        last_pin = pins[0]

        embed = ipy.Embed(
            description=last_pin.content or last_pin.system_content,
            color=ipy.RoleColors.LIGHTER_GRAY,
            timestamp=last_pin.timestamp,
        )
        embed.set_author(
            f"{last_pin.author.display_name} ({last_pin.author.tag})",
            icon_url=last_pin.author.display_avatar.url,
        )

        if last_pin.attachments:
            embed.set_image(last_pin.attachments[0].url)
            embed.add_field(
                "Attachments",
                "\n".join([f"[{x.filename}]({x.url})" for x in last_pin.attachments]),
            )

        if not embed.description:
            embed.description = "*See original message for content.*"

        destination = await self.bot.fetch_channel(int(destination_id))
        if not destination:
            return

        await destination.send(
            embed=embed,
            components=ipy.Button(
                style=ipy.ButtonStyle.LINK,
                label="Original Message",
                url=last_pin.jump_url,
            ),
        )
        await last_pin.unpin()


def setup(bot: utils.CherubBase):
    importlib.reload(utils)
    Pinboard(bot)
