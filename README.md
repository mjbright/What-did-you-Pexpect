# What-did-you-Pexpect

A Pexpect presentation/tutorial with multi-hop ssh key insertion tool

This presentation/tutorial was shown at the 26 April 2016 Grenoble Python User Group.

It contains a Jupyter notebook to demonstrate the Python Pexpect module capabilities
before showing mhop_ssh.py a utility script capable of logging through a chain of servers
using ssh and sudo.  mhop_ssh.py is also capable of installing ssh keys on servers along the route.

Some parts of this tutorial use Docker containers to emulate server machines.  Those containers can be
built and run using the https://github.com/mjbright/Containers-as-servers repository.

Use Case1: Multi-hop logins/ ssh key setup
==========================================

The Pexpect tutorial uses containers to emulate separate machines to demonstrate ssh-key insertion across a
multi-hop and multi-user chain.

Assuming a chain of machines where to get to be root on host3, we must first pass by user 'user' from root@host2
To be root on host2, we must first pass by user 'user' from root@host1
To be root on host1, we must first pass by user 'user'

This was an actual use case for an OpenStack platform where access to certain controller/compute nodes is restricted
and passwords are initially unknown (only access is via ssh-keys from certain machines/accounts to certain machines/accounts).

The above steps can all be automated using Pexpect.

Tool: mhop_ssh.py
==================

The tool used in this case is mhop_ssh.py which allows to login across a chain of ssh/sudo connections.

Note: tools such as ssh-copy-id and pxssh allow to do this, but only directly to a specific user/machine.
      This tool allows to insert keys, for example, when direct access to those machines is not available.

mhop_ssh.py usage:
------------------

TBD

Use Case2: Downloading switch configuration
===========================================

Another use case is to be able to automatically download the configuration from a network switch.

The steps required to do this manually (normally) are:
- ssh to switch
- provide password
- 'sys' command
- 'display current' to dump config
- Press 'space' for each page

The above steps can all be automated using Pexpect.


Tool: switch_config.py
=======================

This tools can be used to output the switch config on stdout.

The tool has to be able to perform ssh login, send the password, run the sys command (change the expected login prompt after 'sys' is run), run the "display current" command, detect 'pager' prompts and send space to advance.


switch_config.py usage:
-----------------------

TBD



