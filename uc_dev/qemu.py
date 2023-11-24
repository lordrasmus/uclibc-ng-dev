

import os

from uc_dev import build
from uc_dev import options
from uc_dev import dev_package

from pprint import pprint


def kernel_cpio_hack(dev_path):
    # Öffnen der Binärdatei im Schreibmodus
    with open( dev_path + 'kernel.img', 'r+b') as file:
        # Binärdaten lesen
        data = file.read()

        with open(dev_path + 'rootfs.img', 'rb') as file2:
            # Binärdaten lesen
            new_string = file2.read()
            
        print("RootFS Size : " + str( len( new_string ) ))
        
        if len( new_string ) > 17825792:
            print("   Size > 17825792")
            exit(1)

        # Suchen nach dem zu ersetzenden String
        old_string = b'HIER_DAS_ECHTE_CPIO_HIN'
        
        index = data.find(old_string)
        print( index )
        # Überprüfen, ob der zu ersetzende String gefunden wurde
        if index != -1:
            # Zur Position im File-Objekt springen
            file.seek(index)
            
            # Den neuen String schreiben
            file.write(new_string)
            print("rootfs.img written to kernel image")
            return
        
        print("HIER_DAS_ECHTE_CPIO_HIN not found in kernel image")
        exit(1)



def run_qemu():
    
    dev_pack = options.get_dev_package_name()
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    
    #pprint( infos )        
    
    if not os.path.exists( os.path.expanduser('~')+"/.uc_dev/qemu-inst.tar.xz"):
        build.print_line_text("download qemu")
        dev_package.download_with_progress("https://raw.githubusercontent.com/lordrasmus/uclibc-ng-qemu-imgs/main/qemu-inst.tar.xz", os.path.expanduser('~')+"/.uc_dev/qemu-inst.tar.xz")
        
    if not os.path.exists( "qemu-inst/.installed"):
        build.print_line_text("extract qemu")
        build.run_command("tar -xaf " + os.path.expanduser('~')+"/.uc_dev/qemu-inst.tar.xz")
        build.touch("qemu-inst/.installed")


    dev_path = "dev_" + dev_pack + "/"
    if not os.path.exists( dev_path ):
        os.mkdir( dev_path )
    
    
    if not os.path.exists(dev_path + "rootfs.img"):
        dev_package.write_dev_pack_file("files/rootfs.img", dev_path + "/rootfs.img", dev_pack )        
    
    if not os.path.exists(dev_path + "rootfs.img.xz"):
        dev_package.write_dev_pack_file("files/rootfs.img.xz", dev_path + "/rootfs.img.xz", dev_pack )        
    
    dev_package.write_dev_pack_file("files/kernel.img", dev_path + "/kernel.img", dev_pack )        
    if infos["CONFIG_KERNEL_ARCH"] == "kvx" or infos["CONFIG_KERNEL_ARCH"] == "xtensa":
        kernel_cpio_hack( dev_path )
	
    
	
    build.run_command( "cd " + dev_path + "; ../qemu-inst/bin/" + infos["CONFIG_QEMU_CMD"] + " -no-reboot" )
#	./qemu-inst/bin/$CONFIG_QEMU_CMD -no-reboot
