


#class ConfigSpace(ctypes.LittleEndianStructures):
#    def __init__(self, buffer, offset, regs):
#

#
#class Config:
#    def __init__(self, device_parent=None):
#        self.device = device_parent
#        self.config_data = None
#        self.config_data_filename = None
#
#    def _get_config_data(self):
#        if self.config_data_filename is not None:
#            
#    def _put_config_data(self, offset, value):
#        # XXX Need the data 
#
#    def build(self):
#        self._get_config_data()
#        
#
#class Device:
#    def __init__(self, devices_parent=None):
#        self.devices = devices_parent
#        self.parent = None
#        self.children = []
#        self.is_root = False
#        self.address = None
#        self.device = None
#        self.vender = None
#
#class Devices:
#    def __init__(self):
#        self.devices = []
#
#    def build(self):
#        basedir = "/sys/bus/devices/pci"
#        devs = 
#        
#    def roots(self):
#        ret = []
#        for d in self.devices:
#            if d.is_root:
#                ret.append(d)
#        return ret
#
#    def get(self, *args):
#        # address, device, vendor, subsystem_device, subsystem_vendor, is_root
#        rm = [d for d in self.devices if d not in args]
#
##        if address is not None:
##            for d in self.devices:
##                if address != d.address:
##                    if d not in rm:
##                        rm.append(d)
##
##        if device is not None:
##            for d in self.devices:
##                if device != d.device:
##                    if d not in rm:
##                        rm.append(d)
##
##        if vendor is not None:
##            for d in self.devices:
##                if vendor != d.vendor:
##                    if d not in rm:
##                        rm.append(d)
##
##        if subsystem_device is not None:
##            for d in self.devices:
##                if subsystem_device != d.subsystem_device:
##                    if d not in rm:
##                        rm.append(d)
##
##        if subsystem_vendor is not None:
##            for d in self.devices:
##                if subsystem_vendor != d.subsystem_vendor:
##                    if d not in rm:
##                        rm.append(d)
##
##        if is_root is not None:
##            for d in self.devices:
##                if is_root != d.is_root:
##                    if d not in rm:
##                        rm.append(d)
#
#        ret = []
#        for d in self.devices:
#            if d is not in rm:
#                ret.append(d)
#
#        return ret
#
#
#
#
#
#
#
#        
#
#
#        
