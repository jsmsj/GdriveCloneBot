"""Imports"""
import discord
import os
from discord.ext import commands
from cogs._helpers import is_allowed,embed
from cogs._config import prefix

class General(commands.Cog):
    """General commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return

    @commands.command(description=f'Checks the ping of the bot.\n`{prefix}ping`')
    async def ping(self,ctx):
        await ctx.send(f'🏓 Pong! Latency: {round(self.bot.latency*1000)}ms')
    
    @is_allowed()
    @commands.command(description=f'Sends the log file\n`{prefix}log`')
    async def log(self,ctx):
        if os.path.exists('log.txt'):
            await ctx.send(embed=embed('📃 Log File','Here is the log file')[0],file=discord.File('log.txt'))
        else:
            await ctx.send(embed=embed('📃 Log File','No logfile found :(')[0])



def setup(bot):
    bot.add_cog(General(bot))
    print("General cog is loaded")