import os
import sys
import code
import argparse
from threading import Thread
import gevent
from binascii import unhexlify
from PyBT.roles import LE_Central
from PyBT.gatt_core import Connection, ConnectionError

def debug(msg):
    if os.getenv("DEBUG"):
        sys.stdout.write(msg)
        sys.stdout.write("\n")


def _argparser():
    parser = argparse.ArgumentParser(description='Gatt Client')
    parser.add_argument('-i', '--interface', dest='interface', action='store',
                        type=int, help='Interface to use', default=0)
    return parser


class InvalidCommand(Exception):
    pass

class UnknownCommand(Exception):
    pass

class CommandModule(object):
    """Dumb container for commands"""
    @staticmethod
    def scan(*args):
        if len(args) == 0 or args[0] == 'on':
            arg = 'on'
        elif args[0] == 'off':
            arg = 'off'
        else:
            raise InvalidCommand("scan [on|off]")
        return ('scan', arg)

    @staticmethod
    def connect(*args):
        def fail():
            raise InvalidCommand("connect <address> [public|random]")

        arg = None
        if len(args) == 1:
            pass
        elif len(args) == 2:
            if args[1] in ('public', 'random'):
                arg = args[1]
            else:
                fail()
        else:
            fail()
        return ('connect', args[0], arg)

    @staticmethod
    def quit(*args):
        return ('quit', )

    @staticmethod
    def write_req(*args):
        if len(args) != 2:
            raise InvalidCommand("write-req <handle> <value>")
        try:
            handle = int(args[0], base=16)
            value = unhexlify(args[1])
        except:
            raise InvalidCommand("Format error, handle is a hex int and value is a bunch of hex bytes")
        return ('write-req', handle, value)

    @staticmethod
    def write_cmd(*args):
        if len(args) != 2:
            raise InvalidCommand("write-cmd <handle> <value>")
        try:
            handle = int(args[0], base=16)
            value = unhexlify(args[1])
        except:
            raise InvalidCommand("Format error, handle is a hex int and value is a bunch of hex bytes")
        return ('write-cmd', handle, value)

    @staticmethod
    def read(*args):
        if len(args) != 1:
            raise InvalidCommand("read <handle>")
        try:
            handle = int(args[0], base=16)
        except:
            raise InvalidCommand("Format error, handle is a hex int")
        return ('read', handle)

    @staticmethod
    def interval(*args):
        if len(args) != 2:
            raise InvalidCommand("interval <min> <max>")
        try:
            min = int(args[0])
            max = int(args[1])
        except:
            raise InvalidCommand("Format error, min and max must be integers")
        return ('interval', min, max)

    @staticmethod
    def raw(*args):
        if len(args) != 1:
            print "Error: raw [data]"
            return None
        try:
            data = unhexlify(args[0])
        except:
            print "Format error, data is a bunch of hex bytes"
            return None
        return ('raw', data)

COMMANDS = {
    'scan': CommandModule.scan,
    'connect': CommandModule.connect,
    'quit': CommandModule.quit,
    'write-req': CommandModule.write_req,
    'write-cmd': CommandModule.write_cmd,
    'read': CommandModule.read,
    'interval': CommandModule.interval,
}


def parse_command(f):
    if len(f) == 0:
        return None
    cmd_name = f[0]
    try:
        cmd = COMMANDS[cmd_name](*f[1:])
        return cmd
    except IndexError:
        pass  # Ignore people mushing return
    except KeyError as e:
        print "Error: Unknown command '%s'" % e.args[0]
        raise UnknownCommand("unknown: %s" % e.args[0])
    except InvalidCommand as e:
        print(repr(e))  # TODO Deal more gracefully


def socket_handler(central):
    global seen, state, onconnect

    # handle events


def runsource_with_connection(connection):
    # orig_runsource = code.InteractiveConsole.runsource

    def runsource(self, source, filename='<input>',
                  symbol='single', encode=True):
        # Try parsing it as a gatt client thing, then fall back to python
        debug("[-] %s" % repr(source.split()))
        oncommand_hack = False
        try:
            parts = source.split()
            if len(parts) == 0:
                return
            if parts[0] == 'oncommand':
                oncommand_hack = True
                parts.pop(0)
            # FIXME(richo) Find out what version gives short syntax
            args = parse_command(parts)
            cmd = args[0].replace('-', '_')
            args = args[1:]
        except UnknownCommand:
            # XXX uncomment me to make this into a python repl
            # return orig_runsource(self, source)
            return None

        if cmd is not None:
            debug("[-] %s(%s)" % (repr(cmd), repr(args)))
            # FIXME(richo) Deal gracefully with the AttributeError
            func = getattr(connection, cmd)
            if oncommand_hack:
                self.connection.oncommand(lambda: func(*args))
            else:
                func(*args)
    return runsource


def main():
    parser = _argparser()
    args = parser.parse_args()

    central = LE_Central(adapter=args.interface)

    connection = Connection(central)
    connection.start()

    code.InteractiveConsole.runsource = runsource_with_connection(connection)
    Thread(target=code.interact).start()

    gevent.wait()

if __name__ == '__main__':
    main()
