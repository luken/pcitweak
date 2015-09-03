#!/usr/bin/python

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys
import trace

def walk_all_devices():
    dl = PCIDevices()
    for pci_dev in dl.devices:
        aspm_current = None
        try:
            pci_dev.config.enumerate()
            aspm_current = pci_dev.config.read("pcie_link_control_aspm_control")
        except Exception, e:
            #print "Error reading ASPM state for device %s: %s" % (pci_dev.addr, e)
            continue

        print "ASPM for %s is 0x%x" % (pci_dev.addr, aspm_current)
        if aspm_current != 0:
            print "      disabeling ASPM"
            pci_dev.config.write("pcie_link_control_aspm_control", 0)

walk_all_devices()
