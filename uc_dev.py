#!/usr/bin/python


import os

uc_dev = os.path.expanduser('~')+"/.uc_dev/repo"


print( uc_dev )

if not os.path.exists( uc_dev ):
    os.system("git clone https://github.com/lordrasmus/uclibc-ng-dev.git " + uc_dev )
else:
    os.system("cd " + uc_dev + "; git pull")

import uc_dev

uc_dev.download_dev_package()
