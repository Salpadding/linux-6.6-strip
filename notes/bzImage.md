# bzIamge 格式

## vmlinux 的由来

```make
# 来自
vmlinux.a: built-in.a
    @# 这一步没有什么特别的就是用归档程序 ar 把多个文件合并成一个文件

# 来自 Makefile.vmlinux_o
vmlinux.o: vmlinux.a lib/lib.a arch/x86/lib/lib.a
    @# vmlinux.o 是一个可重定位的文件 后续还需要静态链接
    ld -m elf_x86_64 -z noexecstack --no-warn-rwx-segments -r -o vmlinux.o  --whole-archive vmlinux.a --no-whole-archive --start-group lib/lib.a arch/x86/lib/lib.a --end-group
    ./tools/objtool/objtool --hacks=jump_label --hacks=noinstr --ibt --static-call --uaccess --link vmlinux.o


# 来自 Makefile.vmlinux
# 1. 链接
# ld -m elf_x86_64 -z noexecstack --no-warn-rwx-segments -z max-page-size=0x200000 --build-id=sha1 --orphan-handling=warn --script=./arch/x86/kernel/vmlinux.lds -o vmlinux --whole-archive vmlinux.o init/version-timestamp.o --no-whole-archive --start-group --end-group
# 2. 生成 .map 文件
# 3. 执行 Makefile.postlink
vmlinux: vmlinux.o arch/x86/kernel/vmlinux.lds scripts/link-vmlinux.sh 

    scripts/link-vmlinux.sh "ld" "-m elf_x86_64 -z noexecstack --no-warn-rwx-segments" "-z max-page-size=0x200000 --build-id=sha1 --orphan-handling=warn"
    make -f ./arch/x86/Makefile.postlink vmlinux
```




## bzImage 依赖关系


```make
bzImage: vmlinux
    make obj=arch/x86/boot -f scripts/Makefile.build arch/x86/boot/bzImage
```


实际上构建 bzImage 的规则是写在 arch/x86/boot/Makefile 里面的

规则如下

```make
# 这里 $(obj) 展开为 arch/x86/boot

# 压缩,合并的工作由 arch/x86/boot/tools/build 完成
cmd_image = $(obj)/tools/build $(obj)/setup.bin $(obj)/vmlinux.bin \
			       $(obj)/zoffset.h $@ $($(quiet)redirect_image)

$(obj)/bzImage: $(obj)/setup.bin $(obj)/vmlinux.bin $(obj)/tools/build FORCE
	$(call if_changed,image)
	@$(kecho) 'Kernel: $@ is ready' ' (#'$(or $(KBUILD_BUILD_VERSION),`cat .version`)')'


OBJCOPYFLAGS_vmlinux.bin := -O binary -R .note -R .comment -S
$(obj)/vmlinux.bin: $(obj)/compressed/vmlinux FORCE
	$(call if_changed,objcopy)


$(obj)/compressed/vmlinux: FORCE
	$(Q)$(MAKE) $(build)=$(obj)/compressed $@

```


### compressed/Makefile

这一步会对项目根目录下的 vmlinux 处理 最重要的一步是生成 piggy.o

顺序

```make
vmlinux.bin:  vmlinux

$(obj)/vmlinux.bin.xz: vmlinux.bin

hostprogs	:= mkpiggy

$(obj)/piggy.S: $(obj)/vmlinux.bin.xz mkpiggy

$(obj)/vmlinux: piggy.o 
```


```makefile
# 注意这里生成的不是根目录下的 vmlinux
$(obj)/vmlinux: $(vmlinux-objs-y) $(vmlinux-libs-y)
    ld -m elf_x86_64 --no-ld-generated-unwind-info  -pie  --no-dynamic-linker --orphan-handling=warn -z noexecstack --no-warn-rwx-segments -T arch/x86/boot/compressed/vmlinux.lds $^

# 注意这一步是从根目录下的 vmlinux 生成出 $(obj)/vmlinux.bin
vmlinux.bin: vmlinux
    objcopy  -R .comment -S vmlinux arch/x86/boot/compressed/vmlinux.bin

# 这里也是对根目录下的 vmlinux.bin 压缩
vmlinux.bin.xz: vmlinux.bin
    { cat arch/x86/boot/compressed/vmlinux.bin | sh ./scripts/xz_wrap.sh; printf \\000\\000\\000\\000; } > arch/x86/boot/compressed/vmlinux.bin.xz


# piggy.S 的前置依赖是 $(obj)/vmlinux.xz 和 mkpiggy
# mkpiggy 从 mkpiggy.c 生成
$(obj)/piggy.S: $(obj)/vmlinux.bin.$(suffix-y) $(obj)/mkpiggy FORCE
	$(call if_changed,mkpiggy)

# mkpiggy vmlinux.bin.xz > piggy.S
```
