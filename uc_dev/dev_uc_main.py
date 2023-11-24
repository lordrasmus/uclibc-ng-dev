
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

    parser.add_argument('-u', '--update',action='store_true', help='Update dev tool')

    
    parser.add_argument('-d', '--download',action='store_true', help='Download Dev Package')
    parser.add_argument('-s', '--select', action='store_true', help='select current dev package')
    parser.add_argument('-b', '--build_uclibc', action='store_true', help='build uclibc-ng')
    parser.add_argument('-r', '--build_rootfs', action='store_true', help='build uclibc-ng')
    parser.add_argument('-q', '--run_qemu', action='store_true', help='run qemu')
    
    parser.add_argument('-a', '--all_archs', action='store_true', help='build for all downloaded archs')
    
    
    parser.add_argument( '--all_tests', action='store_true',  help='do not auto disable tests')
    parser.add_argument( '--test_list',  help='A comma-separated list of tests')
    
    parser.add_argument( '--uclibc_src',  help='path to uclibc')
    
    
    # Füge Positional Argumente hinzu
    

    # Füge ein Argument mit vorgeschriebenen Werten hinzu
    #parser.add_argument('-m', '--mode', choices=['copy', 'move'], default='copy', help='Modus (Kopieren oder Verschieben)')

    # Füge ein Argument mit einem Standardwert hinzu
    #parser.add_argument('--verbose', action='store_true', help='Zeige detaillierte Ausgaben an')

    # Parse die Befehlszeilenargumente
    args = parser.parse_args()

    if args.update:
        
        os.system("cd " + uc_dev + "; git pull")
        exit(0)

    if args.download:

        dev_package.download_dev_package()
        exit(0)
        

    if args.select:
        options.select_dev_package()


    if args.build_uclibc:
        
        if not args.uclibc_src:
            print("Argument --uclibc_src is needed")
            exit(1)
        
        
        build.build_uclibc( args.uclibc_src, args.all_archs )

    
    if args.build_rootfs:
        build.build_rootfs( args.all_archs, args.test_list, no_disabled_tests=args.all_tests )

    if args.run_qemu:
        qemu.run_qemu()


