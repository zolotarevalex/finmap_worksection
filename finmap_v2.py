#!/usr/bin/python3

import requests
import json
import os
import time
import signal
import sys
import hashlib
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(filename='fn_ws.log',
                    format='%(asctime)s - %(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
                    
logging.getLogger().addHandler(RotatingFileHandler(filename='fn_ws.log', maxBytes=100000000, backupCount=10))
 
def signal_handler(sig, frame):
    logging.info('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


class Finmap:
#class members and constants secstion
    apiKey = '7261c28e-aa9a-4a34-b889-6c34ad34a68d4ddb37702177c7838059a2b955b7aee4cd626603'

    baseUrl = 'https://api.finmap.online/'

    HEALTH = 'health'
    PROJECTS = 'project'
    CURRENCIES = 'currencies'
    ACCOUNTS = 'accounts'
    TAGS = 'tags'

    urlDict = {HEALTH:'v2/health',
               CURRENCIES:'v2/currencies',
               ACCOUNTS: 'v2/accounts',
               TAGS: 'v2/tags',
               PROJECTS:'v2/projects'}
    
#class methonds section
    def make_request_url(self, method):
        return self.baseUrl + self.urlDict[method]

    def make_common_header(self):
        return {'accept': 'application/json',
                'apiKey': self.apiKey}

    def get_projects(self):
        projects = []
        status = False
        try:
            request_url = self.make_request_url(self.PROJECTS)
            headers = self.make_common_header()
            
            projects_response = requests.get(url=request_url, headers=headers)

            logging.debug('Finmap:get_projects - \n\trequest_url: %s\n\theaders: %s\n\tresponse: %s',
                          request_url, headers, projects_response)
            
            if (projects_response.status_code == 200):
                status = True
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                for proj in jProjects:
                    projects.append(proj['label'])
        except Exception as e:
            logging.error('Finmap:get_projects - excetpion caught: %s', str(e))
        return set(projects), status
        
    def make_finmap_proj(self, proj):
        logging.info('Finmap:make_finmap_proj - creating: %s project', proj)
        
        status = False
        try:
            request_url = self.make_request_url(self.PROJECTS)
            headers = self.make_common_header()
            headers['Content-Type'] = 'application/json'
            data = json.dumps({'label': proj})
            
            projects_response = requests.post(url=request_url, headers=headers, data=data)
            
            logging.debug('Finmap:get_projects - \n\trequest_url: %s\n\theaders: %s\n\tdata: %s\n\tresponse: %s',
                           request_url, headers, data, projects_response)
                        
            status = projects_response.status_code == 201
        except Exception as e:
            logging.error('Finmap:make_finmap_proj - excetpion caught: %s', str(e))
        return status
    
    

class DirCreator:
#class members and constants secstion
    #PROJ_BASE_DIR = 'projects'
    PROJ_BASE_DIR = ''

#class methonds sectio
    def make_proj_dir_path(self, project):
        return os.path.join(self.PROJ_BASE_DIR, project)

    def make_project_dir(self, proj_name):
        proj_dir = self.make_proj_dir_path(proj_name)
        if os.path.exists(proj_dir):
            if not os.path.isdir(proj_dir):
                logging.error('DirCreator:make_project_dir - %s already exists, but not a directory', proj_dir)
        else:
            logging.info('DirCreator:make_project_dir - creating %s dir', proj_dir)
            os.makedirs(proj_dir)
            if (os.path.exists(proj_dir)):
                logging.info('DirCreator:make_project_dir - %s dir CREATED!!!', proj_dir)
            else:
                logging.info('DirCreator:make_project_dir - %s dir creation FAILED!!!', proj_dir)

    def get_project_dirs(self):
        return set(os.listdir(self.PROJ_BASE_DIR) if os.path.exists(self.PROJ_BASE_DIR) else [])
    
    
class Worksection:
#class members and constants
    apiKey = '6e1421001d7d3fd001bdefd10c39390a'
    domain = 'https://artsolution.worksection.com'
    apiUrl = '/api/admin/v2/?action='
    GET_PROJECTS = 'get_projects'
    POST_PROJECTS = 'post_project'
    
#class methods

    def make_md5(self, action, page = ''):
        return hashlib.md5((page + action + self.apiKey).encode('utf-8')).hexdigest()    
    
    def make_request_url(self, action, page = ''):
        return self.domain + self.apiUrl + action + '&hash=' + self.make_md5(action, page)
        
    def make_common_header(self):
        return {'accept': 'application/json',
                'Content-Type' : 'application/json'}
        
    def get_projects(self):
        projects = []
        status = False
        try:
            request_url = self.make_request_url(self.GET_PROJECTS)
            headers = self.make_common_header()
            
            projects_response = requests.get(url = request_url, headers=headers)
            
            logging.debug('Worksection:get_projects - \n\trequest_url: %s\n\theaders: %s\n\tprojects_response: %s', request_url, headers, projects_response)
            
            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                if jProjects['status'] == 'ok':
                    status = True
                    for proj in jProjects['data']:
                        projects.append(proj['name'])
        except Exception as e:
            logging.error('Worksection:get_projects - excetpion caught: %s', str(e))
        return set(projects), status
        
    def make_worksection_proj(self, proj):
        status = False
        try:
            request_url = self.make_request_url(self.POST_PROJECTS)
            
            projects_response = requests.get(url=request_url)
    
            logging.debug('Worksection:make_worksection_proj - \n\trequest_url: %s\n\tprojects_response: %s', request_url, projects_response)

            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                status = jProjects['status'] == 'ok'
        except Exception as e:
            logging.error('Worksection:make_worksection_proj - excetpion caught: %s', str(e))
        return status
    

def run():
    finmap = Finmap() 
    dir_creator = DirCreator() 
    worksection = Worksection()
    
    fm_initial_set = set()
    dir_initial_set = set()
    ws_initial_set = set()
    
    while True:
        ws_projects, ws_status = worksection.get_projects()
        fm_projects, fn_status  = finmap.get_projects()
        dirs = dir_creator.get_project_dirs()

        logging.debug('run - \n\tws_projects: %s\n\tfm_projects: %s\n\tdirs: %s', ws_projects, fm_projects, dirs)
        
        if len(ws_initial_set) == 0 and ws_status == True:
            ws_initial_set = ws_projects
           
        if len(fm_initial_set) == 0 and fn_status == True:
            fm_initial_set = fm_projects
            
        if len(dir_initial_set) == 0:
            dir_initial_set = dirs
         
        logging.debug('run - \n\tfm_initial_set: %s\n\tws_initial_set: %s\n\tdir_initial_set: %s', fm_initial_set, ws_initial_set, dir_initial_set)
            
            
        initial_set = ws_initial_set.union(fm_initial_set).union(dir_initial_set)
        base_set = ws_projects.union(dirs).union(fm_projects)
        update_set = base_set - initial_set
        
        logging.debug('run - \n\tinitial_set: %s\n\tbase_set: %s\n\tupdate_set: %s', initial_set, base_set, update_set)
        
        
        dirs_to_create = update_set - dirs
        fm_to_create = update_set - fm_projects
        ws_to_create = update_set - ws_projects

        logging.debug('run - \n\tdirs_to_create: %s\n\tfm_to_create: %s\n\tws_to_create: %s', dirs_to_create, fm_to_create, ws_to_create)
        
        for proj in dirs_to_create:
            dir_creator.make_project_dir(proj)
            
        for proj in fm_to_create:
            if finmap.make_finmap_proj(proj):
                logging.info('run - %s finmap project CREATED!!!', proj)
                
        for proj in ws_to_create:
            if worksection.make_worksection_proj(proj):
                logging.info('run - %s worksection project CREATED!!!', proj)
                
        
        time.sleep(1)
        
if __name__ == '__main__':
    logging.info('lights on')
    run()
    logging.info('lights off')


