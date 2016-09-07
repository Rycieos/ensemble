#!/usr/bin/env python

import argparse
import codecs
import ntpath
import os
import posixpath
import time

def main(args = None):
    parser = argparse.ArgumentParser(description='Update universal playlist library')
    parser.add_argument('--daemon', '-D', action='store_true', help='run as daemon')
    parser.add_argument('--debug', '-x', action='store_true', help='print debugging info')
    parser.add_argument('--location', '-l', action='store', default=os.getcwd(),
                        help='playlists location (default: current directory)')
    parser.add_argument('-t', action='store', default=60,
                        help='time between updates in daemon mode (default 60)')
    args = parser.parse_args(args)

    try:
        en = Ensemble(args.location, args.debug)
    except IOError:
        print("Config file not found!")
        os._exit(1)

    if args.debug:
        print("Config file dump:")
        print("OSs': {0}".format(en.oss))
        print("Types: {0}".format(en.types))

    en.make_formats()

    if args.daemon:
        while True:
            en.update()
            time.sleep(float(args.t))
    else:
        en.update()

class Ensemble:
    def __init__(self, location, debug=False):
        self.raw_dir = os.path.join(location, "local")
        self.debug = debug
        self.location = location

        with open(os.path.join(location, "ensemble.config")) as config:
            exec(config.read(), globals(), globals())

        self.oss = oss
        self.types = types
        self.local_prefix = local_prefix

    def make_formats(self):
        if not os.path.exists(self.raw_dir):
            os.makedirs(self.raw_dir)
        for os_ in self.oss:
            for type_ in self.types:
                format_ = os_ + "_" + type_
                if self.debug:
                    print("Playlist format discovered: {0}".format(format_))
                dest = os.path.join(self.location, format_)
                if not os.path.exists(dest):
                    if self.debug:
                        print("Making directory {0}".format(dest))
                    os.makedirs(dest)

    def update(self):
        for os_ in self.oss:
            for type_ in self.types:
                dest = os.path.join(self.location, os_ + "_" + type_)

                for fn in os.listdir(dest):
                    name, ext = os.path.splitext(fn)
                    ext = ext[1:]

                    # Check if this file is the type that should be here
                    if ext != type_:
                        if self.debug:
                            print("Found file {0} with wrong extension".format(fn))
                            print("Had: {0}, should be: {1}".format(ext, type_))
                        continue

                    if os.path.isfile(os.path.join(self.raw_dir, name)):
                        # Have playlist, check it
                        if self.needs_update(dest, fn):
                            self.update_playlist(os_, dest, fn)
                    else:
                        # Don't have, create it
                        self.update_playlist(os_, dest, fn)

    def needs_update(self, dest, playlist):
        name = os.path.splitext(playlist)[0]
        return os.path.getmtime(os.path.join(dest, playlist)) \
                   > os.path.getmtime(os.path.join(self.raw_dir, name))

    def update_playlist(self, os_, dest, playlist):
        name, ext = os.path.splitext(playlist)
        ext = ext[1:]
        print("Updating playlist {0}".format(name))
        raw_file = os.path.join(self.raw_dir, name)

        # Copy new playlist to raw
        os_type, prefix = self.oss[os_]
        inf = open(os.path.join(dest, playlist), "r")
        outf = open(raw_file, "w")

        for line in inf:
            if self.debug:
                print(repr(line))

            # Strip newline and UTF-8 BOM
            line = line.strip()
            if line.startswith(str(codecs.BOM_UTF8)):
                line = line[3:]

            if self.debug:
                print("Input line: {0}".format(line))
                print("Prefix line: {0}".format(prefix))

            # Skip comment lines (for m3u extended)
            if line.startswith("#"):
                continue

            if ext == "pls":
                # Check for pls header
                if not line.startswith("File"):
                    if self.debug:
                        print("Skipping non-file line")
                    continue
                # Remove pls File number
                line = line[(line.index('=') + 1):]
                if self.debug:
                    print("After stripping pls: {0}".format(line))

            # Strip os prefix
            if line.startswith(prefix):
                line = line[len(prefix):]
            else:
                print("Skipping file: '{0}', does not have valid prefix".format(line))
                if self.debug:
                    print(repr(line))
                continue

            # Convert backslashes to local
            if os_type == "win":
                line = os.path.join(*line.split('\\'))

            if self.debug:
                print("Formated line: {0}".format(line))

            # Check if file exists
            if not os.path.isfile(os.path.abspath(os.path.join(self.local_prefix, line))):
                print("Skipping file: '{0}', does not exist in library".format(line))
                continue

            outf.write("{0}\n".format(line))

        inf.close()
        outf.close()

        # Copy new raw to other types (including source)
        if self.debug:
            print("Converting all for playlist {0}".format(name))
        self.convert_all(name)

    def convert_all(self, playlist):
        raw_file = os.path.join(self.raw_dir, playlist)
        for os_ in self.oss:
            for type_ in self.types:
                dest = os.path.join(self.location, os_ + "_" + type_)
                os_type, prefix = self.oss[os_]
                inf = open(raw_file, "r")
                outf = open(os.path.join(dest, playlist + "." + type_), "w")

                if type_ == "pls":
                    outf.write("[playlist]\n")
                    i = 0

                for line in inf:
                    if os_type == "nix":
                        line = posixpath.normpath(posixpath.join(prefix, line))
                    elif os_type == "win":
                        line = ntpath.normpath(ntpath.join(prefix, line))

                    if type_ == "pls":
                        i += 1
                        line = "File" + str(i) + "=" + line

                    outf.write(line)

                if type_ == "pls":
                    outf.write("NumberOfEntries=" + str(i) + "\n")

                inf.close()
                outf.close()

        # Make raw type be newest
        with open(raw_file, 'a'):
            os.utime(raw_file, None)

if __name__ == "__main__":
    main()
