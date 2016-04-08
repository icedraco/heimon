from heimon import HeimdallTest
from heimon.util import *

from os import path
from glob import glob

#--- Configuration -----------------------------------------------------------#

G_TIMEOUT_SECS = 6.0
G_ADDRESS = ("lightbringer.furcadia.com", 6500)
G_CREDS_PATH = path.join('.', 'ini')


#--- Functions ---------------------------------------------------------------#
def read_chars(ini_path):
    def filter_bad_creds(info):
        return "name" in info and "password" in info
    return list(filter(filter_bad_creds, map(readini, glob(path.join(ini_path, '*.ini')))))

def main(argv):
    HeimdallTest.settimeout(G_TIMEOUT_SECS)

    print("Reading Furcadia characters...")
    chars = read_chars(G_CREDS_PATH)
    if len(chars) == 0:
        print("NO CHARACTERS FOUND AT %s - ABORTING" % G_CREDS_PATH)
        return -1

    print("Building HeimdallTest instance... [character: %s]" % chars[0]['name'])
    heimtest = HeimdallTest(G_ADDRESS, chars[0])

    print("Connecting...")
    heimtest.connect()

    print("Connected - parsing data...")
    while heimtest.is_connected():
        heimtest.process_next()

    print(heimtest.result)

    print("DONE")
    return 0


#--- Initialization ----------------------------------------------------------#
if __name__ == "__main__":
    from sys import argv as av
    raise SystemExit(main(av))
