
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
        
def download_dev_package( sel=None ):

    #print("download")

    uc_download = options.get_dev_pack_dir()
        
    if not os.path.exists( uc_download ):
        os.makedirs( uc_download )
            
    url="https://uclibc-ng.tangotanzen.de/index.php?op=listdev_packages"
    
    file_list = get_file_list_with_timestamp( url )
    #pprint( file_list )    
    
    file_list.sort(key=lambda x: x['filename'], reverse=False)

    print("Available Dev Packages")
    for i, file_info in enumerate(file_list, start=1):
        #timestamp_str = datetime.utcfromtimestamp(file_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        #print("{0:2d}) {1}".format( i, file_info['filename'].replace("devel_pack_","").replace(".tar","") ) )
        status = ""
        if os.path.exists( uc_download + file_info['filename'] ):
            status = "\033[01;32mdownloaded\033[00m"
            
            timestamp = os.path.getmtime( uc_download + file_info['filename'] )
            if not timestamp == file_info['timestamp']:
                status = "\033[01;33mupdate avaible\033[00m"
            
            
            #exit(1)
        
        file_display = file_info['filename'][11:-4]
        tmp = file_display.split("-")
        tmp[0] = "\033[01;33m" + tmp[0] + "\033[00m"
        file_display = "-".join(tmp)
        
        size = file_info['size'] / 1024 / 1024
        size = "{0:.1f}".format(size).rjust(6)
        
        
        print("{0:2d}) {1:<70} {2}  MB  {3}".format( i, file_display , size, status ) )


    del file_info
    
    # Auswahl: non-interaktiv via sel (NAME-Substring / Index / "all"), sonst interaktiv
    try:
        if sel is None:
            selection = input("\nPlease choose a file (1-{0}) or a == all: ".format(len(file_list)))
        else:
            selection = str( sel )

        selected_files = []

        if selection in ("a", "all"):
            selected_files = list( file_list )
        elif selection.isdigit():
            selected_files.append( file_list[ int(selection) - 1] )
        else:
            # Substring-Match auf dem Paketnamen (z.B. "alpha", "i686")
            selected_files = [ f for f in file_list if selection in f['filename'] ]
            if not selected_files:
                print("no dev package matches '{0}'".format(selection))
                return

        for sf in selected_files:
            print("\nselected \033[01;32m{0}\033[00m. downloading...".format(sf['filename'][11:-4]))

        
        for selected_file in selected_files:
            
            if os.path.exists( uc_download + selected_file['filename'] ):
                timestamp = os.path.getmtime( uc_download + selected_file['filename'] )
            
                if timestamp == selected_file['timestamp']:
                    print(selected_file['filename'] + " already downloaded and up to date")
                    continue
        
            file_url = 'https://uclibc-ng.tangotanzen.de/uploads/' + selected_file['filename']
            
            download_with_progress(file_url, uc_download + selected_file['filename'])
            
            os.utime(  uc_download + selected_file['filename'], ( selected_file['timestamp'], selected_file['timestamp'] ) )

        
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a number between 1 and {0}.".format(len(file_list)))
        
    except Exception as e:
        print(f"Error while downloading the file: {e}")




def update_downloaded_dev_packages():
    """Holt neue Fassungen der bereits heruntergeladenen Packs.

    Nur die vorhandenen -- "alle" waeren ~50 Packs a ~150 MB.  Erkannt wird ein
    Update wie in der Liste: die mtime der lokalen .tar wird beim Download auf
    den Server-Zeitstempel gesetzt, weicht sie ab, gibt es eine neue Fassung.
    """
    uc_download = options.get_dev_pack_dir()

    if not os.path.exists( uc_download ):
        print("no dev packages downloaded yet")
        return

    try:
        file_list = get_file_list_with_timestamp("https://uclibc-ng.tangotanzen.de/index.php?op=listdev_packages")
    except Exception as e:
        print(f"could not fetch the dev package list: {e}")
        return

    outdated = []
    for file_info in file_list:
        local = uc_download + file_info['filename']
        if os.path.exists( local ) and os.path.getmtime( local ) != file_info['timestamp']:
            outdated.append( file_info )

    if not outdated:
        print("all downloaded dev packages are up to date")
        return

    total = sum( f['size'] for f in outdated )
    print("updating {0} dev package(s), {1:.1f} GB".format( len( outdated ), total / 1024 / 1024 / 1024 ))

    done = 0
    for i, file_info in enumerate( outdated, start=1 ):
        print("\n[{0}/{1}] \033[01;32m{2}\033[00m  ({3:.0f} MB, {4:.1f} of {5:.1f} GB done)".format(
            i, len( outdated ), file_info['filename'][11:-4],
            file_info['size'] / 1024 / 1024,
            done / 1024 / 1024 / 1024, total / 1024 / 1024 / 1024 ))
        download_with_progress('https://uclibc-ng.tangotanzen.de/uploads/' + file_info['filename'],
                               uc_download + file_info['filename'])
        os.utime( uc_download + file_info['filename'],
                  ( file_info['timestamp'], file_info['timestamp'] ) )
        done += file_info['size']


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

    # Older dev packs were built from CRLF-tainted .config files and the
    # CR survived into infos.json as a trailing '\r' on every value
    # (e.g. UCLIBC_FORMAT_FLAT="y\r"). Strip trailing whitespace so
    # downstream equality checks like infos["UCLIBC_FORMAT_FLAT"] == "y"
    # work regardless of which packer produced the dev pack.
    for k, v in list(json_info.items()):
        if isinstance(v, str):
            json_info[k] = v.rstrip()

    return json_info


def write_dev_pack_file( tar_name, out_name, dev_pack ):
    
    #print( "get : " + tar_name )
    data = get_dev_file_content( tar_name, dev_pack )
    
    with open( out_name, "wb" ) as f:
        f.write( data )
