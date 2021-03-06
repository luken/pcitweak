#!/usr/bin/python

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys

FUSION_VENDOR=0x1aed
MELLANOX_VENDOR=0x15b3
PLX_VENDOR=0x10b5

def perf_check():
    bytes_size = [ 128, 256, 512, 1024, 2048, 4096 ]

    dl = PCIDevices()
    print
    for vendor in [FUSION_VENDOR, MELLANOX_VENDOR]:
        check_devs = dl.get(vendor=vendor)
        for check_dev in check_devs:
            # XXX Need to be safer with max payload, check all possible branches.
            worst_supported_maxpayload=0xffff
            dev_index = 0
            for dev in dl.walk_from_root(check_dev):
                try:
                    maxpayload_s = dev.config.read("pcie_device_capabilities_max_payload_size_supported")
                except:
                    print "WARNING: Could not get maxpayload supported for %s" % (dev.addr)
                    continue
                try:
                    maxpayload_c = dev.config.read("pcie_device_control_max_payload_size")
                except:
                    print "WARNING: Could not get maxpayload setting for %s" % (dev.addr)
                    continue
                try:
                    maxreadreq = dev.config.read("pcie_device_control_max_read_request_size")
                except:
                    print "WARNING: Could not get max readreq setting for %s" % (dev.addr)
                    continue
           
                if maxpayload_s < worst_supported_maxpayload:
                    worst_supported_maxpayload = maxpayload_s
#
                indent = "  " * dev_index
                msg = "%s%s " % (indent, dev.addr)
                if dev.vendor == FUSION_VENDOR:
                    msg += "-- Fusion Device "
                if dev.vendor == MELLANOX_VENDOR:
                    msg += "-- Mellanox Device "
                if dev.vendor == PLX_VENDOR:
                    msg += "-- PLX Device "
                if dev.is_root:
                    msg += "-- Root Device"
                print msg
                
                print "%s  MaxPayload supported %d" % (indent, bytes_size[maxpayload_s])
                print "%s  MaxPayload configured %d" % (indent, bytes_size[maxpayload_c])
                print "%s  MaxReadReq %d" % (indent, bytes_size[maxreadreq])
                if worst_supported_maxpayload == 0:
                    print "%s    Warning: MaxPayload can go no higher than 128b, performance may suffer!" % (indent)
                if maxpayload_c < worst_supported_maxpayload:
                    print "%s    Warning: MaxPayload was not configured optimally for this device, bumping up to %d" % (indent, bytes_size[worst_supported_maxpayload])
                    dev.config.write("pcie_device_control_max_payload_size", worst_supported_maxpayload)
                if maxreadreq < 3:
                    print "%s    Warning: MaxReadReq is less than 1024, bumping up" % (indent)
                    dev.config.write("pcie_device_control_max_read_request_size", 3)
                dev_index += 1
                print
            print

perf_check()


def enable_phantom(dev):
    print "Phantom Funcs Supported: 0x%x" % (dev.config.read("pcie_device_capabilities_phantom_functions_supported"))
    print "Phantom Funcs Current: 0x%x" % (dev.config.read("pcie_device_control_phantom_functions_enable"))
    dev.config.write("pcie_device_control_phantom_functions_enable", 1)
    print "Phantom Funcs New: 0x%x" % (dev.config.read("pcie_device_control_phantom_functions_enable"))

def enable_tag(dev):
    print "Extended Tag Supported: 0x%x" % (dev.config.read("pcie_device_capabilities_extended_tag_field_supported"))
    print "Extended Tag Current: 0x%x" % (dev.config.read("pcie_device_control_extended_tag_field_enable"))
    dev.config.write("pcie_device_control_extended_tag_field_enable", 1)
    print "Extended Tag New: 0x%x" % (dev.config.read("pcie_device_control_extended_tag_field_enable"))
 
