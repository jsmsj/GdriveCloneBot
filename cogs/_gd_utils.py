import asyncio
import json
import logging
import os
import pprint
import re
import threading
import urllib.parse as urlparse
from mimetypes import guess_type
from time import sleep
from urllib.parse import parse_qs

import google.auth
import google_auth_httplib2
import googleapiclient
import httplib2
from discord import Message
from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tenacity import *

import cogs._db_helpers as db
from cogs._helpers import embed, humanbytes, list_into_n_parts, status_emb,humantime,threaded_status_emb
from main import logger

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)


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
        self.threaded_details = {"overall_used_sas":[]}

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
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
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
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
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
                        logger.debug(reason)
                        raise IndexError(reason)
                else:
                    logger.error(err,exc_info=True)
                    raise err
            else:
                logger.error(err,exc_info=True)

    async def cloneFolder(self, name, local_path, folder_id, parent_id,msg:Message,total_size:int,total_files):
        files = self.getFilesByFolderId(folder_id)
        new_id = None
        if len(files) == 0:
            return self.__parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                    file_path = os.path.join(local_path, file.get('name'))
                    current_dir_id = self.create_directory(file.get('name'),parent_id=parent_id)
                    new_id = await self.cloneFolder(file.get('name'), file_path, file.get('id'), current_dir_id,msg,total_size,total_files)
            else:
                try:
                    self.transferred_size += int(file.get('size'))
                    self.num_of_files_transferred +=1
                except TypeError:
                    pass
                try:
                    self.copyFile(file.get('id'), parent_id)
                    emb = status_emb(transferred = self.transferred_size,current_file_name = file.get('name'),current_file_size=int(file.get('size')) ,total_size=total_size,start_time=self.start_time,total_files=total_files,num_of_files_transferred=self.num_of_files_transferred)
                    await msg.edit(embed=emb)
                    new_id = parent_id
                except Exception as err:
                    logger.error(err,exc_info=True)
                    return err
        return new_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
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
        self.num_of_files_transferred = 0
        self.start_time = time.time()
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return embed(title="❗ Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.")
        try:
            self.size_service = TotalSize(file_id,self.__service)
            total_size,total_files = self.size_service.calc_size_and_files()
            meta = self.__service.files().get(supportsAllDrives=True, fileId=file_id, fields="name,id,mimeType,size").execute()
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.create_directory(meta.get('name'),parent_id=self.__parent_id)
                result = await self.cloneFolder(meta.get('name'), meta.get('name'), meta.get('id'), dir_id,msg,total_size,total_files)
                return embed(title="✅ Copied successfully.",description=f"[{meta.get('name')}]({self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}) ---- `{humanbytes(self.transferred_size)}`\nTransferred {self.num_of_files_transferred} of {total_files}\n\n{'#️⃣'*19+'▶️'} 100 % (`{humanbytes(int(self.transferred_size/(time.time()-self.start_time)))}/s`)\nElapsed Time: `{humantime(time.time()-self.start_time)}`",url=self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id))
            else:
                file = self.copyFile(meta.get('id'), self.__parent_id)
                self.num_of_files_transferred+=1
                return embed(title="✅ Copied successfully.",description=f"[{file.get('name')}]({self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id'))}) ---- `{humanbytes(int(meta.get('size')))}`\nTransferred {self.num_of_files_transferred} of {total_files}\n\n{'#️⃣'*19+'▶️'} 100 % (`{humanbytes(int(int(meta.get('size'))/(time.time()-self.start_time)))}/s`)\nElapsed Time: `{humantime(time.time()-self.start_time)}`",url=self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id')))
        except Exception as err:
            if isinstance(err, RetryError):
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            further_messages = ["If you were trying to clone a private link, try `privclone` command.","I don't think you have access to this folder/file."]
            further_message = further_messages[0] if self.use_sa else further_messages[1]
            return embed(title="Error",description=f"```\n{err}\n```\n{further_message}")


    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
    def checkFolderLink(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError) as err:
            logger.error(err,exc_info=True)
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
            else:
                logger.error(err,exc_info=True)
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
        except (IndexError, KeyError) as err:
            logger.error(err,exc_info=True)
            return embed(title="❗ Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.")
        size_serve = TotalSize(file_id,self.__service)
        total_size = size_serve.calc_size_and_files()[0]
        return embed('💾 Size',f'`{total_size} bytes`\nor\n`{humanbytes(total_size)}`')

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
    def threaded_getFilesByFolderId(self,thread_name, folder_id):
            page_token = None
            q = f"'{folder_id}' in parents"
            files = []
            while True:
                    response = self.threaded_details[thread_name]['service'].files().list(supportsTeamDrives=True,
                    									    includeTeamDriveItems=True,
                    									    q=q,
                    									    spaces='drive',
                    									    pageSize=200,
                    									    fields='nextPageToken, files(id, name, mimeType,size)',
                    									    pageToken=page_token).execute(http=self.threaded_details[thread_name]['http'])
                    for file in response.get('files', []):
                            files.append(file)
                    page_token = response.get('nextPageToken', None)
                    if page_token is None:
                            break
            return files

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
    def threaded_create_directory(self,thread_name, directory_name,**kwargs):
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
        file = self.threaded_details[thread_name]['service'].files().create(supportsTeamDrives=True, body=file_metadata).execute(http=self.threaded_details[thread_name]['http'])
        file_id = file.get("id")
        return file_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(15),
        retry=retry_if_exception_type(HttpError), before=before_log(logger, logging.DEBUG))
    def threaded_copyFile(self,file_id,dest_id,thread_name):
        body = {
            'parents': [dest_id],
            'description': 'Uploaded by Gdrive Clone Bot'
        }
        try:
            res = self.threaded_details[thread_name]['service'].files().copy(supportsAllDrives=True,fileId=file_id,body=body).execute(http=self.threaded_details[thread_name]['http'])
            return res
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if reason == 'userRateLimitExceeded' or reason == 'dailyLimitExceeded':
                    if self.use_sa:
                        self.threaded_switchSaIndex(thread_name)
                        self.threaded_copyFile(file_id, dest_id,thread_name)
                    else:
                        logger.debug(reason)
                        raise IndexError(reason)
                else:
                    logger.error(err,exc_info=True)
                    raise err
            else:
                logger.error(err,exc_info=True)
    
    def threaded_cloneFolder(self,name,local_path,files,parent_id,thread_name,loop):
        new_id = None
        if len(files) == 0:
            return self.__parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                file_path = os.path.join(local_path, file.get('name'))
                # print('creating directory ' + file_path)
                current_dir_id = self.threaded_create_directory(thread_name,file.get('name'),parent_id=parent_id)
                # print('created directory ' + file_path)
                inner_files = self.threaded_getFilesByFolderId(thread_name,file.get('id'))
                new_id = self.threaded_cloneFolder(file.get('name'), file_path, inner_files, current_dir_id,thread_name,loop)
            else:
                try:
                    self.threaded_details[thread_name]["transferred_size"] += int(file.get('size'))
                    self.threaded_details[thread_name]["num_of_files_transferred"] +=1
                    self.threaded_details[thread_name]["current_file"] = [file.get('name'),int(file.get('size'))]
                except TypeError:
                    pass
                try:
                    # print(f'copying {file.get("name")}')
                    self.threaded_copyFile(file.get('id'), parent_id,thread_name)
                    new_id = parent_id
                    emb = threaded_status_emb(transferred = self.threaded_details[thread_name]["transferred_size"],current_file_name = file.get('name'),current_file_size=int(file.get('size')) ,total_size=self.threaded_details[thread_name]["total_size"],start_time=self.start_time)
                    asyncio.set_event_loop(loop)
                    loop.create_task(self.threaded_details[thread_name]['message'].edit(content="",embed=emb))
                except Exception as err:
                    logger.error(err,exc_info=True)
                    return err
        return new_id
    
    async def threaded_clone(self,messages,link,number_of_threads,loop):
        self.transferred_size = 0
        self.num_of_files_transferred = 0
        self.start_time = time.time()
        try:
            file_id = self.getIdFromUrl(link)
        except (IndexError, KeyError):
            return embed(title="❗ Invalid Google Drive URL",description="Make sure the Google Drive URL is in valid format.")
        try:
            self.size_service = TotalSize(file_id,self.__service)
            total_size,total_files = self.size_service.calc_size_and_files()
            meta = self.__service.files().get(supportsAllDrives=True, fileId=file_id, fields="name,id,mimeType,size").execute()
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                files = self.getFilesByFolderId(file_id)
                dir_id = self.create_directory(meta.get('name'),parent_id=self.__parent_id)
                if len(files) <= 4:
                    number_of_threads = len(files)
                if number_of_threads >10:
                    number_of_threads = 10

                divided_file_ids = list_into_n_parts(files,number_of_threads)

                list_of_threads = []

                for idx,val in enumerate(divided_file_ids):
                    if not len(val) == 0:
                        thread = threading.Thread(name=f"Thread{idx+1}",target=self.threaded_cloneFolder,args=(meta.get('name'), meta.get('name'),val,dir_id,f"Thread{idx+1}",loop))
                        list_of_threads.append(thread)
                        try:
                            thread_total_size = sum([int(file.get('size')) for file in val])
                        except TypeError:
                            thread_total_size = 0
                            for v in val:
                                print(f'calculating size for {v}')
                                size_serve = TotalSize(v.get('id'),self.__service)
                                thread_total_size+= size_serve.calc_size_and_files()[0]
                                print(f'calculated size for {v}')

                        self.threaded_details.update({
                            f"Thread{idx+1}":{
                                "thread":thread,
                                "files":val,
                                "transferred_size":0,
                                "num_of_files_transferred":0,
                                "sa_index":idx,
                                "used_sas": [],
                                "http":None,
                                "current_file":None,
                                "message":messages[idx+1],
                                "total_size":thread_total_size
                            }
                        })
                        # print(f"authorising {idx+1}")
                        self.threaded_details[f"Thread{idx+1}"]['service'] = self.threaded_authorize(f"Thread{idx+1}")
                        # print(f"authorised {idx+1}")
                        # print()
                        overall_used_sas_lst = self.threaded_details['overall_used_sas']
                        # print(overall_used_sas_lst)
                        overall_used_sas_lst.append(idx)
                        self.threaded_details.update({'overall_used_sas':overall_used_sas_lst})
                        # print('going to next')
                
                # pprint.pprint(self.threaded_details)

                for i in list_of_threads:
                    i.start()
                
                for i in list_of_threads:
                    i.join()


                return embed(title="✅ Copied successfully.",description=f"[{meta.get('name')}]({self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}) ---- `{humanbytes(total_size)}`\nTransferred {total_files} of {total_files}\n\n{'#️⃣'*19+'▶️'} 100 % (`{humanbytes(int(total_size/(time.time()-self.start_time)))}/s`)\nElapsed Time: `{humantime(time.time()-self.start_time)}`",url=self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id))
            else:
                file = self.copyFile(meta.get('id'), self.__parent_id)
                self.num_of_files_transferred+=1
                return embed(title="✅ Copied successfully.",description=f"[{file.get('name')}]({self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id'))}) ---- `{humanbytes(int(meta.get('size')))}`\nTransferred {self.num_of_files_transferred} of {total_files}\n\n{'#️⃣'*19+'▶️'} 100 % (`{humanbytes(int(int(meta.get('size'))/(time.time()-self.start_time)))}/s`)\nElapsed Time: `{humantime(time.time()-self.start_time)}`",url=self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get('id')))
        except Exception as err:
            if isinstance(err, RetryError):
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            further_messages = ["If you were trying to clone a private link, try `privclone` command.","I don't think you have access to this folder/file."]
            further_message = further_messages[0] if self.use_sa else further_messages[1]
            return embed(title="Error",description=f"```\n{err}\n```\n{further_message}")

    def threaded_switchSaIndex(self,thread_name):
        all_sas = db.find_sas()
        current_index = self.threaded_details[thread_name]['sa_index']
        if current_index == len(all_sas)-1:
            self.threaded_details[thread_name]['sa_index'] = 0
        self.threaded_details[thread_name]['used_sas'].append(current_index)
        if not current_index in self.threaded_details['overall_used_sas']:
            self.threaded_details['overall_used_sas'].append(current_index)
        sa_index = list({i for i in range(100)}.difference(set(self.threaded_details['overall_used_sas'])))[0]
        self.threaded_details[thread_name]['sa_index']=sa_index

        self.threaded_details[thread_name]['service'] = self.threaded_authorize(thread_name)
        print(f"SWITCHING SA FOR {thread_name} (Old sa: {current_index} :: New sa : {sa_index})")     
        logger.warning(f"SWITCHING SA FOR {thread_name} (Old sa: {current_index} :: New sa : {sa_index})")     


    def threaded_authorize(self,thread_name):
        sa_info = db.find_sa_info_by_id(self.threaded_details[thread_name]["sa_index"])
        sa = {
            "client_email":sa_info["client_email"],
            "token_uri":sa_info["token_uri"],
            "private_key":sa_info["private_key"]
        }
        creds = service_account.Credentials.from_service_account_info(sa,scopes=self.__OAUTH_SCOPE)
        http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())
        self.threaded_details[thread_name]['http'] = http
        return build('drive', 'v3', credentials=creds, cache_discovery=False)

    def switchSaIndex(self):
        all_sas = db.find_sas()
        if self.sa_index == len(all_sas)-1:
            self.sa_index = 0
        print(f"Switching sas from {self.sa_index} to {self.sa_index+1}")
        self.sa_index +=1
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
        return build('drive', 'v3', credentials=creds, cache_discovery=False)


class TotalSize:
    def __init__(self,gdrive_id,service):
        self.link_id = gdrive_id
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__service = service
        self.total_bytes = 0
        self.total_files = 0

    def calc_size_and_files(self):
        drive_file = self.__service.files().get(fileId=self.link_id, fields="id, mimeType, size",
                                                supportsTeamDrives=True).execute()
        if drive_file['mimeType'] == self.__G_DRIVE_DIR_MIME_TYPE:
            self.gDrive_directory(**drive_file)
        else:
            self.gDrive_file(**drive_file)
        return self.total_bytes,self.total_files

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
            self.total_files+=1
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