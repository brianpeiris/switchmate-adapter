import sys
from os import path

sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

from bluepy.btle import (
    Scanner, Peripheral, AssignedNumbers,
    ADDR_TYPE_RANDOM, UUID
)

# firmware == 2.99.15 (or higher?)
SWITCHMATE_SERVICE = 'abd0f555eb40e7b2ac49ddeb83d32ba2'

ORIGINAL_STATE_HANDLE = 0x2e
BRIGHT_STATE_HANDLE = 0x30

ORIGINAL_MODEL_STRING_HANDLE = 0x14

SERVICES_AD_TYPE = 0x07
MANUFACTURER_DATA_AD_TYPE = 0xff

def get_switchmates(scan_entries, mac_address):
    switchmates = []
    for scan_entry in scan_entries:
        service_uuid = scan_entry.getValueText(SERVICES_AD_TYPE)
        is_switchmate = service_uuid == SWITCHMATE_SERVICE
        if not is_switchmate:
            continue
        if mac_address and scan_entry.addr == mac_address:
            return [scan_entry]
        if scan_entry not in switchmates:
            switchmates.append(scan_entry)
    switchmates.sort(key=lambda sw: sw.addr)
    return switchmates


def scan(timeout=None, mac_address=None):
    scanner = Scanner()
    return get_switchmates(scanner.scan(timeout), mac_address)

def is_original_device(device):
    # The handle for reading the model string on Bright devices is actually
    # different from Original devices, but using getCharacteristics to read
    # the model is much slower.
    model = device.readCharacteristic(ORIGINAL_MODEL_STRING_HANDLE)
    return model == b'Original'

def get_state_handle(device):
    if is_original_device(device):
        return ORIGINAL_STATE_HANDLE
    else:
        return BRIGHT_STATE_HANDLE

def switch(mac_address, val):
    device = Peripheral(mac_address, ADDR_TYPE_RANDOM)
    state_handle = get_state_handle(device)
    new_val = b'\x01' if val == True else b'\x00'
    device.writeCharacteristic(state_handle, new_val, True)
    device.disconnect()

def get_battery_level(mac_address):
    device = Peripheral(mac_address, ADDR_TYPE_RANDOM)
    battery_level = device.getCharacteristics(uuid=AssignedNumbers.batteryLevel)[0].read()
    device.disconnect()
    return battery_level

def get_scan_entry_status(scan_entry):
    return bool(int(scan_entry.getValueText(MANUFACTURER_DATA_AD_TYPE)[1]))

def get_status(mac_address, timeout=None):
    entries = scan(timeout, mac_address)

    if len(entries):
        return get_scan_entry_status(entries[0])

    return None
