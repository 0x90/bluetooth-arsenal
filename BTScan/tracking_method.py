#!/usr/bin/env python
import NLMaP, range_estimation, config
from collections import deque
import random, time

class TrackingMethod(object):
    """Abstract class representing a position estimator bound to a single remote device."""
    
    def __init__(self, device_mac):
        self.device_mac = device_mac
    
    def get_position(self, packet):
        """Compute a new position estimate based on an updated dataset.
            data is a data_packet instance.
            Return value is a tuple (x,y).
        """
        raise NotImplementedError



class RandomDataTracker(TrackingMethod):
    """Tracking method that simply returns points in a uniform distribution over [0,1)"""
    
    def get_position(self, packet):
        return (random.random(), random.random())



class NLMaPTracker(TrackingMethod):
    
    def __init__(self, device_mac):
        TrackingMethod.__init__(self, device_mac)
        self.receiver_positions = config.RECEIVER_POSITIONS
  
        self.receiver_buffer = dict([[recv, [deque(), None, None]] \
                              for recv in self.receiver_positions.keys()])
        self.data_max_age = .5 #in seconds
        self.range_estimator = range_estimation.RangeEstimator()
        
        self.iterations = 200
        self.delta = .1
        self.convergence = .8

    def get_position(self, p):
        #print 'Pre-Processing latency: %f sec' % (time.time() - p.timestamp[0])
        
        if not config.USE_FAKE_DATA:
            return (0, 0)
            
        distance = self.range_estimator.get_range(p.rssi)
        
        if not p.receiver_mac in self.receiver_buffer:
            print "[NLMaPTracker for %s]: Packet from unknown receiver %s; dropped" % \
                    (self.receiver_mac, p.receiver_mac)
            return (0, 0)
        
        self.receiver_buffer[p.receiver_mac][0].append((p.timestamp, distance))

        for receiver_mac in self.receiver_buffer.keys():
            data_buffer = self.receiver_buffer[receiver_mac][0]
            
            if len(data_buffer) == 0:
                return (0, 0)   # FIXME -- need error handling at higher level

            #while data_buffer[0][0][0] - timestamp[0] > self.data_max_age:
                #data_buffer.popleft()
            while len(data_buffer) >= 10:
                data_buffer.popleft()
            
            

            buffer = [b[1] for b in data_buffer]
            #print str(buffer)

            avg = sum(buffer) / len(buffer)  #consider a median filter instead of rolling average
            std = (sum([(x-avg)**2 for x in buffer]))**.5
            
            
            if True:
                std = 1  # FIXME: sketchy hack
            
            
            
            self.receiver_buffer[receiver_mac][1] = avg
            self.receiver_buffer[receiver_mac][2] = std
        
        x, y, z, d, s = self.nlmap_format_wrapper()
        
        try:
            m = NLMaP.MultiLateration(x, y, z, d, s, len(self.receiver_buffer.keys()))
            pos = m.GetPosition(self.iterations, self.delta, self.convergence)
        except:
            # FIXME: NLMaP failures (C++ exceptions) currently don't translate to 
            # python exceptions, but instead crash the process.  scan_server
            # currently revives dead TrackingThreads, but we need a better solution.
            print 'Modelling failure, continuing...'
            pos = (0, 0)
        #print 'Processing latency: %f sec' % (time.time() - p.timestamp[0])
        return (pos.x, pos.y)
        
    
    def nlmap_format_wrapper(self):
        
        def mk_float_array(l):
            f = NLMaP.floatArray(len(l))
            for i in range(len(l)):
                f[i] = l[i]
            return f
        
        receivers = self.receiver_positions.keys()
        (x, y, z) = [[self.receiver_positions[r][i] for r in receivers] for i in range(3)]
        (d, s) = [[self.receiver_buffer[r][i] for r in receivers] for i in (1, 2)]
        return map(mk_float_array, (x, y, z, d, s))
        
