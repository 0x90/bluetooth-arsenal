# tracker_interface in PyQt
# kaycool
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import scan_server, config, data_packet, Mysql_logger, rssi_plot
from PIL import Image
from collections import deque
import sys, time, Queue, random
import pickle

class MainApp (QMainWindow):
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        # Variables
        self.device_list = dict() #contains tracking_state, color, row, listed by MAC
        self.position_data = dict()
        self.Hlength = config.TRACKING_HISTORY # length of visible tracking history
        self.evt_queue = Queue.Queue() # queue of data streaming from scan_server
        
        ### GUI SETUP ###
        QMainWindow.__init__(self)
        
        self.resize(1000, 600)
        self.setWindowTitle('Tracker')
        
        # Menu
        # Create actions
        quit = QAction('Quit', self)
        quit.setShortcut('Ctrl+Q')
        quit.setStatusTip('Exit Application')
        self.connect(quit, SIGNAL('triggered()'), SLOT('close()'))

        loadMap = QAction('Load Building', self)
        loadMap.setShortcut('Ctrl+o')
        loadMap.setStatusTip('Load Building')
        self.connect(loadMap, SIGNAL('triggered()'), self.mapOpen)

        showRSSI = QAction('Show RSSI', self)
        showRSSI.setShortcut('Ctrl+r')
        showRSSI.setStatusTip('Show RSSI')
        self.connect(showRSSI, SIGNAL('triggered()'), self.showRSSI)
        
        history = QAction('History', self)
        history.setShortcut('Ctrl+h')
        history.setStatusTip('History')
        self.connect(history, SIGNAL('triggered()'), self.History)
       
       
        # Remove highlighted tab
        rmTab = QAction('Remove Map', self)
        rmTab.setShortcut('Ctrl+w')
        rmTab.setStatusTip('Remove Map')
        self.connect(rmTab, SIGNAL('triggered()'), self.rmCurTab)
        
        # Rename highlighted tab
        rnTab = QAction('Rename Map', self)
        # rnTab.setShortcut('Ctrl+w')
        rnTab.setStatusTip('Rename Map')
        self.connect(rnTab, SIGNAL('triggered()'), self.rnCurTab)
        
        # Initialize menu bar, set menu options
        menubar = QMenuBar()
        file = menubar.addMenu('&File')
        maps = menubar.addMenu('&Map')
        file.addAction(loadMap)
        file.addAction(showRSSI)
        file.addAction(history)
        file.addAction(quit)
        
        tabs = menubar.addMenu("&Tabs")
        tabs.addAction(rmTab)
        tabs.addAction(rnTab)
        
        self.setMenuBar(menubar)
        
        # Tabs
        self.mainTab = QTabWidget()
        self.sideTab = QTabWidget()
        
        self.mapView = Map(self, 'test-grid.gif')
        self.descriptionView = QLabel()
        self.deviceTable = self.createSideMenu()

        self.mainTab.addTab(self.mapView, "Main")
        self.mainTab.addTab(self.descriptionView, "Secondary")
        
        self.sideTab.addTab(self.deviceTable, "Devices")
        
        self.splitter = QSplitter()
        self.splitter.addWidget(self.mainTab)
        self.splitter.addWidget(self.sideTab)
        self.splitter.setSizes([600, 400])
        self.setCentralWidget(self.splitter)
        
        # Creates box for raw data dump; show with showRSSI()
        self.RSSI = rssi_plot.RSSIPlot('mac1')

    def createSideMenu(self):
        tbl = QTableWidget(1, 4)
        self.connect(tbl, SIGNAL("itemChanged(QTableWidgetItem*)"), self.handleItemChanged)
        self.connect(tbl, SIGNAL("cellClicked(int, int)"), self.handleDeviceTableClick)
        
        tbl.setHorizontalHeaderLabels(["", "BT Addr", "# Receivers", "Color"])
        tbl.setColumnWidth(0, 27)
        tbl.setColumnWidth(1, 150)
        tbl.setColumnWidth(2, 90)
        tbl.setColumnWidth(3, 50)
        
        return tbl
    
    def handleItemChanged(self, item):
        data = str(item.data(Qt.UserRole).toString())
        if data:
            if not 'isCheckBox' in item.__dict__:  # FIXME: other half of sketchy checkbox hack
                return      # Not a checkbox
            state = (item.checkState() == 2)
            print 'New tracking state for %s : %s' % (data, state)
            self.device_list[data][0] = state
    
    def handleDeviceTableClick(self, row, col):
        if col == 3:
            item = self.deviceTable.item(row, col)
            dev = str(item.data(Qt.UserRole).toString())
            color = QColorDialog.getColor()
            item.setBackground(QBrush(color))
            self.device_list[dev][1] = color

    
    def mapOpen(self): # Loads map in current tab
        filename = QFileDialog.getOpenFileName(self, 'Open file')
        f=open(filename).readline()
        
        fp=f.rstrip()
        fp=fp.strip('\'')+'.p'
        execfile(filename.__str__())
        building=pickle.load(open(fp))
        
        for floor in building.floors:
            newTab = Map(self, floor.file_name)
            self.addTab(floor.name, floor.file_name)
    
    
    def History(self):
        length = QInputDialog.getInt(self, "Tracking History",
                                      "Please input the history length", value=5,
                                      min=0)
        self.Hlength = length

    def closeEvent(self, event):
        self.pipeline.shutdown()
        event.accept()
    
    def addTab(self, name, image):
        new = Map(self, image)
        tw = self.mainTab
        tw.addTab(new, str(name))
       
    
    def rmCurTab(self):
        self.mainTab.removeTab(self.mainTab.currentIndex())
        
    def rnCurTab(self):
     input = QInputDialog(self)
     input.setLabelText('New name?')
     newName = QInputDialog.getText(self, 'Rename Tab', 'New name?')
     if str(newName[0]) != "":
         mt = self.mainTab
         mt.setTabText(mt.currentIndex(), str(newName[0]))

    def showRSSI(self):
        self.RSSI.show()
        # TODO: pipe raw data to this window

   
       
    ###################################
    ##### DEVICE HANDLING METHODS #####
    ###################################
    
    # Checks queue for new packets (?)
    def check_queue(self):
        try:
             while True:
                item = self.evt_queue.get_nowait()
                if type(item) == str:
                    self.handle_new_device(item)
                else:
                    self.handle_new_position(item)
        except Queue.Empty:
            pass
        self.mainTab.widget(0).update()
    
    # adds necessary information for a new device (device_list, position_data)
    def handle_new_device(self, device_mac):
         print 'New device detected: %s' % device_mac
         self.position_data[device_mac] = deque([])
         self.add_device(device_mac)
        
   
     # Adds new device being tracked to side frame
    def add_device(self, device_mac):
    
        row = len(self.device_list)
        color = Qt.red
        
        # Add device to stored dictionary
        self.device_list[device_mac] = [True, color, row]
              
        ### Add new device in sidebar
        self.deviceTable.setRowCount(row+1)
        
        checkbox = QTableWidgetItem()
        checkbox.isCheckBox = True  # FIXME: Sketchy hack to help event handler
        checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        checkbox.setCheckState(Qt.Checked)
        checkbox.setData(Qt.UserRole, device_mac)
        
        self.deviceTable.setItem(row, 0, checkbox)
        
        dmLabel = QTableWidgetItem(device_mac)
        dmLabel.setFlags(Qt.ItemIsEnabled)
        self.deviceTable.setItem(row, 1, dmLabel)
        
        nrLabel = QTableWidgetItem("#")
        nrLabel.setFlags(Qt.ItemIsEnabled)
        self.deviceTable.setItem(row, 2, nrLabel)
        
        cLabel = QTableWidgetItem("")
        cLabel.setBackground(QBrush(color))
        cLabel.setFlags(Qt.ItemIsEnabled)
        cLabel.setData(Qt.UserRole, device_mac)
        self.deviceTable.setItem(row, 3, cLabel)
       

    def add_packet(self, packet):
        #floor=self.mainTab.indexOf(packet.floor)
        # for now, only uses tab1
        
        tab1.paintEvent(QPaintEvent(self))
                
        #handle lack of map

    def handle_new_position(self, packet):
        if not packet.device_mac in self.position_data:
            self.handle_new_device(packet.device_mac)
        
        self.packet_buf = self.position_data[packet.device_mac]
        self.packet_buf.append(packet)
        
        self.RSSI.plot_point(packet)
        
        while len(self.packet_buf) > self.Hlength:
            
            self.packet_buf.popleft()

        
    ##remove_packet
    
class Map(QLabel):

    #pathname is the pathname of the map file
    # dList
    def __init__ (self, main, image):
        super(Map, self).__init__()
        self.m=main
        self.pm = QPixmap(image).scaled(self.m.mainTab.size())
        self.setPixmap(self.pm)
        self.time=1
        
    #e: event
    def paintEvent(self, e):
        painter = QPainter();
        painter.begin(self)
        painter.drawPixmap(0, 0, self.pm.scaled(self.m.mainTab.size()))
        self.drawPoints(painter)
        painter.end()
    
    def drawPoints(self, qp):

        for device_mac in self.m.position_data.keys():
            if not self.m.device_list[device_mac][0]:
                continue
            
            color = self.m.device_list[device_mac][1]
            qp.setBrush(color)
            qp.setPen(color)
            
            for packet in self.m.position_data[device_mac]:
                x,y = packet.position
                qp.drawEllipse(x*self.width(), y*self.height(),5,5)
                
class SceneMap(QWidget):
    """Higher-performance map implementation.  Work in progress."""
    
    def __init__(self, main, image):
        super(QWidget, self).__init__()
        self.m = main
        self.pm = QGraphicsPixmap(QPixmap(image).scaled(self.m.mainTab.size()))
        self.setPixmap(self.pm)
        self.time = 1
        layout = QVBoxLayout()
        self.scene = QGraphicsScene()
        layout.addItem(self.scene)
        self.setLayout(layout)
    


#file options dialog to define map dimensions
# TODO: adapt to PyQt
#class MapOptions(tkSimpleDialog.Dialog):

    #def __init__(self, parent, callback):
       # self.callback = callback
       # tkSimpleDialog.Dialog.__init__(self, parent)
    
    #def body(self,master):
       # Label(master, text="Name:").grid(row=0)
        #Label(master, text="Width:").grid(row=1)
        #Label(master, text="Height:").grid(row=2)
        
        #self.e1 = Entry(master)
        #self.e2 = Entry(master)
       #self.e3 = Entry(master)
        
       # self.e1.grid(row=0, column=1)
        #self.e2.grid(row=1, column=1)
       # self.e3.grid(row=2, column=1)
        
       # return self.e1
    
   # def validate(self):
        #self.val = True
       # return 1

    #def apply(self):
       # self.callback(self)

# TODO: resize map in response to window resize

# Run application

if __name__ == '__main__':
    app = QApplication(sys.argv)

    if config.USE_FAKE_DATA:
        s = scan_server.TrackingPipeline(fakeit=True)
    else:
        s = scan_server.TrackingPipeline(fakeit=False)
        
    main = MainApp(s)
    s.scan_server.add_new_device_callback(lambda dev: main.evt_queue.put(dev))
    s.add_new_position_callback(lambda packet: main.evt_queue.put(packet))
    
    if config.USE_MYSQL_LOGGING:
        m = Mysql_logger.MysqlLogger()
        s.add_new_position_callback(lambda packet: m.log(packet))
    
    main.show()
    t = QTimer(main)
    main.connect(t, SIGNAL("timeout()"), main.check_queue)
    t.start(100)

    sys.exit(app.exec_())

        
        ##############################
        # Things to add #
        # iconsize, toolButtonStyle #
        ##############################
