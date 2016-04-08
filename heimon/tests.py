# HeimdallTest Result Tests - Project Heimon
#
# Contains all the available tests that can be performed every cycle against
# the incoming results from HeimdallTest class and in general
#
# Version: 20160408-2240
# Author:  Artex / IceDragon <artex@furcadia.com>

from time import time


class TestRunner(object):
    """Responsible for building and running all the tests against a given result"""
    def __init__(self, test_classes, alert_func, log_func):
        self.config = {}

        # pre-build all the objects from the test classes and
        # store them for later use by test() method
        self.tests = list(map(lambda tc: tc(alert_func, log_func, self.config), test_classes))

    def test(self, result):
        for test in self.tests:
            # TEST TEST TEST TEST TESTITY TEST TEST... yeah...
            # test = test.test(test={'test':test})  # test!
            if not test.test(result):
                break


class Test(object):
    """Generic test"""
    def __init__(self, alert_func, log_func, config):
        self.alert_func = alert_func
        self.log_func = log_func
        self.config = config

    def test(self, result):
        return True


class TestNoError(Test):
    """
    Tests for any fatal errors that a heimdall check instance could encounter
    during its run.

    If this test trips, there is no point performing other tests - there may be
    unsifficient data for those...
    """
    def test(self, result):
        if result['is_error']:
            msg = result['error_msg']
            self.alert_func("Heimdall check cycle failed: " + msg)
            return False
        return Test.test(self, result)


class TestUserCountPresent(Test):
    """
    Tests that the user count was properly collected.

    If this test trips, chances are the very first line the server sends us did
    not arrive and therefore, we might've not been able to get as far as AUTH.
    """
    def test(self, result):
        if not result['usercount']:
            self.alert_func("User count not available - the server might not be responding!")
            return False
        return Test.test(self, result)


class TestUserCountAboveThreshold(Test):
    """
    Test that the current user count is above minimal threshold.

    If this test trips, there could be a significant amount of disconnections
    on the server.

    Requirements:
      'usercount_threshold' configuration must be present!
    """
    def test(self, result):
        if 'usercount_threshold' in self.config:
            threshold = self.config['usercount_threshold']
            if result['usercount']['current'] <= threshold:
                self.alert_func("User count not available - the server might not be responding!")
        else:
            self.alert_func("%s/BUG: usercount_threshold is not present!" % self.__class__)

        return Test.test(self, result)


class TestAllComponentsPresent(Test):
    """
    Test that all the components (heimdall, horton, tribble) are detected.
    If this test trips, one of them may be disconnected from the system!
    """
    def test(self, result):
        # heimdall should NEVER be missing from result at this stage!
        # if it is, then there's something screwy in the code...
        if 'heimdall' not in result['which']:
            self.alert_func("%s/BUG: 'heimdall' component is missing from result!" % self.__class__)
            return False

        proceed = True
        for component in ['horton', 'tribble']:
            if component not in result['which']:
                data = (component,
                        result['which']['heimdall']['port'],
                        result['which']['heimdall']['id'])

                self.alert_func("%s component missing from `which on heimdall %d:%d" % data)
                proceed = False

        return proceed and Test.test(self, result)


class TestWhichDelayAboveThreshold(Test):
    """
    Test that the time it took to gather the result is not excessive.

    If this test trips, there could be a high lag on the server, or some of the
    network components are missing from the `which response
    (i.e., disconnected from the system)

    Requirements:
      'delay_threshold' configuration must be present!
    """
    def test(self, result):
        if 'delay_threshold' in self.config:
            threshold = self.config['delay_threshold']
            if result['which']['delay'] > threshold:
                data = (result['which']['delay'], threshold)
                self.alert_func("`which delay above threshold (%d > %d) - there might be lag!" % data)
                return False
        else:
            self.alert_func("%s/BUG: delay_threshold is not present!" % self.__class__)

        return Test.test(self, result)


class TestGlobalIdInSync(Test):
    """
    Test that all the player's global ID values are in sync.

    If this test trips, there may be a synchronization issue for our test
    character among the components involved! This should, theoretically, never
    happen...
    """
    def test(self, result):
        heimdall = result['which']['heimdall']['my']['global_id']
        horton = -1 if 'horton' not in result['which'] else result['which']['horton']['my']['global_id']
        tribble = -1 if 'tribble' not in result['which'] else result['which']['tribble']['my']['global_id']
        data = (heimdall, horton, tribble)

        if not (data[0] == data[1] == data[2]):
            self.alert_func("Player global ID desync: heim/%d hort/%d trib/%d" % data)
            return False

        return Test.test(self, result)


class TestNoHeimdallsAreMissing(Test):
    """
    Test that no heimdalls so far have been missing.

    If this test trips, there is a strong suspicion that said heimdalls are no
    longer handling connection as they should (i.e., frozen/dead)

    Requirements:
      'heimdall_tracker' configuration must be present!
    """
    def test(self, result):
        if 'heimdall_tracker' not in self.config:
            self.alert_func("%s/BUG: heimdall_tracker is not present!" % self.__class__)
            return False

        # first, update the tracker with this result
        tracker = self.config['heimdall_tracker']
        tracker.update_last_check()
        tracker.update_heimdall(result['which']['heimdall']['id'])

        # now ask if anything's missing
        for h_id in tracker.find_missing():
            h_data = tracker.get(h_id)
            data = (h_id, time() - h_data['ts_last_seen'])
            self.alert_func("Heimdall %s has been missing (last seen %.2f secs ago)" % data)

        return Test.test(self, result)
