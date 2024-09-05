#!python3

# see also
# qemu monitor:
# info registers
# info cpus
# info mtree
# info tlb
# info irq
# info qom-tree
# info lapic
# info pic
# info pci
# info mem
# info usb

# pass registers from qemu monitor
import struct

from debug import common
reg_parser = common.reg_parser

