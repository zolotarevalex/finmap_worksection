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

print(IDX['PROJ_IDX'].value)

logging.basicConfig(filename='fm_ws.log',
                    format='%(asctime)s - %(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)
                    
logging.getLogger().addHandler(RotatingFileHandler(filename='fm_ws.log', maxBytes=100000000, backupCount=10))
 
def signal_handler(sig, frame):
    logging.info('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


BASE_URL = 'https://docs.google.com/spreadsheets/d'
SPREADSHEET_ID = '1fdZnAslBu1XSgBoQX3h1T5F3NS_Ss8ykrrD5r4nbFYE'
SHEET_ID = 0

class Worksection:
#class members and constants
    apiKey = 'e84ff16c6e847d2bd3a9a78db313c384'
    domain = 'https://tes4058.worksection.com'
    apiUrl = '/api/admin/v2/?action='
    GET_PROJECTS = 'get_projects'
    POST_PROJECTS = 'post_project'
    
#class methods

    def make_md5(self, action, page = ''):
        return hashlib.md5((page + action + self.apiKey).encode('utf-8')).hexdigest()    
    
    def make_common_request_url(self, action, page = ''):
        return self.domain + self.apiUrl + action + '&hash=' + self.make_md5(action, page)
    
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
                logging.debug('Worksection:make_worksection_proj - \n\tresponse JSON:%s', jProjects)
        except Exception as e:
            logging.error('Worksection:make_worksection_proj - excetpion caught: %s', str(e))
        return status
        
    def get_initial_data(self):
        while True:
            ws_projects, ws_status = self.get_projects()
            if ws_status == True:
                return ws_projects

    
def get_creds():
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
    

def get_service(creds):
  if creds != None:
    try:
      return build("sheets", "v4", credentials=creds)
    except HttpError as error:
      return None
    
def get_values(spreadsheet_id, range_name):
  try:
    service = get_service(get_creds())
    return service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def get_columns(spreadsheet_id, range_start, range_end):
    return get_values(spreadsheet_id, f'{range_start}1:{range_end}1')['values'][0]

def get_projects(spreadsheet_id, range_start, range_end):
  columns = get_columns(SPREADSHEET_ID, range_start, range_end)
  projects = {}
  project_names = set()

  range_id = 2
  while columns != None:
    result = get_values(SPREADSHEET_ID, f'{range_start}{range_id}:{range_end}{range_id}')
    
    if result == None:
       break
    
    rows = result.get("values", [])
    if len(rows) == 0:
      break
    row = rows[0]
    project = {}
    for idx in range(1, len(row)):
      project[columns[idx]] = row[idx]
    proj_name = row[IDX['PROJ_IDX'].value]
    projects[proj_name] = project
    project_names.add(proj_name)
    range_id = range_id + 1

  return projects, project_names

if __name__ == "__main__":
  ws = Worksection()
  while True:
    projects, names = get_projects(SPREADSHEET_ID, 'A', 'N')
    ws_projects, ws_status = ws.get_projects()
    if ws_status != True:
      print('not able to get WS projects')
      continue

    print(ws_projects)  

    for proj in names:
      if proj not in ws_projects:
          print(f'creating {proj} project')
          ws.make_worksection_proj(proj, 'shurik.mindless86@gmail.com', 'shurik.mindless86@gmail.com', 'shurik.mindless86@gmail.com')
    time.sleep(1)
  
  
  
  
  
  
