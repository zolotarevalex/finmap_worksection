#!/usr/bin/python3

import requests
import json
import os
import time
import signal
import sys
import hashlib

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


class Finmap:
#class members and constants secstion
    apiKey = 'f06f1870-6df2-46ee-af8d-411c9cfb8bc3429584e216a8e5354b71f7b1ae2afcf13d08259c'

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
            projects_response = requests.get(self.make_request_url(self.PROJECTS), headers=self.make_common_header())
            if (projects_response.status_code == 200):
                status = True
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                for proj in jProjects:
                    projects.append(proj['label'])
        except Exception as e:
            print('excetpion caught: ', str(e))
        return set(projects), status
        
    def make_finmap_proj(self, proj):
        status = False
        headers = self.make_common_header()
        headers['Content-Type'] = 'application/json'
        print('creating ', proj, ' project')
        try:
            ret = requests.post(self.make_request_url(self.PROJECTS), headers=headers, data=json.dumps({'label': proj}))
            status = ret.status_code == 201
        except Exception as e:
            print('excetpion caught: ', str(e))
        return status
    
    

class DirCreator:
#class members and constants secstion
    PROJ_BASE_DIR = 'projects'

#class methonds sectio
    def make_proj_dir_path(self, project):
        return os.path.join(self.PROJ_BASE_DIR, project)

    def make_project_dir(self, proj_name):
        proj_dir = self.make_proj_dir_path(proj_name)
        if os.path.exists(proj_dir):
            if not os.path.isdir(proj_dir):
                print(proj_dir, ' already exists, but not a directory')
        else:
            print('creating ', proj_dir, 'dir')
            os.makedirs(proj_dir)
            if (os.path.exists(proj_dir)):
                print('CREATED!!!')
            else:
                print('FAILED!!!')

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
            projects_response = requests.get(self.make_request_url(self.GET_PROJECTS),
                                             headers=self.make_common_header())
            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                if jProjects['status'] == 'ok':
                    status = True
                    for proj in jProjects['data']:
                        projects.append(proj['name'])
        except Exception as e:
            print('excetpion caught: ', str(e))
        return set(projects), status
        
    def make_worksection_proj(self, proj):
        status = False
        try:
            projects_response = requests.get(self.make_request_url(self.POST_PROJECTS))
            if projects_response.status_code == 200:
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                status = jProjects['status'] == 'ok'
        except Exception as e:
            print('excetpion caught: ', str(e))
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
        
        #print(len(ws_projects))
        
        if len(ws_initial_set) == 0 and ws_status == True:
            ws_initial_set = ws_projects
           
        if len(fm_initial_set) == 0 and fn_status == True:
            fm_initial_set = fm_projects
            
        if len(dir_initial_set) == 0:
            dir_initial_set = dirs
            
        initial_set = ws_initial_set.union(fm_initial_set).union(dir_initial_set)
        base_set = ws_projects.union(dirs).union(fm_projects)
        update_set = base_set - initial_set
        
        dirs_to_create = update_set - dirs
        fm_to_create = update_set - fm_projects
        ws_to_create = update_set - ws_projects
        
        for proj in dirs_to_create:
            dir_creator.make_project_dir(proj)
            
        for proj in fm_to_create:
            if finmap.make_finmap_proj(proj):
                print('CREATED!!!')
                
#        for proj in ws_to_create:
#            if worksection.make_worksection_proj(proj):
#                print('CREATED!!!')
        
        time.sleep(1)
        
if __name__ == '__main__':
    run()


