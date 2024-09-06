tlb = gdb.execute('monitor info tlb',to_string=True)

lines = []
for line in tlb.split('\n'):
    if not ':' in line: continue

    splited = line.split(':')
    vaddr = int(splited[0], 16)
    paddr_attr = splited[1].split()
    paddr = int(paddr_attr[0], 16)
    # page size = 2MB when P is set
    page_size = 0x200000  if paddr_attr[1][2] == 'P' else 0x1000
    attr = paddr_attr[1][-4:len(paddr_attr[1])]

    lines.append({
        'vaddr': vaddr,
        'paddr': paddr,
        'attr': attr,
        'page_size': page_size,
    })


vstart = None
vend = None
pstart = None
pend = None
attr = None
maps = []

def merge():
    global vstart, vend, pstart, pend, attr, maps
    if vstart == None:
        return

    maps.append({
        'vstart': hex(vstart),
        'vend': hex(vend),
        'pstart': hex(pstart),
        'pend': hex(pend),
        'size': hex(pend - pstart),
        'attr': attr
    })
    vstart = vend = pstart = pend = attr = None

if not len(lines):
    exit(0)



for line in lines:
    if vstart == None:
        vstart = line['vaddr']
        vend = vstart + line['page_size']
        pstart = line['paddr']
        pend = pstart + line['page_size']
        attr = line['attr']
        continue 

    if line['vaddr'] == vend and \
            line['paddr'] == pend and \
            line['attr'] == attr:

        vend = vend + line['page_size']
        pend = pend + line['page_size']
        continue

    merge()


merge()

for m in maps: print(m)
