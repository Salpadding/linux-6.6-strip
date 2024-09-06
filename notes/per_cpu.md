# per cpu implement

Something interesting will shown if you objdump the vmlinux file.

The program header 'percpu' is located at physical memory between `_text` and `_end`. However, 
the virtual memory of this header is begin at '0'. 
As a result, you will never access variable defined in per cpu section by reference it directly in c code. 
If you do so, mostly you will encounter segmentation fault.

So how shall we access those variabe in per cpu section? A native solution is add an offset to memory address behind per cpu variables.
Obviously, `__per_cpu_start` seems a good option since it is the physical address of begining of per cpu section.

To allocate invididual memory for serveral cpus, 
there should exist another way to access per cpu variable rather than addition of offset `__per_cpu_start`


## per cpu 机制的实现代码

1. setup_percpu.c

```c
#define BOOT_PERCPU_OFFSET ((unsigned long)__per_cpu_load)

unsigned long __per_cpu_offset[NR_CPUS] __ro_after_init = {
	[0 ... NR_CPUS-1] = BOOT_PERCPU_OFFSET,
};
EXPORT_SYMBOL(__per_cpu_offset);
```

```c
#define PERCPU_INPUT(cacheline)						\
	__per_cpu_start = .;						\
	*(.data..percpu..first)						\
	. = ALIGN(PAGE_SIZE);						\
	*(.data..percpu..page_aligned)					\
	. = ALIGN(cacheline);						\
	*(.data..percpu..read_mostly)					\
	. = ALIGN(cacheline);						\
	*(.data..percpu)						\
	*(.data..percpu..shared_aligned)				\
	PERCPU_DECRYPTED_SECTION					\
	__per_cpu_end = .;

#define PERCPU_VADDR(cacheline, vaddr, phdr)				\
	__per_cpu_load = .;						\
	.data..percpu vaddr : AT(__per_cpu_load - LOAD_OFFSET) {	\
		PERCPU_INPUT(cacheline)					\
	} phdr								\
	. = __per_cpu_load + SIZEOF(.data..percpu);
```


## 不同的 cpu 如何访问各自的独占内存

假设你是 cpu x, 那么首先你可以通过 `__per_cpu_offset[x]` 得到一个偏移地址
