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

## make prepare 生成步骤(以 arch x86 为例)

make vmlinux 依赖 make prepare, 所以这里先解释 make prepare

### 整体

整体的构建过程可以简化为


```make
archprepare: outputmakefile archheaders archscripts scripts include/config/kernel.release \
	asm-generic $(version_h) include/generated/utsrelease.h \
	include/generated/compile.h include/generated/autoconf.h remove-stale-files

prepare0: archprepare
	$(Q)$(MAKE) INDENT=$(INDENT):$@ $(build)=scripts/mod
	$(Q)$(MAKE) INDENT=$(INDENT):$@:prepare $(build)=. prepare

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

## make vmlinux

### scripts/Makefile.build

```sh
make -f ./scripts/Makefile.build obj=. need-builtin=1 need-modorder=1
```

这里的 obj=. 会让 scripts/Makefile.build include 项目根目录下的 Kbuild

Makefile.build 中默认目标的定义如下:

```make
$(obj)/: $(if $(KBUILD_BUILTIN), $(targets-for-builtin)) \
	 $(if $(KBUILD_MODULES), $(targets-for-modules)) \
	 $(subdir-ym) $(always-y)
	@:
```

可以分成三个部分

- targets-for-builtin (取决于变量KBUILD_BUILTIN)
- targets-for-modules (取决于变量KBUILD_MODULES)
- subdir-ym always-y


当 need-builtin=1 时 scripts/Makefile.lib 会对 obj-y 进行预处理

```make
ifdef need-builtin
# x/ -> x/built-in.a
obj-y		:= $(patsubst %/, %/built-in.a, $(obj-y))
else
obj-y		:= $(filter-out %/, $(obj-y))
endif
```

targets-for-builtin 的定义:

```make
# 第一层构建的 obj = . 也就是项目根目录
# 多数情况下 extra-y 是空的
targets-for-builtin := $(extra-y)

ifneq ($(strip $(lib-y) $(lib-m) $(lib-)),)
# 添加 ./lib.a
targets-for-builtin += $(obj)/lib.a
endif

ifdef need-builtin
# 添加 $(obj)/built-in.a
targets-for-builtin += $(obj)/built-in.a
endif
```

subdir-ym 的定义来自 Makefile.lib

```make
# 从 $(obj-y) 和 $(obj-m) 筛选把以 / 结尾的 然后去掉结尾的 /
subdir-ym := $(sort $(subdir-y) $(subdir-m) \
			$(patsubst %/,%, $(filter %/, $(obj-y) $(obj-m))))
```

综上所述 Kbuild 如果包含如下的定义最终展开为

targets-for-builtin: ./built-in.a  init/built-in.a usr/built-in.a
subdir-ym: init usr

```make
obj-y			+= init/
obj-y			+= usr/
```


## 常见问题

### make 死循环

遇到了一个 make prepare 产生无限递归的问题,原因是没有 copy 项目根目录下的 Kbuild

```make
prepare0: archprepare
	$(Q)$(MAKE) $(build)=scripts/mod

    # 展开为: make -f scripts/Makefile.build prepare
    # scripts/Makefile.build 会 include 根目录下的 Kbuild
	$(Q)$(MAKE) $(build)=. prepare

# All the preparing..
prepare: prepare0
```

以上的代码看上去确实是循环依赖, 因为 prepare0 回调用 prepare

```make
kbuild-file = $(or $(wildcard $(kbuild-dir)/Kbuild),$(kbuild-dir)/Makefile)
```

但是看了下 Kbuild.include 的代码, 根目录下的 Kbuild 优先级会高于 Makefile
所以实际上 make -f scripts/Makefile.build prepare 会 include Kbuild 而不是 Makefile

Kbuild 里面对 prepare 的依赖定义如下

这里会用 kernel/time/timeconst.bc 生成 include/generated/timeconst.h

```make
prepare: $(offsets-file) missing-syscalls $(atomic-checks)
	@:
```

### makefile ./ 开头的目标

make 会尝试在 ./target 和 target 之间互相匹配


```make
single_targets := ./xxx/1 ././xxx/2 ./3 ././4 \
		   xxx/5 6 7

PHONY += $(single_targets)

$(single_targets):
	@echo build $@

.PHONY: $(PHONY)

pattern_targets := 8/a.a 9/a.a 10/a.a
PHONY += $(pattern_targets)

# 模式匹配 中也可以加上 ./
# 8/a.a 可以成功的匹配上 ./%/a.a 然后 % 被替换为 8
# 然后 ./8 可以继续去匹配 8
$(pattern_targets): ./%/a.a: ./%

pattern_subdirs := $(patsubst %/a.a, %, $(pattern_targets))
PHONY += $(pattern_subdirs)

# 定义 target 8 9 10
$(pattern_subdirs): 
	@echo build subdir $@

test:
	@# 没有./开头的目标 匹配 ./ 开头的目标
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) xxx/1
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) xxx/2
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) 3
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) 4

	@# ./ 开头的目标匹配 没有 ./ 开头的目标
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ././xxx/5
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ./6
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ././7

	@# ./8/a.a -> 8/a.a -> ./8/a.a -> ./8 -> 8
	@$(MAKE) --no-print-directory -f $(MAKEFILE_LIST) ./8/a.a
```

### 递归构建基本流程

```make
# ./built-in.a 来自 targets-for-builtin
# arch/x86 arch/x86/lib 来自 subdir-ym
./: $(targets-for-builtin)  $(subdir-ym)

# $(real-obj-y) 中可能包含 $(subdir-builtin) 里面的文件
./built-in.a: $(real-obj-y) # 后面的省略

# 这里会把 subdir-builtin 重定向到 subdir-ym 
$(subdir-builtin): $(obj)/%/built-in.a: $(obj)/%

# subdir-ym 需要递归构建
$(subdir-ym):
	$(Q)$(MAKE) INDENT=$(INDENT):$@ $(build)=$@ \
	need-builtin=$(if $(filter $@/built-in.a, $(subdir-builtin)),1) \
	need-modorder=$(if $(filter $@/modules.order, $(subdir-modorder)),1) \
```

### 如何添加 cflags

Makefile.lib 中对 _c_flags 的定义如下


```make
_c_flags       = $(filter-out $(CFLAGS_REMOVE_$(target-stem).o), \
                     $(filter-out $(ccflags-remove-y), \
                         $(KBUILD_CPPFLAGS) $(KBUILD_CFLAGS) $(ccflags-y)) \
                     $(CFLAGS_$(target-stem).o))

```

所以可以这样单独给 .o 文件添加 cflag

```make
CFLAGS_version.o := -include $(obj)/utsversion-tmp.h
```

### vmlinux.a 


vmlinux.a 来自于以下文件的合并

```txt
init/built-in.a   usr/built-in.a   arch/x86/built-in.a   kernel/built-in.a   certs/built-in.a   mm/built-in.a   fs/built-in.a   ip
c/built-in.a   security/built-in.a   crypto/built-in.a   lib/built-in.a   arch/x86/lib/built-in.a   drivers/built-in.a   sound/built-in.a   virt/built-in.a
```

生成规则
