import yaml
import os

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


with open("config.yaml", 'r') as stream:
    config = yaml.safe_load(stream)

print(config)
wifi_config = {}
for wifi in config['wifis']:
    if wifi['mode'] == 'ap':
        wifi_config[wifi['ssid']] = wifi.copy()
        wifi_config[wifi['ssid']]['bssids'] = collect_bssids(config, wifi['ssid'])

print(wifi_config)
configs = {}
for ap in config['accesspoints']:
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
    configs[ap['name']] = c

for name, ap in configs.items():
    path = 'generated/{}/config'.format(name)
    os.makedirs(path, 0o755, True)
    file = open('{}/wireless'.format(path), 'w')
    file.writelines(ap.dump())
    file.close()
    print('config for {}'.format(name))
    print(ap.dump())
