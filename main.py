import signal
import subprocess
import sys
import threading
import time

import switchmate

from os import path
from gateway_addon import (Adapter, Device, Property)

class SwitchmateProperty(Property):
    def __init__(self, device, name, description, value):
        Property.__init__(self, device, name, description)
        self.value = value

    def set_value(self, value):
        switchmate.switch(self.device.id, value)
        # Allow polling to update cached value and notify change

class SwitchmateDevice(Device):
    def __init__(self, adapter, scan_entry):
        Device.__init__(self, adapter, scan_entry.addr)
        self.name = 'Switchmate {}'.format(scan_entry.addr)
        self._type.append('OnOffSwitch')
        on = switchmate.get_scan_entry_status(scan_entry)
        self.properties['on'] = SwitchmateProperty(self, 'on', {
            '@type': 'OnOffProperty',
            'label': 'On/Off',
            'type': 'boolean'
        }, on)

_TIMEOUT = 1
_POLL_INTERVAL = 1

class SwitchmateAdapter(Adapter):
    def __init__(self, verbose=False):
        self.name = self.__class__.__name__
        Adapter.__init__(self, 'switchmate-adapter', 'switchmate-adapter', verbose=verbose)
        self.start_pairing(_TIMEOUT)

    def start_pairing(self, timeout):
        self.pairing = True
        switchmates = switchmate.scan(timeout=_TIMEOUT)
        for switch in switchmates:
            self.handle_device_added(SwitchmateDevice(self, switch))

        thread = threading.Thread(target=self.poll)
        thread.daemon = True
        thread.start()

    def update_device_props(self):
        switchmates = switchmate.scan(timeout=_TIMEOUT)
        for switch in switchmates:
            device = self.get_device(switch.addr)
            if device is None:
                continue
            val = switchmate.get_scan_entry_status(switch)
            if val is None:
                continue
            prop = device.properties['on']
            if prop.value != val:
                prop.set_cached_value(val)
                device.notify_property_changed(prop)

    def poll(self):
        while (True):
            time.sleep(_POLL_INTERVAL)
            try:
                self.update_device_props()
            except Exception as ex:
                print('Polling failed', ex, flush=True)

_ADAPTER = None

def cleanup(signal, frame):
    if _ADAPTER is not None:
        _ADAPTER.close_proxy()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    helper_path = path.join(path.dirname(path.abspath(__file__)), 'lib/bluepy/bluepy-helper')
    subprocess.run('sudo setcap cap_net_raw,cap_net_admin+eip {}'.format(helper_path).split(' '))

    _ADAPTER = SwitchmateAdapter(verbose=False)

    while _ADAPTER.proxy_running():
        time.sleep(2)
