import numpy
import matplotlib
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import math
import sys

filename = sys.argv[1]

def plot(filename):
	fname = filename

	r = mlab.csv2rec(fname,names=['time','rssi'])

	fig = plt.figure()
	ax = fig.add_subplot(1,1,1)
	ax.plot(r.time,r.rssi)


	plt.show()

plot(filename)
