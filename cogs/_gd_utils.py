import os
import re
import json
import logging
from time import sleep
from tenacity import *
import urllib.parse as urlparse
from mimetypes import guess_type
from urllib.parse import parse_qs
from cogs._helpers import humanbytes
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import cogs._db_helpers as db
from google.oauth2 import service_account
from cogs._helpers import embed,status_emb
# import asyncio
from discord import Message

class GoogleDrive:
    def __init__(self, user_id,use_sa):
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__parent_id = db.find_parent_id(user_id)
        self.user_id = user_id
        self.use_sa = use_sa
        self.sa_index = 0
        self.__service = self.authorize()
        self.size_service = None
        # self.asyncloop = asyncio.get_event_loop()

    def getIdFromUrl(self, link: str):
            if "folders" in link or "file" in link:
                    regex = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"
                    res = re.search(regex,link)
                    if res is None:
                            raise IndexError("GDrive ID not found.")
                    return res.group(5)
            parsed = urlparse.urlparse(link)
            return parse_qs(parsed.query)['id'][0]

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError))
    def getFilesByFolderId(self, folder_id):
            page_token = None
            q = f"'{folder_id}' in parents"
            files = []
            while True:
                    response = self.__service.files().list(supportsTeamDrives=True,
                    									    includeTeamDriveItems=True,
                    									    q=q,
                    									    spaces='drive',
                    									    pageSize=200,
                    									    fields='nextPageToken, files(id, name, mimeType,size)',
                    									    pageToken=page_token).execute()
                    for file in response.get('files', []):
                            files.append(file)
                    page_token = response.get('nextPageToken', None)
                    if page_token is None:
                            break
            return files

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
        retry=retry_if_exception_type(HttpError))
    def copyFile(self, file_id, dest_id):
        body = {
            'parents': [dest_id],
            'description': 'Uploaded by Gdrive Clone Bot'
        }
        try:
            res = self.__service.files().copy(supportsAllDrives=True,fileId=file_id,body=body).execute()
            return res
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if reason == 'userRateLimitExceeded' or reason == 'dailyLimitExceeded':
                    if self.use_sa:
                        self.switchSaIndex()
                        self.copyFile(file_id, dest_id)
                    else:
                        raise IndexError(reason)
                else:
                    raise err

    async def cloneFolder(self, name, local_path, folder_id, parent_id,msg:Message,total_size:int):
        files = self.getFilesByFolderId(folder_id)
        new_id = None
        if len(files) == 0:
            return self.__parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                    file_path = os.path.join(local_path, file.get('name'))
                    current_dir_id = self.create_directory(file.get('name'),parent_id=parent_id)
                    new_id = await self.cloneFolder(file.get('name'), file_path, file.get('id'), current_dir_id,msg,total_size)
            else:
                try:
                    self.transferred_size += int(file.get('size'))
                except TypeError:
                    pass
                try:
                    self.copyFile(file.get('id'), parent_id)
                    emb = status_emb(transferred = self.transferred_size,current_file_name = file.get('name'),total_size=total_size)
                    await msg.edit(embed=emb)
                    new_id = parent_id
                except Exception as err:
                    return err
        return new_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError))
    def create_directory(self, directory_name,**kwargs):
        if not kwargs == {}:
            parent_id = kwargs.get('parent_id')
        else:
            parent_id = self.__parent_id
        file_metadata = {
                "name": directory_name,
                "mimeType": self.__G_DRIVE_DIR_MIME_TYPE,
                'description': 'Uploaded by Gdrive Clone Bot'
        }
        file_metadata["parents"] = [parent_id]
        file = self.__service.files().create(supportsTeamDrives=True, body=file_metadata).execute()
        file_id = file.get("id")
        return file_id

    async def clone(self,msg:Message,link):
        self.transferred_size = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return embed(title="❗ Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.")
        try:
            self.size_service = TotalSize(file_id,self.__service)
            total_size = self.size_service.calc_size()
            meta = self.__service.files().get(supportsAllDrives=True, fileId=file_id, fields="name,id,mimeType,size").execute()
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.create_directory(meta.get('name'),parent_id=self.__parent_id)
                result = await self.cloneFolder(meta.get('name'), meta.get('name'), meta.get('id'), dir_id,msg,total_size)
                return embed(title="✅ Copied successfully.",description=f"[{meta.get('name')}]({self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}) ---- `{humanbytes(self.transferred_size)}`\n{'#️⃣'*19+'▶️'} 100 %",url=self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id))
            else:
                file = self.copyFile(meta.get('id'), self.__parent_id)
                return embed(title="✅ Copied successfully.",description=f"[{file.get('name')}]({self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id'))}) ---- `{humanbytes(int(meta.get('size')))}`\n{'#️⃣'*19+'▶️'} 100 %",url=self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id')))
        except Exception as err:
            if isinstance(err, RetryError):
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            return embed(title="Error",description=f"```\n{err}\n```")


    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError))
    def checkFolderLink(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            raise IndexError
        try:
            file = self.__service.files().get(supportsAllDrives=True, fileId=file_id, fields="mimeType").execute()
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if 'notFound' in reason:
                    return False, ["❗ File/Folder not found.", f"File id - {file_id} Not found. Make sure it exists and accessible by the logged in account."]
                else:
                    return False, ["ERROR:", f"```py\n{str(err).replace('>', '').replace('<', '')}\n```"]
        if str(file.get('mimeType')) == self.__G_DRIVE_DIR_MIME_TYPE:
            return True, file_id
        else:
            return False, ["❗Invalid folder link.","The link you send does not belong to a folder."]

    # def search_drive(self,query,orderby):
    #     page_token = None
    #     result = []
    #     while True:
    #         try:
    #             param = {
    #                 'corpora' : 'allDrives',
    #                 'q': f"name contains '{query}'",
    #                 'includeItemsFromAllDrives': True,
    #                 'supportsAllDrives': True,
    #                 'fields': 'nextPageToken, files(id, name)',
    #                 'pageSize': 1000
    #                 # 'orderBy':orderby
    #             }
    #             if page_token:
    #                 param['pageToken'] = page_token
                
    #             all_files = self.__service.files().list(**param).execute()
    #             print(all_files)
    #             result.extend(all_files['files'])
    #             page_token = all_files.get('nextPageToken')
    #             if not page_token:
    #                 break
    #         except HttpError as e:
    #             print(e)
    #             break
    #     return result

    def size(self,link):
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return embed(title="❗ Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.")
        size_serve = TotalSize(file_id,self.__service)
        total_size = size_serve.calc_size()
        return embed('💾 Size',f'{total_size} bytes\nor\n{humanbytes(total_size)}')

    def switchSaIndex(self):
        all_sas = db.find_sas()
        if self.sa_index == len(all_sas)-1:
            self.sa_index = 0
        sa_index +=1
        self.__service = self.authorize()

    def authorize(self):
        if not self.use_sa:
            creds = db.find_creds(self.user_id)
        else:
            sa_info = db.find_sa_info_by_id(self.sa_index)
            sa = {
                "client_email":sa_info["client_email"],
                "token_uri":sa_info["token_uri"],
                "private_key":sa_info["private_key"]
            }
            creds = service_account.Credentials.from_service_account_info(sa,scopes=self.__OAUTH_SCOPE)
        return build('drive', 'v3', credentials=creds, cache_discovery=False)  #TODO add error handler-> DefaultCredentialsError: Could not automatically determine credentials. Please set GOOGLE_APPLICATION_CREDENTIALS or explicitly create credentials and re-run the application. For more information, please see https://cloud.google.com/docs/authentication/getting-started (happens when you clone without auth or sa)


class TotalSize:
    def __init__(self,gdrive_id,service):
        self.link_id = gdrive_id
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__service = service
        self.total_bytes = 0

    def calc_size(self):
        drive_file = self.__service.files().get(fileId=self.link_id, fields="id, mimeType, size",
                                                supportsTeamDrives=True).execute()
        if drive_file['mimeType'] == self.__G_DRIVE_DIR_MIME_TYPE:
            self.gDrive_directory(**drive_file)
        else:
            self.gDrive_file(**drive_file)
        return self.total_bytes

    def list_drive_dir(self, file_id: str) -> list:
        query = f"'{file_id}' in parents and (name contains '*')"
        fields = 'nextPageToken, files(id, mimeType, size)'
        page_token = None
        page_size = 1000
        files = []
        while True:
            response = self.__service.files().list(supportsTeamDrives=True,
                                                  includeTeamDriveItems=True,
                                                  q=query, spaces='drive',
                                                  fields=fields, pageToken=page_token,
                                                  pageSize=page_size, corpora='allDrives',
                                                  orderBy='folder, name').execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return files

    def gDrive_file(self, **kwargs):
        try:
            size = int(kwargs['size'])
        except:
            size = 0
        self.total_bytes += size

    def gDrive_directory(self, **kwargs) -> None:
        files = self.list_drive_dir(kwargs['id'])
        if len(files) == 0:
            return
        for file_ in files:
            if file_['mimeType'] == self.__G_DRIVE_DIR_MIME_TYPE:
                self.gDrive_directory(**file_)
            else:
                self.gDrive_file(**file_)
    
# orderBy	string	A comma-separated list of sort keys. Valid keys are 
# 'createdTime', 'folder', 'modifiedByMeTime', 'modifiedTime', 'name',
#  'name_natural', 'quotaBytesUsed', 'recency', 'sharedWithMeTime',
#  'starred', and 'viewedByMeTime'. Each key sorts ascending by default,
#  but may be reversed with the 'desc' modifier. Example usage: 
# ?orderBy=folder,modifiedTime desc,name. Please note that there is a current 
# limitation for users with approximately one million files in which the 
# requested sort order is ignored.