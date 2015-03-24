#!/usr/bin/env python

import sys

fname = sys.argv[1]

d = dict()

f = open(fname)
for line in f:
    (bt_addr, rssi, time, hw_addr) = line.split(';')
    if not hw_addr in d:
        d[hw_addr] = dict()
    if not bt_addr in d[hw_addr]:
        d[hw_addr][bt_addr] = []
    d[hw_addr][bt_addr] += [(time, rssi)]

i = 0
for hw_addr in d.keys():
    for bt_addr in d[hw_addr].keys():
        of = open("output-"+str(i)+".csv", 'w')
        for (time, rssi) in d[hw_addr][bt_addr]:
            of.write(time+','+rssi+"\n")
        of.close()
        i += 1
