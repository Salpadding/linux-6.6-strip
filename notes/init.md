# init

64bit 初始化过程
这里暂时不讨论 amd 内存加密以及 内核的随机重定位
假设内核加载到物理地址 0x1000000

## gdt, idt, per_cpu

暂时不讨论

## 初始化四级页表

### cr3 指向哪里

cr3 指向 early_top_pgt

- X86_CR4_PAE long mode 下必须开启
- X86_CR4_PGE 启用 global page 用于实现内核访问的页表不会被切换

```asm
	addq	$(early_top_pgt - __START_KERNEL_map), %rax
	jmp 1f

1:
	movl	$0, %ecx
	orl	$(X86_CR4_PAE | X86_CR4_PGE), %ecx
	movq	%rcx, %cr4
	movq	%rax, %cr3
```

## early_top_pgt 的内容

1. level4 部分


```c
// pgd[511] 指向 level3_kernel_pgt
pgd = fixup_pointer(&early_top_pgt, physaddr);
p = pgd + pgd_index(__START_KERNEL_map);
*p = (unsigned long)level3_kernel_pgt;
*p += _PAGE_TABLE_NOENC - __START_KERNEL_map;
```

```c
// 这里从 data 动态分配一个 4K 的内存用作 pud
pud = fixup_pointer(early_dynamic_pgts[(*next_pgt_ptr)++], physaddr);
// pgd[0] 和 pgd[1] 拥有相同的指向
// [0,512G) 和 [512G,1024G) 完全相同
pgd[i + 0] = (pgdval_t)pud + pgtable_flags;
pgd[i + 1] = (pgdval_t)pud + pgtable_flags;
```

2. level3 部分

```asm
// pud[510] 指向 level2_kernel_pgt
// pud[511] 指向 level2_fixmap_pgt
SYM_DATA_START_PAGE_ALIGNED(level3_kernel_pgt)
	.fill	L3_START_KERNEL,8,0
	/* (2^48-(2*1024*1024*1024)-((2^39)*511))/(2^30) = 510 */
	.quad	level2_kernel_pgt - __START_KERNEL_map + _KERNPG_TABLE_NOENC
	.quad	level2_fixmap_pgt - __START_KERNEL_map + _PAGE_TABLE_NOENC
SYM_DATA_END(level3_kernel_pgt)
```


```c
// 这里从 data 动态分配一个 4K 的内存用作 pmd
pmd = fixup_pointer(early_dynamic_pgts[(*next_pgt_ptr)++], physaddr);
pud[(i + 0) % PTRS_PER_PUD] = (pudval_t)pmd + pgtable_flags;
pud[(i + 1) % PTRS_PER_PUD] = (pudval_t)pmd + pgtable_flags;
```


3. level2 部分

```asm
# 恒等映射 512M
SYM_DATA_START_PAGE_ALIGNED(level2_kernel_pgt)
	PMDS(0, __PAGE_KERNEL_LARGE_EXEC, KERNEL_IMAGE_SIZE/PMD_SIZE)
SYM_DATA_END(level2_kernel_pgt)
```

level2_kernel_pgt 虽然静态恒等映射了 512M, 但是 `__startup_64` 里面 mask 掉了不在 `_text` 和 `_end` 之间的内存映射

```c
pmd = fixup_pointer(level2_kernel_pgt, physaddr);
/* invalidate pages before the kernel image */
for (i = 0; i < pmd_index((unsigned long)_text); i++)
    pmd[i] &= ~_PAGE_PRESENT;

/* fixup pages that are part of the kernel image */
for (; i <= pmd_index((unsigned long)_end); i++)
    if (pmd[i] & _PAGE_PRESENT)
        pmd[i] += load_delta;

/* invalidate pages after the kernel image */
for (; i < PTRS_PER_PMD; i++)
    pmd[i] &= ~_PAGE_PRESENT;
```

这里也是只映射了`_text` 和 `_end` 之间的内存

```c
pmd_entry = __PAGE_KERNEL_LARGE_EXEC & ~_PAGE_GLOBAL;
// physaddr = 16M = &_text
pmd_entry +=  physaddr;

for (i = 0; i < DIV_ROUND_UP(_end - _text, PMD_SIZE); i++) {
// _text 前面的部分跳过
    int idx = i + (physaddr >> PMD_SHIFT);

    pmd[idx % PTRS_PER_PMD] = pmd_entry + i * PMD_SIZE;
}
```

level2_fixmap_pgt

这个定义就是让 506 507 指向 `level1_fixmap_pgt[0]` 和 `level1_fixmap_pgt[1]`

```asm
#define FIXMAP_PMD_NUM 2
SYM_DATA_START_PAGE_ALIGNED(level2_fixmap_pgt)
	.fill	(512 - 4 - FIXMAP_PMD_NUM),8,0
	pgtno = 0
	.rept (FIXMAP_PMD_NUM)
	.quad level1_fixmap_pgt + (pgtno << PAGE_SHIFT) - __START_KERNEL_map \
		+ _PAGE_TABLE_NOENC;
	pgtno = pgtno + 1
	.endr
	/* 6 MB reserved space + a 2MB hole */
	.fill	4,8,0
SYM_DATA_END(level2_fixmap_pgt)
```


4. level1 部分

level1 部分暂时没有看到有赋值操作
假设 _end - _text 对齐到 2M = 10M

最终概括

- 高内存部分

```c
// vstart-vend 映射到 [16M,26M)
unsigned long vstart = (0xffffUL << 48) | (511UL << 39) | (510UL << 30) | (8UL << 21);
unsigned long vend = vstart + 10 << 20;
```

- 低内存部分 2 x 2


```c
// [16M,26M) -> [16M, 26M)
// [16M+1G, 26M+1G) -> [16M, 26M)
// [16M + 512G,26M + 512G) -> [16M, 26M)
// [16M + 513G,26M + 513G) -> [16M, 26M)
```


## 跳转到高内存

```asm
movq	$1f, %rax
jmp	*%rax
```
