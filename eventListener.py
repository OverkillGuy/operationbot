import importlib

from discord import Game, Member, Reaction, Message
from discord.ext.commands import Bot, Cog

import config as cfg
from secret import ADMIN
from eventDatabase import EventDatabase


class EventListener(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print("Waiting until ready")
        await self.bot.wait_until_ready()
        commandchannel = self.bot.get_channel(cfg.COMMAND_CHANNEL)
        print("Ready, importing")
        await commandchannel.send("Importing events")
        await EventDatabase.fromJson(self.bot)
        print("Imported")
        await commandchannel.send("Events imported")
        await self.bot.change_presence(activity=Game(name=cfg.GAME,
                                                     type=2))
        print('Logged in as', self.bot.user.name, self.bot.user.id)

    # Create event command
    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: Member):
        # Exit if reaction is from bot or not in event channel
        if user == self.bot.user \
                or reaction.message.channel.id != cfg.EVENT_CHANNEL:
            return

        log_channel = self.bot.get_channel(cfg.LOG_CHANNEL)

        # Remove the reaction
        await reaction.message.remove_reaction(reaction, user)

        # Get event from database with message ID
        reactedEvent = EventDatabase.getEventByMessage(
                reaction.message.id)
        if reactedEvent is None:
            print("No event found with that id", reaction.message.id)
            await log_channel.send("NOTE: reaction to a non-existent event. "
                                   "msg: {} role: {} user: {}#{}"
                                   .format(reaction.message.id, reaction.emoji,
                                           user.name, user.discriminator))
            return

        # Get emoji string
        emoji = reaction.emoji

        # Find signup of user
        signup = reactedEvent.findSignup(user.id)

        # if user is not signed up, and the role is free, signup
        # if user is not signed up, and the role is not free, do nothing
        # if user is signed up, and he selects the same role, signoff
        # if user is signed up, and he selects a different role, do nothing
        if signup is None:
            # Get role with the emoji
            role = reactedEvent.findRoleWithEmoji(emoji)
            # No role found, or somebody with Nitro added the ZEUS reaction
            # by hand
            if role is None or role.name == "ZEUS":
                print("No role found with that emoji")
                return

            # Sign up if role is free
            if role.userID is None:
                # signup
                reactedEvent.signup(role, user)

                # Update event
                await EventDatabase.updateEvent(reaction.message,
                                                reactedEvent)
                EventDatabase.toJson()
            await log_channel.send("Signup: event: {} role: {} user: {}#{}"
                                   .format(reactedEvent, reaction.emoji,
                                           user.name, user.discriminator))
        elif signup.emoji == emoji:
            # undo signup
            reactedEvent.undoSignup(user)

            # Update event
            await EventDatabase.updateEvent(reaction.message,
                                            reactedEvent)
            EventDatabase.toJson()
            await log_channel.send("Signoff: event: {} role: {} user: {}#{}"
                                   .format(reactedEvent, reaction.emoji,
                                           user.name, user.discriminator))

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            owner = self.bot.get_user(ADMIN)
            await owner.send("DM: [{}]: {}".format(
                message.author, message.content))


def setup(bot: Bot):
    importlib.reload(cfg)
    bot.add_cog(EventListener(bot))
