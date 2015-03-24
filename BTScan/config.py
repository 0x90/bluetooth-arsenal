USE_FAKE_DATA = False
USE_MYSQL_LOGGING = True  #enable mysql database logging

DEFAULT_MAP = 'conf.jpg'  #what map is loaded by default
DEFAULT_MAP_DIMENSIONS = ('default',1,1)

TRACKING_ENABLED = False #program initializes with tracking enabled
TRACKING_HISTORY = 100

DATA_FREQ = 30  #number of data points per second
POLL_PERIOD = 100

if USE_FAKE_DATA:
    RECEIVER_POSITIONS = {'mac1' : (0, 0, 0),
                          'mac2' : (0, 1, 0),
                          'mac3' : (1, 1, 0),
                          'mac4' : (1, 0, 0)}
else:
    RECEIVER_POSITIONS = {'00:09:5b:f8:14:43' : (1, 0, 0),
                          '00:0f:b5:0b:d8:e6' : (1, 1, 0),
                          '00:0f:b5:0b:df:42' : (0, 1, 0),
                          '00:09:5b:f8:a1:35' : (0, 0, 0)}

