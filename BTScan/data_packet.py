class DataPacket(object):
    
    __slots__ = ['timestamp', 'receiver_mac', 'device_mac', 'rssi', 'position']
    
    def __init__(self, timestamp, receiver_mac, device_mac, rssi, position = None):
        
        self.timestamp = timestamp
        self.receiver_mac = receiver_mac
        self.device_mac = device_mac
        self.rssi = rssi
        self.position = position
    
    def __getstate__(self):
        return (self.timestamp, self.receiver_mac, self.device_mac, self.rssi, self.position)
    
    def __setstate__(self, state):
        self.timestamp, self.receiver_mac, self.device_mac, self.rssi, self.position = state

    def __repr__(self):
        return "(DataPacket: t=%f, r=%s, d=%s, rssi=%d, pos=%s)" % (self.timestamp[0], self.receiver_mac, self.device_mac, self.rssi, str(self.position))
