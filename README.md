# uclibc-ng-dev


To use this tool, simply download  [uc_devel](https://raw.githubusercontent.com/lordrasmus/uclibc-ng-dev/main/uc_devel) .

Make it executable using chmod, and run uc_devel -h to view the available options.


The primary focus is on building uclibc-ng, a rootfs with the testsuite and busybox, and running it on QEMU.


While it's still a work in progress, it is already functional. 
There is an option to update it using -u or --update.



All files are stored in a designated working directory, which can be configured using uc_devel --work_dir. The builds are executed within this working directory, and each development package is stored in a separate folder.

To specify the uclibc-ng source tree, you can use uc_devel --uclibc_src. Before the build process begins, it is synchronized into the working directory using rsync.

Dev Packages can be downloaded by using uc_devel -d and selected with uc_devel -s.



iIf you have some ideas write me an github issue or on Discord : https://discord.gg/x7xm7EXW
