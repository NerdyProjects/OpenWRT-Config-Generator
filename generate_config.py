import yaml
import os
import argparse
import sys

parser = argparse.ArgumentParser(description='Generate wifi configurations for OpenWRT Access Points')
parser.add_argument(
    '--config',
    default="config.yaml"
)
parser.add_argument(
    'hostname',
    help=''
)
parser.add_argument(
    'outdir',
    help='output directory (/etc/config on the device)',
)
args = parser.parse_args()


def collect_bssids(config, ssid):
    bssids = []
    for ap in config['accesspoints']:
        for radio in ap['radios']:
            for wifi in radio['wifis']:
                if wifi['ssid'] == ssid:
                    bssids.append(wifi['bssid'])
    return bssids

def generate_r0kh_list(bssids, own_bssid, key):
    r0kh = []
    for bssid in bssids:
        if bssid != own_bssid:
            r0kh.append('{},{},{}'.format(bssid, bssid.translate({ord(':'): None}).lower(), key))
    return r0kh

def generate_r1kh_list(bssids, own_bssid, key):
    r1kh = []
    for bssid in bssids:
        if bssid != own_bssid:
            r1kh.append('{},{},{}'.format(bssid, bssid, key))
    return r1kh

class Config:
    def __init__(self):
        self.config = []
        self.depth = 0

    def append_indented(self, val):
        self.config.append('{}{}'.format('\t' * self.depth, val))

    def append_config_section(self, config_name, config_value = None):
        self.depth = 0
        if config_value is None:
            self.append_indented('config {}'.format(config_name))
        else:
            self.append_indented('config {} \'{}\''.format(config_name, config_value))
        self.depth = 1

    def finish_config_section(self):
        self.depth = 0
        self.append_indented()
    
    def append_config_option(self, option_name, option_value):
        self.append_indented('option {} \'{}\''.format(option_name, option_value))

    def append_config_list_item(self, list_name, item_value):
        self.append_indented('list {} \'{}\''.format(list_name, item_value))

    def dump(self):
        return '\n'.join(self.config)


with open(args.config, 'r') as stream:
    config = yaml.safe_load(stream)

wifi_config = {}
for wifi in config['wifis']:
    if wifi['mode'] == 'ap':
        wifi_config[wifi['ssid']] = wifi.copy()
        wifi_config[wifi['ssid']]['bssids'] = collect_bssids(config, wifi['ssid'])

configs = {}


ap = None
for a in config['accesspoints']:
    if a['name'] == args.hostname:
        ap = a
        break

if not ap:
    print("no access point found. maybe hostname is invalid?")
    sys.exit(1)



c = Config()
radio_i = 0
for radio in ap['radios']:
    device = 'radio{}'.format(radio_i)
    c.append_config_section('wifi-device', device)
    c.append_config_option('type', 'mac80211')
    c.append_config_option('legacy_rates', '0')
    c.append_config_option('country', 'DE')
    copy_options = ['htmode', 'channel', 'path', 'hwmode']
    for opt in copy_options:
        if opt in radio:
            c.append_config_option(opt, radio[opt])
    for wifi in radio['wifis']:
        id = wifi['ssid']
        c.append_config_section('wifi-iface')
        c.append_config_option('device', device)
        c.append_config_option('bssid', wifi['bssid'])
        copy_options = ['mode', 'network', 'encryption', 'auth_port', 'auth_secret', 'auth_server', 'dynamic_vlan', 'vlan_tagged_interface', 'vlan_bridge', 'vlan_naming',
    'dtim_period', 'ieee80211r', 'mobility_domain', 'ft_over_ds', 'ft_psk_generate_local', 'pmk_r1_push', 'ft_bridge', 'key', 'ssid', 'rsn_preauth']
        for opt in copy_options:
            if opt in wifi_config[id]:
                c.append_config_option(opt, wifi_config[id][opt])
        if 'ieee80211r' in wifi_config[id] and 'ft_exchange_aes' in wifi_config[id]:
            r0kh = generate_r0kh_list(wifi_config[id]['bssids'], wifi['bssid'], wifi_config[id]['ft_exchange_aes'])
            r1kh = generate_r1kh_list(wifi_config[id]['bssids'], wifi['bssid'], wifi_config[id]['ft_exchange_aes'])
            for i in r0kh:
                c.append_config_list_item('r0kh', i)
            for i in r1kh:
                c.append_config_list_item('r1kh', i)
    radio_i += 1


print("./wireless")
os.makedirs(args.outdir, 0o755, True)
file = open('{}/wireless'.format(args.outdir), 'w')
file.writelines(c.dump())
file.close()

