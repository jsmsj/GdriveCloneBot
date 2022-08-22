"""Imports"""
import discord
from discord.ext import commands,pages
from cogs._config import prefix

class Help(commands.Cog):
    """Help commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return


    @commands.command(description=f'Help Command\n`{prefix}help`')
    async def help(self,ctx,*,cmd=None):
        com_except_jishaku = [i for i in list(self.bot.commands) if i.name!= "jishaku"]
        if not cmd:
            ls_of_em = []
            com_list = [com_except_jishaku[i:i + 6] for i in range(0, len(com_except_jishaku), 6)]
            for idx,val in enumerate(com_list):
                em = discord.Embed(title=f"Help -- Page: {idx+1}",color=discord.Color.green())
                em.set_footer(text="Made with 💖 by jsmsj")
                em.description = f'Run `{prefix}help cmd_name` for more info on the command.'
                for j in val:
                    em.add_field(name=f"{prefix}{j.name}",value=j.description if j.description else "None",inline=False)
                ls_of_em.append(em)
            paginator = pages.Paginator(pages=ls_of_em)
            return await paginator.send(ctx)
        else:
            cmd = cmd.strip()
            cmd_name_list = [i.name for i in com_except_jishaku]
            if not cmd in cmd_name_list:
                em = discord.Embed(title=f"Unable to find that command",color=discord.Color.green())
                em.set_footer(text="Made with 💖 by jsmsj")
                em.description = f'Command {cmd} not found !'
                return await ctx.send(embed=em)
            else:
                try:
                    idx = cmd_name_list.index(cmd)
                except ValueError:
                    idx= None
                if not idx:
                    em = discord.Embed(title=f"Unable to find that command",color=discord.Color.green())
                    em.set_footer(text="Made with 💖 by jsmsj")
                    em.description = f'Command {cmd} not found !'
                    return await ctx.send(embed=em)
                else:
                    comm:commands.Command = com_except_jishaku[idx]
                    em = discord.Embed(title=f"Help: {comm.name}",color=discord.Color.green())
                    em.set_footer(text="Made with 💖 by jsmsj")
                    em.description = comm.description if comm.description else 'None'
                    em.add_field(name='Category',value=str(comm.cog_name))
                    return await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(Help(bot))
    print("Help cog is loaded")