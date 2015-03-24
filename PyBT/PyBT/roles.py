import logging

from stack import BTStack
from att import ATT_Protocol
from gatt import GATT_Server
from sm import SM, SM_Protocol

from select import select

log = logging.getLogger('PyBT.roles')

class LE_Central:
    def __init__(self, adapter=0):
        self.stack = BTStack(adapter=adapter)
        self.att = ATT_Protocol(self.stack)

class LE_Peripheral:
    def __init__(self, db, adapter=0, encryption=False, random=None):
        self.stack = BTStack(adapter=adapter)
        self.att = ATT_Protocol(self.stack, GATT_Server(db), encryption)
        self.sm = SM()
        self.smp = SM_Protocol(self.stack, self.sm)

        if random is not None:
            self.stack.set_random_address(random)

            self.sm.ra = ''.join(map(lambda x: chr(int(x, 16)), random.split(':')))
            self.sm.ra_type = 1
        else:
            self.sm.ra = self.stack.addr
            self.sm.ra_type = 0

    def run(self):
        while True:
            # select here to play nice with gevent
            r, _, _ = select([self.stack], [], [])
            if len(r) == 0:
                continue

            p = self.stack.s.recv()
            if p.type == 2: # ACL data
                if p.cid == 4: # GATT
                    self.att.marshall_request(p)

                elif p.cid == 6: # SM
                    self.smp.marshall_command(p)

            # LE meta event
            elif p.code == 0x3e:
                # LTK request
                if p.event == 5:
                    handle = p.handle
                    if self.sm.ltk is None:
                        log.info("Sending LTK Negative reply")
                        self.stack.send_ltk_nak(handle)
                    else:
                        log.info("Sending LTK")
                        self.stack.send_ltk_reply(self.sm.ltk[::-1], handle)

            # encryption change, send LTK and EDIV
            elif p.code == 8:
                # TODO check that we actually are changing to encrypted
                self.att.encrypted = True
