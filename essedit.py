#!/usr/bin/env python

import argparse
import datetime
from collections import namedtuple
from struct import unpack

import ImageFile
import Image

def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', dest='essfile', type=str)
    parser.add_argument('-i', '--image', dest='image', type=str)
    return parser.parse_args()


FileHeader = namedtuple('FileHeader', 'fileId majorVersion minorVersion exeTime')
SaveGameHeader = namedtuple('SaveGameHeader', 'headerVersion saveHeaderSize saveNum pcName pcLevel pcLocation gameDays gameTicks gameTime screenshot')
Globals = namedtuple('Globals', 'formIdsOffset recordsNum nextObjectId worldId worldX worldY pcLocation')
PCLocation = namedtuple('PCLocation', 'cell x y z')

def time_from_win_systemtime(systemtime):
    systemtime[7] *= 1000 # ms to us
    systemtime.pop(2) # Remove dayofweek
    return datetime.datetime(*systemtime)


def parse_systemtime(filehandle):
    t = unpack('8H', filehandle.read(16))
    return time_from_win_systemtime(list(t))


def parse_b_or_bzstring(filehandle, bz=False):
    # A string prefixed with a byte length and terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = unpack('%ds' % length, filehandle.read(length))[0]
    if bz:
        assert s[-1] == '\x00'
        return s[:-1]
    else:
        return s


def parse_screenshot(filehandle, write_to_file=None):
    size, width, height = unpack('3I', essfile.read(12))
    print [size, width, height]
    size -= 8
    rgb_data = essfile.read(size)
    im = Image.frombuffer('RGB', (width, height), rgb_data)
    im.rotate(180)
    if write_to_file:
        im.save(write_to_file)
    return im

if __name__ == '__main__':
    options = get_options()
    with open(options.essfile, 'rb') as essfile:
        # FileHeader
        headerpart = list(unpack('12s B B', essfile.read(14)))
        headerpart.append(parse_systemtime(essfile))
        h = FileHeader._make(headerpart)

        # SaveGameHeader
        gameheader = list(unpack('3I', essfile.read(12)))
        gameheader.append(parse_b_or_bzstring(essfile, bz=True))

        gameheader.append(unpack('H', essfile.read(2))[0])

        gameheader.append(parse_b_or_bzstring(essfile, bz=True))
        gameheader.extend(list(unpack('fI', essfile.read(8))))
        gameheader.append(parse_systemtime(essfile))
        gameheader.append(parse_screenshot(essfile, options.image))
        s = SaveGameHeader._make(gameheader)

        # Plugins
        plugins = list()
        plugincount = unpack('B', essfile.read(1))[0]
        for index in range(plugincount):
            plugins.append(parse_b_or_bzstring(essfile))

        # Globals
        globalslist = list()
        globalslist.extend(list(unpack('6I', essfile.read(24))))
        pcloc = PCLocation._make(unpack('4I', essfile.read(16)))
        globalslist.append(pcloc)
        globalsNum = unpack('H', essfile.read(2))
        print globalsNum
        g = Globals._make(globalslist)

    print h
    print s
    print len(plugins)
    print g
