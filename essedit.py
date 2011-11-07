#!/usr/bin/env python

import argparse
import datetime
from collections import namedtuple
from struct import unpack, pack, error

import sys
import ImageFile
import Image

def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', dest='essfile', type=str)
    parser.add_argument('-i', '--image', dest='image', type=str)
    parser.add_argument('-p', '--list_plugins', dest='list_plugins', action='store_true')
    parser.add_argument('-r', '--list_records', dest='list_records', action='store_true')
    parser.add_argument('-w', '--write_to', dest='write_to', type=str)
    return parser.parse_args()

def enum(**nums):
    res = namedtuple('Enum', nums.keys())
    return res(*nums.values()), dict((v,k) for k, v in nums.iteritems())

SaveGame = namedtuple('SaveGame', 'fileheader gameheader globals plugins records tempEffectsData formIds worldSpaces')
FileHeader = namedtuple('FileHeader', 'fileId majorVersion minorVersion exeTime')
SaveGameHeader = namedtuple('SaveGameHeader', 'headerVersion saveHeaderSize saveNum pcName pcLevel pcLocation gameDays gameTicks gameTime screenshot')
Globals = namedtuple('Globals', 'formIdsOffset recordsNum nextObjectId worldId worldX worldY pcLocation globalsNum globals tesClassSize numDeathCounts deathCounts gameModeSeconds processesSize processesData specEventSize specEventData weatherSize weatherData playerCombatCount createdNum createdData quickKeysSize quickKeysData reticuleSize reticuleData interfaceSize interfaceData regionsSize regionsNum regions')
PCLocation = namedtuple('PCLocation', 'cell x y z')

RecordTypes, RecordTypeNames = enum(FACT=6,
                                    APPA=19,
                                    ARMO=20,
                                    BOOK=21,
                                    CLOT=22,
                                    INGR=25,
                                    LIGH=26,
                                    MISC=27,
                                    WEAP=33,
                                    AMMO=34,
                                    NPC_=35,
                                    CREA=36,
                                    SLGM=38,
                                    KEYM=39,
                                    ALCH=40,
                                    CELL=48,
                                    REFR=49,
                                    ACHR=50,
                                    ACRE=51,
                                    INFO=58,
                                    QUST=59,
                                    PACK=61)

def time_from_win_systemtime(systemtime):
    print "1win:       %r" % systemtime
    systemtime[7] *= 1000 # ms to us
    systemtime.pop(2) # Remove dayofweek
    print "1datetime:  %r" % systemtime
    return datetime.datetime(*systemtime)

def time_to_win_systemtime(pythontime):
    systemtime = list(pythontime.timetuple())
    print "2datetime:  %r" % systemtime
    dow = systemtime.pop(6) # Get dayofweek
    systemtime.insert(2, dow+1 % 6)
    systemtime[7] /= 1000 # ms to us
    print "2win:       %r" % systemtime[:8]
    return systemtime[:8]


def parse_systemtime(filehandle):
    t = unpack('8H', filehandle.read(16))
    return time_from_win_systemtime(list(t))


def write_b_or_bzstring(filehandle, s, bz=False):
    # Write a string prefixed with a byte length and optionally terminated with a zero (\x00).
    if bz:
        filehandle.write(pack('B', len(s)+1))
        filehandle.write(s+'\x00')
    else:
        filehandle.write(pack('B', len(s)))
        filehandle.write(s)


def parse_b_or_bzstring(filehandle, bz=False):
    # A string prefixed with a byte length and optionally terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = filehandle.read(length)
    if bz:
        return s[:-1]
    else:
        return s


def parse_screenshot(filehandle, write_to_file=None):
    size, width, height = unpack('3I', filehandle.read(12))
    size -= 8
    rgb_data = filehandle.read(size)
    im = Image.frombuffer('RGB', (width, height), rgb_data, 'raw', 'RGB', 0, 1)

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
    data = filehandle.read(size) # unpack('%d%s' % (size, bytetype), filehandle.read(size))
    return [size, data]

def write_bytelist(filehandle, size, data):
    filehandle.write(pack('H', len(data)))
    filehandle.write(data)

def parse_createddata(filehandle):
    createdNum = unpack('I', filehandle.read(4))[0]
    records = list()
    #print "Found %d created records" % createdNum
    for count in range(createdNum):
        record_type, = unpack('4s', filehandle.read(4))
        #print 'type: %r' % record_type
        record_size, flags, formId, vcinfo = unpack('4I', filehandle.read(16))
        data, = unpack('%ds' % record_size, filehandle.read(record_size))
        #print 'data: %r' % data
        records.append([record_type, record_size, flags, formId, vcinfo, data])

    return [createdNum, records]

def write_created_data(filehandle, globalsdata):
    filehandle.write(pack('I', globalsdata.createdNum))
    for record in globalsdata.createdData:
        filehandle.write(record[0])
        filehandle.write(pack('4I', *(record[1:5])))
        filehandle.write(record[5])

def parse_quickkeydata(filehandle):
    quickKeysSize = unpack('H', filehandle.read(2))[0]
    quickKeysData = filehandle.read(quickKeysSize)

    return [quickKeysSize, quickKeysData]

    # quickKeys = list()
    # bytes_read = 0
    # while True:
    #     if bytes_read >= quickKeysSize:
    #         break

    #     flag = unpack('B', filehandle.read(1))[0]
    #     bytes_read += 1
    #     if flag:
    #         iref = unpack('I', filehandle.read(4))[0]
    #         quickKeys.append(iref)
    #         bytes_read += 4
    #     else:
    #         notset = unpack('B', filehandle.read(1))[0]
    #         quickKeys.append(notset)
    #         bytes_read += 1
    #     print "qs %r" % quickKeys
    #     print "qs %r" % bytes_read

    # return [quickKeysSize, quickKeys]

def parse_regions(filehandle):
    size, count = unpack('2H', filehandle.read(4))

    regions = dict()
    for n in range(count):
        iref, value = unpack('II', filehandle.read(8))
        regions[iref] = value

    return [size, count, regions]


def parse_record(filehandle):
#    formId, record_type, flags, version, datasize = unpack('=IBIBH', filehandle.read(12))
    formId, = unpack('I', filehandle.read(4))
    record_type, = unpack('B', filehandle.read(1))
    flags, = unpack('I', filehandle.read(4))
    version, = unpack('B', filehandle.read(1))
    datasize, = unpack('H', filehandle.read(2))

    data = filehandle.read(datasize)
    return [formId, record_type, flags, version, datasize, data]

def load(options):
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
        pcloc = PCLocation._make(unpack('I3f', essfile.read(16)))
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

        # regions
        globalslist.extend(parse_regions(essfile))

        g = Globals._make(globalslist)

        # change records
        records = list()
        for c in range(g.recordsNum):
            record = parse_record(essfile)
            records.append(record)
            formId, record_type, flags, version, datasize, data = records[-1]

        # temporary effects
        tempEffectsSize = unpack('I', essfile.read(4))[0]
        tempEffectsData = essfile.read(tempEffectsSize)

        # formIds
        formIdsNum = unpack('I', essfile.read(4))[0]
        formIds = unpack('%sI' % formIdsNum, essfile.read(4 * formIdsNum))

        # worldSpaces
        worldSpacesNum = unpack('I', essfile.read(4))[0]
        worldSpaces = unpack('%sI' % worldSpacesNum, essfile.read(4 * worldSpacesNum))

    savegame = SaveGame._make([h, s, g, plugins, records, tempEffectsData, formIds, worldSpaces])
    return savegame

def write(savegame, options):
    with open(options.write_to, 'wb') as essfile:
        # Fileheader
        essfile.write(savegame.fileheader.fileId)
        essfile.write(pack('BB', savegame.fileheader.majorVersion,
                           savegame.fileheader.minorVersion))
        stime = time_to_win_systemtime(savegame.fileheader.exeTime)
        essfile.write(pack('8H', *stime))

        # SaveGameHeader
        essfile.write(pack('3I', savegame.gameheader.headerVersion,
                           savegame.gameheader.saveHeaderSize,
                           savegame.gameheader.saveNum))
        write_b_or_bzstring(essfile, savegame.gameheader.pcName, bz=True)
        essfile.write(pack('H', savegame.gameheader.pcLevel))
        write_b_or_bzstring(essfile, savegame.gameheader.pcLocation, bz=True)
        essfile.write(pack('fI', savegame.gameheader.gameDays,
                           savegame.gameheader.gameTicks))

        gtime = time_to_win_systemtime(savegame.gameheader.gameTime)
        essfile.write(pack('8H', *gtime))
        im = savegame.gameheader.screenshot
        w, h = im.size
        essfile.write(pack('3I', (w*h*3)+8, w, h))
        essfile.write(im.tostring())

        # Plugins
        plugincount = len(savegame.plugins)
        essfile.write(pack('B', plugincount))
        for plugin in savegame.plugins:
            write_b_or_bzstring(essfile, plugin)

        # Globals
        essfile.write(pack('6I', *(savegame.globals[:6])))

        essfile.write(pack('I3f', *(savegame.globals.pcLocation)))
        essfile.write(pack('H', len(savegame.globals.globals)))
        for k,v in savegame.globals.globals.iteritems():
            essfile.write(pack('If', k, v))

        essfile.write(pack('H', savegame.globals.tesClassSize))

        essfile.write(pack('I', len(savegame.globals.deathCounts)))
        for k,v in savegame.globals.deathCounts.iteritems():
            essfile.write(pack('IH', k, v))

        essfile.write(pack('f', savegame.globals.gameModeSeconds))

        write_bytelist(essfile, savegame.globals.processesSize,
                       savegame.globals.processesData)

        write_bytelist(essfile, savegame.globals.specEventSize,
                       savegame.globals.specEventData)

        write_bytelist(essfile, savegame.globals.weatherSize,
                       savegame.globals.weatherData)

        essfile.write(pack('I', savegame.globals.playerCombatCount))
        write_created_data(essfile, savegame.globals)

        essfile.write(pack('H', savegame.globals.quickKeysSize))
        essfile.write(savegame.globals.quickKeysData)

        write_bytelist(essfile, savegame.globals.reticuleSize,
                       savegame.globals.reticuleData)

        write_bytelist(essfile, savegame.globals.interfaceSize,
                       savegame.globals.interfaceData)

        essfile.write(pack('2H', savegame.globals.regionsSize,
                           savegame.globals.regionsNum))

        for iref, data in savegame.globals.regions.iteritems():
            essfile.write(pack('II', iref, data))

        assert savegame.globals.recordsNum == len(savegame.records)

        # Change records
        for formId, record_type, flags, version, size, data in savegame.records:
            essfile.write(pack('I', formId))
            essfile.write(pack('B', record_type))
            essfile.write(pack('I', flags))
            essfile.write(pack('B', version))
            essfile.write(pack('H', size))
            assert len(data) == size
            essfile.write(data)

        essfile.write(pack('I', len(savegame.tempEffectsData)))
        essfile.write(savegame.tempEffectsData)
        essfile.write(pack('I', len(savegame.formIds)))
        essfile.write(pack('%sI' % len(savegame.formIds), *(savegame.formIds)))
        essfile.write(pack('I', len(savegame.worldSpaces)))
        essfile.write(pack('%sI' % len(savegame.worldSpaces), *(savegame.worldSpaces)))

if __name__ == '__main__':
    options = get_options()
    savegame = load(options)

    print savegame.gameheader
    print "%s plugins found" % len(savegame.plugins)
    if options.list_plugins:
        for p in sorted(savegame.plugins):
            print p

    print "%s change records found" % len(savegame.records)

    if options.list_records:
        for r in savegame.records:
            print RecordTypeNames.get(r[1], '%r UKNOWN RECORD TYPE' % r[1])
    print '-----------------------------------------------'

    if options.write_to:
        write(savegame, options)

    print savegame.globals.pcLocation
    print 'Done.'
