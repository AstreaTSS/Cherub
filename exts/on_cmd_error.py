import datetime
import importlib

import humanize
import naff

import common.utils as utils


class OnCMDError(naff.Extension):
    def __init__(self, bot):
        self.bot: naff.Client = bot

    def error_embed_generate(self, error_msg):
        return naff.Embed(color=naff.MaterialColors.RED, description=error_msg)

    @naff.listen(disable_default_listeners=True)
    async def on_command_error(
        self,
        event: naff.events.CommandError,
    ):
        if not isinstance(event.ctx, (naff.PrefixedContext, naff.InteractionContext)):
            return await utils.error_handle(self.bot, event.error)

        if isinstance(event.error, naff.errors.CommandOnCooldown):
            delta_wait = datetime.timedelta(
                seconds=event.error.cooldown.get_cooldown_time()
            )
            await event.ctx.send(
                embeds=self.error_embed_generate(
                    "You're doing that command too fast! "
                    + "Try again in"
                    f" `{humanize.precisedelta(delta_wait, format='%0.0f')}`."
                )
            )
        elif isinstance(event.error, utils.CustomCheckFailure):
            await event.ctx.send(embeds=self.error_embed_generate(str(event.error)))
        elif isinstance(
            event.error,
            naff.errors.BadArgument,
        ):
            await event.ctx.send(embeds=self.error_embed_generate(str(event.error)))
        elif isinstance(event.error, naff.errors.CommandCheckFailure):
            if event.ctx.guild:
                await event.ctx.send(
                    embeds=self.error_embed_generate(
                        "You do not have the proper permissions to use that command."
                    )
                )
        else:
            await utils.error_handle(self.bot, event.error, event.ctx)


def setup(bot):
    importlib.reload(utils)
    OnCMDError(bot)
