from discord.ext import commands
import discord
from discord.ui import Button,View
from cogs._config import allowed_user_ids
import zipfile
import shutil
import os
import time
from math import ceil

def is_allowed():
    async def predicate(ctx:commands.Context):
        if isinstance(allowed_user_ids,list):
            return True if ctx.author.id in allowed_user_ids else False
        elif isinstance(allowed_user_ids,int):
            return True if ctx.author.id == allowed_user_ids else False
        elif isinstance(allowed_user_ids,str):
            return True if ctx.author.id == int(allowed_user_ids) else False
        else:
            return True
    return commands.check(predicate)


def humanbytes(size: int) -> str:
    if not size:
        return ""
    power = 2 ** 10
    number = 0
    dict_power_n = {
        0: " ",
        1: "K",
        2: "M",
        3: "G",
        4: "T",
        5: "P"
    }
    while size > power:
        size /= power
        number += 1
    return str(round(size, 3)) + " " + dict_power_n[number] + 'B'

def humantime(seconds):
    if seconds > 3600:
        return time.strftime("%Hh%Mm%Ss", time.gmtime(seconds))
    else:
        return time.strftime("%Mm%Ss", time.gmtime(seconds))

def extract_sas(filename):
    with zipfile.ZipFile(filename,'r') as myzip:
        myzip.extractall('sas')

    
def embed(title,description,url=None):
    em = discord.Embed(title=title,description=description,color=discord.Color.green(),url="https://github.com/jsmsj/gdriveclonebot")
    em.set_footer(text="Made with 💖 by jsmsj")
    if url:
        btn = Button(label="Link",url=url)
        view = View()
        view.add_item(btn)
        return [em,view]
    return [em,None]

def show_progress_still(current:int,total:int,width:int):
    int_percent = round(current*100/total)
    hashblocks = round((int_percent*width/100)-1)
    if hashblocks<0:
        hashblocks = 0
    return "#️⃣"* hashblocks + "▶️" + "🟦"*(width-hashblocks-1)

def status_emb(transferred:int,current_file_name,current_file_size,total_size:int,start_time,total_files,num_of_files_transferred):
    em = discord.Embed(title="📺 Status : Copying...",color=discord.Color.green(),url="https://github.com/jsmsj/gdriveclonebot")
    em.set_footer(text="Made with 💖 by jsmsj")
    speed = int(transferred/(time.time()-start_time))
    em.description = f"Current File: `{current_file_name}`\nCurrent File Size: `{humanbytes(current_file_size)}`\nStatus: Copying...📚\nTransferred {num_of_files_transferred} of {total_files}\nCopied: {humanbytes(transferred)} of {humanbytes(total_size)} (`{humanbytes(speed)}/s`) (ETA: `{humantime((total_size-transferred)/speed)}` )\n\n{show_progress_still(transferred,total_size,20)}🏁 {round(transferred*100/total_size,3)} %"
    return em

def zip_sas_cre():
    if os.path.exists('accounts'):
        shutil.make_archive("aaccounts", 'zip', "accounts")
        

def list_into_n_parts(lst, n):
  size = ceil(len(lst) / n)
  return list(
    map(lambda x: lst[x * size:x * size + size],
    list(range(n)))
  )

def threaded_status_emb(transferred:int,current_file_name,current_file_size,total_size:int,start_time):
    em = discord.Embed(title="📺 Status : Copying...",color=discord.Color.green(),url="https://github.com/jsmsj/gdriveclonebot")
    em.set_footer(text="Made with 💖 by jsmsj")
    speed = int(transferred/(time.time()-start_time))
    em.description = f"Current File: `{current_file_name}`\nCurrent File Size: `{humanbytes(current_file_size)}`\nStatus: Copying...📚\nCopied: {humanbytes(transferred)} of {humanbytes(total_size)} (`{humanbytes(speed)}/s`) (ETA: `{humantime((total_size-transferred)/speed)}` )\n\n{show_progress_still(transferred,total_size,20)}🏁 {round(transferred*100/total_size,3)} %"
    return em