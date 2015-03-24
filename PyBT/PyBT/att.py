from scapy.layers.bluetooth import *

class ATT_Protocol:
    stack = None
    gatt_server = None
    require_encryption = False

    def __init__(self, stack, gatt_server=None, require_encryption=False):
        self.stack = stack
        self.gatt_server = gatt_server
        self.require_encryption = require_encryption

        self.encrypted = False

    def send(self, body):
        self.stack.raw_att(ATT_Hdr()/body)

    def register_write_cb(self, cb):
        self.write_cb = cb

    def marshall_request(self, r):
        opcode = r.opcode

        if opcode == 0x02:
            self.gatt_server.set_mtu(r.mtu)
            self.send(ATT_Exchange_MTU_Response(mtu=self.mtu))

        elif opcode == 0x04:
            success, body = self.gatt_server.find_information(r.start, r.end)
            if success:
                p = ATT_Find_Information_Response(body)
            else:
                p = ATT_Error_Response(request=r.start, ecode=body)
            self.send(p)

        elif opcode == 0x06: # find by type value request
            success, body = self.gatt_server.find_by_type_value(r.start, r.end, r.uuid, r.data)
            if success:
                p = ATT_Find_By_Type_Value_Response(body)
            else:
                p = ATT_Error_Response(request=opcode, handle=r.start, ecode=body)
            self.send(p)

        elif opcode == 0x08: # read by type
            if self.require_encryption and not self.encrypted:
                p = ATT_Error_Response(request=opcode, handle=r.start, ecode=0xf)
            else:
                success, body = self.gatt_server.read_by_type(r.start, r.end, r.uuid)
                if success:
                    p = ATT_Read_By_Type_Response(body)
                else:
                    p = ATT_Error_Response(request=opcode, handle=r.start, ecode=body)
            self.send(p)

        elif opcode == 0x0a: # read request
            success, body = self.gatt_server.read(r.gatt_handle)
            if success:
                p = ATT_Read_Response(body)
            else:
                p = ATT_Error_Response(request=opcode, handle=r.gatt_handle, ecode=body)
            self.send(p)

        elif opcode == 0x10: # read by group type
            success, body = self.gatt_server.read_by_group_type(r.start, r.end, r.uuid)
            if success:
                p = ATT_Read_By_Group_Type_Response(body)
            else:
                p = ATT_Error_Response(request=opcode, handle=r.start, ecode=body)
            self.send(p)

        elif opcode == 0x12 or opcode == 0x52: # write request or write command
            gatt_handle = r.gatt_handle
            if opcode == 0x12:
                self.send(ATT_Write_Response())

            # TODO handle callbacks
            if self.write_cb is not None:
                self.write_cb.callback(gatt_handle, r.data)

    def read_by_type(self, start, end, uuid):
        self.send(ATT_Read_By_Type_Request(start=start,end=end,uuid=uuid))

    def read(self, handle):
        self.send(ATT_Read_Request(gatt_handle=handle))

    def write_req(self, handle, value):
        self.send(ATT_Write_Request(gatt_handle=handle, data=value))

    def write_cmd(self, handle, value):
        self.send(ATT_Write_Command(gatt_handle=handle, data=value))
