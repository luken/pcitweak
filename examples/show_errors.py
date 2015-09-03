#!/usr/bin/python

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys, optparse

p = optparse.OptionParser()

p.set_usage("%prog [pci_addr] [pci_addr] ...")

(options, args) = p.parse_args()

dl = PCIDevices()
for saddr in args:
    addr = PCIDeviceAddress()
    addr.parse(saddr)
    devs = dl.get(addr=addr)

    for dev in devs:
        print "%s:" % (dev.addr)
        print "  Correctable: %d" % (dev.config.read("pcie_device_status_correctable_error_detected"))
        print "  Non-Fatal: %d" % (dev.config.read("pcie_device_status_non-fatal_error_detected"))
        print "  Fatal: %d" % (dev.config.read("pcie_device_status_fatal_error_detected"))
        print "  Unsupported: %d" % (dev.config.read("pcie_device_status_unsupported_request_detected"))

        dev.config.write("pcie_device_status_correctable_error_detected", 1)
        dev.config.write("pcie_device_status_non-fatal_error_detected", 1)
        dev.config.write("pcie_device_status_fatal_error_detected", 1)
        dev.config.write("pcie_device_status_unsupported_request_detected", 1)

