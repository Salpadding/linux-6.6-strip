# gdb inf wrapper
import struct

# memory access
class inf_clazz:
    def __init__(self, gdb):
        self.inf = gdb.inferiors()[0]

    def u32(self, off):
        return struct.unpack('<I', self.inf.read_memory(off, 4).tobytes())[0]

    def u64(self, off):
        return struct.unpack('<Q', mem)[0]

    def u64_a(self, off, n):
        return struct.unpack('<' + ('Q' * n), mem)

    def c_str(self, off, limit):
        i = 1
        while i < limit:
            bts = self.inf.read_memory(off, i).tobytes()
            if not bts[i-1]: 
                return bts[:i-1].decode('ascii')
            i += 1

        return '' 


class reg_parser:
    def __init__(self, gdb):
        self.input = gdb.execute('monitor info registers',to_string=True)
        self.gdb = gdb
        self.lines = self.input.split('\n')

    def line_of(self, prefix):
        filtered = [x for x in self.lines if x.startswith(prefix)]
        if len(filtered): return filtered[0]
        return None

    def idx_of(self, pair):
        pair = pair.split('=')
        pair = pair[1]
        pair = int(pair, 16)
        return pair

        
    def parse_all(self):
        gdt_line = self.line_of('GDT=')
        self.gdt = self.parse_desc(line=gdt_line)

        ldt_line = self.line_of('LDT=')
        ldt_idx = self.idx_of(ldt_line.split()[0])


        ldt = self.gdt[ldt_idx >> 3]

        self.ldt = None if not ldt else self.parse_desc(off=int(ldt['base'], 16),size=int(ldt['limit'], 16))
    
        regs = ['ES', 'CS', 'SS', 'DS', 'FS', 'GS']

        self.sregs = []

        for line in self.lines:
            if not any(map(lambda x: line.startswith(x + ' ='), regs)):
                continue

            splited = line.split()
            reg_name = splited[0]
            reg_idx = int(splited[1].split('=')[1], 16)

            rpl = reg_idx & 3
            entry = None

            if reg_idx & 4:
            # ldt
                entry = self.ldt[reg_idx >> 3] if self.ldt and len(self.ldt) > (reg_idx >> 3) else None
            else:
            # gdt
                entry = self.gdt[reg_idx >> 3] if self.gdt and len(self.gdt) > (reg_idx >> 3) else None

            self.sregs.append([reg_name, 'LDT' if reg_idx & 4 else 'GDT', rpl, entry])
        
        creg = [x for x in self.lines if x.startswith('CR0')]
        creg = creg[0] if creg and len(creg) else None

        if not creg: return

        self.creg = []

        bitmaps = {
                'CR0': [
                    'Protection Enable', 'Monitor Coprocessor', 'Emulation', 'Task Switched', 
                    'Extension Type', 'Numeric Error', '', '',
                    '', '', '', '',
                    '', '', '', '',
                    'Write Protect', '', 'Alignment Mask', '',
                    '', '', '', '',
                    '', '', '', '',
                    '', 'Not Write-through', 'Cache Disable', 'Paging'
                ],
                'CR4': [
                    'Virtual 8086', 'Protected-mode Virtual Interrupts', 'Time Stamp Disable', 'Debugging Extensions', 
                    'Page Size Extension', 'Physical Address Extension', 'Machine Check Exception', 'Page Global Enabled',
                    'Performance-Monitoring Counter', 'FXSAVE and FXRSTOR', 'Unmasked SIMD', 'User-Mode Instruction Prevention',
                    'Virtual Machine Extensions', 'Safer Mode Extensions', 'FSGSBASE', 'PCID Enable',
                    'XSAVE enable', 'Supervisor Mode', 'Supervisor Mode Access Prevention', 'Protection Key Enable',
                    'Enable Protection Keys for Supervisor-Mode Pages'
                ]
        }

        for cr in creg.split():
            name_val = cr.split('=')
            name = name_val[0]
            val  = int(name_val[1], 16)

            if not name in bitmaps: continue

            flags = [name]
            for i in range(0,32):
                if val & (1 << i) and len(bitmaps[name][i]):
                    flags.append(bitmaps[name][i])

        
            self.creg.append(flags)



    # parse descriptor like gdt & idt
    def parse_desc(self, **kwargs):
        inf = self.gdb.inferiors()[0]
        off = kwargs.get('off', 0)
        size = kwargs.get('size', 0)

        if size == 104:
            print('parse ldt')

        if 'line' in kwargs:
            line = kwargs['line']
            words = line.split()
            off = int(words[1], 16)
            size = int(words[2], 16) + 1

        mem = inf.read_memory(off, size).tobytes()

        entries = struct.unpack('<' + 'Q' * (len(mem) // 8), mem)
        return [self.gdt_entry(x) for x in entries]

    def gdt_entry(self, num):
        flags = []
        num_high = num >> 32
        num_low = num & 0xFFFFFFFF
        access = (num_high >> 8) & 0xff

        if access & 0x80 == 0: # not present
            return None
        
        dpl = (access >> 5) & 3 # dpl
        dc = ''

        if not (access & (1 << 4)):
            types = [
                    '', '16TSS(Avail)', 'LDT', '16TSS(Busy)', 
                    '', '', '', '', 
                    '', '32TSS(Avail)', '', '32TSS(Busy)',
                    '', '', '', ''
            ]

            if access & 0xf  >= len(types):
                print(f'index overflow {access & 0xf} invalid access {hex(access)}')
            flags.append(types[access & 0xf])
        else:
            # code or data
            if access & (1 << 3):
                flags.append('Code')
                if access & (1 << 2):
                    flags.append('Conform')

                if access & 2:
                    flags.append('R')
                else:
                    flags.append('r')

            else:
                flags.append('Data')
                if access & (1 << 2):
                    flags.append('Down') # segment grow down
                else:
                    flags.append('Up') # segment grow up

                if access & 2:
                    flags.append('RW')
                else:
                    flags.append('RO')

        if access & 1:
            flags.append('A')
        
        access = (num_high >> 20) & 0xf

        if access & 2:
            flags.append('Long')

        if access & 4:
            flags.append('32PM')
        else:
            flags.append('16PM')


        base = (num >> 16) & 0x00FFFFFF
        base = base | (num_high & 0xFF000000)
        limit = num_low & 0xFFFF
        limit = limit | (num_high & 0xf0000)

        if access & 8:
            flags.append('G')
            limit = limit << 12
        
        return {
            'base': hex(base),
            'limit': hex(limit),
            'dpl': dpl,
            'flags': flags
        }


def parse_registers():
    # parse gdt
    p = reg_parser(gdb)
    p.parse_all()


    if p.gdt:
        for i in range(0, len(p.gdt)):
            if p.gdt[i]:
                print(f'gdt[{i}]={p.gdt[i]}')

    if p.ldt:
        for i in range(0, len(p.ldt)):
            if p.ldt[i]:
                print(f'ldt[{i}]={p.ldt[i]}')

    for x in p.sregs: print(x)

    if p.creg:
        for x in p.creg: print(x)




parse_registers()
