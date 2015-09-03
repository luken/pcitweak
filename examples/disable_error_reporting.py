#!/usr/bin/python

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys, optparse

FUSION_VENDOR=0x1aed
HP_VENDOR=0x103c
FUSION_IODIMM_GEN1=0x1005
FUSION_IODIMM_GEN2=0x2001

def main():
    dl = PCIDevices()
    #fusion_devs = dl.get(device=FUSION_IODIMM_GEN1)
    fusion_devs = dl.get(vendor=FUSION_VENDOR)
    for fdev in fusion_devs:
        print ""
        print ""
        for dev in list(dl.walk_to_root(fdev))[:-1]:
            # [:-1], don't want to futs with 00:00.0
            print ""
            disable_pcie_error_prop(dev)
            disable_pcie_serr(dev)
            disable_legacy_pci_error(dev)
            disable_legacy_pci_serr(dev)

def setreg(dev, reg, value=0, padding=2):
    print " "*padding, reg, dev.config.read(reg), "(%s)" % (value)
    dev.config.write(reg, value)

def disable_pcie_error_prop(dev):
    print "Disabling PCI-E Error propigation on device:", dev.addr
    setreg(dev, 'pcie_device_control_correctable_error_reporting_enabled')
    setreg(dev, 'pcie_device_control_non-fatal_error_reporting_enabled')
    setreg(dev, 'pcie_device_control_fatal_error_reporting_enabled')
    setreg(dev, 'pcie_device_control_unsupported_request_reporting_enabled')

def disable_pcie_serr(dev):
    print "Disabling PCI-E SERR:", dev.addr
    setreg(dev, "pcie_root_control_serr_correctable")
    setreg(dev, "pcie_root_control_serr_non-fatal")
    setreg(dev, "pcie_root_control_serr_fatal")

def disable_legacy_pci_error(dev):
    print "Disabling legacy PCI misc error reporting", dev.addr
    setreg(dev, 'common_command_parity_error_response')
    if 'type1_bridge_control_parity_error_response_enable' in dev.config:
        setreg(dev, 'type1_bridge_control_parity_error_response_enable')

def disable_legacy_pci_serr(dev):
    print "Disabling legacy PCI SERR", dev.addr
    setreg(dev, "common_command_serr_enable")
    if 'type1_bridge_control_serr_enable' in dev.config:
        setreg(dev, 'type1_bridge_control_serr_enable')
    if 'type1_bridge_control_discard_timer_serr_enable' in dev.config:
        setreg(dev, 'type1_bridge_control_discard_timer_serr_enable')

if __name__ == "__main__":
    main()
