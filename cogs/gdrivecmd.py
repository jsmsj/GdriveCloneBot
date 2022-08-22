"""Imports"""
import discord
import os,shutil
from discord.ext import commands
from cogs._gd_utils import GoogleDrive
import cogs._db_helpers as db
from cogs._db_helpers import has_credentials
from cogs._helpers import extract_sas,is_allowed,embed
from main import logger
import cogs._config

class GdriveCmd(commands.Cog):
    """GdriveCmd commands"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.trigger_typing()    
        return

    @is_allowed()
    @has_credentials()
    @commands.command(description=f'Used to clone Files/Folders which you can access but your Service Accounts cannot.\n`{cogs._config.prefix}privclone gdrive_link`')
    async def privclone(self,ctx,*,link=None):
        user_id = ctx.author.id
        if link:
            em,view = embed(title="🗂️ Cloning into Google Drive...",description="Please wait till this clone completes, and then only send the next link.",url=link)
            sent_message = await ctx.reply(embed=em,view=view)
            user_gd_cls = GoogleDrive(user_id,use_sa=False)
            emb,vieww = await user_gd_cls.clone(sent_message,link)
            await sent_message.edit(embed=emb,view=vieww)
        else:
            em,view = embed(title="❗ Provide a valid Google Drive URL along with commmand.",description=f"```\nUsage -> {cogs._config.prefix}privclone (GDrive Link)\n```")
            await ctx.reply(embed=em,view=view)

    @is_allowed()
    @has_credentials()
    @commands.command(description=f'Used to clone Files/Folders which your Service Accounts can access.\n`{cogs._config.prefix}pubclone gdrive_link`')
    async def pubclone(self,ctx,*,link=None):
        user_id = ctx.author.id
        if link:
            em,view = embed(title="🗂️ Cloning into Google Drive...",description="Please wait till this clone completes, and then only send the next link.",url=link)
            sent_message = await ctx.reply(embed=em,view=view)
            user_gd_cls = GoogleDrive(user_id,use_sa=True)
            emb,vieww = await user_gd_cls.clone(sent_message,link)
            await sent_message.edit(embed=emb,view=vieww)
        else:
            em,view = embed(title="❗ Provide a valid Google Drive URL along with commmand.",description=f"```\nUsage -> {cogs._config.prefix}pubclone (GDrive Link)\n```")
            await ctx.reply(embed=em,view=view)

    @is_allowed()
    @has_credentials()
    @commands.command(description=f'Used to set the defaut cloning location.\n`{cogs._config.prefix}set_folder gdrive_link`')
    async def set_folder(self,ctx,*,link=None):
        user_id = ctx.author.id
        if link:
            if not 'clear' in link:
                em,view = embed(title="🕵️ Set Folder",description=f"**Checking Link...** - {link}",url=None)
                sent_message = await ctx.reply(embed=em,view=view)
                gdrive = GoogleDrive(user_id,use_sa=False)
                try:
                    result, file_id = gdrive.checkFolderLink(link)
                    if result:
                        db.insert_parent_id(user_id,file_id)
                        em,view = embed(title="🆔 ✅ Custom Folder link set successfully.",description=f"Your custom folder id - `{file_id}`\n\nUse `{cogs._config.prefix}set_folder clear` to clear it.",url=None)
                        await sent_message.edit(embed=em,view=view)
                    else:
                        e,v = embed(title=file_id[0],description=file_id[1],url=None)
                        await sent_message.edit(embed=e,view=v)
                except IndexError:
                    em,view = embed(title="❗Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.",url=None)
                    await sent_message.edit(embed=em,view=view)
            else:
                db.delete_parent_id(user_id)
                em,view = embed("🆔 🚮 Custom Folder ID Cleared Successfuly.",f"Use `{cogs._config.prefix}set_folder (Folder Link)` to set it back.",None)
                await ctx.reply(embed=em,view=view)
        else:
            em,view = embed("🆔 Set Folder", f"Your Current Custom Folder ID- `{db.find_parent_id(user_id)}`\n\nUse `{cogs._config.prefix}set_folder (Folder Link)` to change it.",None)
            await ctx.reply(embed=em,view=view)

    @is_allowed()
    @commands.command(description=f'Set the Service Accounts which the bot will use.\n`{cogs._config.prefix}uploadsas zip_file_attachment`')
    async def uploadsas(self,ctx: commands.Context):
        try:
            if len(ctx.message.attachments) !=0:
                attachment = ctx.message.attachments[0]
                if attachment.content_type == "application/zip":
                    await attachment.save(fp="sas.zip")
                    extract_sas('sas.zip')
                    if not db.find_sas():
                        db.upload_sas()
                        em,view = embed("🧾 Service Accounts","Added Service Accounts successfully.",None)
                        await ctx.send(embed=em,view=view)
                    else:
                        db.delete_sas()
                        db.upload_sas()
                        em,view = embed("🧾 Service Accounts","Updated Service Accounts successfully.",None)
                        await ctx.send(embed=em,view=view)
                else:
                    em,view = embed("❗ Service Accounts","You didn't give me a zip file of service accounts. [1]",None)
                    await ctx.send(embed=em,view=view)
            else:
                em,view = embed("❗ Service Accounts","You didn't give me a zip file of service accounts. [2]",None)
                await ctx.send(embed=em,view=view)
        except Exception as e:
            logger.warning(e)
        finally:
            if os.path.exists('sas.zip'):
                os.remove('sas.zip')
            if os.path.exists('sas'):
                shutil.rmtree('sas')

    # @is_allowed()
    # @has_credentials()
    # @commands.command()
    # async def search(self,ctx,orderby,*,query):
    #     gdrive = GoogleDrive(ctx.author.id,use_sa=False)
    #     files = gdrive.search_drive(query,orderby)

    #     print(files)

    @is_allowed()
    @has_credentials()
    @commands.command(description=f'Get size of a google drive file/folder.\n`{cogs._config.prefix}size gdrive_link`')
    async def size(self,ctx,*,url):
        msg = await ctx.reply(embed=embed('💾 Size','Calculating Size ....\nPlease wait')[0])
        gdrive = GoogleDrive(ctx.author.id,use_sa=False)
        emb = gdrive.size(url)[0]
        await msg.edit(embed=emb)


def setup(bot):
    bot.add_cog(GdriveCmd(bot))
    print("GdriveCmd cog is loaded")


#TODO CHECK FAILURE