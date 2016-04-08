# Utilities - Project Heimon
#
# Version: 20160408-1950
# Author:  Artex / IceDragon <artex@furcadia.com>

def readini(filename):
    """Read a Furcadia character INI file and extract information from within it"""
    result = {}
    with open(filename, encoding='utf-8') as fd:
        for line in fd:
            elems = line.strip().split('=', 1)
            if len(elems) > 1:
                key = elems[0].lower()
                value = elems[1]
                result[key] = value
    return result

