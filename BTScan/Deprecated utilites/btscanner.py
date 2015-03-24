import sys,os,random,time,popen2,copy,string,MySQLdb,fcntl,socket,struct,commands,re
sys.path.append('.')

#
# scanners:
#
SCANNER_PIPE = '/tmp/btscan'
SCANNER_PATH = './btscan'

#
#getting local mac address
#
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
hwaddr = getHwAddr('eth1') 


class BTMonitor:
  # class to monitor BT on a device
  def __init__(self, scanner_path = SCANNER_PATH, scanner_pipe = SCANNER_PIPE):
    self.scanner_path = scanner_path
    self.scanner_pipe = scanner_pipe
    self.stopme = False
    
    
  def start(self):
    #open database connection
    self.db = MySQLdb.connect("localhost", "user", "gpuuser", "bluetooth1")

    #prepare a cursor object
    self.cursor =self.db.cursor()

    #prepare regular expression
    self.capture_re = re.compile('\s*(?P<bt_addr>(\w\w:?){6})\s*\|\s*(?P<rssi>-?\d*)')
   
    r, w = popen2.popen2(self.scanner_path)
    ret = r.readline()
    res = ret.rstrip('\n')  # may need to change for windows
    self.btscan_pid = 999999
    try: 
      self.btscan_pid = int(res)
    except:
      self.stop()
      return
    
    f = open(self.scanner_pipe, "r")
    line = "1"
    
    while ( line != "" and not self.stopme):
      line = f.readline()
      if(line != ""):  
        self.process_line(line)      
    f.close()
    r.close()
    w.close()

  def stop(self):
    #disconnect from SQL server
    self.db.close()
    try:
      os.kill(self.btscan_pid,9)
    except OSError:
      pass
    try:
      os.wait()
    except OSError:
      pass

  def process_line(self, data):
             
    m = self.capture_re.search(data)
    bt_addr = m.group('bt_addr')
    rssi = m.group('rssi')
    
    if not bt_addr or not rssi:
      print 'Unable to match line: ' + data
      return
    if bt_addr != "00:1D:6E:D9:59:E0":
        return
    print (bt_addr,rssi,time.time(),hwaddr)
    
    SQL = "INSERT INTO bluetoothTb1 (bdaddr,rssi,time,hwaddr) Values('%s','%s','%d','%s')"  % (bt_addr,rssi,time.time(),hwaddr)
                    
    try:
      #execute SQL command
        self.cursor.execute(SQL)
      #commit changes to database
        self.db.commit()
    except:
      #rollback in case of error
        self.db.rollback()
        print "fail"


#
#Setup and Run BT input
#
if __name__ == '__main__':
    btm = BTMonitor()
    try:
        btm.start()
    except KeyboardInterrupt:
        btm.stop()





