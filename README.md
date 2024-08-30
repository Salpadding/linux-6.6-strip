# README

## 简介

暂时只计划支持在 x86_64 的 linux 系统上编译 ARCH=x86_64 的内核

## 修改记录
- 2024-08-29
  
主要改动是使用INDENT 环境变量追踪 make 的递归深度和当前的 target
目前可以 make defconfig, make nconfig, make mrproper 三步走了 下一步是尝试构建一些设备驱动以及添加 kbuild 相关的介绍


## kbuild 介绍

kbuild 运用了很多值得学习的 makefile 的技巧

###  用宏定义多个目标 

位于 scripts/kconfig/Makefile

```make
config-prog	:= conf
menuconfig-prog	:= mconf
nconfig-prog	:= nconf
gconfig-prog	:= gconf
xconfig-prog	:= qconf

# 这里用 $$< 是因为后面用到了 eval 函数, 这样 eval 可以正确的读到 $<
# 把 make nconfig 定义为 shell 命令 scripts/kconfig/nconf Kconfig
# 对 menuconfig, gconfig, xconfig 也是同理
define config_rule
PHONY += $(1)
$(1): $(obj)/$($(1)-prog)
	$(Q)$$< $(silent) $(Kconfig)

PHONY += build_$(1)
build_$(1): $(obj)/$($(1)-prog)
endef

$(foreach c, config menuconfig nconfig gconfig xconfig, $(eval $(call config_rule,$(c))))
```


### 单独定义 CFLAGS 和 LDFLAGS

```make
target-stem = $(basename $(patsubst $(obj)/%,%,$@))

cmd_host-cmulti	= $(HOSTCC) $(KBUILD_HOSTLDFLAGS) -o $@ \
      $(addprefix $(obj)/, $($(target-stem)-objs)) \
      $(KBUILD_HOSTLDLIBS) $(HOSTLDLIBS_$(target-stem))

# 这些会被 Makefile.host 中的 cmd_host-multi 读到
HOSTLDLIBS_nconf       = $(call read-file, $(obj)/nconf-libs)
HOSTCFLAGS_nconf.o     = $(call read-file, $(obj)/nconf-cflags)
HOSTCFLAGS_nconf.gui.o = $(call read-file, $(obj)/nconf-cflags)

cmd_conf_cfg = $< $(addprefix $(obj)/$*conf-, cflags libs bin); touch $(obj)/$*conf-bin

# 生成 nconf-cflags nconf-libs nconf-bin
$(obj)/%conf-cflags $(obj)/%conf-libs $(obj)/%conf-bin: $(src)/%conf-cfg.sh
	@echo $(INDENT) $< $(addprefix $(obj)/$*conf-, cflags libs bin) 
	@echo $(INDENT) touch $(obj)/$*conf-bin
	$(call cmd,conf_cfg)
```

### 定义依赖

例如把 nconf 的依赖定义为 $(nconf-objs)

```make
# $(call suffix-search,nconf,, -objs)
suffix-search = $(strip $(foreach s, $3, $($(1:%$(strip $2)=%$s))))

# $(call multi_depend, nconf,,-objs)
define multi_depend
$(foreach m, $1, \
	$(eval $m: \
	$(addprefix $(obj)/, $(call suffix-search, $(patsubst $(obj)/%,%,$m), $2, $3))))
endef
```

### tinyconfig 执行流

1. 依赖关系描述


```yml
tinyconfig:
    deps:
        - scripts_basic # from Makefile %config

    receipe:
        - make -f ./Makefile allnoconfig
        - make -f ./Makefile tiny.config

allnoconfig:
    deps:
        - scripts_basic # from Makefile %config
        - scripts/kconfig/conf # from scripts/kconfig/Makefile $(simple-targets): $(obj)/conf

    receipe:
        - scripts/kconfig/conf --allnoconfig Kconfig

olddefconfig:
    deps:
        - scripts_basic # from Makefile %config
        - scripts/kconfig/conf # from scripts/kconfig/Makefile $(simple-targets): $(obj)/conf

    receipe:
        - scripts/kconfig/conf --olddefconfig Kconfig

tiny.config:
    deps:
        - scripts_basic # from Makefile %config
        - scripts/kconfig/conf # scripts/kconfig/Makefile %.config

    receipe:
        - scripts/kconfig/merge_config.sh -m .config  ./kernel/configs/tiny.config
        - make -f ./Makefile olddefconfig


```

2. 解释

make tinyconfig 会依次执行 1. 构建 allnoconfig 生成最小化配置 .config 2. 把 kernel/configs/tiny.config 合并到 .config 3. make olddefconfig


### make clean 执行流

1. 依赖关系描述

```yml
clean-dirs:
    value:
        - _clean_.
        - _clean_Documentation
        - _clean_arch/x86/math-emu
        - _clean_arch/x86/pci
        - _clean_arch/x86/power
        - _clean_arch/x86/video
        - archclean
        - vmlinuxclean
        - resolve_btfids_clean
    receipe:
        - make -f ./scripts/Makefile.clean obj=value.trim('_clean_')
    
```

2. 执行步骤

`_clean_.` 比较容易理解 因为没有定义 subdir-y, subdir-m, subdir- 等变量, 这些变量会触发递归的 clean


递归 clean 

```make
__clean-files	:= \
	$(clean-files) $(targets) $(hostprogs) $(userprogs) \
	$(extra-y) $(extra-m) $(extra-) \
	$(always-y) $(always-m) $(always-) \
	$(hostprogs-always-y) $(hostprogs-always-m) $(hostprogs-always-) \
	$(userprogs-always-y) $(userprogs-always-m) $(userprogs-always-)

__clean-files   := $(filter-out $(no-clean-files), $(__clean-files))

__clean-files   := $(wildcard $(addprefix $(obj)/, $(__clean-files)))

# subdir-ymn = subdir-y subdir-m subdir- 以及 / 结尾的 obj-y obj-m obj-
subdir-ymn := $(sort $(subdir-y) $(subdir-m) $(subdir-) \
		$(patsubst %/,%, $(filter %/, $(obj-y) $(obj-m) $(obj-))))

# Add subdir path
subdir-ymn	:= $(addprefix $(obj)/,$(subdir-ymn))


# 删除文件 
quiet_cmd_clean = CLEAN   $(obj)
      cmd_clean = printf '$(obj)/%s ' $(patsubst $(obj)/%,%,$(__clean-files)) | xargs rm -rf

__clean: $(subdir-ymn)
	@echo $(INDENT) remove files: $(__clean-files)
ifneq ($(strip $(__clean-files)),)
	$(call cmd,clean)
endif
	@:
```


3. clean-dirs 的来源

arch/x86/Makefile 定义了 libs-y, drivers-* 这样的变量

```make
libs-y  += arch/x86/lib/

# drivers-y are linked after core-y
drivers-$(CONFIG_MATH_EMULATION) += arch/x86/math-emu/
drivers-$(CONFIG_PCI)            += arch/x86/pci/

# suspend and hibernation support
drivers-$(CONFIG_PM) += arch/x86/power/

drivers-$(CONFIG_FB_CORE) += arch/x86/video/
```

顶层的 Makefile 会 include arch/x86/Makefile 然后生成 clean-dirs
因为 make clean 的 need-config 没有被定义所以 autoconf 不会被 include
所以 `drivers-$(CONFIG_PCI)` 在 make clean 的上下文里面展开为 `driver-`

```make
clean-dirs	:= $(sort . Documentation \
		     $(patsubst %/,%,$(filter %/, $(core-) \
			$(drivers-) $(libs-))))
```

## vmlinux 生成步骤(以 arch x86 为例)

### 整体

整体的构建过程可以简化为


```make
archprepare: outputmakefile archheaders archscripts scripts include/config/kernel.release \
	asm-generic $(version_h) include/generated/utsrelease.h \
	include/generated/compile.h include/generated/autoconf.h remove-stale-files

prepare0: archprepare
	$(Q)$(MAKE) $(build)=scripts/mod
	$(Q)$(MAKE) $(build)=. prepare

prepare: prepare0

$(build-dir): prepare
	$(Q)$(MAKE) INDENT=$(INDENT):$@ $(build)=$@ need-builtin=1 need-modorder=1 $(single-goals)
```


### archheaders

定义位于 arch/x86/Makefile

目的是生成系统调用相关的头文件 位于 

```sh
SRCARCH=x86
arch/$(SRCARCH)/include/generated/asm
arch/$(SRCARCH)/include/generated/uapi/asm
```

执行的是这个命令 也就是读取 arch/x86/entry/syscalls 里面的 Makefile

```sh
make -f ./scripts/Makefile.build obj=arch/x86/entry/syscalls all
```

### archscripts

定义位于 arch/x86/Makefile

```sh
make -f ./scripts/Makefile.build obj=arch/x86/tools relocs
```

主要是一些 host program, 会议来到 tools/include/tools 里面的头文件

### scripts

定义位于 Makefile 用 ^scripts: 可以搜到

```make
PHONY += scripts
scripts: scripts_basic scripts_dtc
	$(Q)$(MAKE) $(build)=$(@)
```

这个依赖 scripts_dtc, scripts_dtc 的定义如下

```make
PHONY += scripts_dtc
scripts_dtc: scripts_basic
	$(Q)$(MAKE) $(build)=scripts/dtc
```

如果没有配置 CONFIG_DTC scripts/dtc/Makefile 不会产生需要构建的目标

### include/config/kernel.release

```make
ifeq ($(origin KERNELRELEASE),file)
# filechk_kernel.release 传参给 filechk
filechk_kernel.release = $(srctree)/scripts/setlocalversion $(srctree)
else
filechk_kernel.release = echo $(KERNELRELEASE)
endif

define filechk
	$(check-FORCE)
	$(Q)set -e;						\
	mkdir -p $(dir $@);					\
	trap "rm -f $(tmp-target)" EXIT;			\
	{ $(filechk_$(1)); } > $(tmp-target);			\
	if [ ! -r $@ ] || ! cmp -s $@ $(tmp-target); then	\
		$(kecho) '  UPD     $@';			\
		mv -f $(tmp-target) $@;				\
	fi
endef

# Store (new) KERNELRELEASE string in include/config/kernel.release
include/config/kernel.release: FORCE
	$(call filechk,kernel.release)
```

最终展开成 shell

```sh
set -e
mkdir -p include/config/
trap "rm -f include/config/.tmp_kernel.release" EXIT
{ ./scripts/setlocalversion .; } > include/config/.tmp_kernel.release
if [ ! -r include/config/kernel.release ] || ! cmp -s include/config/kernel.release include/config/.tmp_kernel.release; then 
echo '  UPD     include/config/kernel.release'
mv -f include/config/.tmp_kernel.release include/config/kernel.release
fi
```

### asm-generic

先分析 uapi-asm-generic, 因为 asm-generic 依赖这个

```sh
make -f ./scripts/Makefile.asm-generic obj=arch/x86/include/generated/uapi/asm generic=include/uapi/asm-generic
```

scripts/Makefile.asm-generic 

```make
# 简而言之就是读取 $(srctree)/$(generic)/Kbuild 里面的 mandatory-y 然后在 $(obj) 生成对应的头文件 
quiet_cmd_wrap = WRAP    $@
      cmd_wrap = echo "\#include <asm-generic/$*.h>" > $@

quiet_cmd_remove = REMOVE  $(unwanted)
      cmd_remove = rm -f $(unwanted)

all: $(generic-y)
	$(if $(unwanted),$(call cmd,remove))
	@:

$(obj)/%.h:
	$(call cmd,wrap)
```

asm-generic 也是同理 只不过 generic 变量替换成了 include/asm-generic


### $(version_h)

这个展开后= include/generated/uapi/linux/version.h

```make
# 生成过程
define filechk_version.h
	if [ $(SUBLEVEL) -gt 255 ]; then                                 \
		echo \#define LINUX_VERSION_CODE $(shell                 \
		expr $(VERSION) \* 65536 + $(PATCHLEVEL) \* 256 + 255); \
	else                                                             \
		echo \#define LINUX_VERSION_CODE $(shell                 \
		expr $(VERSION) \* 65536 + $(PATCHLEVEL) \* 256 + $(SUBLEVEL)); \
	fi;                                                              \
	echo '#define KERNEL_VERSION(a,b,c) (((a) << 16) + ((b) << 8) +  \
	((c) > 255 ? 255 : (c)))';                                       \
	echo \#define LINUX_VERSION_MAJOR $(VERSION);                    \
	echo \#define LINUX_VERSION_PATCHLEVEL $(PATCHLEVEL);            \
	echo \#define LINUX_VERSION_SUBLEVEL $(SUBLEVEL)
endef
```

### include/generated/utsrelease.h

生成方法

```make
include/generated/utsrelease.h: include/config/kernel.release FORCE
	$(call filechk,utsrelease.h)

uts_len := 64
define filechk_utsrelease.h
	if [ `echo -n "$(KERNELRELEASE)" | wc -c ` -gt $(uts_len) ]; then \
	  echo '"$(KERNELRELEASE)" exceeds $(uts_len) characters' >&2;    \
	  exit 1;                                                         \
	fi;                                                               \
	echo \#define UTS_RELEASE \"$(KERNELRELEASE)\"
endef
```

include/generated/compile.h 也是同理 

```make
filechk_compile.h = $(srctree)/scripts/mkcompile_h \
	"$(UTS_MACHINE)" "$(CONFIG_CC_VERSION_TEXT)" "$(LD)"
```

### include/generated/autoconf.h

这个通过 syncconfig 生成

### remove-stale-files

似乎是删除临时文件的


