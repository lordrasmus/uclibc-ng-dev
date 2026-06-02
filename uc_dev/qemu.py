

import os
import sys
import select
import signal
import subprocess

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



def run_qemu_watch( cmd ):
    # The minimal qemu test kernels often have no working reboot/poweroff
    # driver, so "-no-reboot" never makes qemu exit on its own (the kernel just
    # prints "Restarting system" / "System halted" and loops). Mirror the CI's
    # run_qemu.py instead: read qemu's serial output (CONFIG_QEMU_CMD uses
    # -nographic/console=ttyS0, so it lands on stdout), echo it live, and once
    # the tests_end marker (or a kernel panic) appears, kill qemu's process
    # group. Use --shell to skip this and keep an interactive login.
    line_color = "\033[38;5;166m"
    print( line_color + "run : \033[00m \033[01;32m" + cmd + "\033[00m" )
    sys.stdout.flush()

    proc = subprocess.Popen( cmd, shell=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             start_new_session=True, bufsize=0 )

    read_timeout = 240               # per read; CI uses 240 (riscv64/powerpc slow)
    max_consecutive_timeouts = 3     # 3 x 240s fully silent -> treat as hung
    consecutive = 0
    tail = ""                        # keep a small window to catch a split marker
    try:
        while True:
            rlist, _, _ = select.select( [proc.stdout], [], [], read_timeout )
            if rlist:
                data = os.read( proc.stdout.fileno(), 4096 )
                if not data:                 # EOF -> qemu already exited
                    break
                sys.stdout.buffer.write( data )
                sys.stdout.flush()
                consecutive = 0
                window = tail + data.decode( errors="replace" )
                if "tests_end" in window:
                    print( "\nqemu: tests_end -> stopping qemu" )
                    break
                if "Kernel panic - not syncing: Attempted to kill init" in window:
                    print( "\nqemu: kernel panic -> stopping qemu" )
                    break
                tail = window[-256:]
            else:
                if proc.poll() is not None:
                    break
                consecutive += 1
                print( "\nqemu: no output for {0}s (#{1})".format( read_timeout, consecutive ) )
                if consecutive >= max_consecutive_timeouts:
                    print( "qemu: silent too long, treating as hung -> stopping qemu" )
                    break
    except KeyboardInterrupt:
        print( "\nCtrl+C -> stopping qemu" )
    finally:
        if proc.poll() is None:
            try:
                os.killpg( os.getpgid( proc.pid ), signal.SIGKILL )
            except ProcessLookupError:
                pass
        proc.wait()


def run_qemu( use_system_qemu=False, shell=False, kernel=None ):

    dev_pack = options.get_dev_package_name()

    infos = dev_package.get_dev_infos( dev_pack )


    #pprint( infos )

    # mitgeliefertes qemu nur holen/entpacken, wenn nicht das System-qemu genutzt wird
    if not use_system_qemu:
        if not os.path.exists( options.get_download_dir() + "/qemu-inst.tar.xz"):
            build.print_line_text("download qemu")
            dev_package.download_with_progress("https://raw.githubusercontent.com/lordrasmus/uclibc-ng-qemu-imgs/main/qemu-inst.tar.xz", options.get_download_dir() + "/qemu-inst.tar.xz")

        if not os.path.exists( "qemu-inst/.installed"):
            build.print_line_text("extract qemu")
            build.run_command("tar -xaf " + options.get_download_dir() + "/qemu-inst.tar.xz")
            build.touch("qemu-inst/.installed")


    # Must match build.py's prepare_uclibc/prepare_toolchain, which build
    # into options.get_work_dir() + "dev_" + dev_pack. Earlier this was a
    # bare CWD-relative "dev_" + dev_pack, so -q ran a stale rootfs from a
    # different directory than -b/-r wrote to (e.g. a half-built FLAT image
    # that fails with ENOEXEC), while the freshly built one sat untouched
    # under the work_dir.
    dev_path = options.get_work_dir() + "dev_" + dev_pack + "/"
    if not os.path.exists( dev_path ):
        os.mkdir( dev_path )
    
    
    if not os.path.exists(dev_path + "rootfs.img"):
        dev_package.write_dev_pack_file("files/rootfs.img", dev_path + "/rootfs.img", dev_pack )        
    
    if not os.path.exists(dev_path + "rootfs.img.xz"):
        dev_package.write_dev_pack_file("files/rootfs.img.xz", dev_path + "/rootfs.img.xz", dev_pack )        
    
    # kernel.img: ohne --kernel immer frisch aus dem dev-Pack, damit kein
    # vergessenes lokales Image stillschweigend weiterbenutzt wird; ein
    # eigener Kernel wird explizit mit --kernel <pfad> angegeben
    if kernel is not None:
        if not os.path.exists( kernel ):
            print( "kernel image not found : " + kernel )
            exit(1)
        build.print_line_text("kernel : " + kernel)
        with open( kernel, "rb" ) as src, open( dev_path + "kernel.img", "wb" ) as dst:
            dst.write( src.read() )
    else:
        dev_package.write_dev_pack_file("files/kernel.img", dev_path + "/kernel.img", dev_pack )
    if infos["CONFIG_KERNEL_ARCH"] == "kvx" or infos["CONFIG_KERNEL_ARCH"] == "xtensa" or infos["CONFIG_KERNEL_ARCH"] == "csky":
        kernel_cpio_hack( dev_path )
	
    
	
    # System-qemu (aus PATH) oder mitgeliefertes qemu-inst
    qemu_prefix = "" if use_system_qemu else "../qemu-inst/bin/"
    qemu_cmd = "cd " + dev_path + "; " + qemu_prefix + infos["CONFIG_QEMU_CMD"] + " -no-reboot"
    if shell:
        # Interactive: hand qemu the terminal so the post-test login works;
        # the user quits qemu manually (reboot in the guest, or Ctrl-A X).
        build.run_command( qemu_cmd )
    else:
        # Default: watch the serial output and stop qemu at tests_end.
        run_qemu_watch( qemu_cmd )
