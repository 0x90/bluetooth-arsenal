from struct import unpack
from binascii import hexlify

def decode_flags(flags):
    if len(flags) != 1:
        raise Exception("Flags must be 1 byte")

    bitfield = (
        'LE Limited Discoverable Mode',
        'LE General Discoverable Mode',
        'BR/EDR Not Supported',
        'Simultaneous LE and BR/EDR (Controller)',
        'Simultaneous LE and BR/EDR (Host)',
        'Reserved', 'Reserved', 'Reserved', # silly hack
    )

    res = []
    flags = ord(flags)
    for i in range(0, len(bitfield)):
        value = bitfield[i]
        if flags & 1 << i:
            res.append(value)
    return res

def decode_uuid16(uuids):
    if len(uuids) % 2 != 0:
        raise Exception("List of 16-bit UUIDs must be a multiple of 2 bytes")
    res = []
    for i in range(0, len(uuids), 2):
        res.append('%04x' % unpack('<H', uuids[i:i+2]))
    return res

def decode_uuid128(uuids):
    if len(uuids) % 16 != 0:
        raise Exception("List of 128-bit UUIDsmust be a multiple of 16 bytes")
    res = []
    for i in range(0, len(uuids), 16):
        r = uuids[i:i+16][::-1]
        res.append('-'.join(map(lambda x: hexlify(x), (r[0:4], r[4:6], r[6:8], r[8:10], r[10:]))))
    return res

def decode_tx_power_level(power):
    if len(power) != 1:
        raise Exception("Power level must be 1 byte")
    return '%d dBm' % unpack('b', power)

def decode_slave_connection_interval_range(range):
    if len(range) != 4:
        raise Exception("Range must be 4 bytes")
    return map(lambda x: '%g ms' % (unpack('<H', x)[0] * 1.25, ), (range[0:2], range[2:]))

def decode_service_data(data):
    if len(data) < 2:
        raise Exception("Service data must be at least 2 bytes")

    uuid, data = (data[0:2], data[2:])
    uuid = '%04x' % unpack('<H', uuid)
    return (uuid, data)

manufacturers = {
    '004c': 'Apple, Inc.'
}

def decode_manufacturer_specific_data(data):
    if len(data) < 2:
        raise Exception("Manufacturer specific data must be at least two bytes")

    mfgr, data = (data[0:2], data[2:])
    mfgr = '%04x' % unpack('<H', mfgr)

    mname = manufacturers.get(mfgr)
    if mname is not None:
        mfgr = '%s (%s)' % (mfgr, mname)

    return (mfgr, data)


class GAP:
    fields = []
    types = {
        0x01: 'Flags',
        0x02: 'Incomplete List of 16-bit Service Class UUIDs',
        0x03: 'Complete List of 16-bit Service Class UUIDs',
        0x04: 'Incomplete List of 32-bit Service Class UUIDs',
        0x05: 'Complete List of 32-bit Service Class UUIDs',
        0x06: 'Incomplete List of 128-bit Service Class UUIDs',
        0x07: 'Complete List of 128-bit Service Class UUIDs',
        0x08: 'Shortened Local Name',
        0x09: 'Complete Local Name',
        0x0A: 'Tx Power Level',
        0x0D: 'Class of Device',
        0x0E: 'Simple Pairing Hash C',
        0x0F: 'Simple Pairing Randomizer',
        0x10: 'Security Manager TK Value',
        0x11: 'Security Manager Out of Band Flags',
        0x12: 'Slave Connection Interval Range',
        0x14: 'List of 16-bit Service Solicitation UUIDs',
        0x1F: 'List of 32-bit Service Solicitation UUIDs',
        0x15: 'List of 128-bit Service Solicitation UUIDs',
        0x16: 'Service Data',
        0x20: 'Service Data - 32-bit UUID',
        0x21: 'Service Data - 128-bit UUID',
        0x17: 'Public Target Address',
        0x18: 'Random Target Address',
        0x19: 'Appearance',
        0x1A: 'Advertising Interval',
        0x1B: 'LE Bluetooth Device Address',
        0x1C: 'LE Role',
        0x1D: 'Simple Pairing Hash C-256',
        0x1E: 'Simple Pairing Randomizer R-256',
        0x3D: '3D Information Data',
        0xFF: 'Manufacturer Specific Data',
    }

    decoder = {
        0x01: decode_flags,
        0x02: decode_uuid16,
        0x03: decode_uuid16,
        0x06: decode_uuid128,
        0x07: decode_uuid128,
        0x0A: decode_tx_power_level,
        0x12: decode_slave_connection_interval_range,
        0x16: decode_service_data,
        0xFF: decode_manufacturer_specific_data,
    }

    def __init__(self):
        pass

    def decode(self, data):
        self.fields = []
        pos = 0
        while pos < len(data):
            length = ord(data[pos])
            pos += 1
            if pos + length > len(data):
                raise Exception("Data too short (%d < %d)" % (pos + length, len(data)))
            type = ord(data[pos])
            value = data[pos+1:pos+length]
            self.fields.append((type,value))
            pos += length

    def __repr__(self):
        pretty = []
        for type, value in self.fields:
            t = self.types.get(type, '%02X' % type)
            decoder = self.decoder.get(type, lambda x: repr(x))
            pretty.append('%s: %s' % (t, decoder(value)))
        return ', '.join(pretty)

if __name__ == "__main__":
    gap = GAP()
    data = '\x02\x01\x06\x03\x03\xfa\xfe\x13\xff\xf0\x00\x0016\xac\x81\x85\xc5\xf6\xed\x00\x00\x00\x00\x00\x00\x00'
    gap.decode(data)
    print gap
    data = '\x02\x01\x04\x03\x03\x12\x18\x03\x19\xc2\x03\x0a\x09Bad Mouse'
    gap.decode(data)
    print gap

    data = '\x04\x09\x4f\x6e\x65\x02\x0a\xfa'
    gap.decode(data)
    print gap
    data = '\x02\x01\x06\x11\x06\xba\x56\x89\xa6\xfa\xbf\xa2\xbd\x01\x46\x7d\x6e\x75\x45\xab\xad\x05\x16\x0a\x18\x05\x04'
    gap.decode(data)
    print gap

    data = '\x02\x01\x1a\x13\xff\x4c\x00\x0c\x0e\x00\x1a\x05\x5c\x67\xbe\xc9\xca\xc0\x1d\x54\x4a\x9d\x5d'
    gap.decode(data)
    print gap
