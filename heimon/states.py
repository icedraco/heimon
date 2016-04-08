# Connection States - Project Heimon
#
# Contains data handlers for each connection state that the HeimdallTest class
# can find itself in.
#
# Version: 20160408-2242
# Author:  Artex / IceDragon <artex@furcadia.com>



from heimon.parsers import WhichStringParser
from time import time

class State(object):
    """Generic HeimdallTest state"""
    def __init__(self, test):
        self.heimtest = test

    def __str__(self):
        return State.__name__

    def process(self, line):
        pass

    def enter(self):
        print(">> %s" % self)

    def exit(self):
        pass

    def idle(self):
        print("!! IDLE: %s" % self)


class NullState(State):
    """ NULL State
        Used mostly instead of a "null"/None object to avoid unnecessary null
        checks.
    """
    def __init__(self, test):
        State.__init__(self, test)

    def __str__(self):
        return NullState.__name__


class DragonroarState(State):
    """ Connection ("Dragonroar") State
        Looks for user count info and Dragonroar in order to move on to the
        next (AUTH) stage
    """
    def __init__(self, test, creds):
        State.__init__(self, test)
        self.__creds = creds
        self.__got_usercount = False

    def __str__(self):
        return DragonroarState.__name__

    def process(self, line):
        State.process(self, line)

        # extract usercount
        if line.startswith(b'#') and not self.__got_usercount:
            (u_current, u_max) = tuple(map(int, line[1:].split(b' ')))
            self.heimtest.handle_usercount(u_current, u_max)
            self.__got_usercount = True

        # switch handler when banner is confirmed
        elif line == b'Dragonroar':
            self.heimtest.change_state(AuthState(self.heimtest, self.__creds))

    def exit(self):
        State.exit(self)
        self.__creds = None

    def idle(self):
        State.idle(self)
        self.heimtest.handle_error("Timed out before Dragonroar")


class AuthState(State):
    """ AUTH State:
        Sends login request to the server and awaits confirmation/rejection
        before determining further action
    """
    @staticmethod
    def sanitize_creds(creds):
        """
        Sanitize credentials that may come in with spaces and as regular strings.
        """
        # replace spaces accordingly and return
        return (
            creds[0].replace(' ', '|'),
            creds[1].replace(' ', '_'))

    def __init__(self, test, creds):
        State.__init__(self, test)
        self.__creds = creds

    def __str__(self):
        return AuthState.__name__

    def enter(self):
        State.enter(self)
        creds = self.sanitize_creds((
            self.__creds['name'],
            self.__creds['password']
        ))

        self.heimtest.send("connect %s %s\n" % creds)
        self.__creds = None

    def idle(self):
        State.idle(self)
        self.heimtest.handle_error("Timed out during AUTH stage")

    def process(self, line):
        State.process(self, line)

        # process rejection notice
        if line.startswith(b']#'):
            error_msg = line.split(b' ', 2)[2].decode("utf-8")
            self.heimtest.handle_error(error_msg)

        elif line == b'&&&&&&&&&&&&&':
            self.heimtest.change_state(WhichTestState(self.heimtest))


class WhichTestState(State):
    MAX_WHICH_LINES = 3
    WHICH_TIMEOUT_SECS = 5

    def __init__(self, test):
        State.__init__(self, test)
        self.__parser = WhichStringParser()
        self.__success_counter = 0
        self.__which_ts = time()

    def __str__(self):
        return WhichTestState.__name__

    def enter(self):
        State.enter(self)
        self.__success_counter = 0
        self.heimtest.send("which\n")

    def process(self, line):
        State.process(self, line)

        def callback(result):
            self.heimtest.handle_which_result(result)

        if self.__parser.parse(line, callback):
            self.__success_counter += 1

        # bail out if we have 3 `which lines parsed
        if self.__success_counter >= self.MAX_WHICH_LINES:
            self.heimtest.handle_which_delay(time() - self.__which_ts)
            self.heimtest.change_state(ClosingState(self.heimtest))
        else:
            self.__maybe_timeout()

    def idle(self):
        State.idle(self)
        self.__maybe_timeout()

    def __maybe_timeout(self):
        delay = time() - self.__which_ts
        is_timeout = delay > self.WHICH_TIMEOUT_SECS
        if is_timeout:
            data = (self.__success_counter, self.MAX_WHICH_LINES)
            print("Timed out waiting for all WHICH responses (%d/%d captured)" % data)
            self.heimtest.handle_which_delay(delay)
            self.heimtest.change_state(ClosingState(self.heimtest))
        return is_timeout


class ClosingState(State):
    def __init__(self, test):
        State.__init__(self, test)

    def __str__(self):
        return ClosingState.__name__

    def enter(self):
        State.enter(self)
        self.heimtest.send("quit\n")


class ClosedState(NullState):
    def __str__(self):
        return ClosedState.__name__
