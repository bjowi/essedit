import sys
from struct import unpack, pack, error
from essedit import parse_b_or_bzstring

class StringsFile(object):
    def __init__(self, filename):
        self.filename = filename
        filetype = filename.split('.')[-1]
        if filetype in ['DLSTRINGS', 'ILSTRINGS']:
            self.use_length_prefix = True
        elif filetype in ['STRINGS']:
            self.use_length_prefix = False
        else:
            print "Unknown filetype %r." % filetype

        self.id_to_offset = dict()
        self.id_to_string = dict()
        self.offset_to_string = dict()
        with open(self.filename, 'rb') as sf:
            self._read_offsets(sf)

            for id, offset in self.id_to_offset.iteritems():
                self.id_to_string[id] = self._read_string(sf, offset)

    def _read_offsets(self, sf):
        self.string_count, self.size = unpack('II', sf.read(8))

        for n in range(self.string_count):
            string_id, offset = unpack('II', sf.read(8))
            self.id_to_offset[string_id] = offset
        self.data_begin = sf.tell()


    def _read_string(self, sf, offset):
        sf.seek(self.data_begin + offset)
        if self.use_length_prefix:
            length, = unpack('I', sf.read(4))
            return sf.read(length-1)
        else:
            return parse_b_or_bzstring(sf)

def _parse_b_or_bzstring(filehandle, bz=False):
    # A string prefixed with a byte length and optionally terminated with a zero (\x00).
    length = unpack('B', filehandle.read(1))[0]
    s = filehandle.read(length)
    if bz:
        return s[:-1]
    else:
        return s

class StringStore(object):
    def __init__(self):
        self.strings = dict()
        self.ids = set()

    def load_file(self, filename):
        sf = StringsFile(filename)
        print filename
        self.strings.update(sf.id_to_string)
        print len(self.strings)
