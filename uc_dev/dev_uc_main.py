
import os
import argparse


def dev_uc_main():

    from uc_dev import dev_package
    from uc_dev import options
    from uc_dev import build
    from uc_dev import qemu
    
    
    uc_dev = os.path.expanduser('~')+"/.uc_dev/repo"

    # Erstelle einen ArgumentParser
    parser = argparse.ArgumentParser(description='uclibc-ng dev tool')

    parser.add_argument('-u', '--update',action='store_true', help='Update dev tool and the downloaded dev packs')
    parser.add_argument('-d', '--download', nargs='?', const=True, default=False,
                        help='Download Dev Package. Bare -d is interactive; '
                             '-d NAME (substring) or -d all downloads non-interactively')
    parser.add_argument('-s', '--select', nargs='?', const=True, default=False,
                        help='Select current dev package. Bare -s is interactive; '
                             '-s NAME selects by (substring) match non-interactively')
    parser.add_argument('--clean', action='store_true', help='delete all dev folders in workspace')
    
    parser.add_argument('-a', '--all_archs', action='store_true', help='build for all downloaded archs')
    parser.add_argument( '-w', '--work_dir',  help='path where builds are done and files are cached')
    parser.add_argument( '--uclibc_src',  help='path to uclibc')
    
    
    parser.add_argument('-c', '--config_uclibc', action='store_true', help='configure uclibc-ng')
    parser.add_argument('-b', '--build_uclibc', action='store_true', help='build uclibc-ng')
    parser.add_argument('-r', '--build_rootfs', action='store_true', help='build uclibc-ng')
    
    parser.add_argument('-q', '--run_qemu', action='store_true', help='run qemu')
    parser.add_argument('--system-qemu', action='store_true',
                        help='use the system qemu-system-* (from PATH) instead of the bundled qemu-inst')
    parser.add_argument('--kernel',
                        help='-q: boot this kernel image instead of the dev-pack one (default: the dev-pack kernel.img is restored before every run)')
    parser.add_argument( '--all_tests', action='store_true',  help='do not auto disable tests')
    parser.add_argument( '--test_list',  help='A comma-separated list of tests')
    parser.add_argument( '--shell', action='store_true', help='-q: keep qemu running for an interactive login after the tests (default: -q terminates qemu once it sees the tests_end marker)')
    parser.add_argument( '-m', '--memory',
                        help='-q: qemu RAM size, e.g. 512 or 512M (replaces a -m in the dev pack qemu command)')
    
    
    
    
    
    # Füge Positional Argumente hinzu
    

    # Füge ein Argument mit vorgeschriebenen Werten hinzu
    #parser.add_argument('-m', '--mode', choices=['copy', 'move'], default='copy', help='Modus (Kopieren oder Verschieben)')

    # Füge ein Argument mit einem Standardwert hinzu
    #parser.add_argument('--verbose', action='store_true', help='Zeige detaillierte Ausgaben an')

    # Parse die Befehlszeilenargumente
    args = parser.parse_args()

    if args.update:

        os.system("cd " + uc_dev + "; git pull")
        dev_package.update_downloaded_dev_packages()
        exit(0)

    if args.download:

        dev_package.download_dev_package( None if args.download is True else args.download )
        exit(0)


    if args.select:
        options.select_dev_package( None if args.select is True else args.select )

    if args.uclibc_src:
        options.set_uclibc_repo( args.uclibc_src )
    
    if args.work_dir:
        options.set_options("work_dir", os.path.abspath( args.work_dir ) )
    
    options.check_settings()
    
    if args.clean:
        cmd = "rm -rf " + options.get_work_dir()+ "dev_*"
        print( "\nrunning : " + cmd )
        
        user_input = input("\nDo you want to continue? (yes/no): ")

        # Check the user's input
        if user_input.lower() == "yes" or user_input.lower() == "y":
            print("deleting")
            os.system( cmd )
        
        exit(0)
    
        
    # Options that only mean something together with one action.  This used to
    # print a note and carry on, which reads like it worked: --test_list handed
    # to -q silently ran the whole suite instead of the named tests.
    misused = []
    if ( args.test_list or args.all_tests ) and not args.build_rootfs:
        misused.append( "--test_list and --all_tests need -r/--build_rootfs, "
                        "the test list is written into the rootfs" )
    if ( args.system_qemu or args.kernel or args.shell or args.memory ) \
            and not args.run_qemu:
        misused.append( "--system-qemu, --kernel, --shell and -m need -q/--run_qemu" )
    if len( misused ) > 0:
        for m in misused:
            print( "error: " + m )
        exit(1)


    if args.config_uclibc:
        if options.get_uclibc_repo() == "":
            print("set uclibc-ng src with --uclibc_src")
            exit(1)
            
        build.config_uclibc( options.get_uclibc_repo(), args.all_archs )

    if args.build_uclibc:
        
        if options.get_uclibc_repo() == "":
            print("set uclibc-ng src with --uclibc_src")
            exit(1)
        
        build.build_uclibc( options.get_uclibc_repo(), args.all_archs )

    
    if args.build_rootfs:
        build.build_rootfs( args.all_archs, args.test_list, no_disabled_tests=args.all_tests )

    if args.run_qemu:
        qemu.run_qemu( args.system_qemu, shell=args.shell, kernel=args.kernel, memory=args.memory )


