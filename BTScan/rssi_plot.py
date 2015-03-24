from PyQt4.QtCore import *
from PyQt4.QtGui import *
import matplotlib
matplotlib.use('QT4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import deque
import threading, config

class RSSIPlot(object):

    def __init__(self, device_mac):
        self.device_mac = device_mac
        self.receiver_plots = dict()

        self.window = QWidget()
        self.window.resize(600, 750)
        self.window.setWindowTitle('RSSI')
        
        self.layout = QVBoxLayout(self.window)

        self.figure = Figure(figsize=(5, 5))
        self.canvas = FigureCanvas(self.figure)
        self.figure.subplots_adjust(hspace=.5)
        self.layout.addWidget(self.canvas)
        
        self.i = 0
        
        if config.USE_FAKE_DATA:
            self.buffer_length = 300
        else:
            self.buffer_length = 50
    
    def show(self):
        self.window.show()

    def plot_point(self, packet):        
        if not packet.receiver_mac in self.receiver_plots:
            print 'Creating new plot for receiver %s' % packet.receiver_mac
            i = len(self.receiver_plots) + 1
            ax = self.figure.add_subplot(4, 1, i, title=packet.receiver_mac)
            line, = ax.plot(range(10), lw=2)
            self.receiver_plots[packet.receiver_mac] = [ax, line, [], [], 0]
            
        if not self.window.isVisible():
            return
        
        if config.USE_FAKE_DATA:
            if not packet.device_mac == 'CircleDataGenerator':
                return
        else:
            if not packet.device_mac == '00:1d:6e:d9:59:e0':
                return
        
        ax, line, xdata, ydata, index = self.receiver_plots[packet.receiver_mac]
        index = index + 1
        
        xdata.append(index)
        ydata.append(100 + packet.rssi)
        
        if len(xdata) > self.buffer_length:
            del xdata[0]
            del ydata[0]
        
        ax.set_xbound(lower=index-self.buffer_length, upper=index)
        if config.USE_FAKE_DATA:
            ax.set_ybound(lower=0, upper=100)
        else:
            ax.set_ybound(lower=20, upper=60)
        
        line.set_data(xdata, ydata)
                
        self.i += 1
        if (self.i % 75 == 0) or not config.USE_FAKE_DATA:
            self.canvas.draw()
            
        self.receiver_plots[packet.receiver_mac][2:] = [xdata, ydata, index]
        
        #ax.draw_artist(line)
        #self.figure.canvas.blit(ax.bbox)
        
        
