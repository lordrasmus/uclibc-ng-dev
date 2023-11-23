
import os
import re
import json
import requests

try:
    from tqdm import tqdm
except:
    print("install tqdm with: pip3 install tqdm")
    exit(1)

from pprint import pprint


import urllib.request
from html.parser import HTMLParser
from datetime import datetime



def get_file_list_with_timestamp(url):
    
        
    try:
        response = urllib.request.urlopen(url)
        html_content = response.read().decode('utf-8')

        #print( html_content )
        file_list_with_timestamp = json.loads(html_content)
        

        return file_list_with_timestamp

    except Exception as e:
        print(f"Fehler beim Abrufen der Dateiliste: {e}")
        return []



class TqdmUpTo(tqdm):
    
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        return self.update(b * bsize - self.n)  # also sets self.n = b * bsize


def download_with_progress(url, destination):
    
    destination_tmp = destination+".dl"
    with TqdmUpTo(unit='B', unit_scale=True, unit_divisor=1024, miniters=1, desc=os.path.basename(destination)) as t:  # all optional kwargs
        urllib.request.urlretrieve( url, filename=destination_tmp, reporthook=t.update_to, data=None)
        t.total = t.n
    os.rename( destination_tmp, destination )
        
def download_dev_package():
    
    #print("download")

    uc_cache = os.path.expanduser('~')+"/.uc_dev/downloads/"
        
    if not os.path.exists( uc_cache ):
        os.mkdir( uc_cache )
            
    url="https://uclibc-ng.tangotanzen.de/index.php?op=listdev_packages"
    
    file_list = get_file_list_with_timestamp( url )
    #pprint( file_list )    
    
    file_list.sort(key=lambda x: x['filename'], reverse=False)

    print("Available Dev Packages")
    for i, file_info in enumerate(file_list, start=1):
        #timestamp_str = datetime.utcfromtimestamp(file_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        #print("{0:2d}) {1}".format( i, file_info['filename'].replace("devel_pack_","").replace(".tar","") ) )
        status = ""
        if os.path.exists( uc_cache + file_info['filename'] ):
            status = "\033[01;32mdownloaded\033[00m"
            
            timestamp = os.path.getmtime( uc_cache + file_info['filename'] )
            if not timestamp == file_info['timestamp']:
                status = "\033[01;33mupdate avaible\033[00m"
            
            
            #exit(1)
        
        print("{0:2d}) {1:<30} {2}".format( i, file_info['filename'][11:-4], status ) )

    # Benutzer nach Auswahl fragen
    try:
        selection = int(input("\nPlease choose a file (1-{0}): ".format(len(file_list))))
        selected_file = file_list[selection - 1]
        
        file_url = 'https://uclibc-ng.tangotanzen.de/uploads/' + selected_file['filename']

        
        print("\nYou have selected \033[01;32m {0}\033[00m. The file is being downloaded...".format(selected_file['filename'][11:-4]))

        # Hier kannst du die Datei herunterladen (z.B., mit urllib)
        download_with_progress(file_url, uc_cache + selected_file['filename'])
        
        os.utime(  uc_cache + selected_file['filename'], ( selected_file['timestamp'], selected_file['timestamp'] ) )

        
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a number between 1 and {0}.".format(len(file_list)))
    except Exception as e:
        print(f"Error while downloading the file: {e}")
