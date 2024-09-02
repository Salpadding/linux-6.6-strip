# kernel api

## 常用的宏

1. `__used__` 类似 `__asm__ __volatile__` 里面的 `__volatile__` 告诉编译器优化时不要把这个代码删掉 即使这段代码不会被用到


位于 include/linux/compiler_attributes.h

```c
#define __used                          __attribute__((__used__))
```

2. `__section`

位于 include/linux/compiler_attributes.h

顾名思义 就是把变量或者函数放到特定的节

```c
#define __section(section)              __attribute__((__section__(section)))
```

3. `__PASTE`


位于 include/linux/compiler_types.h

顾名思义 就是通过拼接的方式构造标识符 

```c
#define ___PASTE(a,b) a##b
#define __PASTE(a,b) ___PASTE(a,b)
```

4. `__UNIQUE_ID`

位于 include/linux/compiler-gcc.h

`__COUNTER__` 会被编译器展开成一个全局唯一的 id

所以 `__UNIQUE_ID(x)` 会展开成 `__UNIQUE_ID_x_0` `__UNIQUE_ID_x_1`

```c
#define __UNIQUE_ID(prefix) __PASTE(__PASTE(__UNIQUE_ID_, prefix), __COUNTER__)
```

5. `__ADDRESSABLE`

include/linux/compiler.h

猜测是为了防止内联优化

```c
/*
 * Force the compiler to emit 'sym' as a symbol, so that we can reference
 * it from inline assembler. Necessary in case 'sym' could be inlined
 * otherwise, or eliminated entirely due to lack of references that are
 * visible to the compiler.
 */
#define ___ADDRESSABLE(sym, __attrs) \
	static void * __used __attrs \
		__UNIQUE_ID(__PASTE(__addressable_,sym)) = (void *)&sym;
#define __ADDRESSABLE(sym) \
	___ADDRESSABLE(sym, __section(".discard.addressable"))
```

expansion example:

```c
static void* __attribute__((__used__))
    __attribute__((__section__(".discard.addressable")))
    __UNIQUE_ID_x_0 = (void*) &x;
```

6. `__stringify`

include/linux/stringify.h

```c
#define __stringify_1(x...)	#x
#define __stringify(x...)	__stringify_1(x)
```


7. `EXPORT_SYMBOL`


include/linux/export.h

```c
#define ___EXPORT_SYMBOL(sym, license, ns)		\
	.section ".export_symbol","a"		ASM_NL	\
	__export_symbol_##sym:			ASM_NL	\
		.asciz license			ASM_NL	\
		.asciz ns			ASM_NL	\
		__EXPORT_SYMBOL_REF(sym)	ASM_NL	\
	.previous
#define __EXPORT_SYMBOL(sym, license, ns)			\
	extern typeof(sym) sym;					\
	__ADDRESSABLE(sym)					\
	asm(__stringify(___EXPORT_SYMBOL(sym, license, ns)))
#define _EXPORT_SYMBOL(sym, license)	__EXPORT_SYMBOL(sym, license, "")
#define EXPORT_SYMBOL(sym)		_EXPORT_SYMBOL(sym, "")
```
 

expansion example:

```c
// .section ".export_symbol", "a" 指定下面的代码属于 .export_symbol 这个节 allocatable 
// .previous 切换回原来的节
asm(".section \".export_symbol\",\"a\" ; __export_symbol_x: ; .asciz \"\" ; .asciz \"\" ; .balign 8 ; .quad x ; .previous")
```


8. 神奇的 export.h 

以下代码实际上会 import 很多头文件

```c
#include <linux/export.h> 
```

```txt
. ./include/linux/export.h
.. ./include/linux/compiler.h
... ./include/linux/compiler_types.h
... ./arch/x86/include/generated/asm/rwonce.h
.... ./include/asm-generic/rwonce.h
..... ./include/linux/kasan-checks.h
...... ./include/linux/types.h
....... ./include/uapi/linux/types.h
........ ./arch/x86/include/generated/uapi/asm/types.h
......... ./include/uapi/asm-generic/types.h
.......... ./include/asm-generic/int-ll64.h
........... ./include/uapi/asm-generic/int-ll64.h
............ ./arch/x86/include/uapi/asm/bitsperlong.h
............. ./include/asm-generic/bitsperlong.h
.............. ./include/uapi/asm-generic/bitsperlong.h
........ ./include/uapi/linux/posix_types.h
......... ./include/linux/stddef.h
.......... ./include/uapi/linux/stddef.h
......... ./arch/x86/include/asm/posix_types.h
.......... ./arch/x86/include/uapi/asm/posix_types_64.h
........... ./include/uapi/asm-generic/posix_types.h
..... ./include/linux/kcsan-checks.h
.. ./include/linux/linkage.h
... ./include/linux/stringify.h
... ./include/linux/export.h
... ./arch/x86/include/asm/linkage.h
.... ./arch/x86/include/asm/ibt.h
```
