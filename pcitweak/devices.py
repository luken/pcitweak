import os, re
from config import PCIConfigSpace, PCIConfigSpaceAccess

class PCIDeviceAddress:
    def __init__(self, domain=None, bus=None, device=None, func=None):
        self.domain = domain
        self.bus = bus
        self.device = device
        self.func = func

    def __str__(self):
        return "%04x:%02x:%02x.%x" % (self.domain, self.bus, self.device, self.func)

    def __eq__(self, other):
        if ( self.domain == other.domain and
             self.bus == other.bus and
             self.device == other.device and
             self.func == other.func
          ):
            return True
        else:
            return False

    def __ne__(self, other):
        if self.__eq__(other):
            return False
        else:
            return True

    def parse(self, string, is_hex_not_decimal=True):
        if is_hex_not_decimal:
            base = 16
        else:
            base = 10

        # xxxx:xx:xx.xx form
        m = re.match("^([0-9a-f]*):([0-9a-f]*):([0-9a-f]*)\.([0-9a-f]*).*", string, re.I)
        if m is not None:
            self.domain = int(m.group(1), base)
            self.bus = int(m.group(2), base)
            self.device = int(m.group(3), base)
            self.func = int(m.group(4), base)
            return

        # xx:xx.xx form
        m = re.match("^([0-9a-f]*):([0-9a-f]*)\.([0-9a-f]*).*", string, re.I)
        if m is not None:
            self.domain = 0
            self.bus = int(m.group(1), base)
            self.device = int(m.group(2), base)
            self.func = int(m.group(3), base)
            return
    
        raise ValueError("Provided PCI address '%s' is not parsable" % (string))

class PCIDevice:
    def __init__(self, devices_parent=None):
        self.devices = devices_parent
        # If parent points to itself, it's a root device
        self.parent = None
        self.children = []
        self.is_root = False
        self.addr = PCIDeviceAddress()
        self.vendor = None
        self.device = None
        self.sub_vendor = None
        self.sub_device = None
        self.config = None

class PCIDevices:
    def __init__(self):
        self.devices = []
        self.discover()

    def _discover__build_device(self, dir_parent, dir_dev, device_parent):
        if not re.match("^([0-9a-f]*):([0-9a-f]*):([0-9a-f]*)\.([0-9a-f]*)$", dir_dev, re.I):
            return None

        dir_full = os.path.join(dir_parent, dir_dev)

        dev = PCIDevice(devices_parent=self)

        dev.addr.parse(dir_dev)
        dev.parent = device_parent

        filename = os.path.join(dir_full, "config")
        if not os.path.exists(filename):
            print "Warning: no config space file for device %s" % (dev.addr)
            return None

        dev.config = PCIConfigSpace(PCIConfigSpaceAccess(filename, dev))
        
        dev.device = dev.config.read("common_device_id")
        dev.vendor = dev.config.read("common_vendor_id")
        if "type0_subsystem_vendor_id" in dev.config:
            dev.sub_vendor = dev.config.read("type0_subsystem_vendor_id")
            dev.sub_device = dev.config.read("type0_subsystem_id")
        
        for filename in os.listdir(dir_full):
            newdev = self._discover__build_device(dir_full, filename, dev)
            if newdev is not None:
                dev.children.append(newdev)

        self.devices.append(dev)
        return dev
        
    # When porting, this and it's children should be the only areas
    # in this file that needs work
    def discover(self):
        basedir = "/sys/devices"
        
        # Find all directories matching pciX:Y, then look for a subdirectoriy X:Y:00.0
        devices_subdirs = os.listdir(basedir)
        for device_subdir in devices_subdirs:
            m = re.match("^pci([0-9a-f]*):([0-9a-f]*)$", device_subdir, re.I)
            if m is not None:
                root_addr = PCIDeviceAddress()
                root_addr.domain = int(m.group(1), 16)
                root_addr.bus = int(m.group(2), 16)
                root_addr.device = 0
                root_addr.func = 0

                device_full_dir = os.path.join(basedir, device_subdir)
                root_dev = None
                for child_dev_dir in os.listdir(device_full_dir):
                    newdev = self._discover__build_device(device_full_dir, child_dev_dir, None)
                    if newdev is not None:
                        if newdev.addr == root_addr:
                            root_dev = newdev
                            root_dev.parent = root_dev
                            root_dev.is_root = True
                    
                for dev in self.devices:
                    if dev.parent is None:
                        dev.parent = root_dev
        
    def roots(self):
        ret = []
        for d in self.devices:
            if d.is_root:
                ret.append(d)
        return ret

    def get(self, **args):
        ret = self.devices
        for k, v in args.iteritems():
            ret = [d for d in ret if d.__dict__[k] == v ]
        return ret
            
    def walk_to_root(self, dev):
        yield dev
        while dev.parent is not dev:
            dev = dev.parent
            yield dev

    def walk_from_root(self, dev):
        dev_list = list(self.walk_to_root(dev))
        dev_list.reverse()
        for dev in dev_list:
            yield dev
        
