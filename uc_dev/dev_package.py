
import os
import re
import json
import requests
import tarfile

try:
    from tqdm import tqdm
except:
    print("install tqdm with: pip3 install tqdm")
    exit(1)

from pprint import pprint


import urllib.request
from html.parser import HTMLParser
from datetime import datetime


from uc_dev import options

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




def list_dev_file_content( dev_pack ):

    try:
        dev_tar = options.get_dev_package_tar( dev_pack )
        #print( dev_tar )
        
        with tarfile.open( dev_tar , 'r') as tar:
            # List the files in the TAR archive
            file_list = tar.getnames()

            print("Files in the TAR archive {0}:".format( dev_tar ))
            for file in file_list:
                print(file)
            
             
    except FileNotFoundError:
        print("The file {0} was not found.".format( options.get_dev_package_tar() ))
    except tarfile.TarError as e:
        print(f"Error processing the TAR archive: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
def get_dev_file_content( name, dev_pack ):
    #print( dev_pack )
    try:
        dev_tar = options.get_dev_package_tar( dev_pack )
        #print( name )
        #print( dev_tar )
        with tarfile.open( dev_tar , 'r') as tar:
            # List the files in the TAR archive
            file_list = tar.getnames()

            #print("Files in the TAR archive {0}:".format( options.get_dev_package_tar() ))
            #for file in file_list:
            #    print(file)
            
            
            tar_name = "devel_pack_" + dev_pack + "/" + name
            
            return tar.extractfile(tar_name).read()
             
    except FileNotFoundError:
        print("The file {0} was not found.".format( options.get_dev_package_tar( dev_pack ) ))
    except tarfile.TarError as e:
        print(f"Error processing the TAR archive: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    

def get_dev_infos( dev_pack ):
    
    infos = get_dev_file_content( "infos.json" , dev_pack )
    
    json_info = json.loads( infos )
    
    return json_info


def write_dev_pack_file( tar_name, out_name, dev_pack ):
    
    #print( "get : " + tar_name )
    data = get_dev_file_content( tar_name, dev_pack )
    
    with open( out_name, "wb" ) as f:
        f.write( data )
