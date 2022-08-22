"""Imports"""
import discord
from discord.ext import commands
import cogs._db_helpers as db
from httplib2 import Http
import cogs._config
from oauth2client.client import OAuth2WebServerFlow, FlowExchangeError
from cogs._helpers import is_allowed,embed

from main import logger

OAUTH_SCOPE = "https://www.googleapis.com/auth/drive"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
flow = OAuth2WebServerFlow(
                        cogs._config.G_DRIVE_CLIENT_ID,
                        cogs._config.G_DRIVE_CLIENT_SECRET,
                        OAUTH_SCOPE,
                        redirect_uri=REDIRECT_URI
                )

class Auth(commands.Cog):
    """Auth commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return

    @is_allowed()
    @commands.command(aliases=['authorize'],description=f'Used to authorise your Google Drive with the bot.\n`{cogs._config.prefix}auth`')
    async def auth(self,ctx):
        user_id = ctx.author.id
        creds = db.find_creds(user_id)
        global flow
        if creds is not None:
            creds.refresh(Http())
            db.insert_creds(user_id,creds)
            em,view = embed(title="🔒 Already authorized your Google Drive Account.",description=f"Use `{cogs._config.prefix}revoke` to remove the current account.")
            return await ctx.reply(embed=em,view=view)
        else:
            try:
                auth_url = flow.step1_get_authorize_url()
                em,view = embed(title="⛓️ Authorize",description=f"To Authorize your Google Drive account visit this {auth_url} and send the generated code here, within 120 seconds.\n\nVisit the URL > Allow permissions > you will get a code > copy it > Send it here",url=auth_url)
                await ctx.reply(embed=em,view=view)
            except Exception as e:
                logger.error(e,exc_info=True)
                em,view = embed("Error",f"```py\n{e}\n```",None)
                return await ctx.reply(embed=em,view=view)
        msg = await self.bot.wait_for('message', check=lambda message : message.author == ctx.author and message.channel == ctx.channel, timeout=120)
        token = msg.content
        WORD = len(token)
        if WORD == 62 and token[1] == "/":
            creds = None
            try:
                user_id = ctx.author.id
                sent_message = await ctx.reply("🕵️**Checking the received code...**")
                creds = flow.step2_exchange(token)
                db.insert_creds(user_id,creds)
                em = embed(title="🔐 Authorized Google Drive account Successfully.",description=f"Use `{cogs._config.prefix}revoke` to remove the current account.")[0]
                await sent_message.edit(embed=em)
                flow = None
            except FlowExchangeError as e:
                logger.error(e,exc_info=True)
                em,view = embed(title='❗ Invalid Code',description='The code you have sent is invalid or already used before. Generate new one by the Authorization URL',url=auth_url)
                await sent_message.edit(embed=em,view=view)
            except Exception as e:
                logger.error(e,exc_info=True)
                em,view = embed("Error",f"```py\n{e}\n```",None)
                return await ctx.reply(embed=em,view=view)

    @is_allowed()
    @commands.command(description=f'Used to revoke your Google Drive connected with the bot.\n`{cogs._config.prefix}revoke`')
    async def revoke(self,ctx):
        db.delete_creds(ctx.author.id)
        em = embed(f"🔓 Revoked current logged in account successfully.","Use `{cogs._config.prefix}auth` to authenticate again and use this bot.",None)[0]
        await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(Auth(bot))
    print("Auth cog is loaded")