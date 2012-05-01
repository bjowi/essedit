#!/usr/bin/env python

import argparse
from collections import defaultdict, namedtuple, OrderedDict
import os
from struct import unpack, pack, error
from StringIO import StringIO


BSAHeader = namedtuple('BSAHeader', 'file_id , version, offset, archive_flags, folder_count, file_count, total_folder_name_length, total_file_name_length, file_flags')
#, folder_records, file_record_blocks, file_name_block, files')
Folder = namedtuple('Folder', 'name, name_hash, count, offset, files')
File = namedtuple('File', 'name, name_hash, size, offset')


def get_options():
    parser = argparse.ArgumentParser(description='ff')
    parser.add_argument('-f', '--bsafile', dest='bsafile', type=str)
    parser.add_argument('-w', '--write_to', dest='write_to', type=str)
    return parser.parse_args()

def parse_header(bsafile):
    res = list()
    res.append(bsafile.read(4)) # file_id
    res.append(unpack('I', bsafile.read(4))[0]) # version
    res.append(unpack('I', bsafile.read(4))[0]) # offset
    res.append(unpack('I', bsafile.read(4))[0]) # archive_flags
    res.append(unpack('I', bsafile.read(4))[0]) # folder_count
    res.append(unpack('I', bsafile.read(4))[0]) # file_count
    res.append(unpack('I', bsafile.read(4))[0]) # total_folder_name_length
    res.append(unpack('I', bsafile.read(4))[0]) # total_file_name_length
    res.append(unpack('I', bsafile.read(4))[0]) # file_flags
    header = BSAHeader._make(res)
    return header

def load(filename):
    with open(filename, 'rb') as bsafile:
        header = parse_header(bsafile)
        folders = dict()
        file_names = dict()
        files = dict()
        for folder in range(header.folder_count):
            name_hash, count, offset = unpack('QII', bsafile.read(16))
            folders[name_hash] = Folder._make(['', name_hash, count, offset, list()])

        for c in range(header.folder_count):
            folder_name = parse_b_or_bzstring(bsafile, True)
            folder_hash = tesHash(folder_name)

            file_list = list()

            for c in range(folders[folder_hash].count):
                name_hash, size, offset = unpack('QII', bsafile.read(16))
                f = ['', name_hash, size, offset]
                files[name_hash] = f
                file_list.append(name_hash)

            folders[folder_hash] = folders[folder_hash]._replace(name=folder_name, files=file_list)

        filenames = bsafile.read(header.total_file_name_length).split('\0')[:-1]

        for filename in filenames:
            file_names[tesHash(filename, True)] = filename

        for h, f in files.iteritems():
            f[0] = file_names[h]
            files[h] = File._make(f)

        for h, d in folders.iteritems():
            file_list = list()
            for file_hash in d.files:
                file_list.append(files[file_hash])

            folders[h] = d._replace(files=file_list)

        return header, folders


def parse_b_or_bzstring(filehandle, bz=False):
    # A string prefixed with a byte length and optionally terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = filehandle.read(length)
    if bz:
        return s[:-1]
    else:
        return s

def tesHash(fileName, use_ext=False):
    """Returns tes4's two hash values for filename.
    Based on TimeSlips code with cleanup and pythonization."""
    if use_ext:
        root, ext = os.path.splitext(fileName.lower()) #--"bob.dds" >> root = "bob", ext = ".dds"
    else:
        root = fileName
        ext = ''

    #--Hash1
    chars = map(ord, root) #--'bob' >> chars = [98,11,98]
    if len(chars) > 2:
        bchar = chars[-2]
    else:
        bchar = 0
    hash1 = chars[-1] | bchar << 8 | len(chars) << 16 | chars[0] << 24

    if   ext == '.kf':  hash1 |= 0x80
    elif ext == '.nif': hash1 |= 0x8000
    elif ext == '.dds': hash1 |= 0x8080
    elif ext == '.wav': hash1 |= 0x80000000
    #--Hash2
    #--Python integers have no upper limit. Use uintMask to restrict these to 32 bits.
    uintMask, hash2, hash3 = 0xFFFFFFFF, 0, 0
    for char in chars[1:-2]: #--Slice of the chars array
        hash2 = ((hash2 * 0x1003f) + char ) & uintMask
    for char in map(ord,ext):
        hash3 = ((hash3 * 0x1003F) + char ) & uintMask
    hash2 = (hash2 + hash3) & uintMask
    #--Done
    return (hash2 << 32) + hash1 #--Return as uint64


if __name__ == '__main__':
    options = get_options()
    header, folders = load(options.bsafile)

    for k, d in folders.iteritems():
        print d.name
        for f in d.files:
            print f
        print

    print 'Done.'


