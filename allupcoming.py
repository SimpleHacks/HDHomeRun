#!/usr/bin/python

# enable print() function even in python2
from __future__ import print_function

import requests, json
import platform

# Modules are not covered in __future__, but still changed APIs...
# search for all usage of this variable to find relevant parts
is_py2 = platform.python_version_tuple()[0] == '2'
if is_py2:
    import urllib
else:
    # the urllib module was split into three modules in Python3...
    import urllib.request, urllib.parse, urllib.error

import sys
import time
import socket

def HDHRdiscover():

    discoveredTuners = {}

    # 1. Add to 'discoveredTuners' from discovery URL (https://my.hdhomerun.com/discover)
    SDdiscover = []
    try:
        r = requests.get('https://my.hdhomerun.com/discover', timeout=(.5, .2))
        r.raise_for_status()
        SDdiscover = r.json()
        if not isinstance(SDdiscover, list):
            SDdiscover = []
    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError):
        SDdiscover = []
    # print (SDdiscover)

    for device in SDdiscover:
        if not isinstance(device, dict):
            print ("ignoring device ", device)
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


    # 2. Add to 'discoveredTuners' from a hand-constructed UDP discovery message (device type = tuner, device id = wildcard)
    discovery_udp_msg = bytearray.fromhex('00 02 00 0c 01 04 00 00 00 01 02 04 ff ff ff ff 4e 50 7f 35')
    discovery_udp_port = 65001
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

    # 3. Filter the 'discoveredTuners' into 'eligibleTuners', adding 'LocalIP' property
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
		print ("Discovery failed, use: " + __file__ + " x.x.x.x (HDHomeRun IP)")
		exit()	

if is_py2:
    qstring = urllib.urlencode(vars)
else:
    qstring = urllib.parse.urlencode(vars)
#print (qstring)
url = 'https://api.hdhomerun.com/api/recording_rules?' + qstring
r = requests.get(url)
t = r.json()

for task in t:
	print (task["RecordingRuleID"] + ' / ' + task["SeriesID"] + ': ' + task["Title"])
	vars['SeriesID'] = task["SeriesID"]

	if is_py2:
		qstring = urllib.urlencode(vars)
	else:
		qstring = urllib.parse.urlencode(vars)


	url = "https://api.hdhomerun.com/api/episodes?" + qstring
	#print (url)
	r = requests.get(url)
	if r.text == "null":
		print ("*** NO UPCOMING EPISODES ***")
		continue
	#print (r.text)
	j = r.json()
	for recording in j:
		#print (recording)
		try:
			etitle = recording["EpisodeTitle"]
		except:
			etitle =  task["Title"]
		stime = time.strftime( "%a, %d %b %Y %H:%M", time.localtime(recording["StartTime"]) )
		etime = time.strftime( "%H:%M", time.localtime(recording["EndTime"]) )
		print (stime + '-' + etime, recording["ChannelNumber"], recording["Title"] + ': ' + etitle)
