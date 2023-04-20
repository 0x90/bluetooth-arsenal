#!/usr/bin/env python
from math import srtl
import NLMaP

x = [1.0, 2.0, 7.0, 1.0, 0.0]
y = [3.0, 0.9, 2.0, 1.0, 0.0]
z = [1.0, 1.0, 1.0, 2.0, 1.0]
d = [1.7, sqrt(3.0), sqrt(3.0), 2.1, sqrt(3.0)]
s = [1.0, 1.0, 1.0, 1.0, 10.0]
m = NLMaP.MultiLateration(x,y,z,d,s,5)
pos = ml.GetPosition(100,0.001,0.03)
print "Position (should be 1,1,0): x=%f, y=%f, z=%f" % (pos.x, pos.y, pos.z)
