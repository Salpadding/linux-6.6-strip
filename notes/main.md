[TOC]

# Kernel Personal Notes

## kbuild system

## frequently used kernel api

## main initializtion process

## the bzimage format

### abstract

The bzImage is made up of three parts. The first one is the bootsector which is the first 512 bytes of the bzImage file. The bootsector is defined both by arch/x86/boot/header.S and arch/x86/boot/setup.ld.

### how to hack setup.bin

Since we don't know where the symbol `_start` will be loaded at, we cannot add breakpoint through gdb. I was inspired by the begin code of _start below.

```asm
_start:
		.byte	0xeb		# short (2-byte) jump
		.byte	start_of_setup-1f
```

The code below is a simple relative jump. The operand of short is a signed char. When cpu execute the jump instruction, its instruction pointer will refer to the next instruction which is the physical address of jump instruction added by size of jump instruction. We could make sure that the size of short jump is 2 byte. So the below code will cause a dead loop.

```asm
_start:
		.byte	0xeb		# short (2-byte) jump
		.byte	-2
```

So far we made a so-called breakpoint since the cpu will stays here forever.


### bootsector

The code under `.header` section is defined in arch/x86/boot/header.S. The code under `.header` section should be placed at a specified position of physical address. If you want to tell the linker that some section should be load to a particular address, a general solution is write a linker script.

```asm
	.section ".header", "a"
	.globl	sentinel
sentinel:	.byte 0xff, 0xff        /* Used to detect broken loaders */

	.globl	hdr
hdr:
		.byte setup_sects - 1
root_flags:	.word ROOT_RDONLY
syssize:	.long ZO__edata / 16
ram_size:	.word 0			/* Obsolete */
vid_mode:	.word SVGA_MODE
root_dev:	.word 0			/* Default to major/minor 0/0 */
boot_flag:	.word 0xAA55
	.globl	_start
_start:
```

Let's take a look at the linker script setup.ld.

```ld
OUTPUT_FORMAT("elf32-i386")
OUTPUT_ARCH(i386)
ENTRY(_start)

SECTIONS
{
	. = 0;
	.bstext	: {
		*(.bstext)
		. = 495;
	} =0xffffffff
	.header		: { *(.header) }
	.entrytext	: { *(.entrytext) }
	.inittext	: { *(.inittext) }
	.initdata	: { *(.initdata) }
	__end_init = .;
}
```

The statement `. = 495` move the current position to 495. The size of code starts from `.header` until `_start` is 17. So `_start` will be placed at the second section. And fields like `hdr`, `syssize` will be placed at the bootsector.
 
So qemu bootloader will inspect the first sector of bzImage, and the size of setup.bin, size of arch/x86/boot/vmlinux.bin could be inferred from the hdr field which is the size of setup.bin.

### arch/x86/boot/setup.bin

When the eip move to _start, the segment registers are listed below:

```txt
CS = 0x1020
EIP = 0x0 
ESP = 0xfff0
EAX = 0x1020
CR0 = 0x10
```

The actual instruction pointer refers to `cs*16 + eip = 0x10200`, 0x200 is the size of bootsector. So qemu bootloader will load at least `1+setup_sects` sectors of bzImage into 0x10000. And perform a long jump like `jmp 0x1020,0`.
Then we are in code defined by setup.bin.

### arch/x86/boot/vmlinux.bin

This vmlinux.bin is made of two parts. The first one is code mainly for decompress the actual elf format kernel. The next one is compressed elf format kernel.

The key is a file called mkpiggy.c

```c
printf(".section \".rodata..compressed\",\"a\",@progbits\n");
printf(".globl z_input_len\n");
printf("z_input_len = %lu\n", ilen);
printf(".globl z_output_len\n");
printf("z_output_len = %lu\n", (unsigned long)olen);

printf(".globl input_data, input_data_end\n");
printf("input_data:\n");
printf(".incbin \"%s\"\n", argv[1]);
printf("input_data_end:\n");

printf(".section \".rodata\",\"a\",@progbits\n");
printf(".globl input_len\n");
printf("input_len:\n\t.long %lu\n", ilen);
printf(".globl output_len\n");
printf("output_len:\n\t.long %lu\n", (unsigned long)olen);
```

The file mkpiggy.c is a host program which generate piggy.S at compile-time.
The content of piggy.S looks like below.

```asm
.section ".rodata..compressed","a",@progbits
.globl z_input_len
z_input_len = 167720
.globl z_output_len
z_output_len = 0
.globl input_data, input_data_end
input_data:
.incbin "arch/x86/boot/compressed/vmlinux.bin.xz"
input_data_end:
.section ".rodata","a",@progbits
.globl input_len
input_len:
	.long 167720
.globl output_len
output_len:
	.long 0
```

The most critical statement is `.incbin "arch/x86/boot/compressed/vmlinux.bin.xz"`. This statement include a compressed file into data section directly. And the symbol `input_data`, `input_data_end` could be used to access the included file at runtime like code below.

```c
extern char* input_data;
extern char* input_data_end;

int foo() {
    char* p = input_data;
    char var;
    while(p < input_data_end) {
        var = *p++;
    }
}
```


## init

### arch/x86/boot/main.c 

#### abstract

The qemu bootloader load setup.bin which begin from the second sector of bzImage into memory offset `0x10200`.
We are currently in real mode. After the execution of code and jump to `code_start`, we will enter 32bit protected mode.
The qemu bootloader had already load vmlinux.bin of bzImage to memory 0x100000. So we will jump to code_start directly.

#### first jump

```asm
_start:
		.byte	0xeb		# short (2-byte) jump
		.byte	start_of_setup-1f
```

perform a relative jump, then execute code under start_of_setup

#### start_of_setup

```asm
	.section ".entrytext", "ax"
start_of_setup:
    # ...
	calll	main
```

setup segment and stack pointer, then jump to c code

#### main.c

```c
init_default_io_ops();
copy_boot_params();
console_init();
init_heap();
set_bios_mode();
detect_memory();
keyboard_init();
query_ist();
set_video();
go_to_protected_mode();
```

detect hardware, then jump to protected mode

#### pm.c

```c
	realmode_switch_hook();
	if (enable_a20()) {
		puts("A20 gate not responding, unable to boot...\n");
		die();
	}
	reset_coprocessor();
	mask_all_interrupts();
	setup_idt();
	setup_gdt();
	protected_mode_jump(boot_params.hdr.code32_start,
			    (u32)&boot_params + (ds() << 4));
```

jump to code at code32_start, which is the entry of arch/x86/boot/vmlinux.bin

### arch/x86/boot/compressed/head_64.S

We are currently in 32bit protected mode now, the purpose of `head_64.S` is to switch from 32bit
protected mode to 64bit long mode. Then the compressed elf format vmlinux which stored at data section will be decompressed and move to memory offset 0x1000000.
Then we will enter kernel/head_64.S after a long jump.

#### `startup_32`

1. calculate memory load offset

```asm
	leal	(BP_scratch+4)(%esi), %esp
	call	1f
1:	popl	%ebp
	subl	$ rva(1b), %ebp

# abs(1) = abs(startup_32) + rel(1) - rel(startup_32)
# abs(startup_32) = abs(1) - (rel(1) - rel(startup_32))
```

2. since segmentation fault may occur when decompress linux kernel and `parse_elf` function. It is recommended to let qemu load uncompressed elf kernel. To do so, we need to comment the code in `arch/x86/boot/compressed/misc.c`.

```c
#if 0

	if (__decompress(input_data, input_len, NULL, NULL, outbuf, output_len,
			 NULL, error) < 0)
		return ULONG_MAX;
#endif
#if 0
	entry = parse_elf(outbuf);
#else
    entry = 0;
#endif
```

Then we pass the loader arugment to qemu. The file `arch/x86/boot/compressed/vmlinux.bin` is actually a elf file where debug info is stripped out. Since the qemu is able to load a statically linked elf file into memory by inspect definition of program headers.


```sh
-device loader,file=arch/x86/boot/compressed/vmlinux.bin
```

In the end of arch/x86/boot/compressed/head_64.S, the instruction below will jump to code under `arch/x86/kernel/head_64.S`. The function `extract_kernel` will place the physical entrypoint of kernel to `%rax`.

```asm
call	extract_kernel
movq	%r15, %rsi
jmp	*%rax
```

### kernel/head_64.S

#### abstract

We will setup a minimal page table for higher half kernel here. Then we will update the offset of gs pointer for early per-cpu variable access.


