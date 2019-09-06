#!/usr/bin/python

# enable print() function even in python2
from __future__ import print_function

import requests, json
import urllib
import sys
import socket

def HDHRdiscover():

    #
    # Try a few different ways to identify eligible HDHRs
    #
    #
    # First, obtain list from my.hdhomerun.com (SD provided service)
    #
    # Second, try to get a list of IP addresses that appear to
    # be tuners (via a hand constructed packet (we just collect
    # the IP addresses, and then perform a discovery)
    #

    discoveredTuners = {}

    SDdiscover = []
    try:
        r = requests.get('https://my.hdhomerun.com/discover', timeout=(.5, .2))
        r.raise_for_status()
        SDdiscover = r.json()
        if not isinstance(SDdiscover, list):
            SDdiscover = []
    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError):
        SDdiscover = []

    for device in SDdiscover:
        if not isinstance(device, dict):
            continue
        Legacy = False
        DeviceID = None
        DiscoverURL = None
        LocalIP = None
        if 'Legacy' in device:
            Legacy = bool(device['Legacy'])
        if 'DeviceID' in device:
            DeviceID = device['DeviceID']
        if 'DiscoverURL' in device:
            DiscoverURL = device['DiscoverURL']
        if 'LocalIP' in device:
            LocalIP = device['LocalIP']

        if (Legacy) or (DeviceID is None) or (DiscoverURL is None) or (LocalIP is None):
            continue

        discoveredTuners[LocalIP] = DiscoverURL

    discovery_udp_port = 65001
    # Hand constructed discovery message (device type = tuner, device id = wildcard)
    discovery_udp_msg = bytearray.fromhex('00 02 00 0c 01 04 00 00 00 01 02 04 ff ff ff ff 4e 50 7f 35')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(.2)
    for i in range(2):
        sock.sendto(discovery_udp_msg, ('<broadcast>', discovery_udp_port))
        while True:
            try:
                (buf, addr) = sock.recvfrom(2048)
            except socket.timeout:
                break
            if addr is None:
                continue
            if buf is None:
                continue

            DiscoverURL = 'http://' + addr[0] + ':80/discover.json'
            discoveredTuners[addr[0]] = DiscoverURL

    eligibleTuners = []

    for device in discoveredTuners:
        discoverResponse = {}
        try:
            r = requests.get(discoveredTuners[device], timeout=(.2, .2))
            r.raise_for_status()
            discoverResponse = r.json()
            if not isinstance(discoverResponse, dict):
                discoverResponse = {}
        except (requests.exceptions.RequestException, json.decoder.JSONDecodeError):
            discoverResponse = {}

        Legacy = False
        DeviceID = None
        LineupURL = None
        if 'Legacy' in discoverResponse:
            Legacy = bool(discoverResponse['Legacy'])
        if 'DeviceID' in discoverResponse:
            DeviceID = discoverResponse['DeviceID']
        if 'LineupURL' in discoverResponse:
            LineupURL = discoverResponse['LineupURL']

        if (Legacy) or (DeviceID is None) or (LineupURL is None):
            continue

        discoverResponse['LocalIP'] = device
        eligibleTuners.append(discoverResponse)

    return eligibleTuners

vars = {}
try:
	device = sys.argv[1]
	url = 'http://' + device + '/discover.json'
	r = requests.get(url)
	j = r.json()
	vars['DeviceAuth'] = j['DeviceAuth']
except:
	try:
		discoveredHDHRs = HDHRdiscover()
		vars['DeviceAuth'] = discoveredHDHRs[0]['DeviceAuth']
	except:
		print ("Discovery failed, use: " + __file__ + " \"Search String\" x.x.x.x (HDHomeRun IP)")
		exit()	

try:
	vars['Search'] = sys.argv[1]
except:
	print ("\nsearch <searchstring> [HDHR-IP}\n")
	print ("Use quotes for a multi-word search string")
	print ("Optional - you can put the IP of your HDHomeRun device at the end if discovery isn't working\n\n")
	exit()

qstring = urllib.urlencode(vars)
url = "https://api.hdhomerun.com/api/search?" + qstring
#print (url)
r = requests.get(url)
#print (r.text)
j = r.json()
for recording in j:
	print (recording["SeriesID"] + ': ' + recording["Title"])