
import os
import tarfile
import json
import subprocess

from pprint import pprint

from uc_dev import options



def print_line_text( text ):
    print("\033[01;33m------------------------------  \033[01;32m " + text + " \033[01;33m ---------------------------------------\033[00m")


def touch( file_path ):
    # Erstelle oder aktualisiere die Datei
    with open(file_path, 'a'):
        pass

def run_command( cmd ):
    print( "run : " + cmd )
    try:
        process = subprocess.Popen([ cmd ], shell=True)
        process.wait()
    except KeyboardInterrupt:
        print("\nCtrl+C (SIGINT) received while waiting for the process.")
        # Füge hier deinen eigenen Code hinzu, der beim Empfangen von Ctrl+C während des Wartens auf den Prozess ausgeführt werden soll
        sys.exit(0)
    
def list_dev_file_content( ):

    try:
        with tarfile.open( options.get_dev_package_tar() , 'r') as tar:
            # List the files in the TAR archive
            file_list = tar.getnames()

            print("Files in the TAR archive {0}:".format( options.get_dev_package_tar() ))
            for file in file_list:
                print(file)
            
             
    except FileNotFoundError:
        print("The file {0} was not found.".format( options.get_dev_package_tar() ))
    except tarfile.TarError as e:
        print(f"Error processing the TAR archive: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
def get_dev_file_content( name ):
    try:
        with tarfile.open( options.get_dev_package_tar() , 'r') as tar:
            # List the files in the TAR archive
            file_list = tar.getnames()

            #print("Files in the TAR archive {0}:".format( options.get_dev_package_tar() ))
            #for file in file_list:
            #    print(file)
            
            
            tar_name = "devel_pack_" + options.get_dev_package_name() + "/" + name
            
            return tar.extractfile(tar_name).read()
             
    except FileNotFoundError:
        print("The file {0} was not found.".format( options.get_dev_package_tar() ))
    except tarfile.TarError as e:
        print(f"Error processing the TAR archive: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    

def get_dev_infos( ):
    
    infos = get_dev_file_content( "infos.json" )
    
    json_info = json.loads( infos )
    
    pprint( json_info )
    
    return json_info


def write_dev_pack_file( tar_name, out_name ):
    
    #print( "get : " + tar_name )
    data = get_dev_file_content( tar_name )
    
    with open( out_name, "wb" ) as f:
        f.write( data )


def build_uclibc( uclibc_src, all_dev_packages ):
    
    
    if not all_dev_packages:
        build_dev_pack_uclibc( uclibc_src )
        return


    dev_pack_list = options.get_dev_pack_list()
   
    for dev_pack in dev_pack_list:
        build_dev_pack_uclibc( uclibc_src , dev_pack=dev_pack )
        
    
    
    

def build_dev_pack_uclibc( uclibc_src, dev_pack=None ):
    
    if dev_pack == None:
        dev_name = options.get_dev_package_name()
    else:
        dev_name = dev_pack
        
    
    print_line_text("building " + dev_name )
    
    dev_path = "dev_" + dev_name + "/"
    if not os.path.exists( dev_path ):
        os.mkdir( dev_path )
        
    
    infos = get_dev_infos()
    
    list_dev_file_content()
    
    print_line_text("rsync uclibc-ng code" )
    cmd = "rsync --info=progress2 -a --exclude '.config' " +  uclibc_src + "/* " + dev_path+ "uclibc-ng/"
    run_command( cmd )
    
    
    
    if not os.path.exists( dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed" ):
        print_line_text("extract toolchain " + infos["CONFIG_TOOLCHAIN"] )
        write_dev_pack_file( "files/" + infos["CONFIG_TOOLCHAIN"] + ".tar.xz", dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz" )
        run_command("tar -xaf " + dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz -C " + dev_path )
        
        touch(dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed")
    
    if not os.path.exists( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" ):
        print_line_text("extract linux " + infos["CONFIG_KERNEL_VERS"] )
        write_dev_pack_file( "files/linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz", dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz" )
        run_command("tar -xaf " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz -C " + dev_path )
        
        touch( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" )
    
    
    os.environ["PATH"] += ":" + os.getcwd() + "/" + dev_path + infos["CONFIG_TOOLCHAIN"] + "/usr/bin"
    #print( os.environ["PATH"] )
    
    os.environ["CROSS_COMPILE"] = infos["CONFIG_GCC_PREFIX"]
    os.environ["ARCH"] = infos["CONFIG_KERNEL_ARCH"]
    
    
    if not os.path.exists( dev_path + "sysroot" ):
        os.mkdir( dev_path + "sysroot" )
    
    
    
    if not os.path.exists( dev_path + "sysroot/.kernel_header_installed"):
        print_line_text( "install kernel_header" )
        cmd = "make -C " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + "/ INSTALL_HDR_PATH=" + os.getcwd() + "/" + dev_path + "/sysroot/usr/ headers_install 2>&1 | tee -a build.log"
        run_command( cmd )
        
        touch( dev_path + "sysroot/.kernel_header_installed" )
    
    
    if not os.path.exists( dev_path+"uclibc-ng/.config" ):
        print_line_text("copy default uclibc-ng config" )
        write_dev_pack_file( "files/uclibc-ng-config", dev_path+"uclibc-ng/.config" )
        
        cmd = "sed -i 's|KERNEL_HEADERS=.*|KERNEL_HEADERS=\"" + os.getcwd() + "/" + dev_path + "/sysroot/usr/include\"|g' " + os.getcwd() + "/" + dev_path +  "uclibc-ng/.config"
        run_command( cmd )
        run_command( "make -C " + dev_path + "uclibc-ng oldconfig")
    
    
    
    run_command( "make -C " + dev_path + "uclibc-ng 2>&1 | tee -a " + dev_path + "build.log")
    run_command( "make -C " + dev_path + "uclibc-ng install DESTDIR=" + os.getcwd() + "/" + dev_path + "/sysroot/" )
    
    
    """
    
	rm -f build.log
	echo "\n----------------- uClibc-ng log -------------------------- \n" > build.log
	
	CROSS_COMPILE=$CONFIG_GCC_PREFIX make -C uclibc-ng 
	CROSS_COMPILE=$CONFIG_GCC_PREFIX make -C uclibc-ng install DESTDIR=../sysroot
    
    run_command("make -C " + dev_path + "uclibc-ng" )
    """
    
        
    
        
        
