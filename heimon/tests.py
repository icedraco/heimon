from socket import *

from heimon.states import *


class HeimdallTest(object):
    BUFFER_SIZE = 4096
    IO_TIMEOUT_SECS = 10

    @staticmethod
    def setbuffersize(size):
        HeimdallTest.BUFFER_SIZE = size

    @staticmethod
    def settimeout(timeout):
        HeimdallTest.IO_TIMEOUT_SECS = timeout

    def __init__(self, addr, creds):
        self.__addr = addr
        self.__creds = creds
        self.__socket = socket(AF_INET, SOCK_STREAM)
        self.__state = NullState(self)
        self.__flag_connected = False

        # this is filled over the lifetime of this test
        self.result = {
            'usercount': None,
            'which': {
                'delay': -1
            },
            'is_error': False,
            'error_msg': "(no error)"
        }

    def connect(self):
        self.__socket.settimeout(self.IO_TIMEOUT_SECS)
        self.__socket.connect(self.__addr)
        self.__flag_connected = True
        self.change_state(DragonroarState(self, self.__creds))
        self.__creds = None

    def is_connected(self):
        return self.__flag_connected

    def close(self):
        """Close this connection (without sending `quit first)"""
        if self.__socket:
            self.__socket.close()
            self.__socket = None
            self.__flag_connected = False

        self.change_state(ClosedState(self))

    def process_next(self):
        """Process more data from this test/connection"""
        try:
            buffer = self.recv()
            is_disconnected = buffer == b''

            for line in buffer.split(b'\n'):
                self.__state.process(line)

            if is_disconnected:
                self.handle_disconnected()

        except timeout as e:
            self.__state.idle()


    def send(self, data):
        self.__socket.send(data)

    def recv(self):
        return self.__socket.recv(self.BUFFER_SIZE)

    def shutdown(self):
        """Shut down this test gracefully"""
        self.change_state(ClosingState(self))

    def change_state(self, handler):
        """Change the current state (i.e., handler) to another"""
        if self.__state:
            self.__state.exit()

        self.__state = handler
        self.__state.enter()

    def handle_usercount(self, current, max_count):
        """Update usercount based on server input"""
        self.result['usercount'] = {'current': current, 'max': max_count}

    def handle_error(self, msg):
        """Handle a fatal error"""
        self.result['is_test_successful'] = False
        self.result['is_error'] = True
        self.result['error_msg'] = msg
        self.close()

    def handle_which_result(self, result):
        """Update `which result of Furcadia's respective network component"""
        self.result['which'][result['type']] = result

    def handle_which_delay(self, delay):
        """Uppdate the time it took for the entire `which request to be processed (in seconds)"""
        self.result['which']['delay'] = delay

    def handle_disconnected(self):
        self.close()
