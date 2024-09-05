QEMU := qemu-system-x86_64
QEMU_FLAGS = -cpu 'SandyBridge' -echr 0x14 \
	    -kernel arch/x86_64/boot/bzImage \
		-m 256 -display curses \
		-device loader,addr=0x1000000,file=arch/x86/boot/compressed/vmlinux.bin


qemu-gdb:
	$(QEMU) $(QEMU_FLAGS) -S -s


