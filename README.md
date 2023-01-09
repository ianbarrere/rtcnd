# rtcnd
### Purpose:
rtcnd is a lightweight, open source tool for listening for and acting on potential configuration
changes to network devices. Functionality is mostly modeled after the RTCN feature from SolarWinds
NCM.

### Functionality:
The daemon is only one component among several others required for making this work.

First, something must call the API endpoint to indicate that some device configuration may have
changed. In most cases this will be a syslog server, matching on a particular string in a
received syslog message. There would be a small component on the syslog server which makes
the API call with the hostname in question.

Second, you need a command to run (NCM_COMMAND). I have done this in the past with a wrapper
command that expects a comma-separated list of hosts to run on that runs an ansible playbook
to get device configuration for those hosts:

    sudo -u ansible /usr/local/sbin/ansible_ncm.sh device1,device2,device3

Third, and related to the second point, you need to put the config somewhere. So in the example
above we dump the output to some files in a git repo and then automate the commit and push.

### Process:

1) Network device config is changed
2) Syslog server(s) receives the message and matches a common string that indicates that the
config has changed
3) Syslog server(s) react to received message by sending PUT to /devices/{hostname} on the
host running rtcnd
4) After time period INTERVAL, host running rtcnd runs NCM_COMMAND against the hosts in
the set
