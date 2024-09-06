# qemu

## qemu -kernel 发生了什么

### 两个 vmlinux.bin

1. arch/x86/boot/compressed/vmlinux.bin

这个 .bin 文件其实是 elf 格式的 里面是 64位的代码 只不过去掉了符号表

2. arch/x86/boot/vmlinux.bin

这个是真正意义上的 .bin 文件, 第一个扇区包含可引导标志, 第二个扇区是兼容 16bit 的代码
同时在数据区包含了压缩过的 arch/x86/boot/compressed/vmlinux.bin

### 实模式阶段 

我尝试了以下 hack

1. 修改 _start 

setup.S 中有这样一段相对跳转的代码

```txt
_start:
		.byte	0xeb		# short (2-byte) jump
		.byte	start_of_setup-1f
```

我尝试改成了如下代码, 相当于 `while(1)`, 让 qemu 停留在这里 

```txt
_start:
		.byte	0xeb
		.byte	-2 
```

2. 使用 qemu 配合 gdb 打印寄存器

我得到了如下的输出

```txt
CS = 0x1020
EIP = 0x0 
ESP = 0xfff0
EAX = 0x1020
CR0 = 0x10
```

显然我们正处于 real mode, 基址 0x10200, 因为不确定 base address, 所以这里用了相对跳转, 相对跳转的操作数要用两个绝对地址相减得到,跳到 start_of_setup 的位置

```S
		.byte	0xeb		# short (2-byte) jump
		.byte	start_of_setup-1f
```

代码段和数据段不一样是比较麻烦的事情所以
start_of_setup 有这样一段代码

```S
	pushw	%ds
	pushw	$6f
	lretw
```

这段代码会让 cs 和 ds 都指向 0x1000

start_of_setup 的作用就是设置栈指针,段寄存器,初始化bss,最后跳到main函数

3. code32_start

setup 会进入保护模式 然后跳转到 code32_start 这个地址是 bootloader 传递过来的
令我震惊的是 qemu 传过来的这个地址竟然是 0x100000, 要知道在进入保护模式前没有任何代码可以修改 1M 以上的内存,这里就体现出 qemu 区别于其他 bootloader 的超能力了,他可以在实模式下修改任何内存


pm.c 中回调用 protected_mode_jump

```c
protected_mode_jump(boot_params.hdr.code32_start,
			    (u32)&boot_params + (ds() << 4));
```

由于 gcc 的编译加上了参数 -mregparm=3, 函数调用传参会优先使用 eax, edx, ecx
所以这里 code32_start 传给了 eax, boot_params 的物理地址传给了 edx

pmjump.S 里面又把 boot_params 的地址传给了 esi, 最后用 `jmpl *%eax` 跳到了code32_start

```S
	movl	%edx, %esi		# Pointer to boot_params table
    # 省略
	jmpl	*%eax			# Jump to the 32-bit entrypoint
```



### 保护模式阶段

保护模式下的代码主要是进入长模式然后解压内核详细步骤如下

- 验证cpu是否支持64位 不支持则 panic
- 开启 pae
- 设置 pae 页表, 设置 cr3 但没有修改 cr0 的 PG 位
- 通过 wrmsr 指令开启 long mode
- 修改 cr0 寄存器开启分页
- 长跳转到 startup_64 进入 64 bit 代码
- 重新加载 gdt, stage1 idt
- 复制当前代码到安全的位置 防止解压缩的时候被覆盖
- 跳转到复制到的位置
- 加载 stage 2 idt
- 构造恒等内存映射
- 解压缩内核, 解压缩后的内核是 elf 格式, 还要把解压缩后的 program headers 复制到物理内存地址
- 现在可以跳转到解压缩后的内核了



1. 1MB 处为什么会有代码

因为 qemu 区别于其他 boot loader 的地方在于能够在进入保护模式前提前修改内存, 所以qemu可以读取bzImage的第一个扇区
第一个扇区的 0x1f1 的位置保存了 setup 扇区数量

```c
*((unsigned char*)(0x1f1)) + 1
```


2. startup_32

虽然名字叫 startup_32 因为我们编译的是64位内核 这个函数位于 `head_64.S`

我们现在来到了 0x100000, 也就是code32_start 所在的地址
猜测 BP 的意义是 boot params

```S
# boot_params 有一个 4byte 的空间 可以用来当栈顶指针用
	leal	(BP_scratch+4)(%esi), %esp
	call	1f
1:	popl	%ebp
	subl	$ rva(1b), %ebp
# abs(1) = abs(startup_32) + rel(1) - rel(startup_32)
# abs(startup_32) = abs(1) - (rel(1) - rel(startup_32))
```

3. 解压缩过程中可能发生的问题

- 压缩后的代码可能比压缩前的代码更大
- 解压缩过程中 原有的压缩过的那部分被覆盖
- 解压缩过程中 当前正在执行的代码被覆盖

为了预防这些问题,需要拷贝当前的代码到特定内存


4. 拷贝到的基地址如何计算

16MB + init_size - _end

```S
	/* Target address to relocate to for decompression */
	movl	BP_init_size(%rsi), %ebx
	subl	$ rva(_end), %ebx
	addq	%rbp, %rbx

	/* Set up the stack */
	leaq	rva(boot_stack_end)(%rbx), %rsp
```

这时候压缩后的内核代码也被拷贝过去了

5. 解压缩到哪里?

解压缩到 16MB


6. 如何跳过解压缩和 parse_elf?

因为解压缩和 parse_elf 容易产生段错误, 所以调试时候可以跳过, 让 qemu 直接加载 elf

注释掉代码

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

令 qemu 加载 elf

```sh
qemu-system-x86_64 -cpu 'SandyBridge' \
	    -kernel arch/x86_64/boot/bzImage \
		-m 256 -display curses \
		-device loader,file=arch/x86/boot/compressed/vmlinux.bin
```
