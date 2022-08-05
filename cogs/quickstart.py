"""Imports"""
import json
import shutil

import discord
from discord.ext import commands
from main import logger

import cogs._db_helpers as db
import cogs._sa_creation_utils as sascre
from cogs._db_helpers import not_has_sa_creds,not_has_credentials
from cogs._helpers import embed, is_allowed, zip_sas_cre
import os


class Quickstart(commands.Cog):
    """Quickstart commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return

    @is_allowed()
    @not_has_credentials()
    @not_has_sa_creds()
    @commands.command()
    async def makeithappen(self,ctx:commands.Context,projectid=None,link=None):
        if not projectid:
            return await ctx.send("Error: No project id found, correct usage `gcb quickstart projectid link`.")
        if not link:
            return await ctx.send("Error: No folder id found, correct usage `gcb quickstart projectid link`.")
        await ctx.invoke(self.bot.get_command('authsa'))
        await ctx.invoke(self.bot.get_command('auth'))
        await ctx.invoke(self.bot.get_command('createsa'), projectid=projectid)
        try:
            sa_cls = sascre.ServAcc(ctx.author.id)
            msg = await ctx.send(embed=embed(title="🧾 Service Accounts",description="Downloading the accounts, please wait ...")[0])
            if db.sas_for_projid_exists(projectid):
                db.download_sas_projid(projectid)
            else:
                sa_cls.download_keys(projectid)
                db.create_db_insert_sas(projectid)
            zip_sas_cre()
            await msg.edit(embed=embed("🧾 Service Accounts","Here is the zip file for your service accounts.")[0])
            await ctx.send(file=discord.File('aaccounts.zip'))
            list_of_acc_fname = os.listdir('accounts')
            with open('emails.txt','a') as f:
                for i in list_of_acc_fname:
                    with open(f'accounts/{i}') as f2:
                        data = json.load(f2)
                    f.write(data["client_email"]+"\n")
            await ctx.send(embed=embed("🧾 Service Accounts","Here is the emails file. Add these to a google group and add that google group to a teamdrive, incase you want to copy stuff to teamdrive.")[0],file=discord.File('emails.txt'))
            for idx,filename in enumerate(list_of_acc_fname):
                with open('accounts'+f"\\{filename}") as f:
                    data = json.load(f)
                    data['sa_file_index'] = idx
                    db.sas_db.insert_one(data)

            em,view = embed("🧾 Service Accounts","Added Service Accounts successfully.",None)
            await ctx.send(embed=em,view=view)
        except Exception as e:
            logger.warning(e)
        finally:
            if os.path.exists('aaccounts.zip'):
                os.remove('aaccounts.zip')
            if os.path.exists('accounts'):
                shutil.rmtree('accounts')
            if os.path.exists('emails.txt'):
                os.remove('emails.txt')

        await ctx.invoke(self.bot.get_command('set_folder'),link=link)
        em = embed("🎌 Congratulations","Setup done successfully, now you can clone public as well as private links!\nCommands:\n`gcb pubclone drive.google.com/XXXXXXXX`\n`gcb privclone drive.google.com/XXXXXXXX`\nTo get help on above commands run `gcb help cmd_name`",None)[0]
        await ctx.send(embed=em)

    @makeithappen.error
    async def make_it_happn_err(self,ctx,error):
        return await ctx.send("You have already ran this command once. It cannot be run again. Use other avaialbe commands to generate Service Accounts.")

def setup(bot):
    bot.add_cog(Quickstart(bot))
    print("Quickstart cog is loaded")
