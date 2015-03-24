
import math,time,random
import data_packet, config

class DataGenerator():
    """class used to get pseudo-random data in order to test tracking algorithms"""

    def __init__(self, error):
        
        self.receiver_positions = config.RECEIVER_POSITIONS
        self.mac = "Generator Device"
        self.error = error
        
    def get_position(self):
        """Return an x,y tuple representing the current position."""
        raise NotImplementedError

    def get_data(self):
        """Return a list of DataPackets corresponding to the receiver updates for this timestep. """
        x,y = self.get_position()

        rec = self.receiver_positions.keys()
        dist =  [((self.receiver_positions[i][0]-x)**2 + \
                      (self.receiver_positions[i][1] - y)**2)**.5 for i in rec]
        
        RSSI = [(-40*math.log(i,10) - 50.3) for i in dist]
        noisyRSSI = [int(random.gauss(R,self.error)) for R in RSSI]
                
        packets = [data_packet.DataPacket( \
                (time.time(), 0), rec[i] , self.mac , noisyRSSI[i]) \
                       for i in range(len(rec))]
        
        return packets        

class CircleDataGenerator(DataGenerator):
    
    def __init__(self, error, radius):
        DataGenerator.__init__(self, error)
        self.mac = "CircleDataGenerator"

        self.radius = radius
        
        self.theta = 0
        self.last_update = time.time()
        
    def get_position(self):

        elapsed = time.time() - self.last_update
        self.last_update = time.time()
        self.theta += 2*elapsed

        x = self.radius * (math.cos(self.theta) + 1)
        y = self.radius * (math.sin(self.theta) + 1)
        
        return (x, y)
    

class LinearInterpolator(DataGenerator):
    
    def __init__(self,error,corners_file):
        DataGenerator.__init__(self,error)
        self.mac = "LinearInterpolator"

        f = open(corners_file)
        self.points = [map(float, line[:-1].split(',')) for line in f]
        self.target_point = 1
        self.last_corner = time.time()

        self.time_between_points = 3

    def get_position(self):
        ellapsed = time.time() - self.last_corner
        p0 = self.points[self.target_point]
        p1 = self.points[self.target_point-1]
        x = p1[0] + (p0[0] - p1[0])*(ellapsed/self.time_between_points)
        y = p1[1] + (p0[1] - p1[1])*(ellapsed/self.time_between_points)
        if ellapsed > self.time_between_points:
            self.target_point = (self.target_point +1)% len(self.points)
            self.last_corner = time.time()
        return (x,y)
    

DATA_GENERATORS = [LinearInterpolator(.05, 'points1.txt'), \
                       CircleDataGenerator(1, 0.4)]


if __name__ == '__main__':
    data_gen = CircleDataGenerator(20, .1)
    for i in range(10):
        time.sleep(1.0)
        print str(data_gen.get_data())
