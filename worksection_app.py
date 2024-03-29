#!/usr/bin/python3

from enum import Enum
import requests
import json
import os
import time
import signal
import sys
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

logging.basicConfig(filename='fm_ws.log',
                    format='%(asctime)s - %(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)
                    
logging.getLogger().addHandler(RotatingFileHandler(filename='fm_ws.log', maxBytes=100000000, backupCount=10))
 
def signal_handler(sig, frame):
    logging.info('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class Worksection:
#class members and constants
    apiKey = 'e84ff16c6e847d2bd3a9a78db313c384'
    domain = 'https://tes4058.worksection.com'
    apiUrl = '/api/admin/v2/?action='
    GET_PROJECTS = 'get_projects'
    POST_PROJECTS = 'post_project'
    POST_TASK = 'post_task'
    
#class methods

    def make_md5(self, action, page = ''):
        return hashlib.md5((page + action + self.apiKey).encode('utf-8')).hexdigest()    
    
    def make_common_request_url(self, action, page = ''):
        return self.domain + self.apiUrl + action + f'&page={page}' +f'&hash={self.make_md5(action, page)}'
    
    def make_get_request_url(self, action, page = ''):
        return self.make_common_request_url(action, page)
        
    def make_post_request_url(self, action, title, page = ''):
        return self.make_common_request_url(action, page) + "&" + urlencode({'title' : title})
        
    def make_common_header(self):
        return {'accept': 'application/json',
                'Content-Type' : 'application/json'}
        
    def get_projects(self):
        projects = []
        status = False
        try:
            request_url = self.make_get_request_url(self.GET_PROJECTS) + '&status=active'
            headers = self.make_common_header()
            
            projects_response = requests.get(url = request_url, headers=headers)
            
            logging.debug('Worksection:get_projects - \n\trequest_url: %s\n\theaders: %s\n\tprojects_response: %s', request_url, headers, projects_response)
            
            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                # print(jProjects)
                if jProjects['status'] == 'ok':
                    status = True
                    for proj in jProjects['data']:
                        projects.append(proj['name'])
        except Exception as e:
            logging.error('Worksection:get_projects - excetpion caught: %s', str(e))
        return set(projects), status
        
    def make_worksection_proj(self, proj, user_from, user_to, manager):
        status = False
        proj_id = 0
        try:
            url_params = {
              'email_user_from' : user_from,
              'email_user_to' : user_to,
              'email_manager' : manager
            }

            request_url = self.make_post_request_url(self.POST_PROJECTS, proj) + "&" + urlencode(url_params)

            projects_response = requests.get(url=request_url)
    
            logging.debug('Worksection:make_worksection_proj - \n\trequest_url: %s\n\tprojects_response: %s', request_url, projects_response)

            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                status = jProjects['status'] == 'ok'
                proj_id = int(jProjects['data']['id'])
                logging.debug('Worksection:make_worksection_proj - \n\tresponse JSON:%s', jProjects)
        except Exception as e:
            logging.error('Worksection:make_worksection_proj - excetpion caught: %s', str(e))
        return status, proj_id
    
    def make_worksection_proj_with_default_task(self, proj, sub_tasks_dict, user_from, user_to, manager):
      tokens = proj.split('.')
      if len(tokens) == 0:
        print('ivalid project name: %s', proj)
        return False
      
      task_id = 0

      try:
        task_id = int(tokens[0])
      except Exception as e:
          logging.error('Worksection:make_worksection_proj_with_default_task - excetpion caught: %s', str(e))
          return False
      
      status, proj_id = self.make_worksection_proj(proj, user_from, user_to, manager)
      if status == False:
        return False

      task_name = f'{task_id} (створити фінмап на ПРОЕКТ)'

      subtasks_to_skip = ['СТАТУС', 'ДАТА ОТРИМАННЯ ЗАВДАННЯ']

      try:  
        url_param = {
          'email_user_from' : user_from
        }
        
        url_params = "&" + urlencode(url_param)

        for key, val in sub_tasks_dict.items():
          if len(val) == 0:
            print('need to skip %s - %s', key, val)
            continue
          if key in subtasks_to_skip:
             continue
          
          print(f'need to kreate subtask {key}')
          
          todo_item = {'todo[]': f'{key}-{val}'}
          url_params = url_params + "&" + urlencode(todo_item)

        request_url = self.make_post_request_url(self.POST_TASK, task_name, page=f'/project/{proj_id}/') + url_params

        task_response = requests.get(url=request_url)

        logging.debug('Worksection:make_worksection_proj_with_default_task - \n\trequest_url: %s\n\tprojects_response: %s', request_url, task_response)

        if task_response.status_code == 200:
          jTask = json.loads(task_response._content.decode('utf8').replace("'", '"'))
          status = jTask['status'] == 'ok'
          logging.debug('Worksection:make_worksection_proj_with_default_task - \n\tresponse JSON:%s', jTask)
      except Exception as e:
          logging.error('Worksection:make_worksection_proj_with_default_task - excetpion caught: %s', str(e))
      return status
      
    def get_initial_data(self):
        while True:
            ws_projects, ws_status = self.get_projects()
            if ws_status == True:
                return ws_projects

class DirCreator:
#class members and constants secstion
    #PROJ_BASE_DIR = 'projects'
    PROJ_BASE_DIR = '.'
    PROJ_STRUCTURE = ['МЧ', 'Проект', 'КД', 'Фото']

#class methonds sectio
    def __init__(self, base_dir = '.'):
        # os.chdir('..')
        self.PROJ_BASE_DIR = base_dir
    
    def make_dir_path(self, base_dir, sub_dir):
        return os.path.join(base_dir, sub_dir) if type(sub_dir) == type(str()) else os.path.join(base_dir, *sub_dir)

    def make_dir(self, base_dir, sub_dir):
        result = True
        
        new_dir = self.make_dir_path(base_dir, sub_dir)
        if os.path.exists(new_dir):
            if not os.path.isdir(new_dir):
                logging.error('DirCreator:make_dir - %s already exists, but not a directory', new_dir)
                result = False
        else:
            logging.info('DirCreator:make_dir - creating %s dir', new_dir)
            os.makedirs(new_dir)
            if (os.path.exists(new_dir)):
                logging.info('DirCreator:make_dir - %s dir CREATED!!!', new_dir)
            else:
                logging.info('DirCreator:make_dir - %s dir creation FAILED!!!', new_dir)
                result = False
        return result, new_dir

    def make_project_dir(self, proj_name, sub_dirs = []):
        result, proj_dir = self.make_dir(self.PROJ_BASE_DIR, proj_name)
        if result == True:
            for sub_dir in sub_dirs:
                result,_ = self.make_dir(proj_dir, sub_dir)
                if result == False:
                    break              
        return result
		
    def make_project_dir_with_default_structure(self, proj_name):
        return self.make_project_dir(proj_name, self.PROJ_STRUCTURE)
        
    def get_project_dirs(self, base_dir=''):
        dir_content = []
        try:
            dir_content = os.listdir(self.PROJ_BASE_DIR if len(base_dir) == 0 else base_dir) if os.path.exists(self.PROJ_BASE_DIR) else []
        except Exception as e:
            logging.error('DirCreator:get_project_dirs - excetpion caught: %s', str(e))
        
        return set([dir for dir in dir_content if os.path.isdir(dir)])
    
class SpreadsheetHelper:
  IDX = Enum('IDX', ['PROJ_IDX',
                     'DATE_IDX',
                     'CLIENT_ID_IDX',
                     'CLIENT_NAME_IDX',
                     'DESCRIPTION_IDX',
                     'AMOUNT_IDX',
                     'ADVANCE_IDX',
                     'SOURCE_IDX',
                     'ESTIMATION_IDX',
                     'ASSEMBLY_PRICE_IDX',
                     'DESIGN_PRICE_IDX',
                     'ESTIMATED_COST_IDX',
                     'TASK_LINK_IDX',
                     'ANNEX_IDX'], start = 0)
  
  SPREADSHEET_ID = '166T5m2MVE5PVAc94Zncdn2uTJg6nbcrKfCu4eL1Gl3o'
  SHEET_NAME = 'ОБЄКТИ'
  RANGE_START = ''
  RANGE_END = ''

  def __init__(self, range_start, range_end):
    self.RANGE_START = range_start
    self.RANGE_END = range_end

  def get_creds(self):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
      creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
      else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
      # Save the credentials for the next run
      with open("token.json", "w") as token:
        token.write(creds.to_json())
    return creds 

  def get_service(self, creds):
    if creds != None:
      try:
        return build("sheets", "v4", credentials=creds)
      except HttpError as error:
        print(f"An error occurred: {error}")
    return None

  def make_range(self, range_id_start, range_id_end):
    return f'{self.SHEET_NAME}!{self.RANGE_START}{range_id_start}:{self.RANGE_END }{range_id_end}'

  def get_values(self, range_name):
    print(f'range name: {range_name}')
    try:
      service = self.get_service(self.get_creds())
      if service != None:
        return service.spreadsheets().values().get(spreadsheetId=self.SPREADSHEET_ID, range=range_name).execute()
    except HttpError as error:
      print(f"An error occurred: {error}")
    return None

  def get_columns(self):
      result = self.get_values(self.make_range(1, 1))
      if result != None:
         values = result['values']
         if len(values) > 0:
            return values[0]
      return None
  
  def get_row_number(self):
    try:
      service = self.get_service(self.get_creds())
      if service != None:
        properties = 'sheets/properties/gridProperties'
        ss_data = service.spreadsheets().get(spreadsheetId=self.SPREADSHEET_ID, fields=properties, ranges=f'{self.SHEET_NAME}').execute()
        print(ss_data)
        return ss_data['sheets'][0]['properties']['gridProperties']['rowCount']
    except HttpError as error:
      print(f"An error occurred: {error}")
    return 0
  
  def get_projects(self):
    columns = self.get_columns()
    rows_count = self.get_row_number()
    print(f'received {rows_count} rows')

    projects = {}
    project_names = set()

    range_id_start = 2
    range_id_end = rows_count
    if columns != None and rows_count > 0:
      result = self.get_values(self.make_range(range_id_start, range_id_end))
      
      if result == None:
        pass
      
      rows = result.get("values", [])
      if len(rows) == 0:
        pass

      for row in rows:
        if len(row) == 0:
           continue
        
        proj_name = row[self.IDX['PROJ_IDX'].value]
        if len(proj_name) == 0:
           continue
        
        project = {}
        for idx in range(0, len(row)):
          project[columns[idx]] = row[idx]
        projects[proj_name] = project
        project_names.add(proj_name)

    return projects, project_names
  
  def get_init_data(self):
     _, proj_names = self.get_projects()
     return proj_names

if __name__ == "__main__":
  ssHelper = SpreadsheetHelper('C', 'R')
  ws = Worksection()
  dirCreator = DirCreator('test_dir')

  ws_set = ws.get_initial_data()
  dir_init_set = dirCreator.get_project_dirs()
  ss_projects = ssHelper.get_init_data()

  init_data = ws_set.union(dir_init_set).union(ss_projects)

  print(init_data)

  while True:
    projects, names = ssHelper.get_projects()
    ws_projects, ws_status = ws.get_projects()
    if ws_status != True:
      print('not able to get WS projects')
      continue

    for proj in names:
      if proj in init_data:
         continue
      if proj not in ws_projects:
          print(f'creating {proj} project')
          ws.make_worksection_proj_with_default_task(proj, projects[proj], 'shurik.mindless86@gmail.com', 'shurik.mindless86@gmail.com', 'shurik.mindless86@gmail.com')
      dirs = dirCreator.get_project_dirs()
      if proj not in dirs:
         dirCreator.make_project_dir_with_default_structure(proj)
    time.sleep(10)
  
  
  
  
  
  
