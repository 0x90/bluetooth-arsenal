all: btscan

btscan: btscan.c
	gcc -Wall -O -o btscan btscan.c -lbluetooth

btscan-mips: btscan.c
	mipsel-openwrt-linux-uclibc-gcc -Wall -Os -o btscan.mips btscan.c -lbluetooth -L/home/user/Openwrt/backfire_10.03/staging_dir/target-mipsel_uClibc-0.9.30.1/usr/lib/ -I/home/user/Openwrt/backfire_10.03/staging_dir/target-mipsel_uClibc-0.9.30.1/usr/include/

clean:
	rm -f btscan btscan.mips


##must correct link for cross compiling when updating build version
##ln -s /home/user/Openwrt/backfire_10.03/build_dir/linux-brcm47xx/linux-2.6.32.10/arch/mips/include/asm /home/user/x-tools/mipsel-unknown-linux-uclibc/mipsel-unknown-linux-uclibc/sys-root/usr/include/asm

