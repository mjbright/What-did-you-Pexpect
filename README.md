# What-did-you-Pexpect

A Pexpect presentation/tutorial with multi-hop ssh key insertion tool

This presentation/tutorial was shown at the 26 April 2016 Grenoble Python User Group.

It contains a Jupyter notebook to demonstrate the Python Pexpect module capabilities
before showing mhop_ssh.py a utility script capable of logging through a chain of servers
using ssh and sudo.  mhop_ssh.py is also capable of installing ssh keys on servers along the route.

Some parts of this tutorial use Docker containers to emulate server machines.  Those containers can be
built and run using the https://github.com/mjbright/Containers-as-servers repository.

Multi-hop use case
==================

The Pexpect tutorial uses containers to emulate separate machines to demonstrate ssh-key insertion across a
multi-hop and multi-user chain.

Assuming a chain of machines where to get to be root on host3, we must first pass by user 'user' from root@host2
To be root on host2, we must first pass by user 'user' from root@host1
To be root on host1, we must first pass by user 'user'

This was an actual use case for an OpenStack platform where access to certain controller/compute nodes is restricted
and passwords are initially unknown (only access is via ssh-keys from certain machines/accounts to certain machines/accounts).



