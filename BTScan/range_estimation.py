#!/usr/bin/env python

class RangeEstimator(object):
    """Class used to convert RSS values in Dbm to a distance in meters."""
    
    def get_range(self,RSSI):
       ##RSSI is a variable storing a number in Dbm and is negative
  
       return 10.0 ** ((-503/400.0) - (RSSI/40.0))
        #return RSSI
