
import os
import json

uc_setts = os.path.expanduser('~')+"/.uc_dev/settings.json"

def load_settings():
    if not os.path.exists( uc_setts ):
            setts = { "dev_package": "" }
    else:
        try:
            with open(uc_setts, 'r') as json_file:
                setts = json.load(json_file)
                # Now you can access the loaded data, e.g., data['key']
        except FileNotFoundError:
            print(f"The file {json_file_path} was not found.")
        except json.JSONDecodeError as e:
            print(f"Error decoding the JSON file: {e}")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            exit(1)

    

    return setts
    
def save_settings( setts ):
    try:
    # Writing data to the JSON file
        with open(uc_setts, 'w') as json_file:
            json.dump(setts, json_file, indent=2)
    except Exception as e:
        print(f"Error writing to the JSON file: {e}")


def check_settings( ):
    setts = load_settings()
    
    error = False
    
    if not "work_dir" in setts:
        print("Work dir not set. run uc_devel --work_dir")
        error = True
        
    
    if error:
        exit(1)


def set_options ( name, value ):
    
    
    setts = load_settings()
    
    setts[name] = value
    
    save_settings( setts )
    
def get_option( name ):
    
    setts = load_settings()
    
    return setts[name]
    

def get_work_dir():
    return get_option( "work_dir" ) + "/"
    
def get_cache_dir():
    
    return get_option( "work_dir" )+ "/cache/"
    
def get_download_dir():
    
    return get_option( "work_dir" )+ "/cache/downloads/"    

def get_dev_pack_dir():
    
    return get_option( "work_dir" )+ "/cache/dev_packs/"    
    

def select_dev_package():
    
    
    setts = load_settings()
    
    files = sorted( os.listdir(get_dev_pack_dir()) )

    # Filtere nur Dateien (keine Verzeichnisse) und zeige den vollen Pfad an
    file_list = [file for file in files if os.path.isfile(os.path.join(get_dev_pack_dir(), file)) and not file.endswith(".dl") ]


    #print( file_list )
    
    print("")
    print("downloaded dev packages : ")
    print("")

    for i, file_info in enumerate(file_list, start=1):
        
        selected=""
        if setts["dev_package"] == file_info:
            selected="\033[01;32mselected\033[00m"
        
        file_display = file_info[11:-4]
        tmp = file_display.split("-")
        tmp[0] = "\033[01;33m" + tmp[0] + "\033[00m"
        file_display = "-".join(tmp)
        
        print("{0:2d}) {1:<30} {2} ".format( i, file_display, selected ) )

    # Benutzer nach Auswahl fragen
    try:
        selection = int(input("\nPlease choose a file (1-{0}): ".format(len(file_list))))
        selected_file = file_list[selection - 1]
        
        print("\nYou have selected \033[01;32m {0}\033[00m. ".format(selected_file[11:-4]))
        
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a number between 1 and {0}.".format(len(file_list)))
    except Exception as e:
        print(f"Error: {e}")


    setts["dev_package"] = selected_file[11:-4]

    save_settings( setts )

def get_dev_pack_list():
    
     #setts = load_settings()
    
    files = os.listdir(get_dev_pack_dir())

    # Filtere nur Dateien (keine Verzeichnisse) und zeige den vollen Pfad an
    file_list = [file for file in files if os.path.isfile(os.path.join(get_dev_pack_dir(), file)) and not file.endswith(".dl") ]

    file_list = sorted( file_list )
    
    
    build_list = []
    for tmp in file_list:
        
        dev_pack = tmp[11:-4]
        
        #print( dev_pack )
        build_list.append( dev_pack )
        
    return build_list


def get_dev_package_name( ):
        
    setts = load_settings()
    
    if not "dev_package" in setts or setts["dev_package"] == "":
        print("no dev package selected. run uc_devel -s")
        exit(1)
    
    return setts["dev_package"]

def get_dev_package_tar( dev_pack ):
    
    ret = get_dev_pack_dir() + "devel_pack_" + dev_pack + ".tar"
        
    return ret
    

def set_uclibc_repo( path ):
    
    setts = load_settings()
    
    setts["uclibc-ng_repo"] = os.path.abspath( path )
    
    save_settings( setts )

def get_uclibc_repo( ):
    
    setts = load_settings()
    
    if "uclibc-ng_repo" in setts:
        return setts["uclibc-ng_repo"]
        
    return ""
