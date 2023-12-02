# uclibc-ng-dev


To use this tool, simply download  [uc_devel](https://raw.githubusercontent.com/lordrasmus/uclibc-ng-dev/main/uc_devel) .

Make it executable using chmod, and run uc_devel -h to view the available options.

While it's still a work in progress, it is already functional. 
There is an option to update it using -u or --update.



All files are stored in in a working directory which can be set using uc_devel --work_dir. 
The builds are performed in working directory within a separate folder for each development package.

The primary focus is on building uclibc-ng, a rootfs with the testsuite and busybox, and running it on QEMU.


iIf you have some ideas write me an github issue or on Discord : https://discord.gg/x7xm7EXW
