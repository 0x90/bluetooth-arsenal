import sys
import errno
import select as native_select
import functools
import threading
import gevent
from gevent.select import select
# this is hack because the above does not work
from gevent import monkey
monkey.patch_select()

from PyBT.gap import GAP
from PyBT.stack import BTEvent


def needs_connection(func):
    @functools.wraps(func)
    def inner(self, *args):
        if not self.connected:
            raise ConnectionError("This command requires a connection")
        return func(self, *args)
    return inner


class ConnectionError(Exception):
    pass


class SocketHandler(object):
    def __init__(self, conn):
        self.conn = conn

    def dump_gap(self, data):
        if len(data) > 0:
            try:
                gap = GAP()
                gap.decode(data)
                print "GAP: %s" % gap
            except Exception as e:
                print e
                pass

    # Make this look a bit like a thread.
    def run(self):
        # FIXME(richo) Mutex around shared mutable state
        seen = self.conn.seen
        while True:
            try:
                select([self.conn.central.stack], [], [])
            except native_select.error as ex:
                if ex[0] == errno.EINTR:
                    continue
                raise

            event = self.conn.central.stack.handle_data()
            if event.type == BTEvent.SCAN_DATA:
                addr, type, data = event.data
                print ("Saw %s (%s)" %
                       (addr, "public" if type == 0 else "random"))
                if addr in seen:
                    if len(data) > len(seen[addr][1]):
                        seen[addr] = (type, data)
                        self.dump_gap(data)
                else:
                    seen[addr] = (type, data)
                    self.dump_gap(data)

            elif event.type == BTEvent.CONNECTED:
                # FIXME(richo) Mutex
                self.conn.connected = True
                print "Connected!"
                if len(self.conn.onconnect) > 0:
                    print "Running onconnect comands"
                    while self.conn.onconnect():
                        cmd = self.conn.onconnect(0)
                        cmd()
            elif event.type == BTEvent.DISCONNECTED:
                self.conn.connected = False
                print "Disconnected"

            elif event.type == BTEvent.ATT_DATA:
                pkt = event.data
                # ack handle value notification
                if pkt.opcode == 0x1d:
                    self.central.stack.raw_att("\x1e")
                print event
            elif event.type != BTEvent.NONE:
                print event


class Connection(object):
    def __init__(self, central):
        self.connected = False
        self.central = central
        self.seen = {}
        self.onconnect = []

    def start(self):
        self._dispatchSocketHandler()

    def _dispatchSocketHandler(self):
        handler = SocketHandler(self)
        gevent.spawn(handler.run)

    # Public command functions

    def scan(self, arg):
        if arg == 'on':
            self.central.stack.scan()
        else:
            self.central.stack.scan_stop()

    def connect(self, addr, kind=None):
        if kind is None:
            # We may have inferred it's kind from seeing it advertising
            kind = self.seen.get(addr, (None,))[0]

        if kind is None:
            print "Error: please give address type"
        else:
            print "Connecting.."
            self.central.stack.connect(addr, kind)

    def quit(self):
        # FIXME(richo) Actually do some cleanup, try to put the hci device back
        # together
        sys.exit(0)

    @needs_connection
    def write_req(self, handle, value):
        self.central.att.write_req(handle=handle, value=value)

    @needs_connection
    def write_cmd(self, handle, value):
        self.central.att.write_cmd(handle=handle, value=value)

    @needs_connection
    def read(self, handle):
        self.central.att.read(handle)

    def set_interval(self, int_min, int_max):
        self.central.stack.interval_min = int_min
        self.central.stack.interval_max = int_max

    def on_connect(self, thunk):
        self.onconnect.append(thunk)

    def raw(self, cmd):
        self.central.stack.raw_att(cmd)
