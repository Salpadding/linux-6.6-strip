QEMU := qemu-system-x86_64
QEMU_FLAGS = -cpu 'SandyBridge' -echr 0x14 \
	    -kernel arch/x86_64/boot/bzImage \
		-m 256 -display curses \
		-device loader,file=arch/x86/boot/compressed/vmlinux.bin


qemu-gdb:
	$(QEMU) $(QEMU_FLAGS) -S -s


