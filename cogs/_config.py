from dotenv import load_dotenv
import os
load_dotenv()

bot_token = os.getenv('bot_token')
temp_allowed_uid = os.getenv('allowed_user_ids').split(',')
allowed_user_ids = list(map(int,[i for i in temp_allowed_uid if i!= '']))
db_url = os.getenv('db_url')
G_DRIVE_CLIENT_ID = os.getenv('G_DRIVE_CLIENT_ID')
G_DRIVE_CLIENT_SECRET = os.getenv('G_DRIVE_CLIENT_SECRET')
prefix = os.getenv('prefix')