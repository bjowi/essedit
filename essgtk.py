#!/usr/bin/python

import array
from collections import defaultdict
import glob
import operator
import os
import time
import sys
from io import BytesIO

from gi.repository import Gtk

import cairo

import essedit5

class IdTreeIter(Gtk.TreeIter):
    def __init__(self):
        Gtk.TreeIter.__init__(self)
        self.liststore = None

class Handler:
    def __init__(self, builder):
        self.drawingarea = builder.get_object('drawingarea2')
        self.statusbar = builder.get_object('statusbar')

        self.savegames = dict()
        self.current_savegame = None
        self.current_surface = None

    def on_drawingarea_draw(self, drawingarea, context):
        self.draw_screenshot(drawingarea)

    def draw_screenshot(self, drawingarea):
        if not self.current_surface:
            return

        surface = self.current_surface
        width = surface.get_width()
        height = surface.get_height()
        drawingarea.set_size_request(width, height)
        ctx = drawingarea.get_window().cairo_create()
        ctx.set_source_surface(surface, 0,0)
        ctx.paint()

    def prepare_surface(self):
        width, height, rgb_data = self.current_savegame.gameheader.screenshot
        data = array.array('B', [0] * width * height * 4)

        for y in range(height):
            for x in range(width):
                offset = (x + (y * width)) * 4
                rgb_offset = (x + (y * width)) * 3
                alpha = 0

                data[offset+0] = rgb_data[rgb_offset+2]
                data[offset+1] = rgb_data[rgb_offset+1]
                data[offset+2] = rgb_data[rgb_offset+0]
                data[offset+3] = 0

        surface = cairo.ImageSurface.create_for_data(data,
                                                     cairo.FORMAT_RGB24,
                                                     width, height)
        return surface

    def show_details(self, selection):
        model, treeiter = selection.get_selected()
        filename = model[treeiter][3]
        if not filename:
            return

        self.current_savegame, self.current_surface = self.savegames.get(filename, (None, None))
        if not self.current_savegame:
            self.current_savegame = essedit5.load(filename)
            self.current_surface = self.prepare_surface()
            print(type(self.current_savegame))
            self.savegames[filename] = self.current_savegame, self.current_surface

        self.draw_screenshot(self.drawingarea)

    def on_destroy(self, *args):
        print(args)
        Gtk.main_quit(*args)


def get_files(path):
    files = glob.glob(os.path.join(path, '*.ess'))
    return sorted(files)


if __name__ == '__main__':
    builder = Gtk.Builder()
    builder.add_from_file("essgtk.glade")

    h = Handler(builder)
    builder.connect_signals(h)
    h.statusbar.push(h.statusbar.get_context_id('foo'), 'Loading...')
    t = time.time()

    items = defaultdict(list)
    treestore = builder.get_object('essfile_treestore')
    files = get_files('./ess5')
    for f in files:
        header = essedit5.get_header(f)
        character = header.playerName.decode(sys.stdout.encoding)
        items[character].append(dict(location=header.playerLocation.decode(sys.stdout.encoding),
                                     filename=f,
                                     saveNumber=header.saveNumber))

    for character, files in items.items():
        print(character)
        print(len(files))
        cv_node = treestore.append(None, [character, 0, '', ''])
        for savegame in sorted(files, key=operator.itemgetter('saveNumber')):
            file_node = treestore.append(cv_node, ['', savegame.get('saveNumber', -1),
                                                   savegame.get('location'),
                                                   savegame.get('filename')])
            #file_node.set_property('essfile', savegame.get('filename'))

    h.statusbar.push(h.statusbar.get_context_id('foo'),
                     'Loaded %s files in %.2f seconds.' % (len(files), time.time() - t))
    window = builder.get_object("window1")
    window.show_all()
    Gtk.main()
