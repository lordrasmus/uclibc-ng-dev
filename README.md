# uclibc-ng-dev


To use this tool, simply download  [uc_devel](https://raw.githubusercontent.com/lordrasmus/uclibc-ng-dev/main/uc_devel) .

Make it executable using chmod, and run uc_devel -h to view the available options.


The primary focus is on building uclibc-ng, a rootfs with the testsuite and busybox, and running it on QEMU.


While it's still a work in progress, it is already functional. 
There is an option to update it using -u or --update.



All files are stored in a designated working directory, which can be configured using uc_devel --work_dir. The builds are executed within this working directory, and each development package is stored in a separate folder.

The uclibc-ng source tree is given with uc_devel --uclibc_src (or UC_UCLIBC_SRC) on every run; it is built out of tree in the working directory.

Dev Packages are downloaded with uc_devel -d and chosen per run with -p NAME (or UC_DEV_PACK). Nothing about a run is stored, so runs on several archs can go at the same time.



iIf you have some ideas write me an github issue or on Discord : https://discord.gg/x7xm7EXW
