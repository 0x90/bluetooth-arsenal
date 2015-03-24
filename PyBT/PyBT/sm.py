from Crypto.Cipher import AES
from scapy.layers.bluetooth import *
from scapy.all import hexdump

class SM():
    ia = None
    ia_type = None
    ra = None
    ra_type = None
    tk = None
    prnd = None
    rrnd = None
    pcnf = None
    preq = None
    prsp = None
    ltk = None

    def __init__(self):
        self.tk = '\x00' * 16
        self.rrnd = '\x00' * 16

    # calculates a confirm
    def calc_cfm(self, master=0):
        if master:
            rand = self.prnd
        else:
            rand = self.rrnd

        return ''.join(bt_crypto_c1(self.tk, rand, self.prsp, self.preq, self.ia_type, self.ia, self.ra_type, self.ra))

    def verify_random(self):
        confirm = self.calc_cfm(1)
        if self.pcnf != confirm:
            return False
        self.ltk = bt_crypto_s1(self.tk, self.prnd, self.rrnd)
        return True

    def __repr__(self):
        self._dump('ia')
        self._dump('ra')
        self._dump('prnd')
        self._dump('rrnd')
        self._dump('pcnf')
        self._dump('prsp')
        self._dump('preq')

    def _dump(self, label):
        print "s.%s = '%s'" % (label, ''.join("\\x{:02x}".format(ord(c)) for c in self.__dict__[label]))

def u128_xor(a1, a2):
    return ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(a1, a2))

def bt_crypto_e(key, plaintext):
    aes = AES.new(key)
    return aes.encrypt(plaintext)

def bt_crypto_c1(k, r, pres, preq, iat, ia, rat, ra):
    p1 = ''.join((pres, preq, chr(rat), chr(iat)))
    p2 = ''.join(("\x00\x00\x00\x00", ia, ra))
    res = u128_xor(r, p1)
    res = bt_crypto_e(k, res)
    res = u128_xor(res, p2)
    return bt_crypto_e(k, res)

def bt_crypto_s1(k, r1, r2):
    res = ''.join((r2[8:16], r1[8:16]))
    return bt_crypto_e(k, res)


class SM_Protocol:
    stack = None
    sm = None

    def __init__(self, stack, sm):
        self.stack = stack
        self.sm = sm

    def marshall_command(self, command):
        code = command.sm_command

        # pairing request
        if code == 1:
            # save the pairing request, reversed
            self.sm.preq = str(command[SM_Hdr])[::-1]

            auth = command.authentication
            p = SM_Hdr()/SM_Pairing_Response(authentication=auth, initiator_key_distribution=0, responder_key_distribution=0)

            # save the response, reversed
            self.sm.prsp = str(p[SM_Hdr])[::-1]

            self.stack.raw_l2cap(p)

        # pairing confirm
        elif code == 3:
            # save the confirm
            self.sm.pcnf = str(command[SM_Confirm])[::-1]
            # calculate and send our own confirm
            confirm = self.sm.calc_cfm()
            p = SM_Hdr()/SM_Confirm(confirm=confirm[::-1])
            self.stack.raw_l2cap(p)

        # pairing random
        elif code == 4:
            self.sm.prnd = command.random[::-1]
            res = self.sm.verify_random()
            if not res:
                raise Exception("pairing error")
            # send random
            self.stack.raw_l2cap(SM_Hdr()/SM_Random(random=self.sm.rrnd))
