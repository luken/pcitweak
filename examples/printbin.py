#!/usr/bin/python

from pcitweak.bitstring import BitString

for n in range(0x10):
    b = BitString(uint=n, length=4)
    print "  % 3d  0x%02x  %s" % (n, n, b.bin)
