#!/usr/bin/env python3
"""
Zabbix discovery script for Juniper RPM (Real time Performance Monitoring) tests.

This script discovers RPM owners and tests from Juniper network devices via SNMP
and returns structured JSON data for use with Zabbix external discovery.

Usage:
    discovery_juniper_rpm.py <hostname> <snmp_community>

Output (Zabbix LLD JSON):
    {
        "data": [
            {
                "{#RPMUUID}":  "3.73.83.80.49.6.84.69.83.84.49",
                "{#RPMOWNER}": "ISP1",
                "{#RPMTEST}":  "Test1"
            },
            ...
        ]
    }

The script walks the jnxRpmResSumSent MIB OID to enumerate all RPM tests,
including those not yet successfully completed.

Example SNMP walk on device:
    user@ex2200> show snmp mib walk jnxRpmResSumSent ascii
    jnxRpmResSumSent."ISP1"."Test1".1 = 14
    jnxRpmResSumSent."ISP1"."Test1".2 = 15
    jnxRpmResSumSent."ISP2"."Test2".1 = 13
    jnxRpmResSumSent."ISP2"."Test2".2 = 15
"""

import sys
import json
from pysnmp.hlapi import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    nextCmd,
)

# jnxRpmResSumSent OID – used to enumerate all existing RPM tests
JNX_RPM_RES_SUM_SENT = "1.3.6.1.4.1.2636.3.50.1.2.1.2"

ERR_MSG = (
    '{"data": [{"error": "Usage: discovery_juniper_rpm.py <hostname> <snmp_community>"}]}\n'
)


def parse_rpm_oid_suffix(suffix):
    """
    Parse the OID suffix that encodes RPMOWNER and RPMTEST as length-prefixed
    ASCII byte sequences.

    OID suffix format:
        <owner_len>.<owner_bytes...>.<test_len>.<test_bytes...>.<index>

    Returns (owner, test) as strings, or (None, None) on parse failure.
    """
    parts = suffix.split(".")
    if not parts:
        return None, None

    try:
        owner_len = int(parts[0])
        owner_bytes = parts[1 : 1 + owner_len]
        # Position of the test length field, immediately after the owner bytes
        test_len_idx = 1 + owner_len
        test_len = int(parts[test_len_idx])
        test_bytes = parts[test_len_idx + 1 : test_len_idx + 1 + test_len]

        owner = "".join(chr(int(b)) for b in owner_bytes)
        test = "".join(chr(int(b)) for b in test_bytes)
        return owner, test
    except (IndexError, ValueError):
        return None, None


def discover_rpm(hostname, community):
    """
    Walk jnxRpmResSumSent via SNMPv2c and return a list of unique RPM entries.
    Each entry is a dict with {#RPMUUID}, {#RPMOWNER}, {#RPMTEST}.
    """
    seen = set()
    results = []

    var_binds = nextCmd(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((hostname, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(JNX_RPM_RES_SUM_SENT)),
        lexicographicMode=False,
    )

    for error_indication, error_status, error_index, var_bind_list in var_binds:
        if error_indication:
            sys.stderr.write(f"SNMP error: {error_indication}\n")
            break
        if error_status:
            sys.stderr.write(
                f"SNMP error: {error_status.prettyPrint()} at "
                f"{var_bind_list[int(error_index) - 1][0] if error_index else '?'}\n"
            )
            break

        oid_str = str(var_bind_list[0][0])
        # Extract the suffix after the base OID
        suffix = oid_str[len(JNX_RPM_RES_SUM_SENT) + 1 :]

        if not suffix or suffix in seen:
            continue

        owner, test = parse_rpm_oid_suffix(suffix)
        if owner is None or test is None:
            continue

        seen.add(suffix)
        results.append(
            {
                "{#RPMUUID}": suffix,
                "{#RPMOWNER}": owner,
                "{#RPMTEST}": test,
            }
        )

    results.sort(key=lambda x: x["{#RPMOWNER}"] + x["{#RPMTEST}"])
    return results


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(ERR_MSG)
        sys.exit(1)

    hostname = sys.argv[1]
    community = sys.argv[2]

    data = discover_rpm(hostname, community)
    print(json.dumps({"data": data}, indent=4))


if __name__ == "__main__":
    main()
