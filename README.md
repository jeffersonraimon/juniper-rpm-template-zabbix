# juniper-rpm-template-zabbix

Zabbix 6.0+ template for monitoring Juniper RPM (Real Time Performance Monitoring) probes via SNMPv2c.

Based on [comsourcecz/zabbix-recipes](https://github.com/comsourcecz/zabbix-recipes), updated for Zabbix 6.0+.

## Contents

| File | Description |
|---|---|
| `discovery_juniper_rpm.py` | External discovery script (Python 3 + pysnmp) |
| `template_juniper_rpm.yaml` | Zabbix 6.0 template (YAML) |

## What it monitors

For every RPM probe configured on the Juniper device the template creates:

* **RTT** – round-trip time (ms)
* **Jitter** – jitter (ms)
* **PacketLoss** – packet loss (%)
* **Trigger** – fires when packet loss > 2 %
* **Graph** – RTT + Jitter + PacketLoss per probe

## Requirements

* Zabbix Server 6.0 or later
* Python 3 with [pysnmp](https://pypi.org/project/pysnmp/) installed on the Zabbix Server
* SNMPv2c enabled on the Juniper device

## Juniper device configuration

Configure RPM probes on the Juniper device. Example:

```
services {
    rpm {
        probe ISP1 {
            test Jitter {
                probe-type icmp-ping-timestamp;
                target address 2.2.2.2;
                probe-count 15;
                probe-interval 1;
                test-interval 15;
                source-address 2.2.2.1;
                data-size 1400;
                thresholds {
                    successive-loss 2;
                }
                hardware-timestamp;
            }
        }
        probe ISP2 {
            test Jitter {
                probe-type icmp-ping-timestamp;
                target address 1.1.1.2;
                probe-count 15;
                probe-interval 1;
                test-interval 15;
                source-address 1.1.1.1;
                data-size 1400;
                thresholds {
                    successive-loss 2;
                }
                hardware-timestamp;
            }
        }
    }
}
```

## Installation

1. Install pysnmp on the Zabbix Server:

   ```bash
   pip3 install pysnmp
   ```

2. Copy `discovery_juniper_rpm.py` to the external scripts directory (default `/usr/lib/zabbix/externalscripts/` or as configured in `zabbix_server.conf`):

   ```bash
   cp discovery_juniper_rpm.py /usr/lib/zabbix/externalscripts/
   chmod +x /usr/lib/zabbix/externalscripts/discovery_juniper_rpm.py
   chown zabbix:zabbix /usr/lib/zabbix/externalscripts/discovery_juniper_rpm.py
   ```

3. Import `template_juniper_rpm.yaml` into Zabbix via **Configuration → Templates → Import**.

4. Apply the template **Template Juniper RPM** to the Juniper host.

5. Set the macro `{$SNMP_COMMUNITY}` on the host (or globally) to the correct SNMPv2c community string.

Within 5 minutes the low-level discovery rule will find all RPM tests and create items, triggers and graphs automatically.

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$SNMP_COMMUNITY}` | `public` | SNMPv2c community string |

## Discovery macros returned by the script

| Macro | Example value | Description |
|---|---|---|
| `{#RPMUUID}` | `3.73.83.80.49.6.84.69.83.84.49` | OID suffix unique to each RPM test |
| `{#RPMOWNER}` | `ISP1` | RPM probe owner name |
| `{#RPMTEST}` | `Jitter` | RPM probe test name |