
import os
import json

uc_setts = os.path.expanduser('~')+"/.uc_dev/settings.json"

def load_settings():
    if not os.path.exists( uc_setts ):
            setts = {}
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
    # Atomar: erst eine eigene temporaere Datei, dann rename.  open(..., 'w')
    # kuerzt die Datei sofort, und ein zweiter uc_devel, der in diesem Moment
    # liest, bekam eine leere Datei ("Error decoding the JSON file").
    tmp = uc_setts + ".{0}.tmp".format( os.getpid() )
    try:
        with open(tmp, 'w') as json_file:
            json.dump(setts, json_file, indent=2)
        os.replace( tmp, uc_setts )
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


# Pack-Auswahl nur fuer diesen Aufruf, aus -p/--pack oder UC_DEV_PACK.  Steht
# bewusst NICHT in settings.json: wer gleichzeitig an zwei Arches arbeitet,
# stellt sonst der anderen Sitzung staendig die globale Auswahl um.  Alles
# andere ist ohnehin pro Pack getrennt -- die dev_<name>/-Ordner, der Cache.
# Eine gespeicherte Auswahl (-s) gibt es deshalb nicht mehr.
dev_package_override = None


def set_dev_package_override( name ):
    """Loest einen eindeutigen Namens-Substring auf, ohne settings.json zu aendern."""

    global dev_package_override

    matches = [ p for p in get_dev_pack_list() if name in p ]
    if len( matches ) != 1:
        print("pack '{0}' matched {1} packages: {2}".format(
            name, len(matches), matches ) )
        exit(1)

    dev_package_override = matches[0]
    print("using \033[01;32m{0}\033[00m for this run".format( matches[0] ) )


def get_dev_package_name( ):

    if dev_package_override is not None:
        return dev_package_override

    print("no dev package given: use -p NAME or set UC_DEV_PACK. Downloaded:")
    for p in get_dev_pack_list():
        print("  " + p)
    exit(1)

def get_dev_package_tar( dev_pack ):
    
    ret = get_dev_pack_dir() + "devel_pack_" + dev_pack + ".tar"
        
    return ret
    

# Quellbaeume nur fuer diesen Aufruf, aus --uclibc_src/--test_src oder
# UC_UCLIBC_SRC/UC_TEST_SRC; aus demselben Grund wie das Pack nicht in
# settings.json.
uclibc_repo = os.environ.get( "UC_UCLIBC_SRC", "" )
test_repo = os.environ.get( "UC_TEST_SRC", "" )


def set_uclibc_repo( path ):

    global uclibc_repo
    uclibc_repo = os.path.abspath( path )

def get_uclibc_repo( ):

    return uclibc_repo


def set_test_repo( path ):

    global test_repo
    test_repo = os.path.abspath( path )

def get_test_repo( ):

    return test_repo
