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
import re

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

# 1. First, see if a first argument is the device's IP address, else use autodiscover, to get variables from tuner
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
		vars['DeviceAuth'] = discoveredHDHRs[0]['DeviceAuth'] # Note that this always uses the first discovered HDHR....
	except:
		print ("Discovery failed, use: " + __file__ + " x.x.x.x (HDHomeRun IP)")
		exit()	

# 2. parse the response into a query string (e.g., DeviceAuth), and get the recording rules from the device as JSON
if is_py2:
    qstring = urllib.urlencode(vars)
else:
    qstring = urllib.parse.urlencode(vars)
#print (qstring)
url = 'https://api.hdhomerun.com/api/recording_rules?' + qstring
r = requests.get(url)
t = r.json()

# 3. process the retrieved recording rules...
done = []
for task in t:
    # 3.1 filter recording rules (tasks) to movies (SeriesID starts with 'MV')
	if not re.match(r"^MV", task["SeriesID"]):
		continue
	#print (task["RecordingRuleID"] + ' / ' + task["SeriesID"] + ': ' + task["Title"])
    
    # 3.2 RE-USE the 'vars' dictionary, and add/overwrite the 'SeriesID' member, and ask tuner for episodes with this SeriesID
	vars['SeriesID'] = task["SeriesID"]
	qstring = urllib.parse.urlencode(vars)
	url = "https://api.hdhomerun.com/api/episodes?" + qstring
	#print (url)
	r = requests.get(url)

    # 3.3 stop parsing this recording rule (task) if no upcoming episodes of that movie
	if r.text == "null":
		print ("*** NO UPCOMING EPISODES ***") # BUGBUG -- list SeriesID?
		continue

    # 3.4 process the episodes, storing completed items in 'done'
	#print (r.text)
	j = r.json()
	for recording in j:
        # 3.4.1 Skip if already have the recording in 'done' (duplicate)
		if recording['ProgramID'] in done:
			continue
		else:
			done.append(recording['ProgramID'])
        # 3.4.2 Set the title to either 'EpisodeTitle' (if exists), or 'Title' otherwise
		try:
			etitle = recording["EpisodeTitle"]
		except:
			etitle =  task["Title"]
        # 3.4.3 Outut each result
		stime = time.strftime( "%a, %d %b %Y %H:%M", time.localtime(recording["StartTime"]) )
		etime = time.strftime( "%H:%M", time.localtime(recording["EndTime"]) )
		print (stime + '-' + etime, recording["ChannelNumber"], recording["Title"] + ': ' + etitle)

# Finally, print some output if no episodes for any movies were found
if not done:
    print ("*** No tasks are currently set to record a movie ***")
