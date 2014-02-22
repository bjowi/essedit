#!/usr/bin/env python

import argparse
from difflib import SequenceMatcher, context_diff
import datetime
from collections import defaultdict, namedtuple, OrderedDict
import logging
from struct import unpack, pack, error
import time
import os
import pprint
import io
import sys
from PIL import ImageFile
from PIL import Image

from stringtables import StringStore

log = logging


def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--essfile', required=True, dest='essfile', type=str)
    parser.add_argument('-g', '--essfile2', dest='essfile2', type=str)
    parser.add_argument('-s', '--stringsfile', dest='stringsfile', type=str, nargs='*')
    parser.add_argument('-i', '--image', dest='image', type=str)
    parser.add_argument('-p', '--list_plugins', dest='list_plugins', action='store_true')
    parser.add_argument('-r', '--list_records', dest='list_records', type=str)
    parser.add_argument('-w', '--write_to', dest='write_to', type=str)
    parser.add_argument('--header-only', dest='header_only', action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', action='count')
    return parser.parse_args()

def enum(**nums):
    res = namedtuple('Enum', list(nums.keys()))
    return res(*list(nums.values())), dict((v,k) for k, v in list(nums.items()))

SaveGame = namedtuple('SaveGame', 'gameheader filelocations plugins g1 g2 changeforms g3 formIDArray visitedWorldspaceArrayCount visitedWorldspaceArray unknownBytes')
SaveGameHeader = namedtuple('SaveGameHeader', 'magic headerSize version saveNumber playerName playerLevel playerLocation gameDate playerRaceEditorId playerSex playerCurExp playerLvlUpExp filetime screenshot formVersion pluginInfoSize plugincount')
FileLocationTable = namedtuple('FileLocationTable', 'formIDArrayOffset unknownTable3Offset globalDataTable1Offset globalDataTable2Offset changeFormsOffset globalDataTable3Offset globalDataTable1Count globalDataTable2Count globalDataTable3Count changeFormCount unused1 unused2 unused3 unused4 unused5 unused6 unused7 unused8 unused9 unused10 unused11 unused12 unused13 unused14 unused15')
Globals1 = namedtuple('Globals1', 'misc_stats player_location tes global_variables created_objects effects weater audio skycells')
PCLocation = namedtuple('PCLocation', 'cell x y z')
Record = namedtuple('Record', 'formid changeflags type version length1 length2 data')

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

form_to_savegameform = {v:k for k,v in list(savegameform_to_form.items())}

StatCategoryNames = {0:'General',
                     1:'Quest',
                     2:'Combat',
                     3:'Magic',
                     4:'Crafting',
                     5:'Crime'}

def parse_misc_stats(data, size, name):
    misc_stats = defaultdict(list)
    count, = unpack('I', data.read(4))

    for n in range(count):
        name = parse_wstring(data)
        category, = unpack('B', data.read(1))
        value, = unpack('i', data.read(4))
        misc_stats[StatCategoryNames.get(category, 'Unknown')].append((name, value))
    return dict(misc_stats)

def write_misc_stats(filehandle, misc_stats):
    length = sum([len(l) for l in list(misc_stats.values())])
    filehandle.write(pack('I', length))
    for category, values in list(misc_stats.items()):
        for name, value in values:
            write_wstring(filehandle, name)
            filehandle.write(pack('B', category))
            filehandle.write(pack('i', value))

    return True

def parse_player_loc_old(data, size, name):
    one, = unpack('I', data.read(4))
    two = parse_refid(data)
    three = unpack('4I', data.read(16))
    four = parse_refid(data)
    five, = unpack('I', data.read(4))
    return [one, two, three, four, five]

def write_player_loc_old(filehandle, loc):
    filehandle.write(pack('I', loc[0]))
    write_refid(filehandle, loc[1])
    filehandle.write(pack('II', *loc[2]))
    write_refid(filehandle, loc[3])
    filehandle.write(pack('I', loc[4]))
    return True

def parse_player_loc(data, size, name):
    nextObjectId, = unpack('I', data.read(4))
    worldSpace1 = parse_refid(data)
    cx, cy = unpack('II', data.read(8))
    worldSpace2 = parse_refid(data)
    x, y, z = unpack('fff', data.read(12))
    unknown2, = unpack('B', data.read(1))
    return [nextObjectId, worldSpace1, cx, cy, worldSpace2, x, y, z, unknown2]

def write_player_loc(filehandle, loc):
    filehandle.write(pack('I', loc[0]))
    write_refid(filehandle, loc[1])
    filehandle.write(pack('II', *loc[2]))
    write_refid(filehandle, loc[3])
    filehandle.write(pack('I', loc[4]))
    return True

def parse_tes(filehandle, size, name):
    #data = io.BytesIO(filehandle.read(size))
    #parse_dummy(filehandle, size, name, True)
    begin = filehandle.tell()
    data = filehandle
    list1 = parse_tes_list1(data)
    list2 = list()
    list3 = list()
    #count = parse_vsval(data)
    count, = unpack('I', data.read(4))
    print(("second count %r" % count))
    for i in range(count):
        refid = parse_refid(data)
        list2.append(refid)
        print((filehandle.tell()))
    count = parse_vsval(data)
    print(("third count %r" % count))

    for i in range(count):
        list3.append(parse_refid(data))
    print(("parse tes %r %r %r" % (len(list1), len(list2), len(list3))))
    end = filehandle.tell()
    extra_len = (end-begin) - size
    print(("parsed %s of %s bytes %r" % (end-begin, size, extra_len)))
    if -extra_len > 0:
        extra = data.read(-extra_len)
        with open('dump/' + 'tes_extra', 'wb') as f:
            f.write(extra)

    return list1, list2, list3

def write_tes(filehandle, tes):
    print(("tes %r" % tes))
    write_vsval(filehandle, len(tes[0]))
    for item in tes[0]:
        refid, u = item
        write_refid(filehandle, refid)
        filehandle.write(pack('H', u))

    filehandle.write(pack('I', len(tes[1])))
    for refid in tes[1]:
        write_refid(filehandle, refid)

    write_vsval(filehandle, len(tes[2]))
    for refid in tes[2]:
        write_refid(filehandle, refid)


def parse_globals(data, size, name):
    result = OrderedDict()
    count = parse_vsval(data)
    log.debug("globals count: {}".format(count))
    #sys.exit(8)
    for g in range(count):
        refid = parse_refid(data)
        value, = unpack('f', data.read(4))
        result[refid] = value
        print(refid, value)
    return result


def write_globals(filehandle, global_data):
    write_vsval(filehandle, len(global_data))
    for refid, value in list(global_data.items()):
        write_refid(filehandle, refid)
        filehandle.write(pack('f', value))


def parse_refid_list(data):
    count = parse_vsval(data)
    print("c", count)
    result = list()
    for c in range(count):
        value = parse_refid(data)
        result.append(value)

    return result


def parse_effects(data, size, name):
    count = parse_vsval(data)
    effects = list()
    for i in range(count):
        strength, timestamp, unknown = unpack('ffI', data.read(12))
        refid = parse_refid(data)
        effects.append((strength, timestamp, unknown, refid))

    unknown1, unknown2 = unpack('ff', data.read(8))
    return [effects, unknown1, unknown2]


def parse_weather(data, size, name):
    climate = parse_refid(data)
    weather = parse_refid(data)
    prev_weather = parse_refid(data)
    unk1_weather = parse_refid(data)
    unk2_weather = parse_refid(data)
    unk3_weather = parse_refid(data)

    curtime, begtime, weather_pct = unpack('fff', data.read(12))
    unknowns = unpack('6I', data.read(24))
    print(unknowns)
    more_unknowns = unpack('fI', data.read(8))
    print(more_unknowns)
    flags, = unpack('B', data.read(1))
    print(flags)
    # possibly more, depending on flags
    return [climate, weather, prev_weather,
            unk1_weather, unk2_weather, unk3_weather,
            curtime, begtime, weather_pct,
            unknowns, more_unknowns]

def parse_audio(data, size, name):
    unknown = parse_refid(data)
    tracks = parse_refid_list(data)
    bgm = parse_refid(data)
    return [unknown, tracks, bgm]

def parse_skycells(data, size, name):
    count = parse_vsval(data)
    cells = list()
    for i in range(count):
        cell1 = parse_refid(data)
        cell2 = parse_refid(data)
        cells.append((cell1, cell2))

    return cells


def parse_interface(data, size, name):
    shownHelpMsgCount, = unpack('I', data.read(4))
    print(shownHelpMsgCount)
    shownHelpMsgs = list()
    for c in range(shownHelpMsgCount):
        shownHelpMsg, = unpack('I', data.read(4))
        shownHelpMsgs.append(shownHelpMsg)

    unknown0, = unpack('B', data.read(1))
    print(shownHelpMsgs)
    print("unknown0", unknown0)
    lastUsedWeapons = parse_refid_list(data)
    lastUsedSpells = parse_refid_list(data)
    lastUsedShouts = parse_refid_list(data)

    unknown1, = unpack('B', data.read(1))

    count1 = parse_vsval(data)
    print(count1)
    sl1 = list()
    for i in range(count1):
        us1 = parse_wstring(data)
        us2 = parse_wstring(data)
        unknown_ints = unpack('4I', data.read(16))
        sl1.append((us1, us2, unknown_ints))

    count2 = parse_vsval(data)
    print(count2)
    sl2 = list()
    for i in range(count2):
        us3 = parse_wstring(data)
        sl2.append(us3)

    unknown3, = unpack('I', data.read(4))
    return [shownHelpMsgs, unknown0, lastUsedWeapons, lastUsedSpells, lastUsedShouts, unknown1, sl1, sl2, unknown3]


def parse_dummy(data, size, name, dump=True):
    contents = data.read(size)
    if dump:
        with open('dump/' + name, 'wb') as f:
            f.write(contents)
    return contents


def write_dummy(filehandle, data):
    filehandle.write(data)
    return True

GlobalDataTypeParsers = {0: ('Misc Stats', parse_misc_stats, write_misc_stats),
                         1: ('Player Location', parse_player_loc, write_player_loc),
                         2: ('Tes', parse_dummy, write_dummy),
                         3: ('Global Variables', parse_dummy, write_dummy),
                         4: ('Created Objects', parse_dummy, write_dummy),
                         5: ('Effects', parse_dummy, write_dummy),
                         6: ('Weather', parse_dummy, write_dummy),
                         7: ('Audio', parse_dummy, write_dummy),
                         8: ('SkyCells', parse_dummy, write_dummy),
                         100: ('Process Lists', parse_dummy, write_dummy),
                         101: ('Combat', parse_dummy, write_dummy),
                         102: ('Interface', parse_dummy, write_dummy),
                         103: ('Actor Causes', parse_dummy, write_dummy),
                         104: ('Unknown 104', parse_dummy, write_dummy),
                         105: ('Detection Manager', parse_dummy, write_dummy),
                         106: ('Location Metadata', parse_dummy, write_dummy),
                         107: ('Quest Static Data', parse_dummy, write_dummy),
                         108: ('StoryTeller', parse_dummy, write_dummy),
                         109: ('Magic Favouites', parse_dummy, write_dummy),
                         110: ('PlayerControls', parse_dummy, write_dummy),
                         111: ('Story Event Manager', parse_dummy, write_dummy),
                         112: ('Ingredient Shared', parse_dummy, write_dummy),
                         113: ('Menu Controls', parse_dummy, write_dummy),
                         114: ('MenuTopicManager', parse_dummy, write_dummy),
                         1000: ('Temp Effects', parse_dummy, write_dummy),
                         1001: ('Papyrus', parse_dummy, write_dummy),
                         1002: ('Anim Objects', parse_dummy, write_dummy),
                         1003: ('Timer', parse_dummy, write_dummy),
                         1004: ('Synchronized Animations', parse_dummy, write_dummy),
                         1005: ('Main', parse_dummy, write_dummy),
                         }

GlobalDataTypeParsers_pre9 = GlobalDataTypeParsers.copy()
GlobalDataTypeParsers_pre9[1] = ('Player Location', parse_player_loc_old, write_player_loc_old)

def parse_refid(data):
    byte0, byte1, byte2 = unpack('BBB', data.read(3))
    flag = byte0 >> 6
    assert(flag >= 0)
    assert(flag <= 3)
    value = ((byte0 & 63) << 16) + (byte1 << 8) + byte2
    return flag, ((byte0 & 63) << 16) + (byte1 << 8) + byte2


def write_refid(filehandle, refid):
    flag, value = refid
    byte0 = (value >> 16) + (flag << 6)
    byte1 = (value & 0xff00) >> 8
    byte2 = value & 0xff
    filehandle.write(pack('BBB', byte0, byte1, byte2))
    return True

def parse_vsval(data):
    r = parse_vsval_r(data)
    print(("vsval: %r" % r))
    return r

def parse_vsval_r(data):
    print(("vsval tell: %r" % data.tell()))
    byte0, = unpack('B', data.read(1))
    flag = byte0 & 3
    print(("vsval type: %r" % flag))
    print(("vsval byte0: %r" % bin(byte0)))
    data.seek(-1, os.SEEK_CUR)
    if flag == 0:
        #return (unpack('B', data.read(1))[0]) >> 2
        byte0, = unpack('B', data.read(1))
        return byte0 >> 2
    elif flag == 1:
        #return unpack('H', data.read(2))[0] >> 2
        byte0, byte1 = unpack('BB', data.read(2))
        #byte1, = unpack('B', data.read(1))
        print(("vsval byte0: %r" % byte0))
        print(("vsval byte1: %r" % byte1))
        print(((byte1 << 8) + byte0) >> 2)
        return ((byte1 << 8) + byte0) >> 2
    elif flag == 2:
        #return unpack('I', data.read(4))[0] >> 2
        byte1, byte2, byte3 = unpack('BBB', data.read(3))
        print(("vsval byte2: %r" % byte2))
        print(("vsval byte3: %r" % byte3))
        return ((byte3 << 24) + (byte2 << 16) + (byte1 << 8) + byte0) >> 2
        #return ((byte0 >> 2) << 24) + (byte1 << 16) + (byte2 << 8) + byte3
    else:
        print("error in parse_vsval")
        sys.exit(8)

def write_vsval(filehandle, value):
    if value < 0x40:
        filehandle.write(pack('B', (value << 2) & 0b11111100))
    elif value < 0x4000:
        byte0 = ((value << 2) & 0b11111100) + 1
        filehandle.write(pack('B', byte0))
        byte1 = (0xff & (value >> 6))
        filehandle.write(pack('B', byte1))

    elif value < 0x40000000:
        filehandle.write(pack('B', (0xff & ((value << 2) + 2))))
        filehandle.write(pack('B', (0xff & (value >> 6))))
        filehandle.write(pack('B', (0xff & (value >> 14))))
        filehandle.write(pack('B', (0xff & (value >> 22))))


def parse_tes_list1(data):
    result = list()
    count = parse_vsval(data)
    print(("first count %r" % count))
    for i in range(count):
        refid = parse_refid(data)
        value, = unpack('H', data.read(2))
        result.append((refid, value))
        print(refid)
        print(value)

    return result


def parse_filetime(filehandle):
    t = unpack('II', filehandle.read(8))
    win_epoch = datetime.datetime(1601, 1, 1, 0, 0, 0)
    ts = (t[1] << 32) | t[0]

    return win_epoch + datetime.timedelta(microseconds=ts/10)


def write_filetime(filehandle, dt):
    ticks = time.mktime(dt.timetuple())
    win_epoch = datetime.datetime(1601, 1, 1, 0, 0, 0)
    unix_epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
    dt += (unix_epoch - win_epoch)
    win_ticks = int(time.mktime(dt.timetuple())) * 10000000
    filehandle.write(pack('II', dt.microsecond * 10, (win_ticks >> 32)))


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
    if write_to_file:
        im = Image.frombuffer('RGB', (width, height), rgb_data, 'raw', 'RGB', 0, 1)
        im.save(write_to_file)
    return width, height, rgb_data


def parse_record(filehandle):
    refId = parse_refid(filehandle)
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
    else:
        raise Exception("Strange datasize: %r" % data_length_size)

    data = filehandle.read(datasize1)

    return Record._make([refId, flags, savegameform_to_form[record_type], version, datasize1, datasize2, data])


def write_record(filehandle, record):
    write_refid(filehandle, record.formid)
    filehandle.write(pack('I', record.changeflags))

    # Handle compressed data like this for now
    if record.length2 > 0:
        datasize = record.length2
    else:
        datasize = len(record.data)

    size_bits = 0
    if datasize > 0xff:
        size_bits = 1
    elif datasize > 0xffff:
        size_bits = 2

    # Now the size_bits are calculated, reset to proper size
    datasize = len(record.data)

    record_type = (size_bits << 6) + form_to_savegameform[record.type]
    filehandle.write(pack('B', record_type))
    filehandle.write(pack('B', record.version))
    if size_bits == 0:
        filehandle.write(pack('BB', datasize, record.length2))
    elif size_bits == 1:
        filehandle.write(pack('HH', datasize, record.length2))
    elif size_bits == 2:
        filehandle.write(pack('II', datasize, record.length2))

    filehandle.write(record.data)

    return True


def parse_header(filehandle):
    magic = filehandle.read(13)
    size, = unpack('I', filehandle.read(4))
    version, saveNumber = unpack('II', filehandle.read(8))
    playerName = parse_wstring(filehandle)
    playerLevel, = unpack('I', filehandle.read(4))
    playerLocation = parse_wstring(filehandle)
    gameDate = parse_wstring(filehandle)
    playerRaceEditorId = parse_wstring(filehandle)
    unknown, = unpack('H', filehandle.read(2))
    unknowns = unpack('ff', filehandle.read(8))
    res = [magic, size, version, saveNumber, playerName, playerLevel, playerLocation, gameDate, playerRaceEditorId]
    res.append(unknown)
    res.extend(list(unknowns))
    res.append(parse_filetime(filehandle))
    return res

def parse_file_location_table(filehandle):
    return FileLocationTable._make(list(unpack('25I', filehandle.read(25*4))))

def parse_global_data_item(filehandle, version):
    type, size = unpack('II', filehandle.read(8))
    #data = filehandle.read(size)
    if version < 9:
        parsers = GlobalDataTypeParsers_pre9
    else:
        parsers = GlobalDataTypeParsers

    try:
        name, parser, _ = parsers[type]
        print('Global data of type {}, size {} using parser {}'.format(type, size, name))
    except KeyError as unknown_type:
        name, parser = 'Unknown GlobalDataType {0}'.format(unknown_type), parse_dummy
    #with open(name, 'wb') as f:
    #    f.write(data)
    return name, (size, type, parser(filehandle, size, name))


def write_global_data_item(filehandle, name, item):
    size, type, data = item
    filehandle.write(pack('I', type))
    filehandle.write(pack('I', size))
    name, _, writer = GlobalDataTypeParsers[type]
    return writer(filehandle, data)


def get_header(filename, imagename=None):
    with open(filename, 'rb') as essfile:
        headerpart = parse_header(essfile)
        screenshot = parse_screenshot(essfile, imagename)
        formVersion, = unpack('B', essfile.read(1))
        headerpart.extend([screenshot, formVersion])

        # Plugins
        plugins = list()
        pluginInfoSize, plugincount = unpack('IB', essfile.read(5))
        headerpart.extend([pluginInfoSize, plugincount])
        header = SaveGameHeader._make(headerpart)
        return header

def load(filename, imagename=None):
    print("Opening '{0}'".format(filename))
    with open(filename, 'rb') as essfile:
        headerpart = parse_header(essfile)
        print(headerpart)
        screenshot = parse_screenshot(essfile, imagename)
        formVersion, = unpack('B', essfile.read(1))
        headerpart.extend([screenshot, formVersion])

        # Plugins
        plugins = list()
        pluginInfoSize, plugincount = unpack('IB', essfile.read(5))
        headerpart.extend([pluginInfoSize, plugincount])
        header = SaveGameHeader._make(headerpart)

        for index in range(plugincount):
            plugins.append(parse_wstring(essfile))

        flt = parse_file_location_table(essfile)
        print(flt)
        g1 = OrderedDict()
        for c in range(flt.globalDataTable1Count):
            key, item = parse_global_data_item(essfile, header.version)
            g1[key] = item
        g2 = OrderedDict()
        for c in range(flt.globalDataTable2Count):
            key, item = parse_global_data_item(essfile, header.version)
            g2[key] = item

        changeforms = list()
        for c in range(flt.changeFormCount):
            r = parse_record(essfile)
            changeforms.append(r)

        g3 = OrderedDict()
        for c in range(flt.globalDataTable3Count+1): # +1 bugfix
            key, item = parse_global_data_item(essfile, header.version)
            g3[key] = item

        # formIds
        formIDArrayCount, = unpack('I', essfile.read(4))
        formIDArray = unpack('%sI' % formIDArrayCount, essfile.read(4 * formIDArrayCount))

        # unknown
        unknownCount, = unpack('I', essfile.read(4))
        unknownArray = unpack('%sI' % unknownCount, essfile.read(4 * unknownCount))

        # unknown
        unknowntable3 = list()
        unknownBytes, = unpack('I', essfile.read(4))
        unknownCount, = unpack('I', essfile.read(4))
        for c in range(unknownCount): # +1 bugfix
            unknowntable3.append(parse_wstring(essfile))


    savegame = SaveGame._make([header, flt, plugins, g1, g2, changeforms, g3, formIDArray, unknownArray, unknowntable3, unknownBytes])
    return savegame

def write(savegame, filename):
    with open(filename, 'wb') as essfile:
        # Gameheader
        essfile.write(savegame.gameheader.magic)
        essfile.write(pack('III', savegame.gameheader.headerSize,
                           savegame.gameheader.version, savegame.gameheader.saveNumber))
        write_wstring(essfile, savegame.gameheader.playerName)
        essfile.write(pack('I', savegame.gameheader.playerLevel))
        write_wstring(essfile, savegame.gameheader.playerLocation)
        write_wstring(essfile, savegame.gameheader.gameDate)
        write_wstring(essfile, savegame.gameheader.playerRaceEditorId)
        essfile.write(pack('H', savegame.gameheader.unknown1))
        essfile.write(pack('ff', savegame.gameheader.unknown2, savegame.gameheader.unknown3))
        write_filetime(essfile, savegame.gameheader.filetime)

        im = savegame.gameheader.screenshot
        w, h = im.size
        essfile.write(pack('II', w, h))
        essfile.write(im.tostring())
        essfile.write(pack('B', savegame.gameheader.formVersion))

        # Plugins
        essfile.write(pack('IB', savegame.gameheader.pluginInfoSize, len(savegame.plugins)))
        for plugin in savegame.plugins:
            write_wstring(essfile, plugin)

        essfile.write(pack('25I', *(list(savegame.filelocations._asdict().values()))))

        for key, item in list(savegame.g1.items()):
            write_global_data_item(essfile, key, item)

        for key, item in list(savegame.g2.items()):
            write_global_data_item(essfile, key, item)

        for record in savegame.changeforms:
            write_record(essfile, record)

        for key, item in list(savegame.g3.items()):
            write_global_data_item(essfile, key, item)

        essfile.write(pack('I', len(savegame.formIDArray)))
        essfile.write(pack('%sI' % len(savegame.formIDArray), *(savegame.formIDArray)))
        essfile.write(pack('I', len(savegame.unknown2)))
        essfile.write(pack('%sI' % len(savegame.unknown2), *(savegame.unknown2)))

        essfile.write(pack('I', savegame.unknownBytes))
        essfile.write(pack('I', len(savegame.unknown3)))
        for entry in savegame.unknown3:
            write_wstring(essfile, entry)

def diff_dict(d1, d2):
    commonkeys = set(d1.keys())
    commonkeys.intersection_update(list(d2.keys()))
    d1only = set(d1).difference(set(d2))
    d2only = set(d2).difference(set(d1))
    for key in commonkeys:
        if d1[key] != d2[key]:
            print(('%r' %  (key,)))
            diff_item(d1[key], d2[key])

    if d1only:
        print(("Only in first: %r" % {k:d1[k] for k in d1only}))
    if d2only:
        print(("Only in second: %r" % {k:d2[k] for k in d2only}))

def dictify_namedtuple(d):
    if not isinstance(d, dict):
        return d._asdict()
    else:
        return d

def diff_namedtuple(t1, t2):
    for x, y, field in zip(t1, t2, t1._fields):
        if x != y:
            print(field)
            diff_item(x, y)
            print()

def diff_item(x, y):
    if isinstance(x, tuple):
        if hasattr(x, '_fields'):
            diff_namedtuple(x, y)
        else:
            diff_sequence(x, y)
    elif isinstance(x, dict):
        diff_dict(x, y)
    elif isinstance(x, list):
        diff_sequence(x, y)
    elif isinstance(x, str):
        diff_string(x, y)
    else:
        print(("%r != %r" % (x, y)))

def diff_string(s1, s2):
    print(('len %s' % len(s1)))
    if len(s1) > 1000000:
        print('too long')
    else:
        s = SequenceMatcher(None, s1, s2)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag != 'equal':
                print(("%7s a[%d:%d] (%s) b[%d:%d] (%s)" %
                       (tag, i1, i2, s1[i1:i2], j1, j2, s2[j1:j2])))


def diff_sequence(s1, s2):
    for i1, i2 in zip(s1, s2):
        if i1 != i2:
            diff_item(i1, i2)

if __name__ == '__main__':
#    with open('Tes') as f:
#        res = parse_tes(f, 1312, 'tt')
#        print res
#        write_tes(f, res)
#    sys.exit(8)

    options = get_options()

    loglevel = logging.INFO
    if options.verbose:
        loglevel = logging.DEBUG

    logging.basicConfig(stream=sys.stderr, level=loglevel)

    log.info(options.verbose)
    if options.stringsfile:
        strings = StringStore()
        for f in options.stringsfile:
            strings.load_file(f)

        sys.exit(9)

    if options.header_only:
        print((get_header(options.essfile)))
        sys.exit(0)

    savegame = load(options.essfile, options.image)
    #print((savegame.gameheader))
    if options.essfile2:
        savegame2 = load(options.essfile2, False)
        diff_item(savegame, savegame2)

        sys.exit(0)

    print(("%s plugins found" % len(savegame.plugins)))
    if options.list_plugins:
        for p in sorted(savegame.plugins):
            print(p)

    print(("%s change records found" % len(savegame.changeforms)))
    #print((sorted(set([FormTypes[r.type][0] for r in savegame.changeforms]))))

    if options.list_records:
        for r in savegame.changeforms:
            if FormTypes[r.type][0] == options.list_records:
                print(r)
                with open(options.list_records, 'wb') as f:
                    f.write(r.data)

                print((parse_record(io.StringIO(r.data))))
    #print '-----------------------------------------------'

    if options.write_to:
        print((savegame.gameheader.filetime))
        write(savegame, options.write_to)

    #log.info('BLUU {} {:X}'.format(size, nextObjectId))
    #print 'Done.'
    print((savegame.g1.get('Player Location')))

    if options.verbose:
        pprint.pprint((savegame.g1.get('Misc Stats')))

    if options.verbose:
        pprint.pprint(savegame.g1)
