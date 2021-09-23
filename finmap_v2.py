#!/usr/bin/python3

import requests
import json
import os
import time
import signal
import sys

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
        try:
            projects_response = requests.get(self.make_request_url(self.PROJECTS), headers=self.make_common_header())
            if (projects_response.status_code == 200):
                jProjects = json.loads(projects_response._content.decode('utf8').replace("'", '"'))
                for proj in jProjects:
                    projects.append(proj['label'])
        except:
            print('failed to get list of finmap projects')
        return projects
        
    def make_finmap_proj(self, proj):
        headers = self.make_common_header()
        headers['Content-Type'] = 'application/json'
        print('creating ', proj, ' project')
        try:
            ret = requests.post(self.make_request_url(self.PROJECTS), headers=headers, data=json.dumps({'label': proj}))
            if ret.status_code == 201:
                print('CREATED!!!')
            else:
                print('FAILED!!!')
        except:
            print('FAILED!!!, no internet connection')
    
    

class DirCreator:
#class members and constants secstion
    PROJ_BASE_DIR = 'projects'

##class methonds sectio
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
        return os.listdir(self.PROJ_BASE_DIR) if os.path.exists(self.PROJ_BASE_DIR) else []
    

def run():
    finmap = Finmap() 
    dir_creator = DirCreator() 
    while True:
        dirs = dir_creator.get_project_dirs()
        projects = finmap.get_projects()
        
        finmap_2_dirs = set(projects) - set(dirs)
        dirs_2_finmap = set(dirs) - set(projects)
        
        for proj in finmap_2_dirs:
            dir_creator.make_project_dir(proj)
            
        for proj in dirs_2_finmap:
            finmap.make_finmap_proj(proj)
        time.sleep(1)
        
if __name__ == '__main__':
    run()


