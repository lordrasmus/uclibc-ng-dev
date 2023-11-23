
import os
import json

uc_setts = os.path.expanduser('~')+"/.uc_dev/settings.json"
uc_cache = os.path.expanduser('~')+"/.uc_dev/downloads/"

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
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    return setts
    
def save_settings( setts ):
    try:
    # Writing data to the JSON file
        with open(uc_setts, 'w') as json_file:
            json.dump(setts, json_file, indent=2)
    except Exception as e:
        print(f"Error writing to the JSON file: {e}")

def get_dev_package_name():
    
    setts = load_settings()
    
    return setts["dev_package"][11:-4]

def get_dev_package_tar():
    
    setts = load_settings()
    
    return uc_cache + setts["dev_package"]
  

def select_dev_package():
    
    
    setts = load_settings()
    
    files = os.listdir(uc_cache)

    # Filtere nur Dateien (keine Verzeichnisse) und zeige den vollen Pfad an
    file_list = [file for file in files if os.path.isfile(os.path.join(uc_cache, file)) and not file.endswith(".dl") ]


    #print( file_list )

    for i, file_info in enumerate(file_list, start=1):
        
        selected=""
        if setts["dev_package"] == file_info:
            selected="\033[01;32mselected\033[00m"
        
        print("{0:2d}) {1:<30} {2} ".format( i, file_info[11:-4], selected ) )

    # Benutzer nach Auswahl fragen
    try:
        selection = int(input("\nPlease choose a file (1-{0}): ".format(len(file_list))))
        selected_file = file_list[selection - 1]
        
        print("\nYou have selected \033[01;32m {0}\033[00m. ".format(selected_file[11:-4]))
        
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a number between 1 and {0}.".format(len(file_list)))
    except Exception as e:
        print(f"Error: {e}")


    setts["dev_package"] = selected_file

    save_settings( setts )

def get_dev_pack_list():
    
     #setts = load_settings()
    
    files = os.listdir(uc_cache)

    # Filtere nur Dateien (keine Verzeichnisse) und zeige den vollen Pfad an
    file_list = [file for file in files if os.path.isfile(os.path.join(uc_cache, file)) and not file.endswith(".dl") ]

    file_list = sorted( file_list )
    
    
    build_list = []
    for tmp in file_list:
        
        dev_pack = tmp[11:-4]
        
        print( dev_pack )
        build_list.append( dev_pack )
        
    return build_list
