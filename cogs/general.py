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

    @commands.command(description=f"About Me and instructions on how to deploy the bot.\n`{prefix}info`")
    async def info(self,ctx):
        desc = "A discord bot to **clone public/private google drive links** to your personal teamdrive or google drive. Additionally it offers commands to **generate service accounts**, and with proper tutorials.\n\n> IT IS NOT A MIRROR BOT"
        desc+= "\n\nDeploying Tutorial : [Youtube](https://www.youtube.com/watch?v=MfnP1M0BW7Y)\n"
        desc+="\nOther Tutorials:\n"
        desc+="""[quickstart](https://youtu.be/7PvR1MC_khI)
[auth](https://youtu.be/fUKg5Ge2zl4)
[authsa](https://youtu.be/rz59wScRrqE)
[uploadsas](https://youtu.be/ofbelNADAtA)
[pubclone](https://youtu.be/9dH121W0DZQ)
[privclone](https://youtu.be/1eM3jXXJJtM)
[set_folder](https://youtu.be/e1wqjROvc-I)
[size](https://youtu.be/765uHC6Ybfk)
[listprojects, createsa, downloadsazip, saemails](https://youtu.be/hWmX-a22uLA)"""
        em,view = embed('About Me',desc,url="https://www.youtube.com/watch?v=csH-SaaDN6A")
        await ctx.send(embed=em,view=view)



def setup(bot):
    bot.add_cog(General(bot))
    print("General cog is loaded")