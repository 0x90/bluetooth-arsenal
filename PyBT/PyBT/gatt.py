from struct import pack, unpack
from binascii import hexlify

GATT_PERMIT_READ = 0x01
GATT_PERMIT_WRITE = 0x02
GATT_PERMIT_AUTH_READ = 0x04
GATT_PERMIT_AUTH_WRITE = 0x08

GATT_PROP_BCAST         = 0x01
GATT_PROP_READ          = 0x02
GATT_PROP_WRITE_NO_RSP  = 0x04
GATT_PROP_WRITE         = 0x08
GATT_PROP_NOTIFY        = 0x10
GATT_PROP_INDICATE      = 0x20

class GATT_Server:
    attributes = []
    mtu = 23

    def __init__(self, db):
        self.db = db

    def set_mtu(self, mtu):
        self.mtu = mtu

    def read(self, handle):
        value = self.db.read(handle)
        if value is None:
            return (False, 0x0a)
        return (True, value[:self.mtu])

    def read_by_type(self, start, end, uuid):
        resp = self.db.read_by_type(start, end, uuid)
        if len(resp) == 0:
            return (False, 0x0a)

        value_len = None
        total_len = 2
        response_body = []
        for r in resp:
            (handle, value) = r
            if value_len is not None and len(value) != value_len:
                break
            # TODO handle MTU larger than 256+4 (length is a single byte)
            value_len = min(len(value), self.mtu-4) # 4 = 2 + an extra 2 for the handle
            response_body.append(pack('<h', handle))
            response_body.append(value[:value_len])
            total_len += value_len+2
            if total_len >= self.mtu:
                break
        return (True, ''.join((chr(value_len+2), ''.join(response_body))))

    def find_information(self, start, end):
        resp = self.db.find_information(start, end)
        if len(resp) == 0:
            return (False, 0x0a)

        response_body = []
        uuid_type = None
        total_len = 2

        for r in resp:
            (handle, uuid) = r

            if uuid_type is None:
                uuid_type = uuid.type
                # hack: we know that uuid_type is the value the spec expects
                response_body.append(chr(uuid_type))
            if uuid.type != uuid_type:
                break

            if total_len + 2 + len(uuid.packed) > self.mtu:
                break

            response_body.append(pack('<h', handle))
            response_body.append(uuid.packed)
            total_len += 2 + len(uuid.packed)

        return (True, ''.join(response_body))

    def find_by_type_value(self, start, end, uuid, value):
        resp = self.db.find_by_type_value(start, end, uuid, value)
        if len(resp) == 0:
            return (False, 0x0a)

        response_body = []
        total_len = 1

        for r in resp:
            (handle, end) = r
            if total_len + 4 > self.mtu:
                break
            response_body.append(pack('<h', handle))
            response_body.append(pack('<h', end))
            total_len += 4
        return (True, ''.join(response_body))

    def read_by_group_type(self, start, end, uuid):
        resp = self.db.read_by_group_type(start, end, uuid)
        if len(resp) == 0:
            return (False, 0x0a)

        response_body = []
        total_len = 0
        value_len = None
        for r in resp:
            (start, end, value) = r

            if value_len is None:
                value_len = min(4 + len(value), self.mtu - 2)
                response_body.append(chr(value_len))
            this_len = min(4 + len(value), self.mtu - 2)
            if this_len != value_len or total_len + value_len > self.mtu:
                break

            response_body.append(pack('<h', start))
            response_body.append(pack('<h', end))
            response_body.append(value[:value_len-4])
            total_len += value_len

        return (True, ''.join(response_body))

class UUID:
    TYPE_16   = 1
    TYPE_128  = 2

    uuid = None
    packed = None
    type = None

    def __init__(self, uuid):
        if isinstance(uuid, UUID):
            self.uuid = uuid.uuid
            self.packed = uuid.packed
            self.type = uuid.type

        # integer
        elif isinstance(uuid, int):
            # TODO 128 bit
            if uuid >= 0 and uuid <= 65536:
                self.uuid = '%04X' % uuid
                self.packed = pack('<h', uuid)
                self.type = UUID.TYPE_16

        elif len(uuid) == 4:
            self.uuid = uuid
            self.packed = uuid.decode("hex")[::-1]
            self.type = UUID.TYPE_16
        elif len(uuid) == 36:
            temp = uuid.translate(None, '-')
            if len(temp) == 32:
                self.uuid = uuid
                self.packed = temp.decode("hex")[::-1]
                self.type = UUID.TYPE_128

        # binary
        elif len(uuid) == 2:
            self.uuid = '%04X' % unpack('<h', uuid)[0]
            self.packed = uuid
            self.type = UUID.TYPE_16
        elif len(uuid) == 16:
            r = uuid[::-1]
            self.uuid = '-'.join(map(lambda x: hexlify(x), (r[0:4], r[4:6], r[6:8], r[8:10], r[10:])))
            self.packed = uuid
            self.type = UUID.TYPE_128

        if self.uuid is None:
            raise Exception("Invalid UUID")

    def __eq__(self, other):
        # TODO expand 16 bit UUIDs
        return self.packed == other.packed

    def __repr__(self):
        return self.uuid

class GATT_Attribute:
    uuid = None
    permissions = None
    handle = None
    value = None

    def __init__(self, uuid, permissions, value):
        self.uuid = uuid
        self.permissions = permissions
        self.value = value

    def __repr__(self):
        return "%s: '%s'" % (self.uuid, ' '.join(x.encode('hex') for x in self.value))

class Attribute_DB:
    attributes = []

    def primary(self, uuid_str):
        uuid = UUID(uuid_str)
        attr = GATT_Attribute(UUID("2800"), GATT_PERMIT_READ, uuid.packed)
        self.attributes.append(attr)

    def characteristic(self, uuid_str, properties):
        uuid = UUID(uuid_str)
        attr = GATT_Attribute(UUID("2803"), GATT_PERMIT_READ, ''.join((chr(properties), '\x00\x00', uuid.packed)))
        self.attributes.append(attr)

    def client_characteristic_configuration(self):
        attr = GATT_Attribute(UUID("2902"), GATT_PERMIT_READ | GATT_PERMIT_WRITE, '\x00\x00')
        self.attributes.append(attr)

    def attribute(self, uuid_str, permissions, value):
        uuid = UUID(uuid_str)
        attr = GATT_Attribute(uuid, permissions, value)
        self.attributes.append(attr)

    # update handle in characteristic attributes
    def refresh_handles(self):
        chr_uuid = UUID("2803")
        for i in range(0, len(self.attributes)):
            attr = self.attributes[i]
            if attr.uuid == chr_uuid:
                attr.value = attr.value[0] + pack('<h', i+2) + attr.value[3:]

    def __repr__(self):
        a = []
        for i in range(0, len(self.attributes)):
            a.append('%x - %s' % (i+1, self.attributes[i]))
        return '\n'.join(a)


    def read(self, handle):
        attr = None
        try:
            attr = self.attributes[handle-1]
            return attr.value
        except:
            pass
        return None

    def read_by_type(self, start, end, uuid_str):
        resp = []
        uuid = UUID(uuid_str)
        try:
            for i in range(start, end+1):
                attr = self.attributes[i-1]
                if attr.uuid == uuid:
                    resp.append((i, attr.value))
        except:
            pass

        return resp

    def find_information(self, start, end):
        resp = []
        # TODO check that start < end?
        try:
            for i in range(start, end+1):
                attr = self.attributes[i-1]
                resp.append((i, attr.uuid))
        except:
            pass
        return resp

    def find_by_type_value(self, start, end, uuid_str, value):
        resp = []
        uuid = UUID(uuid_str)
        try:
            for i in range(start, end+1):
                attr = self.attributes[i-1]
                if attr.uuid == uuid and attr.value == value:
                    max_handle = i
                    try:
                        for j in range(i+1, end+1):
                            if self.attributes[j-1].uuid == uuid:
                                break
                            max_handle = j
                    except:
                        pass
                    resp.append((i, max_handle))
        except:
            pass
        return resp

    def read_by_group_type(self, start, end, uuid_str):
        resp = []
        uuid = UUID(uuid_str)
        try:
            for i in range(start, end+1):
                attr = self.attributes[i-1]
                if attr.uuid == uuid:
                    max_handle = i
                    try:
                        for j in range(i+1, end+1):
                            if self.attributes[j-1].uuid == uuid:
                                break
                            max_handle = j
                    except:
                        pass
                    resp.append((i, max_handle, attr.value))
        except:
            pass
        return resp
