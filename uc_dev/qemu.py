

import os
import sys
import select
import signal
import subprocess
import time

from uc_dev import build
from uc_dev import options
from uc_dev import dev_package

from pprint import pprint


MARKER = b'HIER_DAS_ECHTE_CPIO_HIN'


def kernel_has_cpio_marker(dev_path):
    with open( dev_path + 'kernel.img', 'rb') as file:
        return file.read().find( MARKER ) != -1


def kernel_cpio_hack(dev_path, rootfs_img='rootfs.img'):
    # Öffnen der Binärdatei im Schreibmodus
    with open( dev_path + 'kernel.img', 'r+b') as file:
        # Binärdaten lesen
        data = file.read()

        with open(dev_path + rootfs_img, 'rb') as file2:
            # Binärdaten lesen
            new_string = file2.read()

        # Suchen nach dem zu ersetzenden String
        index = data.find( MARKER )
        if index == -1:
            print("HIER_DAS_ECHTE_CPIO_HIN not found in kernel image")
            exit(1)

        # Der Platzhalter ist "Marker + Nullen"; seine Laenge ausmessen statt
        # zu raten -- die Images haben unterschiedlich grosse Platzhalter
        # (17 MB bei xtensa/csky/kvx, 24 MB bei m68k-cf5208), und ein zu
        # grosszuegiges Limit wuerde in den Kernel dahinter schreiben.
        end = index + len( MARKER )
        while end < len( data ) and data[end] == 0:
            end += 1
        max_size = end - index

        print("RootFS Size : " + str( len( new_string ) ))
        print("Placeholder : " + str( max_size ) + " (at " + str( index ) + ")")

        if len( new_string ) > max_size:
            print("   Size > " + str( max_size ))
            exit(1)

        # Zur Position im File-Objekt springen
        file.seek(index)

        # Den neuen String schreiben
        file.write(new_string)
        print("rootfs.img written to kernel image")



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


PACK_DIR = ".pack/"


def resolve_rootfs( dev_path, dev_pack ):
    """Waehlt das Rootfs fuer den qemu-Lauf und liefert (img, img_xz, beschreibung).

    Selbst gebaut schlaegt Dev-Pack: 'uc_devel -r' schreibt rootfs.img[.xz]
    direkt nach dev_path, das soll ein spaeterer -q benutzen.  Die Dateien aus
    dem Pack landen daneben unter .pack/ und werden bei JEDEM Lauf frisch aus
    dem Tar geschrieben -- sonst bleibt nach 'uc_devel -d' die alte Version
    liegen (die Namen sind gleich, ein veraltetes Image ist von einem frisch
    gebauten nicht zu unterscheiden) und der Lauf misst still das falsche
    Userspace.
    """
    if os.path.exists( dev_path + "rootfs.img.xz" ) or os.path.exists( dev_path + "rootfs.img" ):
        stamp = file_stamp( dev_path + "rootfs.img.xz" )
        if stamp == "?":
            stamp = file_stamp( dev_path + "rootfs.img" )
        return ( "rootfs.img", "rootfs.img.xz", "selbst gebaut  (" + stamp + ")" )

    if not os.path.exists( dev_path + PACK_DIR ):
        os.makedirs( dev_path + PACK_DIR )

    dev_package.write_dev_pack_file( "files/rootfs.img", dev_path + PACK_DIR + "rootfs.img", dev_pack )
    dev_package.write_dev_pack_file( "files/rootfs.img.xz", dev_path + PACK_DIR + "rootfs.img.xz", dev_pack )

    # Stand des PACKS zeigen, nicht den des Auspackens: die Dateien werden bei
    # jedem Lauf neu geschrieben und traegen daher immer "jetzt".  Die mtime der
    # .tar ist der Server-Zeitstempel (beim Download per os.utime gesetzt, daran
    # erkennt -d auch "update avaible"), also der Zeitpunkt des CI-Builds.
    return ( PACK_DIR + "rootfs.img", PACK_DIR + "rootfs.img.xz",
             "dev pack  (" + file_stamp( options.get_dev_package_tar( dev_pack ) ) + ")" )


def file_stamp( path ):
    try:
        return time.strftime( "%Y-%m-%d %H:%M", time.localtime( os.path.getmtime( path ) ) )
    except OSError:
        return "?"


def set_qemu_initrd( cmd, name ):
    # Die Kommandozeile kommt aus infos.json und nennt "rootfs.img.xz" fest;
    # auf das tatsaechlich gewaehlte Image umbiegen.
    parts = cmd.split()
    for i, p in enumerate( parts ):
        if p == "-initrd" and i + 1 < len( parts ):
            parts[i + 1] = name
    return " ".join( parts )


def set_qemu_memory( cmd, memory ):
    # "512" -> "512M"; qemu braucht eine Einheit oder interpretiert MiB, aber
    # explizit ist klarer. Ein schon vorhandenes -m wird ersetzt, nicht
    # dupliziert (mehrere -m akzeptiert qemu nicht).
    if memory[-1].isdigit():
        memory = memory + "M"
    parts = cmd.split()
    if "-m" in parts:
        parts[ parts.index("-m") + 1 ] = memory
        return " ".join( parts )
    return cmd + " -m " + memory


def run_qemu( use_system_qemu=False, shell=False, kernel=None, memory=None ):

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
    
    
    rootfs_img, rootfs_xz, rootfs_origin = resolve_rootfs( dev_path, dev_pack )
    build.print_line_text("rootfs : " + rootfs_origin)

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
        build.print_line_text("kernel : dev pack  (" + file_stamp( options.get_dev_package_tar( dev_pack ) ) + ")")
    # Manche qemu-Maschinen haben ueberhaupt keine initrd-Unterstuetzung
    # (mcf5208evb, xtensa, csky, kvx ...) -- dort wird das Rootfs in den
    # Platzhalter im Kernel-Image geschrieben. Nicht an einer Arch-Liste
    # entscheiden, sondern daran, ob der Aufruf ein -initrd hat und das
    # Image ueberhaupt einen Platzhalter mitbringt.
    if "-initrd" not in infos["CONFIG_QEMU_CMD"] and kernel_has_cpio_marker( dev_path ):
        kernel_cpio_hack( dev_path, rootfs_img )
	
    
	
    # System-qemu (aus PATH) oder mitgeliefertes qemu-inst
    qemu_prefix = "" if use_system_qemu else "../qemu-inst/bin/"
    # Welche Variante, entscheidet das Pack: sein CONFIG_QEMU_CMD nennt das
    # Image, das zu seinem Kernel passt.  Der riscv32-6.18-noMMU-Kernel etwa ist
    # ohne CONFIG_RD_XZ gebaut und panict mit rootfs.img.xz ("invalid magic at
    # start of compressed archive" -> "Unable to mount root fs").  Nur ausweichen,
    # wenn die genannte Datei fehlt.
    named = ""
    parts = infos["CONFIG_QEMU_CMD"].split()
    if "-initrd" in parts:
        i = parts.index( "-initrd" )
        if i + 1 < len( parts ):
            named = parts[i + 1]
    initrd = rootfs_xz if named.endswith( ".xz" ) else rootfs_img
    if not os.path.exists( dev_path + initrd ):
        initrd = rootfs_img if initrd == rootfs_xz else rootfs_xz
    machine_cmd = set_qemu_initrd( infos["CONFIG_QEMU_CMD"], initrd )
    if memory is not None:
        machine_cmd = set_qemu_memory( machine_cmd, memory )
        build.print_line_text("qemu memory : " + memory)
    qemu_cmd = "cd " + dev_path + "; " + qemu_prefix + machine_cmd + " -no-reboot"
    if shell:
        # Interactive: hand qemu the terminal so the post-test login works;
        # the user quits qemu manually (reboot in the guest, or Ctrl-A X).
        build.run_command( qemu_cmd )
    else:
        # Default: watch the serial output and stop qemu at tests_end.
        run_qemu_watch( qemu_cmd )
