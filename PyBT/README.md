PyBT
====

Hackable Bluetooth stack written in Python
------------------------------------------

PyBT is a crappy half implementation of a Bluetooth stack in Python. At
the moment it only supports Bluetooth Smart (BLE).

PyBT emphasizes hackability over correctness. It mostly follows the
rules, unless you tell it not to.

Installation
------------

A standard python setup script is included.

    # python setup.py install

This will install the `PyBT` egg.

PyBT is built on Scapy, but depends on features that have not yet been
merged upstream. For the time being, please install Scapy from
https://bitbucket.org/mikeryan1/scapy
