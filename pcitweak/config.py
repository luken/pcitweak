import os
from bitstring import BitString


####################################################################
#### PCI Config Space Data Manipulation
####################################################################

# When porting, this should be the only class in this file that needs work
class PCIConfigSpaceAccess:
    def __init__(self, config_fn, device):
        self.config = open(config_fn, 'r+')
        self.dev = device
    
    def __del__(self):
        self.config.close()

    # XXX Hack, rewrite
    def swap_le_be(self, bs):
        ret = BitString(uintle=bs.uint, length=bs.length)
        return ret
        
    def read(self, offset, length, bit_offset=None, bit_length=None):
        self.config.seek(offset)
        data = self.config.read(length/8)
        data = BitString(bytes=data, length=length)
        data = self.swap_le_be(data)
        #print "Read 0x%x at 0x%x" % (data.uint, offset)
        
        if bit_offset is None:
            ret = data.uint
        else:
            #print data.bin
            #print "Reading bit %d length %d" % (bit_offset, bit_length)
            #for i in range(length):
                #print "%d %d" % (i, data[i].uint)
            #print "Using slice %d:%d" % ( length - (bit_offset + bit_length) , length - bit_offset )
            #print data[ length - (bit_offset + bit_length) : length - bit_offset ].bin

            # Bit slice addresses are reversed
            ret = data[ length - (bit_offset + bit_length) : length - bit_offset ].uint

        return ret

    def write(self, value, offset, length, bit_offset=None, bit_length=None):
        """
        If a whole register, writes value to the whole register
        If a bit field, reads the register and mods only the specified bit then writes that new value back
        """
        if bit_offset is None:
            data = BitString(uint=value, length=length)
        else:
            orig = self.read(offset, length)
            #print "orig int 0x%x" % (orig)
            orig = BitString(uint=orig, length=length)
            #print "orig bs %s" % (orig.bin)
            new = BitString(uint=value, length=bit_length)
            #print "new bs %s going in at offset %d" % (new.bin, bit_offset)
            # Slice addresses are in reverse order
            orig.overwrite(new, length - (bit_offset + bit_length))
            #orig.overwrite(new, bit_offset)
            data = orig

        #print "%s %s" % (data.hex, data.bin)
        data = self.swap_le_be(data)
        self.config.seek(offset)
        self.config.write(data.bytes)

    def clear(self, offset, length, bit_offset=None, bit_length=None):
        """
        If a whole register, writes ones to the whole register
        If a bit field, writes a one to the specified bit with everything else being zero
        """
        bs = BitString(length=length)
        if bit_offset is None:
            bs = ~bs
        else:
            # Slice addresses are backward, ex: msb is 0, lsb is 31 so bit_offset 32 is slice[0] (for 32 bit)
            for i in range(length - (bit_offset + bit_length), length - bit_offset):
                bs[i] = 1

        self.write(bs.uint, offset, length)


####################################################################
#### Base Register Set
####################################################################
class ConfigReg:
    def __init__(self, name, length, base_offset, offset, bit_offset=None, bit_length=None):
        self.base_offset = base_offset
        self.name = name
        self.length = length
        self.offset = offset
        self.bit_offset = bit_offset
        if bit_offset is not None and bit_length is None:
            self.bit_length = 1
        else:
            self.bit_length = bit_length

    def read(self, config):
        offset = self.base_offset + self.offset
        return config.read(offset, self.length, self.bit_offset, self.bit_length)

    def write(self, value, config):
        offset = self.base_offset + self.offset
        config.write(value, offset, self.length, self.bit_offset, self.bit_length)

    def clear(self, config):

        off = self.base_offset + self.offset

        data = BitString(length=self.length)
        if self.bit_offset is None:
            data = ~data
        else:
            for i in range(self.bit_offset, self.bit_offset+self.bit_length):
                data[i] = 1
        
        #print data.bin
        # file objects
        config.seek(off)
        config.write(data.bytes)

    def enumerate(self, config):
        ret = "%s = 0x%x\n" % (self.name, self.read(config))
        return ret

class ConfigRegSet:
    def __init__(self, name, base_offset, config):
        self.name = name
        self.regs = []
        self.regs_byname = {}
        self.base_offset = base_offset
        self.config = config
        self.extend_attrs = []

    def __contains__(self, name):
        if name in self.regs_byname:
            return True
        else:
            return False

    def __iter__(self):
        for reg in self.regs:
            yield reg.name
        
    def add(self, name, length, offset, base_offset=None, bit_offset=None, bit_length=None):
        if base_offset is None:
            base_offset = self.base_offset
        # Check for collisions
        if name in self.regs_byname:
            raise RuntimeError("Register %s already exsits in set %s" % (self.name, name))
        
        reg = ConfigReg(name, length, base_offset, offset, bit_offset, bit_length)
        self.regs.append(reg)
        self.regs_byname[name] = reg

    def extend(self, other):
        for rself in self.regs:
            if rself.name in other.regs_byname:
                raise RuntimeError("Error extending Reg Set '%s' with '%s', conflict on reg '%s'" % (self.name, other.name, rself.name))
                
        self.regs.extend(other.regs)
        for reg in self.regs:
            self.regs_byname[reg.name] = reg

        for attr in other.extend_attrs:
            if attr in self:
                raise RuntimeError("Attribute %s from %s already exists in %s" % (attr, other.name, self.name))
            setattr(self, attr, getattr(other, attr))

    def read(self, reg_name):
        return self.regs_byname[reg_name].read(self.config)
        
    def write(self, reg_name, value):
        return self.regs_byname[reg_name].write(value, self.config)

    def clear(self, reg_name):
        return self.regs_byname[reg_name].clear(self.config)

    def avaliable(self):
        # pull from list to keep in order
        return [reg.name for reg in self.regs]

    def enumerate(self):
        ret = "\n"
        ret += "Register Set %s\n" % (self.name)
        for reg in self.regs:
            ret += reg.enumerate(self.config)
        return ret

####################################################################
#### Main class for external consumption
####################################################################

class PCIConfigSpace(ConfigRegSet):
    def __init__(self, config): 

        ConfigRegSet.__init__(self, "Config space master", 0x0, config)

        cs = ConfigPCICommon(self.config)
        self.extend(cs)

        header_type = self.read("common_header_type")
	if header_type > 0xf:
	    print "Warning: Reported header type 0x%x invalid, using 0x%x instead for %s" % (header_type, 0xf & header_type, self.config.dev.addr)
	    header_type = header_type & 0xf
        if header_type == 0:
            cs = ConfigPCIType0(self.config)
        elif header_type == 1:
            cs = ConfigPCIType1(self.config)
        else:
            print "Unknown common_header_type 0x%x on %s" % (header_type, self.config.dev.addr)
            return

        self.extend(cs)

        cap = self._get_first_cap()
        while cap is not None:
            self.extend(cap)
            cap = cap.get_next_cap()

    def _get_first_cap(self):
        offset = self.read("common_capabilities_pointer")
        if offset == 0x00:
            return None
        cap = CapabilityRegSet("Base CapabilityRegSet", offset, 0x0, self.config, "none")
        cap = cap.get_cap_type()
        return cap
       
    def enumerate_all(self):
        print self.enumerate()
        if self.read("common_header_type") == 0:
            cs_type = ConfigPCIType0(self.config)
        if self.read("common_header_type") == 1:
            cs_type = ConfigPCIType1(self.config)
        print cs_type.enumerate()

        cap = self._get_first_cap()
        while cap is not None:
            print cap.enumerate()
            cap = cap.get_next_cap()
   
####################################################################
#### Common Register Set Definitions
####################################################################

class ConfigPCICommon(ConfigRegSet):
    def __init__(self, config):
        ConfigRegSet.__init__(self, "Common Configuration Space", 0x0, config)
        self.add("common_vendor_id", 16, 0x00)
        self.add("common_device_id", 16, 0x02)
        self.add("common_command", 16, 0x04)
        self.add("common_command_bus_master_enable", 16, 0x04, bit_offset=2)
        self.add("common_command_special_cycle_enable", 16, 0x04, bit_offset=3)
        self.add("common_command_memory_write_and_invalidate", 16, 0x04, bit_offset=4)
        self.add("common_command_vga_palette_snoop", 16, 0x04, bit_offset=5)
        self.add("common_command_parity_error_response", 16, 0x04, bit_offset=6)
        self.add("common_command_idsel_stepping_or_wait_cycle_control", 16, 0x04, bit_offset=7)
        self.add("common_command_serr_enable", 16, 0x04, bit_offset=8)
        self.add("common_command_fast_back_to_back_transactions_enable", 16, 0x04, bit_offset=9)
        self.add("common_command_interrupt_disable", 16, 0x04, bit_offset=10)

        self.add("common_status", 16, 0x06)
        self.add("common_status_interrupt_status", 16, 0x06, bit_offset=3)
        self.add("common_status_capabilities_list", 16, 0x06, bit_offset=4)
        self.add("common_status_66mhz_capable", 16, 0x06, bit_offset=5)
        self.add("common_status_fast_back_to_back_transactions_capable", 16, 0x06, bit_offset=7)
        self.add("common_status_master_data_parity_error", 16, 0x06, bit_offset=8)
        self.add("common_status_devsel_timing", 16, 0x06, bit_offset=9, bit_length=2)
        self.add("common_status_signaled_target_abort", 16, 0x06, bit_offset=11)
        self.add("common_status_received_target_abort", 16, 0x06, bit_offset=12)
        self.add("common_status_received_master_abort", 16, 0x06, bit_offset=13)
        self.add("common_status_signaled_system_error", 16, 0x06, bit_offset=14)
        self.add("common_status_detected_parity_error", 16, 0x06, bit_offset=15)
        
        self.add("common_revision_id", 8, 0x08)
        self.add("common_class_code", 24, 0x09)
        self.add("common_cache_line_size", 8, 0x0c)
        self.add("common_master_latency_timer", 8, 0x0d)
        self.add("common_header_type", 8, 0x0e)
        self.add("common_bist", 8, 0x0f)
        self.add("common_capabilities_pointer", 8, 0x34)
        self.add("common_interrupt_line", 8, 0x3c)
        self.add("common_interrupt_pin", 8, 0x3d)

class ConfigPCIType0(ConfigRegSet):
    def __init__(self, config):
        ConfigRegSet.__init__(self, "Type 0 Configuration Space", 0x0, config)
        # XXX BARs at addresses starting at 0x10 and ending at 0x27
        self.add("type0_cardbus_cis_pointer", 32, 0x28)
        self.add("type0_subsystem_vendor_id", 16, 0x2c)
        self.add("type0_subsystem_id", 16, 0x2e)
        self.add("type0_expansion_rom_base_address", 32, 0x30)
        self.add("type0_min_gnt", 8, 0x3e)
        self.add("type0_max_lat", 8, 0x3f)
        
class ConfigPCIType1(ConfigRegSet):
    def __init__(self, config):
        ConfigRegSet.__init__(self, "Type 1 Configuration Space", 0x0, config)
        # XXX BARs at addresses starting at 0x10 and ending at 0x17
        self.add("type1_primary_bus_number", 8, 0x18)
        self.add("type1_secondary_bus_number", 8, 0x19)
        self.add("type1_subordinate_bus_number", 8, 0x1a)
        self.add("type1_secondary_latency_timer", 8, 0x1b)
        self.add("type1_io_base", 8, 0x1c)
        self.add("type1_io_limit", 8, 0x1d)

        self.add("type1_secondary_status", 16, 0x1e)
        self.add("type1_secondary_status_66mhz_capable", 16, 0x1e, bit_offset=5)
        self.add("type1_secondary_status_fast_back_to_back_transactions_capable", 16, 0x1e, bit_offset=7)
        self.add("type1_secondary_status_master_data_parity_error", 16, 0x1e, bit_offset=8)
        self.add("type1_secondary_status_devsel_timing", 16, 0x1e, bit_offset=9, bit_length=2)
        self.add("type1_secondary_status_signaled_target_abort", 16, 0x1e, bit_offset=11)
        self.add("type1_secondary_status_received_target_abort", 16, 0x1e, bit_offset=12)
        self.add("type1_secondary_status_received_master_abort", 16, 0x1e, bit_offset=13)
        self.add("type1_secondary_status_received_system_error", 16, 0x1e, bit_offset=14)
        self.add("type1_secondary_status_detected_parity_error", 16, 0x1e, bit_offset=15)

        self.add("type1_memory_base", 16, 0x20)
        self.add("type1_memory_limit", 16, 0x22)
        self.add("type1_prefetchable_memory_base", 16, 0x24)
        self.add("type1_prefetchable_memory_limit", 16, 0x26)
        self.add("type1_prefetchable_base_upper_32_bits", 32, 0x28)
        self.add("type1_prefetchable_limit_upper_32_bits", 32, 0x2c)
        self.add("type1_io_base_upper_16_bits", 16, 0x30)
        self.add("type1_io_limit_upper_16_bits", 16, 0x32)
        self.add("type1_expansion_rom_base_address", 32, 0x38)

        self.add("type1_bridge_control", 16, 0x3e)
        self.add("type1_bridge_control_parity_error_response_enable", 16, 0x3e, bit_offset=0)
        self.add("type1_bridge_control_serr_enable", 16, 0x3e, bit_offset=1)
        self.add("type1_bridge_control_master_abort_mode", 16, 0x3e, bit_offset=5)
        self.add("type1_bridge_control_secondary_bus_reset", 16, 0x3e, bit_offset=6)
        self.add("type1_bridge_control_fast_back_to_back_transactions_enabled", 16, 0x3e, bit_offset=7)
        self.add("type1_bridge_control_primary_discard_timer", 16, 0x3e, bit_offset=8)
        self.add("type1_bridge_control_secondary_discard_timer", 16, 0x3e, bit_offset=9)
        self.add("type1_bridge_control_discard_timer_status", 16, 0x3e, bit_offset=10)
        self.add("type1_bridge_control_discard_timer_serr_enable", 16, 0x3e, bit_offset=11)

####################################################################
#### Base Capability Register Set
####################################################################
cap_types = {}
class CapabilityRegSet(ConfigRegSet):
    def __init__(self, name, base_offset, capability_id, config, prefix):
        ConfigRegSet.__init__(self, name, base_offset, config)
        self.capability_id = capability_id
        self.prefix = prefix
        self.add("%s_capability_id" % (prefix), 8, 0x0)
        self.add("%s_capability_next" % (prefix), 8, 0x1)

    def get_cap_type(self):
        "Convert a generic capability structure to a specific one for that cap type"
        id = self.read("%s_capability_id" % (self.prefix))
        try:
            cap = cap_types[id](self.base_offset, self.config)
        except KeyError:
            #print "WARNING: unknown capability at 0x%x of type 0x%x" % (self.base_offset, id)
            cap = CapabilityRegSet("Unknown Capability ID 0x%x" % (id), self.base_offset, id, self.config, "cap_%02x" % (id))
        return cap
       
    def get_next_cap(self):
        "Get the next capability in the tree, return None of at end"
        next_offset = self.read("%s_capability_next" % (self.prefix))
        if next_offset == 0x00:
            return None # end of list
        next = CapabilityRegSet("Base CapabilityRegSet", next_offset, 0x0, self.config, "none")
        next = next.get_cap_type()
        return next

    def type_specific_cap_type(self):
        """
        For capabilites with multiple versions or other special requirements,
        override this to detect the version and return the updated type"
        return None
        """
        pass

####################################################################
#### Capability Register Set Definitions
####################################################################

# XXX Not Done: PCI Bus Power Management Interface Specification, Revision. 1.2.
cap_types[0x01] = lambda base_offset, config: CapabilityPCIPower(base_offset, config)
class CapabilityPCIPower(CapabilityRegSet):
    def __init__(self, base_offset, config):
        CapabilityRegSet.__init__(self, "PCI Power Management Capability Structure", base_offset, 0x01, config, "power")


# XXX Not Done: PCI Local Bus Specification, Revision 3.0.
cap_types[0x05] = lambda base_offset, config: CapabilityMSI(base_offset, config)
class CapabilityMSI(CapabilityRegSet):
    def __init__(self, base_offset, config):
        CapabilityRegSet.__init__(self, "MSI Capability Structure", base_offset, 0x05, config, "msi")



# XXX Not Done: MSI-X ECN for the PCI Local Bus Specification, Revision 3.0.
cap_types[0x11] = lambda base_offset, config: CapabilityMSIX(base_offset, config)
class CapabilityMSIX(CapabilityRegSet):
    def __init__(self, base_offset, config):
        CapabilityRegSet.__init__(self, "MSI-X Capability Structure", base_offset, 0x11, config, "msix")


cap_types[0x10] = lambda base_offset, config: CapabilityPCIExpress(base_offset, config)
class CapabilityPCIExpress(CapabilityRegSet):
    def __init__(self, base_offset, config):
        CapabilityRegSet.__init__(self, "PCI Express Capability Structure", base_offset, 0x10, config, "pcie")
        self.add_pcie_cap()
        self.add_pcie_device()
        self.add_pcie_link()
        self.add_pcie_slot()
        self.add_pcie_root()
        self.add_pcie_device2()
        self.add_pcie_link2()
        self.add_pcie_slot2()

    def add_pcie_cap(self):
        self.add("pcie_cap_register", 16, 0x02)
        self.add("pcie_cap_register_version", 16, 0x02, bit_offset=0, bit_length=4)
        self.add("pcie_cap_register_device_port_type", 16, 0x02, bit_offset=4, bit_length=4)
        self.add("pcie_cap_register_slot_implemented", 16, 0x02, bit_offset=8, bit_length=1)
        self.add("pcie_cap_register_interrupt_message_number", 16, 0x02, bit_offset=9, bit_length=5)

        self.devports = {}
        self.devports[0x0] = "PCI Express Endpoint Device"
        self.devports[0x1] = "Legacy PCI Express Endpoint device"
        self.devports[0x2] = "Undefined"
        self.devports[0x3] = "Undefined"
        self.devports[0x4] = "Root Port of PCI Express Root Complex"
        self.devports[0x5] = "Upstream Port of PCI Express Switch"
        self.devports[0x6] = "Downstream Port of PCI Express Switch"
        self.devports[0x7] = "PCI Expressto-PCI/PCI-X Bridge"
        self.devports[0x8] = "PCI/PCI-X to PCI Express Bridge"
        self.devports[0x9] = "Root Complex Integrated Endpoint Device"
        self.devports[0xa] = "Root Complex Event Collector"

    def add_pcie_device(self):
        ## All Devices
        self.add("pcie_device_capabilities", 32, 0x04)
        self.add("pcie_device_capabilities_max_payload_size_supported", 32, 0x04, bit_offset=0, bit_length=3)
        self.add("pcie_device_capabilities_phantom_functions_supported", 32, 0x04, bit_offset=3, bit_length=2)
        self.add("pcie_device_capabilities_extended_tag_field_supported", 32, 0x04, bit_offset=5, bit_length=1)
        self.add("pcie_device_capabilities_endpoint_l0s_acceptable_latency", 32, 0x04, bit_offset=6, bit_length=3)
        self.add("pcie_device_capabilities_endpoint_l1s_acceptable_latency", 32, 0x04, bit_offset=9, bit_length=3)
        self.add("pcie_device_capabilities_role_based_error_reporting", 32, 0x04, bit_offset=15, bit_length=1)
        self.add("pcie_device_capabilities_captured_slot_power_limit_value", 32, 0x04, bit_offset=18, bit_length=8)
        self.add("pcie_device_capabilities_captured_slot_power_limit_scale", 32, 0x04, bit_offset=26, bit_length=2)

        self.add("pcie_device_control", 16, 0x08)
        self.add("pcie_device_control_correctable_error_reporting_enabled", 16, 0x08, bit_offset=0)
        self.add("pcie_device_control_non-fatal_error_reporting_enabled", 16, 0x08, bit_offset=1)
        self.add("pcie_device_control_fatal_error_reporting_enabled", 16, 0x08, bit_offset=2)
        self.add("pcie_device_control_unsupported_request_reporting_enabled", 16, 0x08, bit_offset=3)
        self.add("pcie_device_control_enable_relaxed_ordering", 16, 0x08, bit_offset=4)
        self.add("pcie_device_control_max_payload_size", 16, 0x08, bit_offset=5, bit_length=3)
        self.add("pcie_device_control_extended_tag_field_enable", 16, 0x08, bit_offset=8)
        self.add("pcie_device_control_phantom_functions_enable", 16, 0x08, bit_offset=9)
        self.add("pcie_device_control_aux_power_pm_enable", 16, 0x08, bit_offset=10)
        self.add("pcie_device_control_enable_snoop_not_required", 16, 0x08, bit_offset=11)
        self.add("pcie_device_control_max_read_request_size", 16, 0x08, bit_offset=12, bit_length=4)
        self.add("pcie_device_control_bridge_configuration_retry_enable", 16, 0x08, bit_offset=15)

        self.add("pcie_device_status", 16, 0x0a)
        self.add("pcie_device_status_correctable_error_detected", 16, 0x0a, bit_offset=0)
        self.add("pcie_device_status_non-fatal_error_detected", 16, 0x0a, bit_offset=1)
        self.add("pcie_device_status_fatal_error_detected", 16, 0x0a, bit_offset=2)
        self.add("pcie_device_status_unsupported_request_detected", 16, 0x0a, bit_offset=3)
        self.add("pcie_device_status_aux_power_detected", 16, 0x0a, bit_offset=4)
        self.add("pcie_device_status_transactions_pending", 16, 0x0a, bit_offset=5)

        self.maxsize = {}
        self.maxsize[0] = "128 bytes"
        self.maxsize[1] = "256 bytes"
        self.maxsize[2] = "512 bytes"
        self.maxsize[3] = "1024 bytes"
        self.maxsize[4] = "2048 bytes"
        self.maxsize[5] = "4096 bytes"

    def add_pcie_link(self):
        ## Devices with Links, Ports with Slots, Root Ports
        self.add("pcie_link_capabilities", 32, 0x0c)
        self.add("pcie_link_capabilities_max_link_speed", 32, 0x0c, bit_offset=0, bit_length=4)
        self.add("pcie_link_capabilities_max_link_width", 32, 0x0c, bit_offset=4, bit_length=6)
        self.add("pcie_link_capabilities_aspm_support", 32, 0x0c, bit_offset=10, bit_length=2)
        self.add("pcie_link_capabilities_l0s_exit_latency", 32, 0x0c, bit_offset=12, bit_length=3)
        self.add("pcie_link_capabilities_l1_exit_latency", 32, 0x0c, bit_offset=15, bit_length=3)
        self.add("pcie_link_capabilities_clock_power_management", 32, 0x0c, bit_offset=18)
        self.add("pcie_link_capabilities_supprise_down_error_reporting_capable", 32, 0x0c, bit_offset=19)
        self.add("pcie_link_capabilities_data_link_layer_link_active_reporting_capable", 32, 0x0c, bit_offset=20)
        self.add("pcie_link_capabilities_port_number", 32, 0x0c, bit_offset=24, bit_length=8)

        self.add("pcie_link_control", 16, 0x10)
        self.add("pcie_link_control_aspm_control", 16, 0x10, bit_offset=0, bit_length=2)
        self.add("pcie_link_control_read_completion_boundery", 16, 0x10, bit_offset=3)
        self.add("pcie_link_control_link_disable", 16, 0x10, bit_offset=4)
        self.add("pcie_link_control_retrain_link", 16, 0x10, bit_offset=5)
        self.add("pcie_link_control_common_clock_configuration", 16, 0x10, bit_offset=6)
        self.add("pcie_link_control_extended_synch", 16, 0x10, bit_offset=7)
        self.add("pcie_link_control_enable_clock_power_management", 16, 0x10, bit_offset=8)
        

        self.add("pcie_link_status", 16, 0x12)
        self.add("pcie_link_status_link_speed", 16, 0x12, bit_offset=0, bit_length=4)
        self.add("pcie_link_status_negotiated_link_width", 16, 0x12, bit_offset=5, bit_length=6)
        self.add("pcie_link_status_link_training", 16, 0x12, bit_offset=11)
        self.add("pcie_link_status_slot_clock_configuration", 16, 0x12, bit_offset=12)
        self.add("pcie_link_status_data_link_layer_link_active", 16, 0x12, bit_offset=13)

    def add_pcie_slot(self):
        ## Ports with slots, Root Ports
        self.add("pcie_slot_capabilities", 32, 0x14)
        self.add("pcie_slot_capabilities_attention_button_present",                 32, 0x14, bit_offset=0, bit_length=1)
        self.add("pcie_slot_capabilities_power_control_present",                    32, 0x14, bit_offset=1, bit_length=1)
        self.add("pcie_slot_capabilities_MRL_sensor_present",                       32, 0x14, bit_offset=2, bit_length=1)
        self.add("pcie_slot_capabilities_attention_indicator_present",              32, 0x14, bit_offset=3, bit_length=1)
        self.add("pcie_slot_capabilities_power_indicator_present",                  32, 0x14, bit_offset=4, bit_length=1)
        self.add("pcie_slot_capabilities_hot_plug_surprise",                        32, 0x14, bit_offset=5, bit_length=1)
        self.add("pcie_slot_capabilities_hot_plug_capable",                         32, 0x14, bit_offset=6, bit_length=1)
        self.add("pcie_slot_capabilities_slot_power_limit_value",                   32, 0x14, bit_offset=7, bit_length=8)
        self.add("pcie_slot_capabilities_slot_power_limit_scale",                   32, 0x14, bit_offset=15, bit_length=2)
        self.add("pcie_slot_capabilities_slot_electromechanical_interlock_present", 32, 0x14, bit_offset=17, bit_length=1)
        self.add("pcie_slot_capabilities_slot_no_command_completed_support",        32, 0x14, bit_offset=18, bit_length=1)
        self.add("pcie_slot_capabilities_physical_slot_number",                     32, 0x14, bit_offset=19, bit_length=13)

        self.slot_power_scale = {
                0b00: 1,
                0b01: 0.1,
                0b10: 0.01,
                0b11: 0.001
        }
        self.extend_attrs.append('slot_power_scale')

        self.add("pcie_slot_control", 16, 0x18)
        self.add("pcie_slot_control_attention_button_press_enable",         16, 0x18, bit_offset=0, bit_length=1)
        self.add("pcie_slot_control_power_fault_detection_enable",          16, 0x18, bit_offset=1, bit_length=1)
        self.add("pcie_slot_control_MRL_sensor_changed_enable",             16, 0x18, bit_offset=2, bit_length=1)
        self.add("pcie_slot_control_presence_detect_changed_enable",        16, 0x18, bit_offset=3, bit_length=1)
        self.add("pcie_slot_control_command_completed_interrupt_enable",    16, 0x18, bit_offset=4, bit_length=1)
        self.add("pcie_slot_control_hot_plug_interrupt_enable",             16, 0x18, bit_offset=5, bit_length=1)
        self.add("pcie_slot_control_attention_indicator_control",           16, 0x18, bit_offset=6, bit_length=2)
        self.add("pcie_slot_control_power_indicator_control",               16, 0x18, bit_offset=8, bit_length=2)
        self.add("pcie_slot_control_power_controller_control",              16, 0x18, bit_offset=10, bit_length=1)
        self.add("pcie_slot_control_electromechanical_interlock_control",   16, 0x18, bit_offset=11, bit_length=1)
        self.add("pcie_slot_control_data_link_layer_state_changed_enable",  16, 0x18, bit_offset=12, bit_length=1)
        self.add("pcie_slot_control_reserved",                              16, 0x18, bit_offset=13, bit_length=3)

        self.add("pcie_slot_status", 16, 0x1a)
        self.add("pcie_slot_status_attention_button_pressed",               16, 0x1a, bit_offset=0, bit_length=1)
        self.add("pcie_slot_status_power_fault_detected",                   16, 0x1a, bit_offset=1, bit_length=1)
        self.add("pcie_slot_status_MRL_sensor_changed",                     16, 0x1a, bit_offset=2, bit_length=1)
        self.add("pcie_slot_status_presence_detect_changed",                16, 0x1a, bit_offset=3, bit_length=1)
        self.add("pcie_slot_status_command_completed",                      16, 0x1a, bit_offset=4, bit_length=1)
        self.add("pcie_slot_status_MRL_sensor_state",                       16, 0x1a, bit_offset=5, bit_length=1)
        self.add("pcie_slot_status_presence_detect_state",                  16, 0x1a, bit_offset=6, bit_length=1)
        self.add("pcie_slot_status_electromechanical_interlock_status",     16, 0x1a, bit_offset=7, bit_length=1)
        self.add("pcie_slot_status_data_link_layer_state_changed",          16, 0x1a, bit_offset=8, bit_length=1)
        self.add("pcie_slot_status_reserved",                               16, 0x1a, bit_offset=9, bit_length=7)

        self.extend_attrs.append('get_pcie_slot_cap_watts')
        self.extend_attrs.append('set_pcie_slot_cap_watts')

    def get_pcie_slot_cap_watts(self):
        pwr_value = self.read("pcie_slot_capabilities_slot_power_limit_value")
        pwr_scale = self.read("pcie_slot_capabilities_slot_power_limit_scale")
        # From the spec rev 2.1 section 7.8.9,
        # if scale == 0, power values above 0xef are reserved
        if pwr_scale == 0b00 and pwr_value > 0xef:
            if pwr_value == 0xf0:
                return 250
            elif pwr_value == 0xf1:
                return 275
            elif pwr_value == 0xf2:
                return 300
            else:
                print "Warning: undefined slot power 0x%x value for %s" % (pwr_value, self.addr)
                return -1
        for regval, scale in self.slot_power_scale.iteritems():
            if pwr_scale == regval:
                return pwr_value * scale
        print "Warning: unhandled slot power value/scale (0x%x, 0x%x) for %s" % (pwr_value, pwr_scale, self.addr)
        return -1

    def set_pcie_slot_cap_watts(self, watts):
        # This should fail, registers are flagged HwInit, this is only to see if the device has a bug
        # Because of this, not implimenting any of the special scailing stuff, just taking the int passed in
        pwr_value = 0
        pwr_scale = 0
        if watts > 0xef:
            raise RuntimeError("Can't try to fake set watts higher than 0xef, tried 0x%x" % (watts))
                
        self.write("pcie_slot_capabilities_slot_power_limit_value", watts)
        self.write("pcie_slot_capabilities_slot_power_limit_scale", 0)

    def add_pcie_root(self):
        ## Root Ports, Root Complex Event Collector
        self.add("pcie_root_control", 16, 0x1c)
        self.add("pcie_root_control_serr_correctable", 16, 0x1c, bit_offset=0)
        self.add("pcie_root_control_serr_non-fatal", 16, 0x1c, bit_offset=1)
        self.add("pcie_root_control_serr_fatal", 16, 0x1c, bit_offset=2)
        self.add("pcie_root_control_pme_interrupt_enable", 16, 0x1c, bit_offset=3)
        self.add("pcie_root_control_crs_software_visibility_enable", 16, 0x1c, bit_offset=4)

        self.add("pcie_root_capabilities", 16, 0x1e)
        self.add("pcie_root_capabilities_crs_software_visibility", 16, 0x1e, bit_offset=0)

        self.add("pcie_root_status", 32, 0x20)
        self.add("pcie_root_status_pme_requester_id", 32, 0x20, bit_offset=0, bit_length=16)
        self.add("pcie_root_status_pme_status", 32, 0x20, bit_offset=16)
        self.add("pcie_root_status_pme_pending", 32, 0x20, bit_offset=17)

    def add_pcie_device2(self):
        ## Device2 Registers
        self.add("pcie_device2_capabilities", 32, 0x24)
        self.add("pcie_device2_control", 16, 0x28)
        self.add("pcie_device2_status", 16, 0x2a)

    def add_pcie_link2(self):
        self.add("pcie_link2_capabilities", 32, 0x2c)
        self.add("pcie_link2_control", 16, 0x30)
        self.add("pcie_link2_status", 16, 0x32)

    def add_pcie_slot2(self):
        self.add("pcie_slot2_capabilities", 32, 0x34)
        self.add("pcie_slot2_control", 16, 0x38)
        self.add("pcie_slot2_status", 16, 0x3a)

