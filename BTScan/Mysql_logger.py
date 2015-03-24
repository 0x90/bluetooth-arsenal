import MySQLdb

class MysqlLogger(object):

    def __init__(self):
        self.db = MySQLdb.connect("18.125.1.67","user","gpuuser","bluetooth1")
        self.cursor =self.db.cursor()

    def log(self, p):
        x, y = p.position
        
        
        SQL = "INSERT INTO BluetoothTB1 " + \
            "(timestamp, receiver_mac, device_mac, rssi, x_pos, y_pos)" + \
            " Values('%d','%s','%s','%d','%f','%f')" \
            % (p.timestamp[0], p.receiver_mac, p.device_mac, p.rssi, x, y)
                
        try:
            self.cursor.execute(SQL)
            self.db.commit()
        except Exception, e:
            self.db.rollback()
            print "Failed to commit log to database, received %s" % str(e)

    def stop(self):
        self.db.close()
