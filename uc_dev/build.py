
import os
import sys
import glob
import json
import subprocess
import time

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


def print_error( text ):
    print("\033[01;31m" + "error: " + text + "\033[00m")


def is_coldfire( infos ):
    # ColdFire needs -mxgot (the 16-bit GOT overflows: "R_68K_GOT16O truncated
    # to fit") and -fno-dwarf2-cfi-asm, like openadk's ADK_TARGET_CPU_CF.
    # Ask the compiler instead of parsing the dev-pack name.
    if infos.get("UCLIBC_ARCH") != "m68k":
        return False
    cmd = infos["CONFIG_GCC_PREFIX"] + "gcc -dM -E - < /dev/null"
    ret = subprocess.getstatusoutput( cmd )
    return ret[0] == 0 and "__mcoldfire__" in ret[1]


def cf_flags( infos ):
    return " -mxgot -fno-dwarf2-cfi-asm" if is_coldfire( infos ) else ""


def embeds_rootfs( infos ):
    # These kernels carry the rootfs in a fixed slot (the cpio hack): ~17 MB
    # for xtensa/kvx/csky/arc, 24 MB in the ColdFire ELF image. Same test as
    # z_images_workflow.yml, which skips the -O2 twins and strips there.
    if infos.get("CONFIG_KERNEL_ARCH") in ( "xtensa", "kvx", "csky", "arc" ):
        return True
    return "mcf5208" in infos.get("CONFIG_QEMU_CMD", "") and infos.get("UCLIBC_FORMAT_ELF") == "y"


def config_has( needle, path="uclibc-ng/.config" ):
    """True if the built uClibc-ng config contains this exact line."""
    try:
        with open( path ) as f:
            return any( line.strip() == needle for line in f )
    except OSError:
        return False


def is_nommu_elf( infos ):
    # noMMU + UCLIBC_FORMAT_ELF: the kernel loads these via BINFMT_ELF_FDPIC,
    # which needs PIE -- a plain ELF gives ENOEXEC ("error -8") on exec.
    return infos.get("UCLIBC_MMU") == "No" and infos.get("UCLIBC_FORMAT_ELF") == "y"


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
        return config_dev_pack_uclibc( uclibc_src, options.get_dev_package_name() )


    dev_pack_list = options.get_dev_pack_list()

    ok = True
    for dev_pack in dev_pack_list:
        if not config_dev_pack_uclibc( uclibc_src , dev_pack ):
            ok = False

    return ok



def build_uclibc( uclibc_src, all_dev_packages ):


    if not all_dev_packages:
        return build_dev_pack_uclibc( uclibc_src, options.get_dev_package_name() )


    dev_pack_list = options.get_dev_pack_list()

    # Bei -a nicht beim ersten Fehler abbrechen -- die uebrigen Arches sind
    # unabhaengig und sollen gebaut werden -- aber den Fehler bis zum
    # Rueckgabewert durchreichen und am Ende noch einmal nennen.
    failed = []
    for dev_pack in dev_pack_list:
        if not build_dev_pack_uclibc( uclibc_src , dev_pack ):
            failed.append( dev_pack )

    for dev_pack in failed:
        print_error( "uclibc-ng build failed: " + dev_pack )

    return len( failed ) == 0


def prepare_toolchain( dev_pack ):
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    dev_path = options.get_work_dir() + "dev_" + dev_pack + "/"
    if not os.path.exists( dev_path ):
        os.mkdir( dev_path )
        
    
    if not os.path.exists( dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed" ):
        print_line_text("extract toolchain " + infos["CONFIG_TOOLCHAIN"] )
        dev_package.write_dev_pack_file( "files/" + infos["CONFIG_TOOLCHAIN"] + ".tar.xz", dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz", dev_pack=dev_pack )
        run_command("tar -xaf " + dev_path + infos["CONFIG_TOOLCHAIN"] + ".tar.xz -C " + dev_path )

        # Mirrors the CI 'Isolate toolchain elf2flt.ld' step
        # (.github/workflows/z_build_workflow.yml): ld-elf2flt looks up
        # elf2flt.ld via <ld-binary>/../lib/elf2flt.ld which resolves to
        # <toolchain>/usr/<target>/lib/elf2flt.ld. Older packers shipped
        # that path as a dangling symlink, newer ones point it at
        # sysroot/usr/lib which exposes the toolchain's pre-built libc.so
        # ldscript and collides with the freshly built uClibc-ng. Replace
        # the symlink with a real directory containing only elf2flt.ld.
        import glob, shutil
        tc_root = dev_path + infos["CONFIG_TOOLCHAIN"]
        sysroot_script = tc_root + "/sysroot/usr/lib/elf2flt.ld"
        for L in glob.glob(tc_root + "/usr/*-*linux-uclibc*/lib"):
            if os.path.islink(L):
                os.remove(L)
                os.makedirs(L)
                if os.path.isfile(sysroot_script):
                    shutil.copy(sysroot_script, L + "/elf2flt.ld")
                # re-expose ldscripts (ld needs them on arches whose binutils
                # doesn't embed them, e.g. nds32; no libc in there)
                if os.path.isdir(tc_root + "/sysroot/usr/lib/ldscripts"):
                    os.symlink("../../../sysroot/usr/lib/ldscripts", L + "/ldscripts")
                print("isolated: " + L + " (elf2flt.ld + ldscripts)")

        touch(dev_path + infos["CONFIG_TOOLCHAIN"]+"/.installed")

    drop_fixincluded_libc_headers( dev_path + infos["CONFIG_TOOLCHAIN"] )

    os.environ["PATH"] += ":" + dev_path + infos["CONFIG_TOOLCHAIN"] + "/usr/bin"
    #print( os.environ["PATH"] )
    
    os.environ["CROSS_COMPILE"] = infos["CONFIG_GCC_PREFIX"]
    os.environ["ARCH"] = infos["CONFIG_KERNEL_ARCH"]
    
    os.environ["GCC_COLORS"] ='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'
    os.environ["TERM"] = "xterm-256color"
    
    return dev_path

def drop_fixincluded_libc_headers( tc_root ):
    # Mirrors the CI 'Drop fixincluded libc headers' step
    # (.github/workflows/z_images_workflow.yml). When gcc is built,
    # fixincludes copies libc headers it wants to patch into
    # lib/gcc/<target>/<ver>/include-fixed/, which comes BEFORE the sysroot
    # on the include path.  For uClibc-ng it always takes pthread.h (rule
    # pthread_incomplete_struct_argument: __sigsetjmp's "__env[1]").  That
    # copy is the pthread.h of whatever uClibc-ng the toolchain was built
    # with, so every program sees it instead of the one we just installed:
    # a function added to pthread.h later is "implicitly declared".  Only
    # files carrying fixincludes' header are removed; gcc's own limits.h,
    # syslimits.h and README stay.  Runs every time, not just on extract,
    # so already installed toolchains are cleaned too.
    import glob
    for f in glob.glob( tc_root + "/usr/lib/gcc/*/*/include-fixed/**", recursive=True ):
        if not os.path.isfile( f ):
            continue
        with open( f, errors="replace" ) as fh:
            head = fh.read( 512 )
        if "auto-edited by fixincludes" in head:
            os.remove( f )
            print( "dropped fixincluded libc header: " + f.split( "include-fixed/" )[1] )


def uclibc_make( uclibc_src, dev_path ):
    return "make -C " + uclibc_src + " O=" + dev_path + "uclibc-ng"


def check_clean_source( uclibc_src ):
    # Ein In-tree-Bau hinterlaesst generierte Dateien im Quellbaum, und die
    # gewinnen auch bei O= : '#include "ucontext_i.h"' sucht zuerst neben der
    # .S-Datei, vor jedem -I. Ein x86_64-ucontext_i.h von 2023 landete so in
    # jedem spaeteren x86_64-Bau. Deshalb nicht bauen, solange so etwas da ist.
    # Host-Werkzeuge von kconfig (extra/config/) sind harmlos, O= baut eigene.
    ret, out = subprocess.getstatusoutput( "git -C " + uclibc_src
        + " ls-files --others --ignored --exclude-standard" )
    if ret != 0:
        print("\033[01;33m" + uclibc_src + " ist kein git-Baum, Pruefung auf"
              " In-tree-Bauprodukte uebersprungen\033[00m")
        return True
    suffixes = ( ".o", ".os", ".oS", ".a", ".so", ".h", ".dep" )
    stale = [ f for f in out.splitlines()
              if not f.startswith( ( "extra/config/", "qemu-inst/" ) )
              and ( f.endswith( suffixes ) or ".so." in f ) ]
    if not stale:
        return True
    print_error( uclibc_src + " enthaelt Bauprodukte eines In-tree-Baus:" )
    for f in stale[:20]:
        print("    " + f)
    if len( stale ) > 20:
        print("    ... und " + str( len( stale ) - 20 ) + " weitere")
    print("Entfernen mit:  make -C " + uclibc_src + " distclean"
          "   (oder ansehen: git -C " + uclibc_src + " clean -X -n)")
    return False


def migrate_copied_tree( build_dir ):
    # Dev-Verzeichnisse von vor der O=-Umstellung enthalten eine Kopie des
    # Quellbaums. Die muss weg: -I$(top_builddir)include steht vor srcdir,
    # alte Header dort wuerden die echten verdecken. .config bleibt erhalten.
    if not os.path.exists( build_dir + "/Makefile" ):
        return
    print_line_text("remove copied uclibc-ng source tree (now built with O=)")
    config = None
    if os.path.exists( build_dir + "/.config" ):
        with open( build_dir + "/.config" ) as f:
            config = f.read()
    run_command( "rm -rf " + build_dir )
    os.makedirs( build_dir )
    if config is not None:
        with open( build_dir + "/.config", "w" ) as f:
            f.write( config )


def prepare_uclibc( uclibc_src, dev_pack ):

    infos = dev_package.get_dev_infos( dev_pack )
    
    dev_path = prepare_toolchain( dev_pack )

    # Out-of-tree: die Quellen bleiben in uclibc_src, dev_path/uclibc-ng nimmt nur
    # .config und Bauprodukte auf (make O=). Frueher wurde der Quellbaum per rsync
    # hineinkopiert; geloeschte Dateien blieben dabei liegen (m68k/float.h), und
    # Bauprodukte des Quellbaums wanderten mit (Symlink-Farm, sysnum.h).
    if not check_clean_source( uclibc_src ):
        return None
    migrate_copied_tree( dev_path + "uclibc-ng" )
    os.makedirs( dev_path + "uclibc-ng", exist_ok=True )


    if not os.path.exists( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" ):
        print_line_text("extract linux " + infos["CONFIG_KERNEL_VERS"] )
        dev_package.write_dev_pack_file( "files/linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz", dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz", dev_pack=dev_pack )
        run_command("tar -xaf " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + ".tar.xz -C " + dev_path )
        
        touch( dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] +"/.installed" )
    
    
    
    
    if not os.path.exists( dev_path + "sysroot" ):
        os.mkdir( dev_path + "sysroot" )
    
    
    
    if not os.path.exists( dev_path + "sysroot/.kernel_header_installed"):
        print_line_text( "install kernel_header" )
        cmd = "make -C " + dev_path + "linux-" + infos["CONFIG_KERNEL_VERS"] + "/ INSTALL_HDR_PATH=" + dev_path + "/sysroot/usr/ headers_install 2>&1 | tee -a build.log"
        run_command( cmd )
        
        touch( dev_path + "sysroot/.kernel_header_installed" )
    
    
    if not os.path.exists( dev_path+"uclibc-ng/.config" ):
        print_line_text("copy default uclibc-ng config" )
        dev_package.write_dev_pack_file( "files/uclibc-ng-config", dev_path+"uclibc-ng/.config", dev_pack )

    # Vor JEDEM Bau, nicht nur beim Anlegen: der Wert ist ein absoluter Pfad
    # auf genau dieses Dev-Verzeichnis. Eine .config, die aelter ist als diese
    # Zeile oder aus dem Pack selbst stammt, traegt den Pfad des CI-Bauers
    # ("linux-headers/include"), und der zeigt hier ins Leere. make bricht dann
    # beim Erzeugen von include/bits/sysnum.h mit "Could not generate syscalls"
    # ab -- das sieht nach fehlenden Kernel-Headern aus und nicht nach einer
    # stale Einstellung, und das Dev-Pack baut nie wieder.
    cmd = "sed -i 's|KERNEL_HEADERS=.*|KERNEL_HEADERS=\"" + dev_path + "/sysroot/usr/include\"|g' " + dev_path +  "uclibc-ng/.config"
    run_command( cmd )

    # Vor JEDEM Bau, nicht nur beim Anlegen. Die .config des Packs beantwortet
    # die Symbole, die es beim CI-Bau gab; der Quell-Tree aus --uclibc_src
    # wandert davon unabhaengig weiter. Kommt dort ein Symbol dazu -- etwa ein
    # neuer Port in der Target-Choice -- steht in der .config keine Antwort
    # dafuer, und kconfig will beim Erzeugen von include/bits/uClibc_config.h
    # fragen: "Restart config...". Unter < /dev/null bricht make dann ab,
    # interaktiv bleibt der Bau stehen.
    # olddefconfig statt oldconfig: vorhandene Antworten bleiben unangetastet,
    # nur neue Symbole bekommen ihren Default, der Bau wartet also nie.
    before = read_kconfig( dev_path + "uclibc-ng/.config" )
    run_command( uclibc_make( uclibc_src, dev_path ) + " olddefconfig" )
    report_kconfig_changes( before, read_kconfig( dev_path + "uclibc-ng/.config" ) )

    return dev_path


def read_kconfig( path ):
    """Liest eine .config als {Symbol: Wert}. '# FOO is not set' wird zu n."""

    values = {}
    if not os.path.exists( path ):
        return values

    with open( path ) as f:
        for line in f:
            line = line.strip()
            if line.startswith("# ") and line.endswith(" is not set"):
                values[ line[2:-11] ] = "n"
            elif "=" in line and not line.startswith("#"):
                name, _, value = line.partition("=")
                values[ name ] = value

    return values


def report_kconfig_changes( before, after ):
    """Sagt, was olddefconfig entschieden hat.

    Ohne das waere die Entscheidung unsichtbar: eine neue Option bekaeme still
    ihren Default, und niemand erfuehre davon -- auch dann nicht, wenn sie uns
    nicht egal ist.  KERNEL_HEADERS bleibt draussen, das schreiben wir selbst.
    """

    changes = []
    for name in sorted( set( before ) | set( after ) ):
        if name == "KERNEL_HEADERS":
            continue
        old = before.get( name )
        new = after.get( name )
        if old == new:
            continue
        if old is None:
            changes.append( "  neu       " + name + "=" + new )
        elif new is None:
            changes.append( "  entfallen " + name )
        else:
            changes.append( "  geaendert " + name + ": " + old + " -> " + new )

    if len( changes ) == 0:
        return

    print_line_text( "olddefconfig hat die .config geaendert" )
    for c in changes:
        print( "\033[01;33m" + c + "\033[00m" )
    

def config_dev_pack_uclibc( uclibc_src, dev_pack ):
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    print_line_text("configure uclibc-ng " + dev_pack, big=True , gcc="GCC   : " + infos["GCC"], linux="Linux : " + infos["CONFIG_KERNEL_VERS"])
    
    
    dev_path = prepare_uclibc( uclibc_src, dev_pack )
    if dev_path is None:
        return False

    ret = run_command( uclibc_make( uclibc_src, dev_path ) + " menuconfig")
    if ret != 0:
        print_error( "menuconfig failed for " + dev_pack + " (make returned " + str( ret ) + ")" )
        return False

    return True



def build_dev_pack_uclibc( uclibc_src, dev_pack ):
    
    
    infos = dev_package.get_dev_infos( dev_pack )
    
    #pprint( infos )
    #list_dev_file_content()    
    
    print_line_text("building uclibc-ng " + dev_pack, big=True , gcc="GCC   : " + infos["GCC"], linux="Linux : " + infos["CONFIG_KERNEL_VERS"])
    
    dev_path = prepare_uclibc( uclibc_src, dev_pack )
    if dev_path is None:
        return False

    # FLAT (bFLT) builds need -Wl,-elf2flt=-r at link time. For rv32/rv64
    # the compiler additionally needs -fPIC so the linker emits
    # R_RISCV_RELATIVE for GOT slots — without it elf2flt has no source
    # for GOT relocs and binfmt_flat can't fix them up at load time.
    # Mirrors openadk's mk/vars.mk treatment of ADK_TARGET_BINFMT_FLAT
    # and the CI workflow (.github/workflows/z_build_workflow.yml).
    extra = ""
    if infos.get("UCLIBC_FORMAT_FLAT") == "y":
        extra = "-Wl,-elf2flt=-r"
        if infos.get("UCLIBC_ARCH","").startswith("riscv"):
            extra = "-fPIC " + extra
    extra = ( extra + cf_flags( infos ) ).strip()
    make_extra = " UCLIBC_EXTRA_CFLAGS='" + extra + "'" if extra else ""

    ret = run_command( uclibc_make( uclibc_src, dev_path ) + " -j20" + make_extra )
    if ret != 0:
        print_error( "build failed for " + dev_pack + " (make returned " + str( ret ) + ")" )
        return False
    # dev_path is already absolute; do not prefix os.getcwd() (that produced a
    # doubled path so -r/build_rootfs never saw the freshly installed libs)
    ret = run_command( uclibc_make( uclibc_src, dev_path ) + make_extra + " install DESTDIR=" + dev_path + "sysroot/" )
    if ret != 0:
        print_error( "install failed for " + dev_pack + " (make returned " + str( ret ) + ")" )
        return False

    # Mirror z_build_workflow.yml: add lib32/lib64/libx32 -> lib symlinks to the
    # sysroot. gcc looks for startfiles (crt1.o, ...) in the ABI's multilib OS
    # dir -- e.g. usr/lib32 for mips n32 -- but uClibc installs only into
    # usr/lib, so a --sysroot link would miss crt1.o without these. (The
    # toolchain isolation empties usr/<target>/lib, so this is the only path
    # left for the test-suite link on non-FLAT arches.)
    for base in ("", "usr/"):
        for ml in ("lib32", "lib64", "libx32"):
            link = dev_path + "sysroot/" + base + ml
            if not os.path.lexists( link ):
                os.symlink( "lib", link )

    # Two things uClibc builds but does not install when HAVE_SHARED is off,
    # which noMMU ELF (HAVE_LDSO=y, DOPIC=y, STATIC_PIE=y) needs anyway.
    # Same workarounds as the CI (z_build_workflow.yml) and openadk.
    if is_nommu_elf( infos ):
        # Makerules only builds S$(CRT).o for HAVE_SHARED/shared-FLAT, so gcc
        # cannot link -pie: "cannot find Scrt1.o". crt1.o already carries the
        # noMMU PIC handling, so a link to it is correct here.
        # Relinked on every install: make install replaces crt1.o, and an
        # old hard link would keep the previous build's file.
        for crt1 in glob.glob( dev_path + "sysroot/**/crt1.o", recursive=True ):
            scrt1 = os.path.join( os.path.dirname( crt1 ), "Scrt1.o" )
            if os.path.lexists( scrt1 ):
                os.remove( scrt1 )
            os.link( crt1, scrt1 )
            print("Scrt1.o: not shipped, linked to crt1.o")

        # install_runtime (Makefile.in) hangs entirely in ifeq($(HAVE_SHARED),y),
        # so sysroot/lib stays empty and the rootfs has no PT_INTERP -> every
        # exec fails with ENOEXEC. Copy the loader plus its symlink chain.
        # Copied on every install, not only into an empty sysroot/lib:
        # otherwise a rebuild keeps the first build's loader, which on
        # 2026-10-20 still lacked TLS after the library had gained it
        # ("Program uses unsupported TLS data!", init dead at boot).
        loaders = glob.glob( dev_path + "uclibc-ng/lib/ld*-uClibc*.so*" )
        if loaders:
            os.makedirs( dev_path + "sysroot/lib", exist_ok=True )
            run_command("cp -a " + dev_path + "uclibc-ng/lib/ld*-uClibc*.so* "
                        + dev_path + "sysroot/lib/")
            print("ld-uClibc: not installed by make install, copied from lib/")

    touch( dev_path + "sysroot/.sysroot_installed" )


    run_command("rm -rf " + dev_path + "/rootfs" )

    return True




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
        return build_dev_pack_rootfs( options.get_dev_package_name(), test_list, rebuild_rootfs=rebuild_rootfs, no_disabled_tests=no_disabled_tests )


    dev_pack_list = options.get_dev_pack_list()

    failed = []
    for dev_pack in dev_pack_list:
        if not build_dev_pack_rootfs( dev_pack, test_list, rebuild_rootfs=rebuild_rootfs, no_disabled_tests=no_disabled_tests ):
            failed.append( dev_pack )

    for dev_pack in failed:
        print_error( "rootfs build failed: " + dev_pack )

    return len( failed ) == 0
        
        
TEST_MANIFEST = ".uc_dev_files"


def remove_dropped_test_files( dest, files ):
    # rsync --files-from loescht nichts. Ein im Testbaum geloeschter oder
    # umbenannter Test blieb deshalb als .c in der Kopie liegen, und
    # Test.mak (TESTS := $(wildcard *.c)) baute und startete ihn weiter.
    # Abhilfe: die Liste des letzten Syncs aufheben und entfernen, was
    # seitdem wegfiel -- samt den Bauprodukten des Tests.
    manifest = dest + "/" + TEST_MANIFEST
    if not os.path.exists( dest ):
        return
    if not os.path.exists( manifest ):
        # Kopie von vor dem Manifest: was darin veraltet ist, weiss niemand.
        # Einmal frisch anlegen; einen git-Klon nur beiseitelegen, er kann
        # lokale Aenderungen tragen.
        if os.path.exists( dest + "/.git" ):
            aside = dest + ".clone-" + time.strftime("%Y%m%d-%H%M%S")
            print("uclibc-ng-test: Klon nach " + aside + " verschoben")
            os.rename( dest, aside )
        else:
            run_command("rm -rf " + dest)
        return

    with open( manifest ) as f:
        old = set( l for l in f.read().split("\n") if l != "" )
    new = set( files )
    new_dirs = set( os.path.dirname( f ) for f in new )

    for d in sorted( set( os.path.dirname( f ) for f in old ) - new_dirs ):
        if d != "" and os.path.isdir( dest + "/" + d ):
            print("uclibc-ng-test: entferne " + d + "/")
            run_command("rm -rf " + dest + "/" + d)

    for f in sorted( old - new ):
        if os.path.dirname( f ) not in new_dirs:
            continue
        print("uclibc-ng-test: entferne " + f)
        victims = [ f ]
        if f.endswith(".c"):
            stem = f[:-2]
            for b in ( stem, stem + "-O2", stem + "_glibc" ):
                victims += [ b, b + ".o", b + ".d", b + ".out" ]
        for v in victims:
            if os.path.lexists( dest + "/" + v ):
                os.remove( dest + "/" + v )


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
    
    run_command("cp -a "+ infos["CONFIG_TOOLCHAIN"] + "/sysroot/usr/lib/libatomic* sysroot/usr/lib")
    run_command("cp -a "+ infos["CONFIG_TOOLCHAIN"] + "/sysroot/usr/lib/libgcc* sysroot/usr/lib")

    
    run_command("cp -av sysroot/lib/*.so*     rootfs/lib/")
    run_command("cp -av sysroot/usr/lib/*.so* rootfs/usr/lib/")
    #run_command("cp -av sysroot/usr/lib/libgcc*.so* rootfs/usr/lib/")

    
    test_src = options.get_test_repo()
    
    if test_src != "":
        # Gegenstueck zu --uclibc_src: einen lokalen Testbaum hineinsyncen, statt
        # den geklonten zu benutzen. Damit ist das Verzeichnis im Dev-Pack ein
        # reines Bauverzeichnis -- man darf es jederzeit wegwerfen, und niemand
        # muss beim Aktualisieren auf lokale Aenderungen aufpassen.
        print_line_text("rsync uclibc-ng-test code")
        
        # Welche Dateien Quellcode sind, beantwortet git und nicht eine
        # Endungsliste: die .gitignore der Suite ignoriert alles OHNE Endung, und
        # genau das sind die gebauten Testprogramme. Ein Quellbaum, in dem schon
        # mal gebaut wurde, traegt davon welche fuer die falsche Arch (hier lagen
        # i386-Binaries darin), die sonst in der rootfs landen.
        ret = subprocess.getstatusoutput("git -C " + test_src + " ls-files --cached")
        if ret[0] != 0:
            print("--test_src ist kein git-Checkout: " + test_src)
            os.chdir( cur_dir )
            return False
        
        tracked = [ f for f in ret[1].split("\n") if f != "" ]
        tracked_dirs = set( os.path.dirname( f ) for f in tracked )
        
        # Noch nicht committete Tests sollen mit, fremde Verzeichnisse nicht. Die
        # Regel dafuer: eine unversionierte Datei kommt nur mit, wenn in ihrem
        # Verzeichnis schon versionierte liegen. Ein neues test/misc/tst-foo.c ist
        # damit dabei, ein Werkzeugbaum, der sich jemand dort abgelegt hat, nicht.
        # Ohne diese Regel waren es sechs Kopien eines entpackten qemu zu je 240 MB
        # -- die .gitignore der Suite hebt mit "!*/" alle Verzeichnisse und mit
        # "!*.*" jede Datei mit Endung wieder auf, .tar und .so darin sind also
        # nicht ignoriert. Die rootfs wuchs auf 315 MB, und der Gast brach beim
        # Auspacken ab: "Initramfs unpacking failed: write error".
        ret = subprocess.getstatusoutput("git -C " + test_src + " ls-files --others --exclude-standard")
        
        untracked = [ f for f in ret[1].split("\n")
                      if f != "" and os.path.dirname( f ) in tracked_dirs ]
        
        # .d/.o/.out haben eine Endung, sind damit nicht ignoriert und muessen
        # von Hand raus.
        files = [ f for f in tracked + untracked
                  if not f.endswith((".d", ".o", ".out")) ]
        
        remove_dropped_test_files( "uclibc-ng-test", files )

        with open("uclibc-ng-test.files", "w") as f:
            f.write("\n".join( files ) + "\n")

        run_command("mkdir -p uclibc-ng-test")
        run_command("rsync -a --no-times --files-from=uclibc-ng-test.files " + test_src + "/ uclibc-ng-test/")

        os.replace("uclibc-ng-test.files", "uclibc-ng-test/" + TEST_MANIFEST)
        
    elif not os.path.exists("uclibc-ng-test/.installed"):
        print_line_text("clone uclibc-ng-test")
        
        run_command("git clone https://github.com/lordrasmus/uclibc-ng-test.git")
        
        touch( "uclibc-ng-test/.installed" )
    else:
        # Der Klon entstand bisher genau einmal und wurde nie wieder angefasst: ein
        # Dev-Pack von vor einem halben Jahr baute also eine ein halbes Jahr alte
        # Testsuite, ohne das irgendwo zu sagen. Am 2026-10-13 lief so ein Test
        # gegen einen Klon, dessen run_tests.sh einen Testrunner aufruft, den es
        # dort noch nicht gibt -- der Gast meldete "./uclibcng-testrunner: not
        # found" und direkt danach tests_end, was wie ein sauberer Lauf aussieht.
        #
        # --ff-only, nie mergen. Eine lokale Aenderung am Klon ist ein legitimer
        # Arbeitsstil (einen Test im Dev-Pack direkt anpassen und sofort booten),
        # die darf das Update nicht wegwerfen. Deshalb ist ein Fehlschlag -- kein
        # Netz, lokale Aenderungen, abgezweigter Branch -- auch kein Abbruch: er
        # wird gemeldet, gebaut wird mit dem vorhandenen Stand.
        print_line_text("update uclibc-ng-test")
        if run_command("git -C uclibc-ng-test pull --ff-only") != 0:
            print("\033[01;33muclibc-ng-test nicht aktualisiert (kein Netz oder "
                  "lokale Aenderungen) -- es wird mit dem vorhandenen Stand "
                  "gebaut\033[00m")

    
    test_disable = []
    if no_disabled_tests == False:
        print_line_text("detecting tests to disable ")
        
        if not os.path.exists( "uclibc-ng/.config" ):
            print_line_text("copy default uclibc-ng config" )
            run_command("mkdir -p uclibc-ng")
            dev_package.write_dev_pack_file( "files/uclibc-ng-config", "uclibc-ng/.config", dev_pack )
        
        ret = subprocess.getstatusoutput('./uclibc-ng-test/get_disabled_tests.py uclibc-ng/.config')
        
        # NAME=1 for a directory, DISABLED_TESTS=dir/test,... for single
        # tests -- take the value as given, it is not always 1.
        for s in ret[1].split(" "):
            if "=" not in s : continue

            print( "disable test : " + s )
            name, value = s.split("=", 1)
            test_disable.append( name )
            os.environ[name] = value
    #run_command("env")
    
    os.environ["CROSS_COMPILE"] = infos["CONFIG_GCC_PREFIX"]
    sysroot = "--sysroot=" + os.getcwd() + "/sysroot/"

    # The test binaries must be built FLAT too, otherwise they come out as
    # ELF, fail to exec on noMMU and the testrunner reports them as exit
    # 127 ("applet not found"). Mirror CI (z_images_workflow.yml) exactly --
    # every flag below is one the CI passes, and a local run that differs
    # measures something the CI never builds.
    flat = ""
    if infos.get("UCLIBC_FORMAT_FLAT") == "y":
        # -s65536: elf2flt defaults to a 4 KB stack, and a bFLT stack cannot
        # grow -- it is a fixed slice of the one mapping that also holds text,
        # data and bss. test/unistd/clone.c alone declares 24 KB of locals.
        flat = " -Wl,-elf2flt=-r -Wl,-elf2flt=-s65536"
        if infos.get("UCLIBC_ARCH","").startswith("riscv"):
            # -fPIC so GOT slots get relocs elf2flt can harvest; --no-relax
            # because ld turns pc relative sequences into absolute ones once
            # the address fits a 12 bit immediate, and a bFLT load base is
            # not known at link time.
            flat = " -fPIC -Wl,--no-relax" + flat

    # noMMU ELF is loaded by BINFMT_ELF_FDPIC and must be PIE.
    pie_c = pie_ld = ""
    if not flat and is_nommu_elf( infos ):
        pie_c  = " -fpie"
        pie_ld = " -fpie -pie"

    # A uClibc-ng built without HAVE_SHARED leaves no libc.so behind, but the
    # dev pack's sysroot still ships a shared libgcc; without -static the link
    # picks that up and dies on an undefined dl_iterate_phdr. -static is also
    # simply what a static libc wants. Not for FLAT or noMMU ELF: both need
    # their own link mode and -static would override the -pie.
    static = ""
    if not flat and not pie_ld and not config_has( "HAVE_SHARED=y" ):
        static = " -static"

    cf = cf_flags( infos )
    os.environ["CFLAGS"]  = sysroot + flat + pie_c  + cf
    os.environ["LDFLAGS"] = sysroot + flat + pie_ld + static + cf
    
    
    
    
    
    slot = embeds_rootfs( infos )
    mk_flags = " O2_TWINS=0" if slot else ""
    testsuite_ret = run_command("make -C uclibc-ng-test -j20" + mk_flags)
    run_command("make -C uclibc-ng-test install DESTDIR=../rootfs" + mk_flags + " > /dev/null  2>&1")

    run_command("find rootfs -type f -name '*.gdb' -exec rm {} \;")
    if slot:
        # strip refuses the scripts and FLAT files and leaves them as they are
        run_command("find rootfs/usr/lib/uclibc-ng-test -type f -exec " + infos["CONFIG_GCC_PREFIX"]
                    + "strip --strip-unneeded {} + 2>/dev/null")
    
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

    # No inittab and no run_tests.sh: the test runner is /init (see below)
    # and does their work itself.  Left over in an older rootfs, they would
    # only mislead.
    for stale in ( "rootfs/etc/inittab", "rootfs/bin/run_tests.sh" ):
        if os.path.exists( stale ):
            os.remove( stale )
        

    if not test_list == None:

        runner = "rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in"

        # Eine Runner-Zeile ist: <erwarteter_rc> <quellname> <binaername> <verzeichnis> <cmd>
        # Auf dem Binaernamen vergleichen, nicht per Teilstring auf der Zeile:
        # "clone" traf sonst auch tst-clone1, "tst-tls3" auch tst-tls3mod.so.
        with open( runner, "r") as f:
            lines = [ l for l in f.readlines() if len( l.split() ) >= 4 ]

        def fields( line ):
            f = line.split()
            return f[2], f[3]           # binaername, verzeichnis

        selected = []
        for t in [ x.strip() for x in test_list.split(",") if x.strip() ]:

            # "verzeichnis/name" waehlt gezielt aus; ohne Verzeichnis zaehlt der
            # Name allein, und der -O2-Zwilling kommt wie bisher mit.
            subdir, _, name = t.rpartition("/")
            names = { name } if name.endswith("-O2") else { name, name + "-O2" }

            hits = [ l for l in lines
                     if fields( l )[0] in names
                     and ( subdir == "" or fields( l )[1] == subdir ) ]

            if len( hits ) == 0:
                print("\033[01;31mtest " + t + " nicht in der Testliste\033[00m")
                continue

            dirs = sorted( { fields( l )[1] for l in hits } )
            if subdir == "" and len( dirs ) > 1:
                print("test " + t + ": in " + ", ".join( dirs ) + " -- alle ausgewaehlt")

            selected += hits

        if len( selected ) == 0:
            # Sonst laeuft eine leere Suite durch und meldet "0 failed".
            print("\033[01;31m--test_list: kein Test ausgewaehlt, Abbruch\033[00m")
            sys.exit( 1 )

        with open( runner, "w") as f:
            f.write( "".join( selected ) )
    
    
    run_command("sort -k4,4 -k1,1 rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in > rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in.sort")
    run_command("mv rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in.sort rootfs/usr/lib/uclibc-ng-test/test/uclibcng-testrunner.in")
        



    if not os.path.exists( options.get_download_dir() + "/busybox-1.36.1.tar.bz2" ):
        print_line_text("download busybox")
        dev_package.download_with_progress("https://raw.githubusercontent.com/lordrasmus/toolchains/main/busybox-1.36.1.tar.bz2", options.get_download_dir() + "/busybox-1.36.1.tar.bz2")

    if not os.path.exists("busybox-1.36.1/installed"):
        print_line_text("extract busybox")
        run_command("tar -xaf " + options.get_download_dir() + "/busybox-1.36.1.tar.bz2")
        touch("busybox-1.36.1/installed")


    
    # Only what the guest still runs: the shell for popen(), system() and
    # posix_spawn() in the tests, ls and true for the vfork tests, and reboot
    # for leaving the --shell session.  init, getty and login are gone with
    # the runner as /init.  On riscv32 noMMU that is 145 KB instead of the
    # 1.1 MB of defconfig, and every exec of it a 256 KB block instead of 2 MB.
    # The marker replaces a defconfig .config left by an older uc_devel.
    if not os.path.exists( "busybox-1.36.1/.config.minimal"):
        print_line_text("busybox minimal config")
        run_command("make -C busybox-1.36.1/ allnoconfig > /dev/null")
        opts = [ "LFS",         # uClibc-ng forces a 64 bit off_t
                 "LS", "TRUE", "ECHO", "TEST", "KILL", "REBOOT", "POWEROFF",
                 "FEATURE_EDITING" ]
        if infos["UCLIBC_MMU"] == "No":
            opts += [ "SHELL_HUSH", "HUSH", "SH_IS_HUSH", "HUSH_INTERACTIVE",
                      "HUSH_ECHO", "HUSH_TEST", "HUSH_READ", "HUSH_KILL",
                      "HUSH_EXPORT", "HUSH_TRAP" ]
        else:
            # ASH_INTERNAL_GLOB: ash refuses uClibc's glob() at build time
            opts += [ "SHELL_ASH", "ASH", "SH_IS_ASH", "ASH_ECHO", "ASH_TEST",
                      "ASH_INTERNAL_GLOB" ]
        for o in opts:
            replace_line( "# CONFIG_" + o + " is not set", "CONFIG_" + o + "=y", "busybox-1.36.1/.config" )
        # the applet links of a defconfig busybox, now pointing nowhere
        run_command("find rootfs -type l -lname '*busybox' -delete")
        for m in ( "rootfs/.busybox_build", "rootfs/.busybox_installed" ):
            if os.path.exists( m ):
                os.remove( m )
        touch( "busybox-1.36.1/.config.minimal" )
    
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
        replace_line('CONFIG_EXTRA_CFLAGS=""','CONFIG_EXTRA_CFLAGS="-mlongcalls"'       , "busybox-1.36.1/.config")

    # -static would silently override the -pie below, and noMMU ELF must be PIE.
    # Unset it explicitly: the busybox .config is generated once and reused, so
    # skipping the assignment would leave a CONFIG_STATIC=y from an earlier run.
    if not is_nommu_elf( infos ):
        replace_line('# CONFIG_STATIC is not set','CONFIG_STATIC=y'                     , "busybox-1.36.1/.config")
    else:
        print("noMMU ELF: CONFIG_STATIC off (-static would defeat -pie)")
        replace_line('CONFIG_STATIC=y','# CONFIG_STATIC is not set'                     , "busybox-1.36.1/.config")

    # busybox tc applet references TCA_CBQ_* / TC_CBQ_* constants that were
    # removed from <linux/pkt_sched.h> in Linux 6.18 (CBQ scheduler dropped
    # upstream). Disable it unconditionally — CBQ has been deprecated for
    # years and tc isn't enabled in our defconfig-based rootfs anyway.
    replace_line('CONFIG_TC=y','# CONFIG_TC is not set'                                 , "busybox-1.36.1/.config")

    if infos["UCLIBC_FORMAT_FLAT"] == "y" :
        os.environ["SKIP_STRIP"]="y"
        # Match CI exactly: put the full FLAT_CFLAGS into BOTH
        # CONFIG_EXTRA_CFLAGS and CONFIG_EXTRA_LDFLAGS, not split. busybox's
        # link line uses LDFLAGS but its compile line uses CFLAGS, and on
        # rv32 the -fPIC needs to reach every compilation unit so GOT
        # slots end up R_RISCV_RELATIVE — otherwise some objects compile
        # absolute and binfmt_flat can't relocate them, returning ENOEXEC.
        flat = "-Wl,-elf2flt=-r"
        if infos.get("UCLIBC_ARCH","").startswith("riscv"):
            flat = "-fPIC " + flat
        replace_line('CONFIG_EXTRA_CFLAGS=""' , 'CONFIG_EXTRA_CFLAGS="' + flat + '"' , "busybox-1.36.1/.config")
        replace_line('CONFIG_EXTRA_LDFLAGS=""', 'CONFIG_EXTRA_LDFLAGS="' + flat + '"', "busybox-1.36.1/.config")
    else:
        os.environ["SKIP_STRIP"]="0"
        # Prefix match, not '=""': the .config survives between runs, so these
        # must overwrite whatever an earlier run left behind.
        cf = cf_flags( infos ).strip()
        if is_nommu_elf( infos ):
            replace_line('CONFIG_EXTRA_CFLAGS=' , 'CONFIG_EXTRA_CFLAGS="-fpie ' + cf + '"' , "busybox-1.36.1/.config")
            replace_line('CONFIG_EXTRA_LDFLAGS=', 'CONFIG_EXTRA_LDFLAGS="-fpie -pie"'      , "busybox-1.36.1/.config")
        elif cf:
            replace_line('CONFIG_EXTRA_CFLAGS=' , 'CONFIG_EXTRA_CFLAGS="' + cf + '"'       , "busybox-1.36.1/.config")
            replace_line('CONFIG_EXTRA_LDFLAGS=', 'CONFIG_EXTRA_LDFLAGS="' + cf + '"'      , "busybox-1.36.1/.config")
        
    if not os.path.exists( "rootfs/.busybox_build"):
        run_command("yes '' | make -C busybox-1.36.1 oldconfig > /dev/null")
        if not run_command("make -C busybox-1.36.1 -j20 busybox") == 0:
            exit(1)
        touch("rootfs/.busybox_build")
    
    if not os.path.exists( "rootfs/.busybox_installed"):
        if not run_command("make -C busybox-1.36.1/ install  > /dev/null") == 0:
            exit(1)
        touch("rootfs/.busybox_installed")


    # The C test runner is init: as PID 1 it does what busybox init and
    # run_tests.sh did, so a test run execs nothing but the tests -- on noMMU
    # every busybox exec costs a 2 MB block.  Replaced on every build, an
    # older rootfs has /init -> /sbin/init.
    # /sbin/init too: some kernels bring their own command line with
    # rdinit=/sbin/init (csky has it in the built-in device tree), and busybox
    # no longer provides one.
    os.makedirs( "rootfs/sbin", exist_ok=True )
    for link in ( "rootfs/init", "rootfs/sbin/init" ):
        if os.path.lexists( link ):
            os.remove( link )
        os.symlink( "/usr/lib/uclibc-ng-test/test/uclibcng-testrunner", link )
    
    if not os.path.exists( "rootfs/lib32"):
        run_command("( cd rootfs ; ln -s lib lib32 )")
    if not os.path.exists( "rootfs/lib64"):
        run_command("( cd rootfs ; ln -s lib lib64 )")
    if not os.path.exists( "rootfs/libx32"):
        run_command("( cd rootfs ; ln -s lib libx32 )")

    if not os.path.exists( "rootfs/usr/lib32"):
        run_command("( cd rootfs/usr ; ln -s lib lib32 )")
    if not os.path.exists( "rootfs/usr/lib64"):
        run_command("( cd rootfs/usr ; ln -s lib lib64 )")
    if not os.path.exists( "rootfs/usr/libx32"):
        run_command("( cd rootfs/usr ; ln -s lib libx32 )")
    
    run_command("rm -f rootfs.img")
    run_command("( cd rootfs ; find . | sort | cpio -o -H newc ) > rootfs.img")
    #run_command("cp rootfs.img rootfs.cpio")
    run_command("rm -f rootfs.img.xz")
    run_command("xz -v -k --check=crc32 rootfs.img")
    
    # gone, not "0": the next dev pack (-a) must not inherit a test list
    for t in test_disable:
        os.environ.pop( t, None )
    #run_command("env")


    os.chdir( cur_dir )

    # Der Bau der Testsuite darf nicht still durchgehen: das rootfs entsteht
    # trotzdem, nur mit weniger Tests darin, und der qemu-Lauf meldet dann eine
    # kleinere Zahl statt eines Fehlers.
    if testsuite_ret != 0:
        print_error( "testsuite build failed for " + dev_pack
                     + " (make returned " + str( testsuite_ret ) + ")" )
        return False

    return True
