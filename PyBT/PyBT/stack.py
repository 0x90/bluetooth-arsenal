import os
import sys
from fcntl import ioctl
import logging

import socket as s
from scapy.layers.bluetooth import *
from select import select

log = logging.getLogger("PyBT.stack")

class HCIConfig(object):
    @staticmethod
    def down(iface):
        # 31 => PF_BLUETOOTH
        # 0 => HCI_CHANNEL_USER
        # 0x400448ca => HCIDEVDOWN
        sock = s.socket(31, s.SOCK_RAW, 1)
        ioctl(sock.fileno(), 0x400448ca, iface)
        sock.close()
        return True

    @staticmethod
    def up(iface):
        sock = s.socket(31, s.SOCK_RAW, iface)
        # TODO
        # ioctl(sock.fileno(), HCIDEVUP, 0)
        sock.close()
        return False


class BTStack:
    s = None
    addr = None
    rand_addr = None

    def __init__(self, adapter=0):
        self.interval_min = None
        self.interval_max = None

        self.s = self.get_socket(adapter)

        # set up device
        self.command(HCI_Cmd_Reset())

        # get BD ADDR
        r = self.command(HCI_Cmd_Read_BD_Addr())
        self.addr = str(r[HCI_Cmd_Complete_Read_BD_Addr])[::-1]

        self.command(HCI_Cmd_Set_Event_Filter())
        self.command(HCI_Cmd_Connect_Accept_Timeout())
        self.command(HCI_Cmd_Set_Event_Mask())
        self.command(HCI_Cmd_LE_Host_Supported())

        self.command(HCI_Cmd_LE_Read_Buffer_Size())

    def get_socket(self, adapter):
        try:
            return BluetoothUserSocket(adapter)
        except BluetoothSocketError as e:

            sys.stderr.write("[!] Creating socket failed: %s\n" % (repr(e)))
            if os.getuid() > 0:
                sys.stderr.write("[!] Are you definitely root? detected uid: %d\n" % (os.getuid()))
            else:
                sys.stderr.write("[+] have root, attempting to take iface down\n")
                HCIConfig.down(adapter)
                try:
                    return BluetoothUserSocket(adapter)
                except BluetoothSocketError:
                    sys.stderr.write("[!] Giving up.\n")
        sys.exit(1)

    # hack to make this select-able
    def fileno(self):
        return self.s.ins.fileno()

    def set_random_address(self, random):
        self.rand_addr = random
        self.command(HCI_Cmd_LE_Set_Random_Address(address=random))

    def set_advertising_data(self, data):
        self.command(HCI_Cmd_LE_Set_Advertising_Data(data=data))

    def set_advertising_params(self, adv_type, channel_map=0, interval_min=0, interval_max=0, daddr='00:00:00:00:00:00', datype=0):
        oatype= 1 if self.rand_addr is not None else 0
        command = HCI_Cmd_LE_Set_Advertising_Parameters(adv_type=adv_type, channel_map=channel_map, interval_min=interval_min, interval_max=interval_max, daddr=daddr, datype=datype, oatype=oatype)
        self.command(command)

    def set_advertising_enable(self, enable):
        self.command(HCI_Cmd_LE_Set_Advertise_Enable(enable=enable))

    def send_ltk_reply(self, ltk, handle):
        self.command(HCI_Cmd_LE_Long_Term_Key_Request_Reply(handle=handle, ltk=ltk))

    def send_ltk_nak(self, handle):
        self.command(HCI_Cmd_LE_Long_Term_Key_Request_Negative_Reply(handle=handle))

    def handle_data(self):
        p = self.s.recv()

        if p.type == 0x2: # ACL Data (GATT)
            try:
                # data = str(p[ATT_Hdr])
                return BTEvent(BTEvent.ATT_DATA, p[ATT_Hdr])
            except:
                log.warn("unknown ACL data")
                pass
        elif p.type == 0x4: # HCI Event
            if p.code == 0x3e:
                if p.event == 1:
                    # grorious scapy hack
                    meta = str(p[HCI_LE_Meta_Connection_Complete])[5:11]
                    return BTEvent(BTEvent.CONNECTED, (p.status, meta[::-1], p.patype))
                if p.event == 2:
                    return BTEvent(BTEvent.SCAN_DATA, (p.addr, p.atype, p.data))
            elif p.code == 0x5:
                return BTEvent(BTEvent.DISCONNECTED)
        else:
            log.warn("Don't know how to handle %s" % p)
        return BTEvent(BTEvent.NONE)

    def scan(self):
        # start scanning
        self.command(HCI_Cmd_LE_Set_Scan_Parameters())
        self.command(HCI_Cmd_LE_Set_Scan_Enable())

    def scan_stop(self):
        self.command(HCI_Cmd_LE_Set_Scan_Enable(enable=0))

    def connect(self, addr, type):
        if self.interval_min is not None and self.interval_max is not None:
            self.s.send(HCI_Hdr()/HCI_Command_Hdr()/HCI_Cmd_LE_Create_Connection(paddr=addr,patype=type, \
                        min_interval=self.interval_min, max_interval=self.interval_max))
        else:
            self.s.send(HCI_Hdr()/HCI_Command_Hdr()/HCI_Cmd_LE_Create_Connection(paddr=addr,patype=type))
        # can't use send_command() on this guy because we get a command status (0x0e) and not
        # command complete (0x0f)
        while True:
            p = self.s.recv()
            if p.code == 0x0f:
                if p.status == 0:
                    break
                else:
                    raise Exception("Problem establishing connection")

    def connect_sync(self, addr, type):
        self.connect(addr, type)
        while True:
            p = self.s.recv()
            if p.code == 0x3e and p.event == 0x01:
                if p.status == 0:
                    break
                else:
                    raise Exception("Problem establishing connection")

    def command(self, cmd):
        return self.s.send_command(HCI_Hdr()/HCI_Command_Hdr()/cmd)

    def raw_att(self, data):
        self.s.send(HCI_Hdr()/HCI_ACL_Hdr(handle=64)/L2CAP_Hdr(cid=4)/data)

    # maybe we want an optional CID parameter
    def raw_l2cap(self, data):
        self.s.send(HCI_Hdr()/HCI_ACL_Hdr(handle=64)/L2CAP_Hdr()/data)

class BTEvent:
    NONE = 0
    SCAN_DATA = 1
    CONNECTED = 2
    DISCONNECTED = 3
    ATT_DATA = 4

    # there has to be a better way..
    _type_string = {
        NONE: "NONE",
        SCAN_DATA: "SCAN_DATA",
        CONNECTED: "CONNECTED",
        DISCONNECTED: "DISCONNECTED",
        ATT_DATA: "ATT_DATA",
    }

    data = None
    type = None

    def __init__(self, type, data=None):
        self.type = type
        self.data = data

    def __repr__(self):
        return "BTEvent(%s, %s)" % (self._type_string[self.type], repr(self.data))
