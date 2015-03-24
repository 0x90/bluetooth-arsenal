#!/usr/bin/env python2.7
from tracking_method import TrackingMethod, RandomDataTracker, NLMaPTracker
from data_generator import CircleDataGenerator, LinearInterpolator
import config, data_packet, data_generator
import socket, struct, threading, Queue, multiprocessing, time

PORT = 2410
MSG_MAX_LEN = 128

class ScanListener(threading.Thread):
    """Deocde receiver packet data, asynchronously.
        Provides callbacks on receipt of packets.
    """
    
    def __init__(self, addr='0.0.0.0', port=PORT, open=True):
        threading.Thread.__init__(self)
        self.daemon = True
        
        self.addr = addr
        self.port = port
        
        self.callbacks = []
        if open:
            self.open()
        
    def open(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.addr, self.port))
        
    def add_callback(self, callback):
        self.callbacks.append(callback)

    def decode_packet(self, data):
        try:
            #print 'Packet (len %s): %s' % (len(data), [ord(x) for x in data])
            fields = struct.unpack('!LLBBBBBBBBBBBBb', data)
            tstamp_sec, tstamp_usec = fields[0:2]
            receiver_mac = ':'.join([hex(f)[2:].zfill(2) for f in fields[2:8]])
            device_mac = ':'.join([hex(f)[2:].zfill(2) for f in fields[13:7:-1]])  # Yes, the bluetooth address comes over backwards
            rssi = fields[14]
            p = data_packet.DataPacket((tstamp_sec, tstamp_usec), receiver_mac, device_mac, rssi)
            print p
            return p
        except Exception, e:
            print 'Malformed packet (%s); dropped' % str(e)

    def run(self):    
        while True:
            data, addr = self.sock.recvfrom(MSG_MAX_LEN)
            info = self.decode_packet(data)
            for c in self.callbacks:
                c(info)

class FakeListener(ScanListener):
    """Return fake data, for the lulz."""

    def __init__(self):
        ScanListener.__init__(self, open=False)
        self.data_sources = data_generator.DATA_GENERATORS
    
    def run(self):
        while True:
            time.sleep(1.0/config.DATA_FREQ)
            data = reduce(lambda x, y: x+y, [source.get_data() for source in self.data_sources])
            for packet in data:
                for c in self.callbacks:
                    c(packet)


class ScanServer(object):
    """Process decoded packet data to provide higher-level tracking status.
    
        self.data is a dictionary mapping device macs to receiver dictionaries,
        each of which mapps receiver macs to a stack of the most recent contacts
        between the given device / receiver pair.
    
    """
    
    def __init__(self, *args, **kwargs):
        if "fakeit" in kwargs and kwargs["fakeit"]:
            self.listener = FakeListener()
        else:
            del kwargs['fakeit']
            self.listener = ScanListener(*args, **kwargs)
        
        self.listener.add_callback(self.process_packet)
        
        self.devices = []
        self.receivers = []
        self.data = dict()
        
        self.new_device_callbacks = []
        self.new_data_callbacks = []
        
        self.listener.start()
        
    def add_new_device_callback(self, callback):
        self.new_device_callbacks.append(callback)
    
    def add_new_data_callback(self, callback):
        self.new_data_callbacks.append(callback)
    
    def process_packet(self, packet):

        if not packet.device_mac in self.data:
            self.data[packet.device_mac] = {packet.receiver_mac : [packet.rssi]}
            self.devices.append(packet.device_mac)
            
            map(lambda c: c(packet.device_mac), self.new_device_callbacks)
            
        else:
            if not packet.receiver_mac in self.data[packet.device_mac]:
                self.data[packet.device_mac][packet.receiver_mac] = [packet.rssi]
                if not packet.receiver_mac in self.receivers:
                    self.receivers.append(packet.receiver_mac)
            else:
                self.data[packet.device_mac][packet.receiver_mac].append(packet.rssi)
        
        map(lambda c: c(packet), self.new_data_callbacks)
        
                    
class TrackingThread(multiprocessing.Process):
    """Multiprocessing wrapper around TrackingMethod."""
    
    def __init__(self, method):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        
        self.method = method
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
    
    def handle_new_data(self, data):
        self.in_queue.put(data)
    
    def get_new_packet(self, timeout):
        try:
            return self.out_queue.get(True, timeout)
        except:
            return None
    
    def run(self):
        while True:
            packet = self.in_queue.get()
            packet.position = self.method.get_position(packet)
            self.out_queue.put(packet)

class TrackingPipeline(object):
    """Manage a tracking pipline, handling incoming data to produce 
        a stream of position updates. Callbacks will be invoked as
        c(device, new_pos)
    """
    
    def __init__(self, fakeit=True):
        self.scan_server = ScanServer(fakeit=fakeit)
        self.tracking_threads = dict()
        self.new_position_callbacks = []
        
        self.shouldExit = False
        
        self.scan_server.add_new_device_callback(self.handle_new_device)
        self.scan_server.add_new_data_callback(self.handle_new_data)
        
        self.merge_thread = threading.Thread(target=self.merge_queues)
        self.merge_thread.daemon = True
        self.merge_thread.start()
    
    def add_new_position_callback(self, callback):
        self.new_position_callbacks.append(callback)
        
    def get_tracking_method(self):
        return NLMaPTracker
    
    def handle_new_device(self, device_mac):
        method_cls = self.get_tracking_method()
        method = method_cls(device_mac)
        self.tracking_threads[device_mac] = TrackingThread(method)
        self.tracking_threads[device_mac].start()
    
    def handle_new_data(self, packet):
        if not self.tracking_threads[packet.device_mac].is_alive():
            if self.shouldExit:
                return
            print 'Reviving dead tracking thread'
            self.handle_new_device(packet.device_mac)
        self.tracking_threads[packet.device_mac].handle_new_data(packet)
    
    def merge_queues(self):
        while True:
            for device, tracker in self.tracking_threads.items():
                packet = tracker.get_new_packet(0.1)
                if packet and packet.position:
                    map(lambda c: c(packet), self.new_position_callbacks)
    
    def shutdown(self):
        self.shouldExit = True
        for thread in self.tracking_threads.values():
            thread.terminate()
    
    
        
