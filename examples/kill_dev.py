#!/usr/bin/python

# Picks an ioDimm and walks up the tree towards the root device.  Kills the
# link at the ioDimm's immideate parent, causing the ioDimm to become
# unreachable

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys

FUSION_VENDOR=0x1aed
MELLANOX_VENDOR=0x15b3
PLX_VENDOR=0x10b5

FUSION_IODIMM_GEN1=0x1005

def kill_dev():
    bytes_size = [ 128, 256, 512, 1024, 2048, 4096 ]

    dl = PCIDevices()

    fusion_devs = dl.get(device=FUSION_IODIMM_GEN1)
    # Try to get fioa to kill
    fusion_devs.sort(key=lambda m: str(m.addr))

    kill_dimm = fusion_devs[0]
    print ""
    print "Killing device '%s' using link control at parent '%s'" % (kill_dimm.addr, kill_dimm.parent.addr)
    kill_dimm.parent.config.write("pcie_link_control_link_disable", 1)

kill_dev()

