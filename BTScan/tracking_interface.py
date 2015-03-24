from Tkinter import *
import time, tkMessageBox,tkColorChooser,tkFileDialog,Queue,random,tkSimpleDialog
import scan_server, config, data_packet, Mysql_logger  #rssi_plot
from PIL import Image,ImageTk
from collections import deque

class App:
 
    def __init__(self):
        
        self.root = Tk()

        self.frame = Frame(self.root,width=800,height=800)
        self.frame.pack()
        
       
        self.MainMenu()
        self.SideFrame()
        self.MainCanvas()
        
        self.device_list = dict()   # GUI elements for devices
        
        self.position_data = dict()
        
        self.Hlength = config.TRACKING_HISTORY  #length of visible tracking history
                
        self.evt_queue = Queue.Queue()
        self.root.after(config.POLL_PERIOD, self.check_queue)

        self.rssi_plot = None
    
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
        
        self.root.after(config.POLL_PERIOD, self.check_queue)
    
    def handle_new_device(self, device_mac):
        print 'New device detected: %s' % device_mac
        self.position_data[device_mac] = deque([])
        self.add_device(device_mac)

        #if not self.rssi_plot:
            #self.rssi_plot = (device_mac, rssi_plot.RSSIPlot(device_mac))
    
    def handle_new_position(self, packet):
        if not packet.device_mac in self.position_data:
            self.handle_new_device(packet.device_mac)
        
        packet_buf = self.position_data[packet.device_mac]
        packet_buf.append(packet)
        self.add_packet(packet)
        
        while len(packet_buf) > self.Hlength:
            
            old_packet = packet_buf.popleft()
            self.remove_packet(old_packet)

        #print 'Through-graphics latency: %f sec' % (time.time() - packet.timestamp[0])

        #if packet.device_mac == self.rssi_plot[0]:
            #self.rssi_plot[1].plot_point(packet)
    
    def mainloop(self):
        self.root.mainloop()
        

    #create main application menu
    def MainMenu(self):

        menubar = Menu(self.root)
        self.root.config(menu=menubar)
                
        filemenu = Menu(menubar)
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="Load map",command=self.Load_Map)
        filemenu.add_command(label="History",command=self.History)
        filemenu.add_separator()
        filemenu.add_command(label="Exit",command=self.Close)


    #create and resize canvas area for maps
    def MainCanvas(self):
        self.trackingarea = Canvas(self.frame, bg="white",width=600,height=400)
        if config.DEFAULT_MAP:
            self.image = Image.open(config.DEFAULT_MAP)
            self.map = ImageTk.PhotoImage(self.image)
            self.trackingarea.config(width=self.image.size[0],height=self.image.size[1])
            self.trackingarea.create_image(0,0, anchor=NW, image = self.map, tag="map")
            self.dimensions = config.DEFAULT_MAP_DIMENSIONS
        self.trackingarea.pack(anchor=NW,fill=BOTH,expand=1)

    def SideFrame(self):
       
        self.sideframe = Frame(self.frame,width=100,height=400)
        self.sideframe.pack(side=RIGHT,expand=1,fill=BOTH)
        Label(self.sideframe, text="track").grid(row=0,column=0)
        Label(self.sideframe, text="BD_ADDR").grid(row=0,column=1)
        Label(self.sideframe, text="#_RCVR").grid(row=0,column=2)
        Label(self.sideframe, text="color").grid(row=0,column=3)

    def add_device(self,device_mac):
                    
        def mk_button_handler(button,color):
            def handle():
                result=tkColorChooser.askcolor()
                color[:] = list(result[1])
                button.config(bg=result[1])
            return handle

        row = len(self.device_list)+1
   
        checkbox_state = IntVar()
        checkbox_state.set(1)
        checkbox = Checkbutton(self.sideframe,variable=checkbox_state).grid(row=row,column=0)
        L1 = Label(self.sideframe, text=device_mac)
        L1.grid(row=row,column=1)
        L2 = Label(self.sideframe, text="#")
        L2.grid(row=row,column=2)
        color = list('blue')
        colorbutton = Button(self.sideframe,text="color")
        colorbutton.config(command=mk_button_handler(colorbutton,color), bg="blue")
        colorbutton.grid(row=row,column=3)

        self.device_list[device_mac] = (checkbox_state,color,(checkbox,L1,L2,colorbutton))




    #handle application closing
    def Close(self):
        if tkMessageBox.askokcancel("Quit","Do you really wish to quit?"):
            self.root.destroy()
    
    def History(self):
        length =  tkSimpleDialog.askinteger("Tracking History","Please input the history length",parent=self.root,minvalue=0,initialvalue=5)
        self.Hlength = length

    #handle opening the map
    def Load_Map(self):
        img_name = tkFileDialog.askopenfilename()
        if img_name == "":
            return
        self.image = Image.open(img_name)
        self.map = ImageTk.PhotoImage(self.image)
        optwindow = MapOptions(self.root, self.map_loaded)

    def map_loaded(self, map_dialog):
        
        if not map_dialog.val:
            return

        name = (map_dialog.e1.get())
        width = float(map_dialog.e2.get())
        height = float(map_dialog.e3.get())
        self.dimensions = (name,width,height)
        
        self.trackingarea.config(width=self.image.size[0],height=self.image.size[1])
        self.trackingarea.delete("map")
        self.trackingarea.create_image(0,0, anchor=NW, image = self.map, tag="map")
        self.trackingarea.pack(fill=BOTH, expand=1)
        
        
    def add_packet(self, packet):
        if not self.trackingarea.find_withtag("map"):
            return
        self.trackingarea.delete("loc")
        widthadj = self.image.size[0]/self.dimensions[1]
        heightadj = self.image.size[1]/self.dimensions[2]

        tracking_state, color, gui_element = self.device_list[packet.device_mac]
        if tracking_state.get() == 1:
            x, y = packet.position
            xloc, yloc = (x*widthadj, y*heightadj)
            c = ''.join(color)
            tag = str(packet.timestamp[0])
            self.trackingarea.create_rectangle(xloc-3, yloc-3, xloc+3, yloc+3, \
                                                   fill=c, tags=(tag))
        self.trackingarea.pack()

    def remove_packet(self, packet):
        tag = str(packet.timestamp[0])
        self.trackingarea.delete(tag)
        self.trackingarea.pack()
        
        
        
        
#file options dialog to define map dimensions
class MapOptions(tkSimpleDialog.Dialog):

    def __init__(self, parent, callback):
        self.callback = callback
        tkSimpleDialog.Dialog.__init__(self, parent)
    
    def body(self,master):
        Label(master, text="Name:").grid(row=0)
        Label(master, text="Width:").grid(row=1)
        Label(master, text="Height:").grid(row=2)
        
        self.e1 = Entry(master)
        self.e2 = Entry(master)
        self.e3 = Entry(master)
        
        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        
        return self.e1
    
    def validate(self):
        self.val = True
        return 1

    def apply(self):
        self.callback(self)
        
        

if __name__ == '__main__':
    s = scan_server.TrackingPipeline()
    a = App()
    s.scan_server.add_new_device_callback(lambda dev: a.evt_queue.put(dev))
    s.add_new_position_callback(lambda packet: a.evt_queue.put(packet))

    #m = Mysql_logger.MysqlLogger()
    #s.add_new_position_callback(lambda packet: m.log(packet))

    try:
        a.mainloop()
    except KeyboardInterrupt:
        pass

    #m.stop()
