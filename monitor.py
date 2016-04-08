# Monitor Component - Project Heimon
#
# Version: 20160409-0000
# Author:  Artex / IceDragon <artex@furcadia.com>

import sys

from heimon.tests import *
from heimon import HeimdallTest
from heimon.util import *

from time import *
from os import path
from glob import glob


# --- Configuration --------------------------------------------------------- #

# All the heimdall IDs we are looking for
G_HEIMDALL_IDS = range(1, 7)  # 1..(7-1) - BE CAREFUL!

# Amount of seconds past which a heimdall should be considered missing
G_HEIMDALL_ALERT_SECS = 60  # secs

# Amount of seconds to wait before re-announcing that a heimdall is missing
G_FRESHLY_MISSING_THRESHOLD = 60  # secs

# current/max_seen user count percentage below which an alert is triggered
G_USERCOUNT_THRESHOLD = 10.0  # percent

# `which obtaining delay past which an alert is triggered
# used to check for lag in obtaining `which results, or incomplete results
G_WHICH_DELAY_THRESHOLD = 5  # secs

# Interval between each login/check
G_CHECK_INTERVAL = 2.0  # secs

# Data I/O and connection timeout
# used to limit how long each instance would wait for data before timing out
G_TIMEOUT_SECS = 6.0

# Furcadia gameserver address
G_ADDRESS = ("lightbringer.furcadia.com", 6500)

# Path to all the INI files to use in the credentials pool
G_CREDS_PATH = path.join('.', 'ini')

# All the tests to perform on the HeimdallTest result data in this order
# (the test classes themselves are stored in heimon/tests.py)
G_RESULT_TESTS = [
    TestNoError,
    TestUserCountPresent,
    TestUserCountAboveThreshold,
    TestAllComponentsPresent,
    TestWhichDelayAboveThreshold,
    TestGlobalIdInSync,
    TestNoHeimdallsAreMissing,
    TestNoLongerMissingHeimdalls
]


# --- Classes --------------------------------------------------------------- #
# TODO: Get this thing out of here...
class HeimdallTracklist(object):
    MISSING_THRESHOLD = 60 # secs

    def __init__(self, heimdall_ids):
        self.__last_check = time()
        self.__heimdalls = {}
        for hid in heimdall_ids:
            self.add(hid)

    def add(self, heimdall_id):
        self.__heimdalls[heimdall_id] = {
            'id': heimdall_id,
            'ts_added': time(),
            'ts_last_seen': 0,
            'ts_reported_missing': 0
        }
        return self

    def get(self, heimdall_id):
        return self.__heimdalls.get(heimdall_id, None)

    def find_missing(self):
        current_time = time()

        def filter_missing(heimdall):
            delta = current_time - max(heimdall['ts_added'], heimdall['ts_last_seen'])
            return delta > self.MISSING_THRESHOLD

        # locate missing heimdalls
        missing_heimdalls = filter(filter_missing, self.__heimdalls.values())

        # update their "reported missing" timestamp
        for heimdall in missing_heimdalls:
            heimdall['ts_reported_missing'] = current_time

        # return the missing heimdalls
        return missing_heimdalls

    def update_heimdall(self, h_id):
        if h_id not in self.__heimdalls:
            alert("%s/BUG: Unknown heimdall ID detected: %s" % (self.__class__, h_id))
            self.add(h_id)

        self.__heimdalls[h_id]['ts_reported_missing'] = 0
        self.__heimdalls[h_id]['ts_last_seen'] = time()

    def update_last_check(self):
        self.__last_check = time()


# --- Functions ------------------------------------------------------------- #
# TODO: Something a bit more dignifying than this...
G_ALERT_BUFFER = []


def alert(message):
    """Display alert in STDERR and add to buffer for later bulk transmission"""
    global G_ALERT_BUFFER
    data = "[%s][ALERT!] %s\n" % (asctime(), message)
    sys.stderr.write(data)
    G_ALERT_BUFFER += [data]


def flush_alert_buffer():
    """Flush the alert buffer so far into some sort of destination"""
    all_alerts = G_ALERT_BUFFER[:] # clone the list
    G_ALERT_BUFFER.clear()
    do_email(all_alerts)
    return all_alerts


def do_email(alerts):
    """Send an e-mail with the given alert message list"""
    if len(alerts) > 0:
        # <<e-mail code here>>
        pass


def log(message):
    sys.stdout.write("[%s] %s\n" % (asctime(), message))


def read_chars(ini_path):
    def filter_bad_creds(info):
        return "name" in info and "password" in info and "password" != "Password"
    return list(filter(filter_bad_creds, map(readini, glob(path.join(ini_path, '*.ini')))))


def main(argv):
    HeimdallTest.settimeout(G_TIMEOUT_SECS)

    tracker = HeimdallTracklist(G_HEIMDALL_IDS)

    # prepare factory and all the requirements for the tests within
    test_runner = TestRunner(G_RESULT_TESTS, alert, log)
    test_runner.config['heimdall_tracker'] = tracker
    test_runner.config['usercount_threshold'] = G_USERCOUNT_THRESHOLD
    test_runner.config['delay_threshold'] = G_WHICH_DELAY_THRESHOLD
    test_runner.config['freshly_missing_threshold'] = G_FRESHLY_MISSING_THRESHOLD

    print("Reading Furcadia characters...")
    chars = read_chars(G_CREDS_PATH)
    if len(chars) == 0:
        print("NO CHARACTERS FOUND AT %s - ABORTING" % G_CREDS_PATH)
        return -1

    char_index = 0
    while True:
        try:
            character = chars[char_index % len(chars)]
            char_index += 1

            print("Building HeimdallTest instance... [character: %s]" % character['name'])
            heimtest = HeimdallTest(G_ADDRESS, character)

            print("Obtaining data from the server...")
            heimtest.connect()
            while heimtest.is_connected():
                heimtest.process_next()

            if 'heimdall' in heimtest.result['which']:
                print("Found heimdall %d" % heimtest.result['which']['heimdall']['id'])

            # process results
            print("Testing result...")
            test_runner.test(heimtest.result)
        except Exception as ex:
            alert("main()/BUG: Caught exception while executing -> %s" % ex)

        # sleep until the next time
        print("Sleeping (%d secs)" % G_CHECK_INTERVAL)
        sleep(G_CHECK_INTERVAL)
        flush_alert_buffer()

    print("DONE")
    return 0


# --- Initialization -------------------------------------------------------- #
if __name__ == "__main__":
    from sys import argv as av
    raise SystemExit(main(av))
