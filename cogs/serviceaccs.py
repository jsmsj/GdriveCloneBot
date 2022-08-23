"""Imports"""
import urllib
import requests
import os,shutil
import asyncio

import discord
from discord.ext import commands
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

import cogs._db_helpers as db
import cogs._sa_creation_utils as sascre
from cogs._config import G_DRIVE_CLIENT_ID, G_DRIVE_CLIENT_SECRET,prefix
from cogs._db_helpers import has_sa_creds
from cogs._helpers import is_allowed,embed,zip_sas_cre
import json
from main import logger

class ServiceAccounts(commands.Cog):
    """ServiceAccounts commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return

    @is_allowed()
    @commands.command(description=f'Use this to authorize for managing Service Accounts.\n`{prefix}authsa`')
    async def authsa(self,ctx):
        creds = db.sascre_find_creds(ctx.author.id)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                db.sascre_insert_creds(ctx.author.id,creds)
                em = embed(title="🧾 Service Accounts",description="You have already authorized for Service Accounts")[0]
                await ctx.send(embed=em)
            else:
                credentials = {
                    "installed": {
                            "client_id": G_DRIVE_CLIENT_ID,
                            "client_secret": G_DRIVE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "redirect_uris": [
                                "http://localhost"
                            ]
                        }
                }
                flow = InstalledAppFlow.from_client_config(credentials,sascre.SCOPES)
                # flow.redirect_uri = 'https://jsmsj.github.io/GdriveCloneBot/auth'
                flow.redirect_uri = 'http://localhost:1'
                auth_url, _ = flow.authorization_url(access_type='offline')
                em,view = embed(title="🧾 Service Accounts",description=f"Visit the following URL and the authorise. You will be redirected to a error page. That page's url would be something like: https://localhost:1/XXXXXXXXX\nCopy that url and send here within 2 minutes.\n\n{auth_url}",url=auth_url)
                # em,view = embed(title="🧾 Service Accounts",description=f"Visit the following URL and the authorise. Make sure to select all the scopes, copy the code and send it here within 2 minutes.\n\n{auth_url}",url=auth_url)
                await ctx.send(embed=em,view=view)
                try:
                    msg:discord.Message = await self.bot.wait_for('message', check=lambda message : message.author == ctx.author and message.channel == ctx.channel, timeout=120)
                except asyncio.TimeoutError:
                    return await ctx.send(embed=embed('Error | Timed out','You did not respond in time. Re run the command and try to respond under 120 seconds.')[0])
                sent_message = await ctx.reply("🕵️**Checking the received code...**")
                try:
                    redir_url = msg.content
                    query = urllib.parse.urlparse(redir_url).query
                    code = urllib.parse.parse_qs(query)['code'][0]
                    # code = redir_url
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    db.sascre_insert_creds(ctx.author.id,creds)
                    em = embed(title="🧾 Service Accounts",description="You have successfully authorized for Service Accounts")[0]
                    await sent_message.edit(embed=em)
                except Exception as e:
                    logger.error(e,exc_info=True)
                    em,view = embed(title='❗ Invalid Link',description=f'The link you have sent is invalid. Generate new one by the Authorization URL `{prefix}authsa`',url=auth_url)
                    # em,view = embed(title='❗ Invalid Code',description='The code you sent is invalid. Generate new one by the Authorization URL',url=auth_url)
                    await sent_message.edit(embed=em,view=view)
        else:
            em = embed(title="🧾 Service Accounts",description="You have already authorized for Service Accounts")[0]
            await ctx.send(embed=em)

    @has_sa_creds()
    @is_allowed()
    @commands.command(description=f'List the project ids of available projects in your google cloud console.\n`{prefix}listprjects`')
    async def listprojects(self,ctx):
        sa_cls = sascre.ServAcc(ctx.author.id)
        desc = "```\n"
        for i in sa_cls._list_projects():
            desc+=f"{i}\n"
        desc+="```"
        em = embed(title="List of Projects",description=desc,url=None)[0]
        await ctx.send(embed=em)

    @has_sa_creds()
    @is_allowed()
    @commands.command(description=f'Create the service accounts in a given project.\n`{prefix}createsa projectId`')
    async def createsa(self,ctx,projectid=None):
        if not projectid:
            return await ctx.send(f"Error: No project id found, correct usage `{prefix}createsa projectid` . Checkout the list of project ids via `{prefix}listprojects` command.")
        sa_cls = sascre.ServAcc(ctx.author.id)
        sa_cls.enableservices(projectid)
        sa_cls.createsas(projectid)
        await ctx.send(embed=embed(title="🧾 Service Accounts",description=f"Successfully Created Service accounts, use `{prefix}downloadsazip` to get the service accounts in json format.\nUse `{prefix}saemails` to get the emails of the service accounts.",url=None)[0])

    @has_sa_creds()
    @is_allowed()
    @commands.command(description=f'Get the Service accounts for a projectId as a zip file.\n`{prefix}downloadsazip projectId`')
    async def downloadsazip(self,ctx,projectid=None):
        try:
            if not projectid:
                return await ctx.send(f"Error: No project id found, correct usage `{prefix}downloadsazip projectid` . Checkout the list of project ids via `{prefix}listprojects` command.")
            sa_cls = sascre.ServAcc(ctx.author.id)
            msg = await ctx.send(embed=embed(title="🧾 Service Accounts",description="Downloading the accounts, please wait ...")[0])
            if db.sas_for_projid_exists(projectid):
                db.download_sas_projid(projectid)
            else:
                sa_cls.download_keys(projectid)
                db.create_db_insert_sas(projectid)
            zip_sas_cre()
            await msg.edit(embed=embed("🧾 Service Accounts","Here is the zip file for your service accounts.")[0],file=discord.File('aaccounts.zip'))
        except Exception as e:
            logger.error(e,exc_info=True)
        finally:
            if os.path.exists('aaccounts.zip'):
                os.remove('aaccounts.zip')
            if os.path.exists('accounts'):
                shutil.rmtree('accounts')
    
    @has_sa_creds()
    @is_allowed()
    @commands.command(description=f'Get the Service Accounts Emails for a projectId.\n`{prefix}saemails projectId`')
    async def saemails(self,ctx,projectid=None):
        try:
            if not projectid:
                return await ctx.send(f"Error: No project id found, correct usage `{prefix}saemails projectid` . Checkout the list of project ids via `{prefix}listprojects` command.")
            msg = await ctx.send(embed=embed(title="🧾 Service Accounts",description="Getting emails please wait ...")[0])
            sa_cls = sascre.ServAcc(ctx.author.id)
            if db.sas_for_projid_exists(projectid):
                db.download_sas_projid(projectid)
            else:
                sa_cls.download_keys(projectid)
                db.create_db_insert_sas(projectid)
            list_of_acc_fname = os.listdir('accounts')
            with open('emails.txt','a') as f:
                for i in list_of_acc_fname:
                    with open(f'accounts/{i}') as f2:
                        data = json.load(f2)
                    f.write(data["client_email"]+"\n")
            await msg.edit(embed=embed("🧾 Service Accounts","Here is the emails file.")[0],file=discord.File('emails.txt'))
        except Exception as e:
            logger.error(e,exc_info=True)
        finally:
            if os.path.exists('accounts'):
                shutil.rmtree('accounts')
            if os.path.exists('emails.txt'):
                os.remove('emails.txt')    
        
    @has_sa_creds()
    @is_allowed()
    @commands.command(description=f'Used to revoke your account connected to Service Accounts with the bot.\n`{prefix}revokesa`')
    async def revokesa(self,ctx):
        creds = db.sascre_find_creds(ctx.author.id)
        if creds:
            revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
                    params={'token': creds.token},
                    headers = {'content-type': 'application/x-www-form-urlencoded'})
            if revoke.status_code == 200:
                db.sascre_delete_creds(ctx.author.id)
                await ctx.send(embed=embed("🔓 Revoked current logged in account for Service Accounts.",f"Use `{prefix}authsa` to authenticate again.",None)[0])
            else:
                await ctx.send(embed=embed("❗ Error | Unable to delete credentials",f"An error occured\nError: {revoke.json()['error']}\nDescription: {revoke.json()['error_description']}",None)[0])
        else:
            await ctx.send(embed=embed("🔓 Already Revoked",f"You haven't even signed in. Use `{prefix}authsa` to sign in.",None)[0])
        
def setup(bot):
    bot.add_cog(ServiceAccounts(bot))
    print("ServiceAccounts cog is loaded")
