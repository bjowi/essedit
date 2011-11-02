#!/usr/bin/env python

import argparse
import datetime
from collections import namedtuple
from struct import unpack

def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', dest='essfile', type=str)
    return parser.parse_args()

FileHeader = namedtuple('FileHeader', 'fileId majorVersion minorVersion exeTime')
SaveGameHeader = namedtuple('SaveGameHeader', 'headerVersion saveHeaderSize saveNum pcName')

def time_from_win_systemtime(systemtime):
    systemtime[7] *= 1000 # ms to us
    systemtime.remove(2) # Remove dayofweek
    return datetime.datetime(*systemtime)

def parse_bzstring(filehandle):
    # A string prefixed with a byte length and terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = unpack('%ds' % length, filehandle.read(length))[0]
    assert s[-1] == '\x00'
    return s[:-1]

if __name__ == '__main__':
    options = get_options()
    with open(options.essfile, 'rb') as essfile:
        headerpart = list(unpack('12s B B', essfile.read(14)))
        exetime = unpack('8H', essfile.read(16))
        exetime = time_from_win_systemtime(list(exetime))
        headerpart.append(exetime)
        h = FileHeader._make(headerpart)

        gameheader = list(unpack('3I', essfile.read(12)))
        gameheader.append(parse_bzstring(essfile))

    print h
    print gameheader

