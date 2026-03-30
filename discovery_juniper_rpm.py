#!/usr/bin/env python3
"""
 Zabbix discovery junper rpm tests external script
 this script is intended to find RPM (Real test perfomance monitoring) owners and tests out of a juniper network devices

 the script accepts 2 arguments: hostname and community
 and returns a structured data back to a zabbix server

 first it does snmpwalk over jnxRpmResSumSent MIB Object
 from a device perspective it looks like this:

 user@ex2200> show snmp mib walk jnxRpmResSumSent ascii
 jnxRpmResSumSent."ISP1"."Test1".1 = 14
 jnxRpmResSumSent."ISP1"."Test1".2 = 15
 jnxRpmResSumSent."ISP1"."Test1".4 = 45614
 jnxRpmResSumSent."ISP2"."Test2".1 = 13
 jnxRpmResSumSent."ISP2"."Test2".2 = 15
 jnxRpmResSumSent."ISP2"."Test2".4 = 6073

 using jnxRpmResSumSent MIB Object we can find all existed tests. even those that are not performed successfully

 returned data are being structured to a form of a Zabbix discobery JSON
 { data: [
 {"{#RPMUUID}":"3.73.83.80.49.6.84.69.83.84.49", "{#RPMOWNER}":"ISP1", "{#RPMTEST}":"Test1" },
 {"{#RPMUUID}":"4.73.83.80.50.84.69.83.84.50", "{#RPMOWNER}":"ISP2", "{#RPMTEST}":"Test2" },
 ]}
"""

import sys
import json
import subprocess

def fail(msg):
    sys.stderr.write(str(msg) + "\n")
    print(json.dumps({"data": []}))
    raise SystemExit(1)


try:
    from pysnmp.hlapi import *
except Exception:
    # Fallback will use snmpwalk CLI if pysnmp API is unavailable.
    pass

def findsubstrings(s):
    la = s.split('.')
    lb = la[1:]

    i = int(la[0]) # length of RPMOWNER string

    l1 = lb[:i]    # get RPMOWNER part of array
    l2 = lb[i+1:]  # get RPMTEST part of array
    param2 = ''.join([chr(int(i)) for i in l1]) # convert number array to char array and join to string
    param3 = ''.join([chr(int(i)) for i in l2]) # convert number array to char array and join to string
    return param2, param3


if len(sys.argv) != 3:
    fail("Error parsing arguments")

hostname = sys.argv[1]
community=sys.argv[2]
jnxRpmResSumSent         = "1.3.6.1.4.1.2636.3.50.1.2.1.2"
jnxRpmResultsSampleTable = "1.3.6.1.4.1.2636.3.50.1.2.1.2"
l = []

try:
    used_pysnmp = False

    # pysnmp old API path
    if "nextCmd" in globals() and "SnmpEngine" in globals():
        used_pysnmp = True
        varBind = nextCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((hostname, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(jnxRpmResultsSampleTable)),
            lexicographicMode=False,
        )

        # do snmmpwalk and collect an rpm specific substring
        for res in varBind:
            s = str(res[3][0][0])[len(jnxRpmResultsSampleTable) + 1 : -2]
            l.append(s)

    # fallback path: net-snmp snmpwalk binary
    if not used_pysnmp:
        cmd = [
            "snmpwalk",
            "-v2c",
            "-c",
            community,
            "-On",
            hostname,
            jnxRpmResultsSampleTable,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            fail(proc.stderr.strip() or proc.stdout.strip() or "snmpwalk failed")

        prefix = jnxRpmResultsSampleTable + "."
        for line in proc.stdout.splitlines():
            left = line.split(" = ", 1)[0].strip()
            if left.startswith("."):
                left = left[1:]
            if not left.startswith(prefix):
                continue
            suffix = left[len(prefix) :]
            parts = suffix.split(".")
            if len(parts) > 1:
                suffix = ".".join(parts[:-1])
            if suffix:
                l.append(suffix)

except Exception as exc:
    fail(exc)

# lets make values inside the list l uniq
u = set(l)


jsonData=[]
for param1 in u:
    d={}
    if len(param1) > 0: # skip processing of empty responses
      param2, param3 = findsubstrings(param1)
      d["{#RPMUUID}"] = param1
      d["{#RPMOWNER}"] = param2
      d["{#RPMTEST}"] = param3
      jsonData.append(d)

jsonData = sorted(jsonData, key=lambda x: x['{#RPMOWNER}']+x['{#RPMTEST}'])

print(json.dumps({"data": jsonData}))
