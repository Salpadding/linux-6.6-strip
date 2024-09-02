# 测试 Makefile.lib 里面的函数
targets := 

obj-y := foo.o bar.o

foo-objs := foo1.o foo2.o foo3.o
foo-y := foo4.o foo5.o

bar-objs := barr1.o bar2.o bar3.o

# foo3.o 最多展开到 foo3.o, foo3.o 不会再展开成 foo31.o
foo3-objs := foo31.o foo32.o foo33.o
bar3-objs := bar31.o bar32.o bar33.o


include scripts/Makefile.lib

PHONY += all

# suffix-search 仅支持单个参数 例如 foo.o 或者 bar.o
# suffix-search 展开过程可以解释为
# foo.o -> foo-y foo-objs -> $(foo-y) $(foo-objs)

# real-search 支持多个参数 而且若 foo.o 可以展开 那么结果就不会包含 foo.o 
# foo.o bar.o -> foo-objs bar-objs foo-y bar-y -> $(foo-objs) $(bar-objs) $(foo-y) $(bar-y)

all:
	@echo suffix-search foo.o =
	@echo $(call suffix-search, foo.o, .o, -objs -y)
	@echo real-obj-y =
	@echo $(call real-search, $(obj-y), .o, -objs -y)


.PHONY: $(PHONY)
