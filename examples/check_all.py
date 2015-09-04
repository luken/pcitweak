#!/usr/bin/python

from pcitweak.devices import PCIDevices, PCIDeviceAddress

import os, sys

FUSION_VENDOR=0x1aed
MELLANOX_VENDOR=0x15b3
PLX_VENDOR=0x10b5

def check_power(dev, at_least_watts=25):
    watts = dev.parent.config.get_pcie_slot_cap_watts()
    if watts < at_least_watts:
        print "Warning: Device %s's upstream port (%s) reports limited power, %d watts" % (dev.addr, dev.parent.addr, watts)
        dev.parent.config.set_pcie_slot_cap_watts(at_least_watts)
        new_watts = dev.parent.config.get_pcie_slot_cap_watts()
        if new_watts != watts:
            print "ERROR:   Tried to update to %d watts.  This should not be possible, watts changed from %d to %d" % (at_least_watts, watts, new_watts)

    #print "Device %s's parent (%s) has slot power limited to %.02f" % (dev.addr, dev.parent.addr, watts)
    print

def check_maxpayload(check_dev, dl):
    print "Checking Max Payload setting"
    bytes_size = [ 128, 256, 512, 1024, 2048, 4096 ]
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

        indent = "  " * dev_index
        msg = "%s%s " % (indent, dev.addr)
        print msg

        print "%s  MaxPayload supported %d" % (indent, bytes_size[maxpayload_s])
        print "%s  MaxPayload configured %d" % (indent, bytes_size[maxpayload_c])
        if maxpayload_c != maxpayload_s:
            print "%s  TUNING: Setting MaxPayload to %d" % (indent, bytes_size[maxpayload_s])
            dev.config.write("pcie_device_control_max_payload_size", maxpayload_s)
        dev_index += 1
        print
    print

def check_maxreadreq(check_dev, dl):
    print "Checking Max Read Request setting"
    bytes_size = [ 128, 256, 512, 1024, 2048, 4096 ]
    MAXREADREQ = 4096
    dev_index = 0
    for dev in dl.walk_from_root(check_dev):
        try:
            maxreadreq = dev.config.read("pcie_device_control_max_read_request_size")
        except:
            print "WARNING: Could not get max readreq setting for %s" % (dev.addr)
            continue

        indent = "  " * dev_index
        msg = "%s%s " % (indent, dev.addr)
        print msg

        print "%s  MaxReadReq %d" % (indent, bytes_size[maxreadreq])
        if bytes_size[maxreadreq] != MAXREADREQ:
            print "%s  TUNING: Setting MaxReadReq to %d" % (indent, MAXREADREQ)
            dev.config.write("pcie_device_control_max_read_request_size", bytes_size.index(MAXREADREQ))
        dev_index += 1
        print
    print

def check_errors(dev):
    print "Checking error flags"
    corr = dev.config.read("pcie_device_status_correctable_error_detected")
    non_fatal = dev.config.read("pcie_device_status_non-fatal_error_detected")
    fatal = dev.config.read("pcie_device_status_fatal_error_detected")
    unsup = dev.config.read("pcie_device_status_unsupported_request_detected")

    if corr:
        print "  WARNING: Correctable errors detected, clearing"
        dev.config.write("pcie_device_status_correctable_error_detected", 1)
    if non_fatal:
        print "  WARNING: Non-fatal errors detected, clearing"
        dev.config.write("pcie_device_status_non-fatal_error_detected", 1)
    if fatal:
        print "  WARNING: Fatal errors detected, clearing"
        dev.config.write("pcie_device_status_fatal_error_detected", 1)
    if unsup:
        print "  WARNING: Unsupported Request errors detected, clearing"
        dev.config.write("pcie_device_status_unsupported_request_error_detected", 1)
    print

def check_phantom(dev):
    cap = dev.config.read("pcie_device_capabilities_phantom_functions_supported")
    stat = dev.config.read("pcie_device_control_phantom_functions_enable")
    print "Checking phantom funcs setting, currently %d" % (stat)
    if cap != stat:
        print "TUNING: Phantom Funcs supported is %d but setting is %d, updating to supported value" % (cap, stat)
        dev.config.write("pcie_device_control_phantom_functions_enable", 1)
    print

def check_tag(dev):
    cap = dev.config.read("pcie_device_capabilities_extended_tag_field_supported")
    stat = dev.config.read("pcie_device_control_extended_tag_field_enable")
    print "Checking extended tag support, currently %d" % (stat)
    if cap != stat:
        print "TUNING: Extended tag supported is %d but setting is %d, updating to supported value" % (cap, stat)
        dev.config.write("pcie_device_control_tag_field_enable", 1)
    print

def select_devices():
    dl = PCIDevices()
    for vendor in [FUSION_VENDOR, MELLANOX_VENDOR]:
        check_devs = dl.get(vendor=vendor)
        for check_dev in check_devs:
            print "### Checking device %s" % (check_dev.addr)
            check_power(check_dev)
            check_maxpayload(check_dev, dl)
            check_maxreadreq(check_dev, dl)
            check_errors(check_dev)
            check_phantom(check_dev)
            check_tag(check_dev)

select_devices()
