import logging
from discord.ext import commands
import discord
import os
import cogs._config
import shutil,os
from cogs._helpers import embed

if os.path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

logger = logging.getLogger(__name__)

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=cogs._config.prefix, intents=intents, help_command=None, case_insensitive=True) 

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Google Drive"))
    print("Bot is ready!")

@bot.event
async def on_command_error(ctx:commands.Context,error):
    if hasattr(ctx.command, 'on_error'):
        return
    if isinstance(error,commands.CommandNotFound):
        return
    elif isinstance(error,commands.CheckFailure):
        await ctx.send(f"You do not have permission to run this command.\nOR\nYou have not authorized the bot with your account. Run `{cogs._config.prefix}auth` to authorize.\nOR\nYou are using a command related to service accounts, and have not authorized for it. Use `{cogs._config.prefix}authsa` to authorize for service accounts.")
    else:
        logger.warning(error)
        _file=None
        if os.path.exists('log.txt'):
            _file = discord.File('log.txt')
        await ctx.send(embed=embed(f'Error | {ctx.command.name}',f'An error occured, kindly report it to jsmsj#5252.\n```py\n{error}\n```\nHere is the attached logfile.')[0],file=_file)

if __name__ == '__main__':
    # When running this file, if it is the 'main' file
    # i.e. its not being imported from another python file run this
    if os.path.exists('accounts'):
        shutil.rmtree('accounts')
    if os.path.exists('sas.zip'):
        os.remove('sas.zip')
    if os.path.exists('emails.txt'):
        os.remove('emails.txt')
    if os.path.exists('aacounts.zip'):
        os.remove('aaccounts.zip')
    if os.path.exists('sas'):
        shutil.rmtree('sas')

    for file in os.listdir("cogs/"):
        if file.endswith(".py") and not file.startswith("_"):
            bot.load_extension(f"cogs.{file[:-3]}")

    logger.info("Bot has started, all cogs are loaded.")
    bot.run(cogs._config.bot_token)

