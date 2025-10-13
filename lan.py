import network
import logging
import time
import cmd_processor

log = logging.getLogger(__name__)

status_decode = {
    network.STAT_IDLE:          'idle',                     # 0
    network.STAT_CONNECTING:    'connecting',               # 1
    2:                          'waiting for IP address',
    network.STAT_GOT_IP:        'connected',                # 3
    network.STAT_CONNECT_FAIL:  'connect fail',             #-1
    network.STAT_NO_AP_FOUND:   'no AP found',              #-2
    network.STAT_WRONG_PASSWORD:'wrong password',           #-3
    }
class lan():

    def wifi_scan(self):
        if self.time_of_last_scan is None:
            seconds_since_last_scan = 10
        else:
            seconds_since_last_scan = time.time() - self.time_of_last_scan
        if seconds_since_last_scan >= 10:
                # request list of available AP
            scan_list = self.wlan.scan()
                # extract names and rssi, eliminate duplicates and hidden values
            ap_strength = {}
            for ap in scan_list:
                ap_name = ap[0].decode()
                ap_rssi = ap[3]
                if ap_name in ap_strength:
                    if ap_rssi > ap_strength[ap_name]:
                        ap_strength[ap_name] = ap_rssi
                elif ap_name != '':
                    ap_strength[ap_name] = ap_rssi
                # sort available APs by signal strength
            self.ap_list = []
            for ap in sorted(ap_strength, key=ap_strength.get, reverse=True):
                self.ap_list.append([ap, ap_strength[ap]])
            self.time_of_last_scan = time.time()

    def __init__(self):
        cmd_processor.reg_cmds(self, self.cmd_list)
#       self.network_ip = '0.0.0.0'
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.ap = ''
        self.time_of_last_scan = None
        self.wifi_scan()
        self.user_ap_list = []
        self.mac_address = self.wlan.config('mac').hex(':')

    def wifi_list(self):
        self.wifi_scan()
        self.user_ap_list = self.ap_list.copy()
        response = []
        for index in range(len(self.ap_list)):
            name, rssi = self.ap_list[index]
            response.append(f' {index:2} {rssi:4} {name}')
        return '\n'.join(response)

    def wifi_connect(self, hostname, networks):
        if self.wlan.isconnected():
            self.wifi_disconnect()
        if hostname:
            self.hostname = hostname
            network.hostname(hostname)
        else:
            self.hostname = network.hostname()
        for ap in self.wlan.scan() :
            ssid = ap[0].decode() 
            if ssid in networks:
                self.wlan.connect(ssid, networks[ssid])
                self.ap = ssid
                log.info(f'WIFI is connected to {ssid} as {self.hostname}')
                break

    def wifi_disconnect(self):
        self.wlan.disconnect()
        log.info(f'Disconnecting from WIFI {self.wlan.config('ssid')}')
        time.sleep(1)

    def status(self):
        response = []
        response.append(f'hostname: {network.hostname()}')
        status = self.wlan.status()
        if status == network.STAT_GOT_IP :
            response.append(f'network: up')
            response.append(f'MAC address: {self.mac_address}')
            response.append(f'AP: {self.ap}')
            self.network_ip = self.wlan.ifconfig()[0]
            response.append(f'IP address: {self.network_ip}')
        elif status in status_decode :
            response.append( status_decode[status])
        else :
            response.append( f'Unknown status {status}')
        return '\n'.join(response)

    def help(self, *args):
        response = []
        response.append('Available commands:')
        response.append(' wifi status - reports current wifi status')
        response.append(' wifi scan - report available wifi access points and the signal strengths')
        response.append('Use "config set wifi.<ssid> <password> to set up wifi access')
        response.append('Use "config set hostname" to specify the device network name')
        return '\n'.join(response)
    cmd_list = (
        (r'wifi status', status,
            'wifi status                    report current wifi status'),
        (r'wifi scan', wifi_list,
            'wifi scan                      list available wifi access points and their signal strength'),
        (r'wifi help', help,
            'wifi help                      wifi subsystem information'),
    )
