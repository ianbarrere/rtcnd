#!/usr/bin/python3
"""
rtcnd.py
A lightweight realtime change notification daemon similar to the SolarWinds RTCN
functionality.

Expects a separate component (usually a syslog server) to make a PUT call towards the
API endpoint in the event of a likely config change on a device (as a result of a
received syslog message for example).

Starts a thread which listens for PUT requests at /devices. Expects a single hostname
to be input. Compiles a set of hostnames and runs NCM_COMMAND on an interval to check
for config changes.

Requires a few environment variables to be set, examples on following line:
RTNCD_NCM_COMMAND: OS level command to run when triggered. Usually an ansible playbook.
    'sudo -u ansible /usr/local/sbin/ansible_ncm.sh'
RTCND_CHECK_INTERVAL: Check interval in seconds
    300
RTCND_HOSTNAME_FORMAT: Expected format for hostnames
    '^[A-Z]{3}\\d{1}[A-Z]{2,5}\\d{2}'
RTCND_LOG: Logfile
    '/var/log/rtcn.log'
RTCND_JOIN_FUNCTION: How to join the host_set together into an argument for NCM_COMMAND
    '",".join(map(str, host_set))'
"""
import time
import os
import re
import datetime
import sys
import threading
from fastapi import FastAPI


def require_env(variables) -> None:
    """Check environment variables required for running"""
    env = os.environ

    missing = [x for x in variables if x not in env or env[x].strip() == ""]

    if missing:
        print("rtcnd requires these environment variables to be set:")

        for x in variables:
            if x in missing:
                print(f"[ ] {x}")
            else:
                print(f"[x] {x}")

        sys.exit(1)


NCM_COMMAND = os.environ.get("RTNCD_NCM_COMMAND")
INTERVAL = int(os.environ.get("RTCND_CHECK_INTERVAL"))
HOSTNAME_FORMAT = os.environ.get("RTCND_HOSTNAME_FORMAT")
LOGFILE = os.environ.get("RTCND_LOG")
HOST_SET_SEPARATOR = ","

require_env(
    ["RTNCD_NCM_COMMAND", "RTCND_CHECK_INTERVAL", "RTCND_HOSTNAME_FORMAT", "RTCND_LOG"]
)

app = FastAPI()
app.state.host_set = set()


@app.put("/devices/{hostname}")
def add_host(hostname: str):
    """
    Main logic function
    Handles PUTs to /devices, adds device to host_set, starts thread for checking
    host_set
    """
    message = process_hostname(hostname, app.state.host_set)

    with open(LOGFILE, "a") as logfile:
        logfile.write(message)

    check = threading.Thread(
        name="list_check", target=host_set_check, args=(app.state.host_set,)
    )
    check.daemon = True
    check.start()


def process_hostname(hostname: str, host_set: set) -> str:
    """Checks hostname against host_set and returns log message"""
    iso_time = datetime.datetime.now().isoformat()
    if not re.compile(HOSTNAME_FORMAT).match(hostname):
        return (
            f"{iso_time}: ERROR! unrecognized hostname format, got string "
            f"'{hostname}', ignoring.\n"
        )

    if hostname not in host_set:
        host_set.add(hostname)
        return (
            f"{iso_time}: {hostname} not in host list for next check, "
            f"adding. Current host list: {host_set}\n"
        )

    return (
        f"{iso_time}: {hostname} already in host list for next check, "
        f"ignoring. Current host list: {host_set}\n"
    )


def host_set_check(host_set: set) -> None:
    """
    Checks host_set periodically and runs NCM_COMMAND when required
    """
    while True:
        time.sleep(INTERVAL)
        ncm_command_argument = HOST_SET_SEPARATOR.join(map(str, host_set))
        if len(host_set) > 0:
            iso_time = datetime.datetime.now().isoformat()
            with open(LOGFILE, "a") as logfile:
                logfile.write(
                    f"{iso_time}: possible changes to {ncm_command_argument} during "
                    f"the last {INTERVAL} seconds, running {NCM_COMMAND}\n"
                )
            os.system(f"{NCM_COMMAND} {ncm_command_argument}")
            host_set.clear()
