#!/usr/bin/env python

import argparse
import datetime
from collections import namedtuple
from struct import unpack
import sys
import ImageFile
import Image

def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', dest='essfile', type=str)
    parser.add_argument('-i', '--image', dest='image', type=str)
    parser.add_argument('-p', '--list_plugins', dest='list_plugins', action='store_true')
    return parser.parse_args()


FileHeader = namedtuple('FileHeader', 'fileId majorVersion minorVersion exeTime')
SaveGameHeader = namedtuple('SaveGameHeader', 'headerVersion saveHeaderSize saveNum pcName pcLevel pcLocation gameDays gameTicks gameTime screenshot')
Globals = namedtuple('Globals', 'formIdsOffset recordsNum nextObjectId worldId worldX worldY pcLocation globalsNum globals tesClassSize numDeathCounts deathCounts gameModeSeconds processesSize processesData specEventSize specEventData weatherSize weatherData playerCombatCount createdNum createdData quickKeysSize quickKeysData reticuleSize reticuleData interfaceSize interfaceData regionsSize regionsNum regions')
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
    size, width, height = unpack('3I', filehandle.read(12))
    print [size, width, height]
    size -= 8
    rgb_data = filehandle.read(size)
    im = Image.frombuffer('RGB', (width, height), rgb_data)
    im.rotate(180)
    if write_to_file:
        im.save(write_to_file)
    return im

def parse_globals(filehandle):
    n_globals = unpack('H', filehandle.read(2))[0]
    globals_dict = dict()
    for n in range(n_globals):
        iref, value = unpack('If', filehandle.read(8))
        globals_dict[iref] = value

    return [n_globals, globals_dict]

def parse_deathcounts(filehandle):
    numDeathCounts = unpack('I', filehandle.read(4))[0]
    deathCounts = dict()
    for n in range(numDeathCounts):
        actor, deathCount = unpack('IH', filehandle.read(6))
        deathCounts[actor] = deathCount

    return [numDeathCounts, deathCounts]

def parse_bytelist(filehandle, bytetype='s'):
    size = unpack('H', filehandle.read(2))[0]
    data = unpack('%d%s' % (size, bytetype), filehandle.read(size))
    return [size, data]

def parse_createddata(filehandle):
    createdNum = unpack('I', filehandle.read(4))[0]
    records = list()
    print "Found %d created records" % createdNum
    for count in range(createdNum):
        record_type = unpack('4s', filehandle.read(4))
        print 'type: %r' % record_type
        record_size = unpack('4I', filehandle.read(16))
        print 'size: %r' % list(record_size)
        data = unpack('%ds' % record_size[0], filehandle.read(record_size[0]))
#        print 'data: %r' % data
        records.append((record_type, data))

    return [createdNum, records]

def parse_quickkeydata(filehandle):
    quickKeysSize = unpack('H', filehandle.read(2))[0]
    quickKeys = list()
    for count in range(quickKeysSize):
        flag = unpack('B', filehandle.read(1))[0]
        if flag:
            iref = unpack('I', filehandle.read(4))[0]
            quickKeys.append(iref)
        else:
            notset = unpack('B', filehandle.read(1))[0]
            quickKeys.append(notset)

    return [quickKeysSize, quickKeys]

def parse_regions(filehandle):
    size, count = unpack('2H', filehandle.read(4))

    regions = dict()
    for n in range(count):
        iref, value = unpack('II', filehandle.read(8))
        regions[iref] = value

    return [size, count, regions]

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
        globalslist.extend(parse_globals(essfile))
        tesClassSize = unpack('H', essfile.read(2))[0]
        globalslist.append(tesClassSize)
        globalslist.extend(parse_deathcounts(essfile))
        globalslist.append(unpack('f', essfile.read(4))[0])

        # processesData
        globalslist.extend(parse_bytelist(essfile))

        # specEventData
        globalslist.extend(parse_bytelist(essfile))

        # weatherData
        globalslist.extend(parse_bytelist(essfile))

        globalslist.append(unpack('I', essfile.read(4))[0])

        globalslist.extend(parse_createddata(essfile))

        globalslist.extend(parse_quickkeydata(essfile))

        # reticuleData
        globalslist.extend(parse_bytelist(essfile, bytetype='s'))

        # interface stuff
        globalslist.extend(parse_bytelist(essfile))

        globalslist.extend(parse_regions(essfile))
        g = Globals._make(globalslist)

        records = parse_records(essfile)

    print h
    print s
    print "%s plugins found" % len(plugins)
    if options.list_plugins:
        for p in sorted(plugins):
            print p
    print g

