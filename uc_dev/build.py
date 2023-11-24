
import os
import sys
import glob
import json
import subprocess

from pprint import pprint

from uc_dev import options
from uc_dev import dev_package



def print_line_text( text , big=False, gcc=None, linux=None):
    width  = 110
    if big:
        
        line_color= "\033[38;5;75m"
        
        pre = "             "
        print(line_color + '┌' + '─' * width + '┐' + "\033[00m")
        print(line_color +'│' + ' ' * width + '│' + "\033[00m")
        print(line_color +'│' + pre +"\033[01;32m" + text + ' ' * ( width - len( pre ) - len( text ) ) + line_color + '│' + "\033[00m")
        print(line_color +'│' + ' ' * width + '│' + " \033[00m")
        
        if gcc:
            print(line_color +'│' + pre +"\033[01;33m" + gcc + ' ' * ( width - len( pre ) - len( gcc ) ) + line_color + '│' + "\033[00m")
            
        if linux:
            print(line_color +'│' + pre +"\033[01;33m" + linux + ' ' * ( width - len( pre ) - len( linux ) ) + line_color + '│' + "\033[00m")
        
        print(line_color +'│' + ' ' * width + '│' + " \033[00m")
        print(line_color + '└' + '─' * width + '┘' + "\033[00m")
        
        return
    print("\033[01;33m" + '─' * 25 + " \033[01;32m " + text + " \033[01;33m " + '─' * ( width - 28 -len( text ) )  + "\033[00m")


def touch( file_path ):
    # Erstelle oder aktualisiere die Datei
    with open(file_path, 'a'):
        pass

def run_command( cmd ):
    
    line_color="\033[38;5;166m"
    
    log_file = open("log.txt","w")
    
    print( line_color + "run : \033[00m \033[01;32m" + cmd + "\033[00m" )
    
    try:
        process = subprocess.Popen([ cmd ], shell=True)
        process.wait()
        return process.returncode
    except KeyboardInterrupt:
        print("\nCtrl+C (SIGINT) received while waiting for the process.")
        # Füge hier deinen eigenen Code hinzu, der beim Empfangen von Ctrl+C während des Wartens auf den Prozess ausgeführt werden soll
        sys.exit(0)

"""        
    try:
        #process = subprocess.Popen([ cmd ], shell=True)
        process = subprocess.Popen([ cmd ], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True )
        #stdout, stderr = process.communicate()
        #print( stdout )
#        process.wait()
        for line in iter(process.stdout.readline, ''):
                sys.stdout.write(line)
                log_file.write(line)

        for line in iter(process.stderr.readline, ''):
                sys.stderr.write(line)
                log_file.write(line)

        process.stdout.close()
        process.stderr.close()

            # Warte auf den Abschluss des Prozesses
        process.wait()
        return process.returncode
    except KeyboardInterrupt:
        print("\nCtrl+C (SIGINT) received while waiting for the process.")
        # Füge hier deinen eigenen Code hinzu, der beim Empfangen von Ctrl+C während des Wartens auf den Prozess ausgeführt werden soll
        sys.exit(0)
    """
    
    

def config_uclibc( uclibc_src, all_dev_packages ):

    if not all_dev_packages:
        config_dev_pack_uclibc( uclibc_src, options.get_dev_package_name() )
        return


    dev_pack_list = options.get_dev_pack_list()
   
    for dev_pack in dev_pack_list:
        config_dev_pack_uclibc( uclibc_src , dev_pack )



def build_uclibc( uclibc_src, all_dev_packages ):
    
    
    if not all_dev_packages:
        build_dev_pack_uclibc( uclibc_src, options.get_dev_package_name() )
        return


    dev_pack_list = options.get_dev_pack_list()
   
    for dev_pack in dev_pack_list:
        build_dev_pack_uclibc( uclibc_src , dev_pack )


def prepare_toolchain( dev_pack ):
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    dev_path = "dev_" + dev_pack + "/"
    if not os.path.exists( dev_path ):
        os.mkdir( dev_path )
        
    
    if not os.path.exists( dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed" ):
        print_line_text("extract toolchain " + infos["CONFIG_TOOLCHAIN"] )
        dev_package.write_dev_pack_file( "files/" + infos["CONFIG_TOOLCHAIN"] + ".tar.xz", dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz", dev_pack=dev_pack )
        run_command("tar -xaf " + dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz -C " + dev_path )
        
        touch(dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed")

    os.environ["PATH"] += ":" + os.getcwd() + "/" + dev_path + infos["CONFIG_TOOLCHAIN"] + "/usr/bin"
    #print( os.environ["PATH"] )
    
    os.environ["CROSS_COMPILE"] = infos["CONFIG_GCC_PREFIX"]
    os.environ["ARCH"] = infos["CONFIG_KERNEL_ARCH"]
    
    os.environ["GCC_COLORS"] ='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'
    os.environ["TERM"] = "xterm-256color"
    
    return dev_path

def prepare_uclibc( uclibc_src, dev_pack ):

    infos = dev_package.get_dev_infos( dev_pack )
    
    dev_path = prepare_toolchain( dev_pack )

    print_line_text("rsync uclibc-ng code" )
    cmd = "rsync --info=progress2 -a --exclude '.config' " +  uclibc_src + "/* " + dev_path+ "uclibc-ng/"
    run_command( cmd )

    
    if not os.path.exists( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" ):
        print_line_text("extract linux " + infos["CONFIG_KERNEL_VERS"] )
        dev_package.write_dev_pack_file( "files/linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz", dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz", dev_pack=dev_pack )
        run_command("tar -xaf " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz -C " + dev_path )
        
        touch( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" )
    
    
    
    
    if not os.path.exists( dev_path + "sysroot" ):
        os.mkdir( dev_path + "sysroot" )
    
    
    
    if not os.path.exists( dev_path + "sysroot/.kernel_header_installed"):
        print_line_text( "install kernel_header" )
        cmd = "make -C " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + "/ INSTALL_HDR_PATH=" + os.getcwd() + "/" + dev_path + "/sysroot/usr/ headers_install 2>&1 | tee -a build.log"
        run_command( cmd )
        
        touch( dev_path + "sysroot/.kernel_header_installed" )
    
    
    if not os.path.exists( dev_path+"uclibc-ng/.config" ):
        print_line_text("copy default uclibc-ng config" )
        dev_package.write_dev_pack_file( "files/uclibc-ng-config", dev_path+"uclibc-ng/.config", dev_pack )
        
        cmd = "sed -i 's|KERNEL_HEADERS=.*|KERNEL_HEADERS=\"" + os.getcwd() + "/" + dev_path + "/sysroot/usr/include\"|g' " + os.getcwd() + "/" + dev_path +  "uclibc-ng/.config"
        run_command( cmd )
        run_command( "make -C " + dev_path + "uclibc-ng oldconfig")
    
    
    return dev_path
    

def config_dev_pack_uclibc( uclibc_src, dev_pack ):
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    print_line_text("configure uclibc-ng " + dev_pack, big=True , gcc="GCC   : " + infos["GCC"], linux="Linux : " + infos["CONFIG_KERNEL_VERS"])
    
    
    dev_path = prepare_uclibc( uclibc_src, dev_pack )
    
    
    ret = run_command( "make -C " + dev_path + "uclibc-ng menuconfig")
    
    

def build_dev_pack_uclibc( uclibc_src, dev_pack ):
    
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    #pprint( infos )
    #list_dev_file_content()    
    
    print_line_text("building uclibc-ng " + dev_pack, big=True , gcc="GCC   : " + infos["GCC"], linux="Linux : " + infos["CONFIG_KERNEL_VERS"])
    
    dev_path = prepare_uclibc( uclibc_src, dev_pack )
    
    
    
    ret = run_command( "make -C " + dev_path + "uclibc-ng V=1 ") #2>&1 | tee -a " + dev_path + "build.log")
    if ret != 0:
        return
    ret = run_command( "make -C " + dev_path + "uclibc-ng install DESTDIR=" + os.getcwd() + "/" + dev_path + "/sysroot/" )
    
    touch( dev_path + "sysroot/.sysroot_installed" )
   
    
        



def replace_line( old, new, file_path ):
    
    
    #print(old)
    #print(new)
    #print(file_path)
    
    new_lines=[]
    
    with open( file_path, "r") as f:
        lines = f.readlines()
    
    for line in lines:    
        if line.startswith( old ):
            print("match "+ old)
            new_lines.append( new + "\n" )
            continue
        
        new_lines.append( line )
    
    #pprint(new_lines)
    with open( file_path, "w") as f:
        for line in new_lines:    
            f.write( line )
        
    
        
def build_rootfs( all_dev_packages, test_list, rebuild_rootfs=False, no_disabled_tests=False ):
    
    
    if not all_dev_packages:
        build_dev_pack_rootfs( options.get_dev_package_name(), test_list, rebuild_rootfs=rebuild_rootfs, no_disabled_tests=no_disabled_tests )
        return


    dev_pack_list = options.get_dev_pack_list()
   
    for dev_pack in dev_pack_list:
        build_dev_pack_rootfs( dev_pack, test_list, rebuild_rootfs=rebuild_rootfs, no_disabled_tests=no_disabled_tests )
        
        
def build_dev_pack_rootfs( dev_pack, test_list, rebuild_rootfs=False, no_disabled_tests=False ):
    
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    dev_path = prepare_toolchain( dev_pack )
    
    
    #pprint( infos )        
    
    print_line_text("building rootfs " + dev_pack, big=True , gcc="GCC   : " + infos["GCC"], linux="Linux : " + infos["CONFIG_KERNEL_VERS"])
    
    

    os.environ["PATH"] += ":" + os.getcwd() + "/" + dev_path + infos["CONFIG_TOOLCHAIN"] + "/usr/bin"

    if not os.path.exists( dev_path + "sysroot/.sysroot_installed" ):
        dev_package.write_dev_pack_file( "files/sysroot.tar.xz", dev_path +  "sysroot.tar.xz", dev_pack )
        run_command("tar -xaf " + dev_path + "sysroot.tar.xz -C " + dev_path )
        
        touch( dev_path + "sysroot/.sysroot_installed" )
    
    cur_dir = os.getcwd()
    os.chdir( dev_path )
    
    #if os.path.exists( "uclibc-ng/.config" ):
    #    run_command("cp uclibc-ng/.config uclibc-ng-config")
    
    
    if rebuild_rootfs:
        run_command("rm -rf rootfs" )
        
    run_command("mkdir -p rootfs" )
    run_command("mkdir -p rootfs/lib/" )
    run_command("mkdir -p rootfs/usr/lib/" )
    run_command("( cd rootfs ; mkdir bin ; mkdir dev; mkdir etc; mkdir proc; mkdir sys; mkdir tmp )" )
    
    run_command("cp "+ infos["CONFIG_TOOLCHAIN"] + "/sysroot/usr/lib/libatomic* sysroot/usr/lib")
    run_command("cp "+ infos["CONFIG_TOOLCHAIN"] + "/sysroot/usr/lib/libgcc* sysroot/usr/lib")

    
    run_command("cp -av sysroot/lib/*.so*     rootfs/lib/")
    run_command("cp -av sysroot/usr/lib/*.so* rootfs/usr/lib/")

    
    if not os.path.exists("uclibc-ng-test/.installed"):
        print_line_text("clone uclibc-ng-test")
        
        run_command("git clone https://github.com/lordrasmus/uclibc-ng-test.git")
        
        touch( "uclibc-ng-test/.installed" )

    
    test_disable = []
    if no_disabled_tests == False:
        print_line_text("detecting tests to disable ")
        
        if not os.path.exists( "uclibc-ng/.config" ):
            print_line_text("copy default uclibc-ng config" )
            run_command("mkdir -p uclibc-ng")
            dev_package.write_dev_pack_file( "files/uclibc-ng-config", "uclibc-ng/.config", dev_pack )
        
        ret = subprocess.getstatusoutput('./uclibc-ng-test/get_disabled_tests.py uclibc-ng/.config')
        
        for s in ret[1].split(" "):
            if len( s ) < 2 : continue
            
            print( "disable test : " + s )
            test_disable.append( s.split("=")[0] )
        
        for t in test_disable:
            os.environ[t] = "1"
    #run_command("env")
    
    os.environ["CROSS_COMPILE"] = infos["CONFIG_GCC_PREFIX"]
    os.environ["CFLAGS"]  = "--sysroot=" + os.getcwd() + "/sysroot/"
    os.environ["LDFLAGS"] = "--sysroot=" + os.getcwd() + "/sysroot/"
    
    
    
    
    
    run_command("make -C uclibc-ng-test -j20")
    run_command("make -C uclibc-ng-test install DESTDIR=../rootfs > /dev/null  2>&1")

    run_command("find rootfs -type f -name '*.gdb' -exec rm {} \;")
    
    with open( "rootfs/etc/ethers", "w") as f:
        f.write("08:00:20:00:61:CA  pal\n")
        f.write("08:00:20:00:61:CB  192.168.11.2\n")
        f.write("08:00:20:00:61:CC  teeth\n")
    
    with open( "rootfs/etc/hosts", "w") as f:
        f.write( "127.0.0.1 localhost\n")
    
    with open( "rootfs/etc/passwd", "w") as f:
        f.write("root:x:0:0:root:/root:/bin/sh\n")
        
    with open( "rootfs/etc/shadow", "w") as f:
        f.write("root:2A2wEGJ5Cmq2.:16801:0:99999:7:::\n")
        
    with open( "rootfs/etc/group", "w") as f:
        f.write("root:x:0:\n")
        
    with open( "rootfs/etc/hostname", "w") as f:
        f.write("Qemu\n")

    with open( "rootfs/etc/inittab", "w") as f:

        f.write("::sysinit:/bin/mount -t devtmpfs none /dev\n")
        f.write("::sysinit:/bin/mount -t proc none /proc\n")
        f.write("::sysinit:/bin/mount -t sysfs none /sys\n")
        f.write("::sysinit:/bin/dmesg -n1\n")
        f.write("::sysinit:/bin/hostname Qemu\n")
        f.write("::sysinit:/bin/echo 'test console' > /dev/console\n")
        f.write("::sysinit:/bin/echo 'test ttyS0' > /dev/ttyS0\n")

        f.write("console::sysinit:/bin/run_tests.sh\n")
        #f.write("console::respawn:/bin/sh\n")
        f.write("console::respawn:/sbin/getty -n -L -t 360 console 0 xterm-256color\n")

        """
        Usage: getty [OPTIONS] BAUD_RATE[,BAUD_RATE]... TTY [TERMTYPE]

        Open TTY, prompt for login name, then invoke /bin/login

                -h              Enable hardware RTS/CTS flow control
                -L              Set CLOCAL (ignore Carrier Detect state)
                -m              Get baud rate from modem's CONNECT status message
                -n              Don't prompt for login name
                -w              Wait for CR or LF before sending /etc/issue
                -i              Don't display /etc/issue
                -f ISSUE_FILE   Display ISSUE_FILE instead of /etc/issue
                -l LOGIN        Invoke LOGIN instead of /bin/login
                -t SEC          Terminate after SEC if no login name is read
                -I INITSTR      Send INITSTR before anything else
                -H HOST         Log HOST into the utmp file as the hostname
        """        

    if not test_list == None:

        liste = test_list.split(",")
            
        liste_found = []
        
        for t in liste:
            #print(t)
            
            ret= glob.glob("rootfs/usr/lib/uclibc-ng-test/test/*/" + t)
            if len( ret ) != 1:
                print("\033[01;31mtest " + t + " not found\033[00m")
            else:
                liste_found.append( t )
                
        
        with open("rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in", "r") as f:
            lines = f.readlines()
        
        new_file = ""
        
        for line in lines:
            
            for t in liste_found:
                
                if t in line:
                    #print(line)
                    new_file += line
                    break
        
        #print( new_file )
        
        with open("rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in", "w") as f:
            f.write( new_file )
    
    
    run_command("sort -k4,4 -k1,1 rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in > rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in.sort")
    run_command("mv rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in.sort rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in")
        

    #cp tests_disable rootfs
    with open( "rootfs/bin/run_tests.sh", "w") as f:
        f.write("#!/bin/sh\n")
        #f.write("echo -n 'Disabled Tests : ' ; cat /tests_disable"                     >> rootfs/bin/run_tests.sh
        f.write("cd /usr/lib/uclibc-ng-test/test/\n")
        text = "tests_start"
        width  = 110
        f.write("echo -e '\033[01;33m" + '─' * 25 + " \033[01;32m " + text + " \033[01;33m " + '─' * ( width - 28 -len( text ) )  + "\033[00m'\n")
        #f.write("echo '-------------------- tests_start ------------------------'\n")
        f.write("sh uclibcng-testrunner_color.sh\n")
        text = "tests_end"
        f.write("echo -e '\033[01;33m" + '─' * 25 + " \033[01;32m " + text + " \033[01;33m " + '─' * ( width - 28 -len( text ) )  + "\033[00m'\n")
        #f.write("echo '-------------------- tests_end --------------------------'\n")
        f.write("echo ''\n")
        f.write("echo 'run reboot or shutdown to quit qemu'\n")
        f.write("echo ''\n")
        f.write("echo 'login -> root , no password'\n")
        f.write("echo ''\n")
    run_command("chmod 777 rootfs/bin/run_tests.sh")


    if not os.path.exists( os.path.expanduser('~')+"/.uc_dev/busybox-1.36.1.tar.bz2" ):
        print_line_text("download busybox")
        dev_package.download_with_progress("https://raw.githubusercontent.com/lordrasmus/toolchains/main/busybox-1.36.1.tar.bz2", os.path.expanduser('~')+"/.uc_dev/busybox-1.36.1.tar.bz2")

    if not os.path.exists("busybox-1.36.1/installed"):
        print_line_text("extract busybox")
        run_command("tar -xaf " + os.path.expanduser('~')+"/.uc_dev/busybox-1.36.1.tar.bz2")
        touch("busybox-1.36.1/installed")


    
    if not os.path.exists( "busybox-1.36.1/.config"):
        print_line_text("busybox defconfig")
        run_command("make -C busybox-1.36.1/ defconfig > /dev/null")
    
    replace_line('CONFIG_CROSS_COMPILER_PREFIX=""','CONFIG_CROSS_COMPILER_PREFIX="' + infos["CONFIG_GCC_PREFIX"] + '"', "busybox-1.36.1/.config")
    
    
    replace_line('CONFIG_SYSROOT=""','CONFIG_SYSROOT="'+ os.getcwd() + '/sysroot/"'     , "busybox-1.36.1/.config")
    replace_line('CONFIG_PREFIX="./_install"','CONFIG_PREFIX="../rootfs"'               , "busybox-1.36.1/.config")
    replace_line('CONFIG_FEATURE_EJECT_SCSI=y','# CONFIG_FEATURE_EJECT_SCSI is not set' , "busybox-1.36.1/.config")
    replace_line('CONFIG_MKSWAP=y','# CONFIG_MKSWAP is not set'                         , "busybox-1.36.1/.config")
    replace_line('CONFIG_SWAPON=y','# CONFIG_SWAPON is not set'                         , "busybox-1.36.1/.config")
    replace_line('CONFIG_SWAPOFF=y','# CONFIG_SWAPOFF is not set'                       , "busybox-1.36.1/.config")
    
    #CONFIG_PASSWORD_MINLEN
    #CONFIG_BOOTCHARTD

    # no MMU fixes
    if infos["UCLIBC_MMU"] == "No":
        replace_line('CONFIG_SHELL_ASH=y','# CONFIG_SHELL_ASH is not set|'              , "busybox-1.36.1/.config")
        replace_line('CONFIG_ASH=y','# CONFIG_ASH is not set'                           , "busybox-1.36.1/.config")
        replace_line('CONFIG_SH_IS_ASH=y','# CONFIG_SH_IS_ASH is not set'               , "busybox-1.36.1/.config")
        replace_line('# CONFIG_SH_IS_HUSH is not set','CONFIG_SH_IS_HUSH=y'             , "busybox-1.36.1/.config")
        replace_line('# CONFIG_NOMMU is not set','CONFIG_NOMMU=y'                       , "busybox-1.36.1/.config")


    if infos["UCLIBC_ARCH"] == "xtensa":
        replace_line('CONFIG_EXTRA_CFLAGS=".*"','CONFIG_EXTRA_CFLAGS="-mlongcalls"'     , "busybox-1.36.1/.config")

    replace_line('# CONFIG_STATIC is not set','CONFIG_STATIC=y'                         , "busybox-1.36.1/.config")
    


    if infos["UCLIBC_FORMAT_FLAT"] == "y" :
        os.environ["SKIP_STRIP"]="y"
    else:
        os.environ["SKIP_STRIP"]="0"
        
    if not os.path.exists( "busybox-1.36.1/.build"):
        run_command("make -C busybox-1.36.1 oldconfig > /dev/null")
        if not run_command("make -C busybox-1.36.1 -j20 busybox") == 0:
            exit(1)
        touch("busybox-1.36.1/.build")
    
    if not os.path.exists( "rootfs/.busybox_installed"):
        if not run_command("make -C busybox-1.36.1/ install  > /dev/null") == 0:
            exit(1)
        touch("rootfs/.busybox_installed")


    if rebuild_rootfs:
        run_command("( cd rootfs ; ln -s /sbin/init init )")
        run_command("( cd rootfs ; ln -s lib lib32 )")
        run_command("( cd rootfs ; ln -s lib lib64 )")
        run_command("( cd rootfs ; ln -s lib libx32 )")
    
        run_command("( cd rootfs/usr ; ln -s lib lib32 )")
        run_command("( cd rootfs/usr ; ln -s lib lib64 )")
        run_command("( cd rootfs/usr ; ln -s lib libx32 )")
    
    run_command("rm -f rootfs.img")
    run_command("( cd rootfs ; find . | sort | cpio -o -H newc ) > rootfs.img")
    #run_command("cp rootfs.img rootfs.cpio")
    run_command("rm -f rootfs.img.xz")
    run_command("xz -v -k --check=crc32 rootfs.img")
    
    for t in test_disable:
        os.environ[t] = "0"
    #run_command("env")
    
    
    os.chdir( cur_dir )
