#!/usr/bin/env python

import argparse
import datetime
from collections import defaultdict, namedtuple
from struct import unpack, pack, error
from StringIO import StringIO

import sys
import ImageFile
import Image

def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', dest='essfile', type=str)
    parser.add_argument('-g', '--essfile2', dest='essfile2', type=str)
    parser.add_argument('-i', '--image', dest='image', type=str)
    parser.add_argument('-p', '--list_plugins', dest='list_plugins', action='store_true')
    parser.add_argument('-r', '--list_records', dest='list_records', action='store_true')
    parser.add_argument('-w', '--write_to', dest='write_to', type=str)
    return parser.parse_args()

def enum(**nums):
    res = namedtuple('Enum', nums.keys())
    return res(*nums.values()), dict((v,k) for k, v in nums.iteritems())

SaveGame = namedtuple('SaveGame', 'gameheader filelocations plugins g1 g2 changeforms g3 formIDArray, unknown2, unknown3')
SaveGameHeader = namedtuple('SaveGameHeader', 'headerVersion, saveNumber, playerName, playerLevel, playerLocation, gameDate, playerRaceEditorId unknown1 unknown2 unknown3 filetime screenshot formVersion')
FileLocationTable = namedtuple('FileLocationTable', 'formIDArrayOffset unknownTable3Offset globalDataTable1Offset globalDataTable2Offset changeFormsOffset globalDataTable3Offset globalDataTable1Count globalDataTable2Count globalDataTable3Count changeFormCount unused1 unused2 unused3 unused4 unused5 unused6 unused7 unused8 unused9 unused10 unused11 unused12 unused13 unused14 unused15')
Globals = namedtuple('Globals', 'formIdsOffset recordsNum nextObjectId worldId worldX worldY pcLocation globalsNum globals tesClassSize numDeathCounts deathCounts gameModeSeconds processesSize processesData specEventSize specEventData weatherSize weatherData playerCombatCount createdNum createdData quickKeysSize quickKeysData reticuleSize reticuleData interfaceSize interfaceData regionsSize regionsNum regions')
PCLocation = namedtuple('PCLocation', 'cell x y z')

FormTypes = {
    0: ('NONE', '', ''),
    1: ('TES4', '', ''),
    2: ('GRUP', '', ''),
    3: ('GMST', '', ''),
    4: ('KYWD', 'Keyword', 'BGSKeyword'),
    5: ('LCRT', 'LocationRefType', 'BGSLocationRefType'),
    6: ('AACT', 'Action', 'BGSAction'),
    7: ('TXST', '', 'BGSTextureSet'),
    8: ('MICN', '', 'BGSMenuIcon'),
    9: ('GLOB', 'GlobalVariable', 'TESGlobal'),
    10: ('CLAS', 'Class', 'TESClass'),
    11: ('FACT', 'Faction', 'TESFaction'),
    12: ('HDPT', '', 'BGSHeadPart'),
    13: ('HAIR', '', 'TESHair'),
    14: ('EYES', '', 'TESEyes'),
    15: ('RACE', 'Race', 'TESRace'),
    16: ('SOUN', 'Sound', 'TESSound'),
    17: ('ASPC', '', 'BGSAcousticSpace'),
    18: ('SKIL', '', ''),
    19: ('MGEF', 'MagicEffect', 'EffectSetting'),
    20: ('SCPT', '', 'Script'),
    21: ('LTEX', '', 'TESLandTexture'),
    22: ('ENCH', 'Enchantment', 'EnchantmentItem'),
    23: ('SPEL', 'Spell', 'SpellItem'),
    24: ('SCRL', 'Scroll', 'ScrollItem'),
    25: ('ACTI', 'Activator', 'TESObjectACTI'),
    26: ('TACT', 'TalkingActivator', 'BGSTalkingActivator'),
    27: ('ARMO', 'Armor', 'TESObjectARMO'),
    28: ('BOOK', 'Book', 'TESObjectBOOK'),
    29: ('CONT', 'Container', 'TESObjectCONT'),
    30: ('DOOR', 'Door', 'TESObjectDOOR'),
    31: ('INGR', 'Ingredient', 'IngredientItem'),
    32: ('LIGH', 'Light', 'TESObjectLIGH'),
    33: ('MISC', 'MiscObject', 'TESObjectMISC'),
    34: ('APPA', 'Apparatus', 'BGSApparatus'),
    35: ('STAT', 'Static', 'TESObjectSTAT'),
    36: ('SCOL', '', 'BGSStaticCollection'),
    37: ('MSTT', '', 'BGSMovableStatic'),
    38: ('GRAS', '', 'TESGrass'),
    39: ('TREE', '', 'TESObjectTREE'),
    40: ('CLDC', '', 'BGSCloudClusterForm'),
    41: ('FLOR', 'Flora', 'TESFlora'),
    42: ('FURN', 'Furniture', 'TESFurniture'),
    43: ('WEAP', 'Weapon', 'TESObjectWEAP'),
    44: ('AMMO', 'Ammo', 'TESAmmo'),
    45: ('NPC_', 'ActorBase', 'TESNPC'),
    46: ('LVLN', 'LeveledActor', 'TESLevCharacter'),
    47: ('KEYM', 'Key', 'TESKey'),
    48: ('ALCH', 'Potion', 'AlchemyItem'),
    49: ('IDLM', '', 'BGSIdleMarker'),
    50: ('NOTE', '', 'BGSNote'),
    51: ('COBJ', 'ConstructibleObject', 'BGSConstructibleObject'),
    52: ('PROJ', 'Projectile', 'BGSProjectile'),
    53: ('HAZD', 'Hazard', 'BGSHazard'),
    54: ('SLGM', 'SoulGem', 'TESSoulGem'),
    55: ('LVLI', 'LeveledItem', 'TESLevItem'),
    56: ('WTHR', 'Weather', 'TESWeather'),
    57: ('CLMT', '', 'TESClimate'),
    58: ('SPGD', 'ShaderParticleGeometry', 'BGSShaderParticleGeometryData'),
    59: ('RFCT', 'VisualEffect', 'BGSReferenceEffect'),
    60: ('REGN', '', 'TESRegion'),
    61: ('NAVI', '', ''),
    62: ('CELL', 'Cell', 'TESObjectCELL'),
    63: ('REFR', 'ObjectReference', ''),
    64: ('ACHR', 'Actor', ''),
    65: ('PMIS', '', ''),
    66: ('PARW', '', ''),
    67: ('PGRE', '', ''),
    68: ('PBEA', '', ''),
    69: ('PFLA', '', ''),
    70: ('PCON', '', ''),
    71: ('PBAR', '', ''),
    72: ('PHZD', '', ''),
    73: ('WRLD', 'WorldSpace', 'TESWorldSpace'),
    74: ('LAND', '', 'TESObjectLAND'),
    75: ('NAVM', '', 'NavMesh'),
    76: ('TLOD', '', ''),
    77: ('DIAL', 'Topic', 'TESTopic'),
    78: ('INFO', 'TopicInfo', 'TESTopicInfo'),
    79: ('QUST', 'Quest', 'TESQuest'),
    80: ('IDLE', 'Idle', 'TESIdleForm'),
    81: ('PACK', 'Package', ''),
    82: ('CSTY', '', 'TESCombatStyle'),
    83: ('LSCR', '', 'TESLoadScreen'),
    84: ('LVSP', 'LeveledSpell', 'TESLevSpell'),
    85: ('ANIO', '', 'TESObjectANIO'),
    86: ('WATR', '', 'TESWaterForm'),
    87: ('EFSH', 'EffectShader', 'TESEffectShader'),
    88: ('TOFT', '', ''),
    89: ('EXPL', 'Explosion', 'BGSExplosion'),
    90: ('DEBR', '', 'BGSDebris'),
    91: ('IMGS', '', 'TESImageSpace'),
    92: ('IMAD', 'ImageSpaceModifier', 'TESImageSpaceModifier'),
    93: ('FLST', 'FormList', 'BGSListForm'),
    94: ('PERK', 'Perk', 'BGSPerk'),
    95: ('BPTD', '', 'BGSBodyPartData'),
    96: ('ADDN', '', 'BGSAddonNode'),
    97: ('AVIF', '', ''),
    98: ('CAMS', '', 'BGSCameraShot'),
    99: ('CPTH', '', 'BGSCameraPath'),
    100: ('VTYP', 'VoiceType', 'BGSVoiceType'),
    101: ('MATT', '', 'BGSMaterialType'),
    102: ('IPCT', '', 'BGSImpactData'),
    103: ('IPDS', 'ImpactDataSet', 'BGSImpactDataSet'),
    104: ('ARMA', '', 'TESObjectARMA'),
    105: ('ECZN', 'EncounterZone', 'BGSEncounterZone'),
    106: ('LCTN', 'Location', 'BGSLocation'),
    107: ('MESG', 'Message', 'BGSMessage'),
    108: ('RGDL', '', 'BGSRagdoll'),
    109: ('DOBJ', '', ''),
    110: ('LGTM', '', 'BGSLightingTemplate'),
    111: ('MUSC', 'MusicType', 'BGSMusicType'),
    112: ('FSTP', '', 'BGSFootstep'),
    113: ('FSTS', '', 'BGSFootstepSet'),
    114: ('SMBN', '', 'BGSStoryManagerBranchNode'),
    115: ('SMQN', '', 'BGSStoryManagerQuestNode'),
    116: ('SMEN', '', 'BGSStoryManagerEventNode'),
    117: ('DBLR', '', 'BGSDialogueBranch'),
    118: ('MUST', '', 'BGSMusicTrackFormWrapper'),
    119: ('DLVW', '', ''),
    120: ('WOOP', 'WordOfPower', 'TESWordOfPower'),
    121: ('SHOU', 'Shout', 'TESShout'),
    122: ('EQUP', '', 'BGSEquipSlot'),
    123: ('RELA', '', 'BGSRelationship'),
    124: ('SCEN', 'Scene', 'BGSScene'),
    125: ('ASTP', 'AssociationType', 'BGSAssociationType'),
    126: ('OTFT', 'Outfit', 'BGSOutfit'),
    127: ('ARTO', '', 'BGSArtObject'),
    128: ('MATO', '', 'BGSMaterialObject'),
    129: ('MOVT', '', 'BGSMovementType'),
    130: ('SNDR', '', 'BGSSoundDescriptorForm'),
    131: ('DUAL', '', 'BGSDualCastData'),
    132: ('SNCT', 'SoundCategory', 'BGSSoundCategory'),
    133: ('SOPM', '', 'BGSSoundOutput'),
    134: ('COLL', '', 'BGSCollisionLayer'),
    135: ('CLFM', '', 'BGSColorForm'),
    136: ('REVB', '', 'BGSReverbParameters'),
    138: ('', 'Alias' ''),
    139: ('', 'ReferenceAlias' ''),
    140: ('', 'LocationAlias' ''),
    141: ('', 'ActiveMagicEffect' '')
    }

savegameform_to_form = {
    0: 63,
    1: 64,
    2: 65,
    3: 67,
    4: 68,
    5: 69,
    6: 62,
    7: 78,
    8: 79,
    9: 45,
    10: 25,
    11: 26,
    12: 27,
    13: 28,
    14: 29,
    15: 30,
    16: 31,
    17: 32,
    18: 33,
    19: 34,
    20: 35,
    21: 37,
    22: 42,
    23: 43,
    24: 44,
    25: 47,
    26: 48,
    27: 49,
    28: 50,
    29: 105,
    30: 10,
    31: 11,
    32: 81,
    33: 75,
    34: 120,
    35: 19,
    36: 115,
    37: 124,
    38: 106,
    39: 123,
    40: 72,
    41: 71,
    42: 70,
    43: 93,
    44: 46,
    45: 55,
    46: 84,
    47: 66,
    48: 22
    }

StatCategoryNames = {0:'General',
                     1:'Quest',
                     2:'Combat',
                     3:'Magic',
                     4:'Crafting',
                     5:'Crime'}

def parse_misc_stats(data, size):
    misc_stats = defaultdict(list)
    count, = unpack('I', data.read(4))
    for n in range(count):
        name = parse_wstring(data)
        category, = unpack('B', data.read(1))
        value, = unpack('i', data.read(4))
        misc_stats[category].append((name, value))

    return misc_stats

def parse_player_loc(data, size):
    one, = unpack('I', data.read(4))
    two = parse_refid(data)
    three = unpack('4I', data.read(16))
    four = parse_refid(data)
    five, = unpack('I', data.read(4))
    return [one, two, three, four, five]

def parse_tes(data, size):
    with open('tes', 'wb') as f:
        f.write(data.read(size))
    return None

    print data.tell()
    list1 = parse_tes_list1(data)
    print list1
    print data.tell()
    list2 = list()
    list3 = list()
    count, = unpack('H', data.read(2))
    print data.tell()
    print "count 2 %r" % count
    for i in range(count):
        list2.append(parse_refid(data))
    print list2
    print data.tell()
    count = parse_vsval(data)
    for i in range(count):
        list3.append(parse_refid(data))
    print list3
    print data.tell()
    return list1, list2, list3

def parse_globals(data, size):
    print 'glob'
    with open('glob', 'wb') as f:
        f.write(data.read(size))
    return None

def parse_created(data, size):
    with open('created', 'wb') as f:
        f.write(data.read(size))
    return None

def parse_dummy(data, size, name):
    contents = data.read(size)
    with open(name, 'wb') as f:
        f.write(contents)
    return contens

GlobalDataTypeParsers = {0: ('Misc Stats', parse_misc_stats),
                         1: ('Player Location', parse_player_loc),
                         2: ('Tes', parse_dummy),
                         3: ('Global Variables', parse_dummy),
                         4: ('Created Objects', parse_dummy),
                         5: ('Effects', parse_dummy),
                         6: ('Weather', parse_dummy),
                         7: ('Audio', parse_dummy),
                         8: ('SkyCells', parse_dummy),
                         100: ('Process Lists', parse_dummy),
                         101: ('Combat', parse_dummy),
                         102: ('Interface', parse_dummy),
                         103: ('Actor Causes', parse_dummy),
                         104: ('Detection Manager', parse_dummy),
                         105: ('Location Metadata', parse_dummy),
                         106: ('Quest Static Data', parse_dummy),
                         107: ('StoryTeller', parse_dummy),
                         108: ('Magic Favouites', parse_dummy),
                         109: ('PlayerControls', parse_dummy),
                         110: ('Story Event Manager', parse_dummy),
                         111: ('Ingredient Shared', parse_dummy),
                         112: ('Menu Controls', parse_dummy),
                         113: ('MenuTopicManager', parse_dummy),
                         114: ('Unknown 114', parse_dummy),
                         1000: ('Temp Effects', parse_dummy),
                         1001: ('Papyrus', parse_dummy),
                         1002: ('Anim Objects', parse_dummy),
                         1003: ('Timer', parse_dummy),
                         1004: ('Synchronized Animations', parse_dummy),
                         1005: ('Main', parse_dummy),
}

def parse_refid(data):
    byte0, byte1, byte2 = unpack('BBB', data.read(3))
    #print "%d %d %d" % (byte0, byte1, byte2)
    flag = byte0 >> 6
    return flag, ((byte0 & 63) << 16) + (byte1 << 8) + byte2

def parse_vsval(data):
    byte0, = unpack('B', data.read(1))
    flag = byte0 & 3
    if flag == 0:
        return byte0 & 252
    elif flag == 1:
        byte1, = unpack('B', data.read(1))
        return ((byte0 & 252) << 8) + byte1
    elif flag == 2:
        byte1, byte2, byte3 = unpack('BBB', data.read(3))
        return ((byte0 & 252) << 32) + (byte1 << 16) + (byte2 << 8) + byte3

def parse_tes_list1(data):
    result = list()
    count = parse_vsval(data)
    for i in range(count):
        flag, refid = parse_refid(data)
        value, = unpack('H', data.read(2))
        result.append((flag, refid, value))
    return result

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


def parse_filetime(filehandle):
    t = unpack('II', filehandle.read(8))
    win_epoch = datetime.datetime(1601, 1, 1, 0, 0, 0)
    ts = (t[1] << 32)  |t[0]

    return win_epoch + datetime.timedelta(microseconds=ts/10)


def parse_systemtime(filehandle):
    t = unpack('8H', filehandle.read(16))
    print t
    return time_from_win_systemtime(list(t))

def write_b_or_bzstring(filehandle, s, z=False):
    # Write a string prefixed with a byte length and optionally terminated with a zero (\x00).
    if z:
        filehandle.write(pack('B', len(s)+1))
        filehandle.write(s+'\x00')
    else:
        filehandle.write(pack('B', len(s)))
        filehandle.write(s)


def parse_b_or_bzstring(filehandle, z=False):
    # A string prefixed with a byte length and optionally terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = filehandle.read(length)
    if z:
        return s[:-1]
    else:
        return s


def write_wstring(filehandle, s, z=False):
    # Write a string prefixed with a byte length and optionally terminated with a zero (\x00).
    if z:
        filehandle.write(pack('H', len(s)+1))
        filehandle.write(s+'\x00')
    else:
        filehandle.write(pack('H', len(s)))
        filehandle.write(s)


def parse_wstring(filehandle, z=False):
    # A string prefixed with a uint16 length and optionally terminated with a zero (\x00).
    length, = unpack('H', filehandle.read(2))
    s = filehandle.read(length)
    if z:
        return s[:-1]
    else:
        return s

def parse_screenshot(filehandle, write_to_file=None):
    width, height = unpack('II', filehandle.read(8))
    rgb_data = filehandle.read(3*width*height)
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
    flag, refId = parse_refid(filehandle)
    flags, = unpack('I', filehandle.read(4))
    rt, = unpack('B', filehandle.read(1))
    data_length_size = rt >> 6
    record_type = rt & 63

    version, = unpack('B', filehandle.read(1))
    if data_length_size == 0:
        datasize1, datasize2 = unpack('BB', filehandle.read(2))
    elif data_length_size == 1:
        datasize1, datasize2 = unpack('HH', filehandle.read(4))
    elif data_length_size == 2:
        datasize1, datasize2 = unpack('II', filehandle.read(8))

    data = filehandle.read(datasize1)

    return [refId, record_type, flags, version, datasize1, datasize2, data]

def parse_misc(data):
    print data

def parse_header(filehandle):
    size, = unpack('I', filehandle.read(4))
    version, saveNumber = unpack('II', filehandle.read(8))
    playerName = parse_wstring(filehandle)
    playerLevel, = unpack('I', filehandle.read(4))
    playerLocation = parse_wstring(filehandle)
    gameDate = parse_wstring(filehandle)
    playerRaceEditorId = parse_wstring(filehandle)
    unknown, = unpack('H', filehandle.read(2))
    unknowns = unpack('ff', filehandle.read(8))
    res = [version, saveNumber, playerName, playerLevel, playerLocation, gameDate, playerRaceEditorId]
    res.append(unknown)
    res.extend(list(unknowns))
    res.append(parse_filetime(filehandle))
    return res

def parse_file_location_table(filehandle):
    return FileLocationTable._make(list(unpack('25I', filehandle.read(25*4))))

def parse_global_data_item(filehandle):
    type, size = unpack('II', filehandle.read(8))
    #data = filehandle.read(size)
    #print type, size
    name, parser = GlobalDataTypeParsers[type]
    #with open(name, 'wb') as f:
    #    f.write(data)
    print name
    if type > 1:
        return name, parser(filehandle, size, name)
    else:
        return name, parser(filehandle, size)


def load(filename, imagename=None):
    with open(filename, 'rb') as essfile:
        magic = essfile.read(13)
        print magic
        headerpart = parse_header(essfile)
        screenshot = parse_screenshot(essfile, imagename)
        formVersion, = unpack('B', essfile.read(1))
        headerpart.extend([screenshot, formVersion])
        s = SaveGameHeader._make(headerpart)
        print s

        # Plugins
        plugins = list()
        pluginInfoSize, plugincount = unpack('IB', essfile.read(5))
        print plugincount

        for index in range(plugincount):
            plugins.append(parse_wstring(essfile))
        print plugins
        flt = parse_file_location_table(essfile)
        print "flt.globalDataTable1Count %r" % flt.globalDataTable1Count
        g1 = list()
        for c in range(flt.globalDataTable1Count):
            g1.append(parse_global_data_item(essfile))

        g2 = list()
        for c in range(flt.globalDataTable2Count):
            g2.append(parse_global_data_item(essfile))

        changeforms = list()
        print "flt.changeFormCount %r" % flt.changeFormCount
        for c in range(flt.changeFormCount):
            changeforms.append(parse_record(essfile))

        s = set([t[1] for t in changeforms])
        print [FormTypes[savegameform_to_form[f]][0] for f in sorted(s)]
        g3 = list()

        for c in range(flt.globalDataTable3Count+1): # +1 bugfix
            g3.append(parse_global_data_item(essfile))

        # formIds
        formIDArrayCount, = unpack('I', essfile.read(4))
        print formIDArrayCount
        formIDArray = unpack('%sI' % formIDArrayCount, essfile.read(4 * formIDArrayCount))
        print list(formIDArray)

        # unknown
        unknownCount, = unpack('I', essfile.read(4))
        print unknownCount
        unknownArray = unpack('%sI' % unknownCount, essfile.read(4 * unknownCount))
        print list(unknownArray)

        # unknown
        unknowntable3 = list()
        unknownBytes, = unpack('I', essfile.read(4))
        unknownCount, = unpack('I', essfile.read(4))
        print unknownBytes
        print unknownCount
        for c in range(unknownCount): # +1 bugfix
            unknowntable3.append(parse_wstring(essfile))
        print unknowntable3

    savegame = SaveGame._make([s, flt, plugins, g1, g2, changeforms, g3, formIDArray, unknownArray, unknowntable3])
    return savegame

def write(savegame, filename):
    with open(filename, 'wb') as essfile:
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
    savegame = load(options.essfile, options.image)
    if options.essfile2:
        savegame2 = load(options.essfile2, False)
        for x, y, field in zip(savegame.globals, savegame2.globals, Globals._fields):
            if x != y:
                print "%s: %s != %s" % (field, x, y)
                if field == 'globals':
                    subobj1 = savegame.globals.globals
                    subobj2 = savegame2.globals.globals
                    print subobj1
                    for key in subobj1.keys():
                        x,y = subobj1[key], subobj2[key]
                        if x != y:
                            print "%s: %s != %s" % (key, x, y)

        sys.exit(0)


    #print savegame.gameheader
    #print "%s plugins found" % len(savegame.plugins)
    if options.list_plugins:
        for p in sorted(savegame.plugins):
            print p

    #print "%s change records found" % len(savegame.records)

    if options.list_records:
        for r in savegame.records:
            print RecordTypeNames.get(r[1], '%r UKNOWN RECORD TYPE' % r[1])
    #print '-----------------------------------------------'

    if options.write_to:
        write(savegame, options.write_to)

    #print savegame.globals.pcLocation
    #print 'Done.'
    print savegame
