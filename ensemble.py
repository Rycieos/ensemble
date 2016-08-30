#!/usr/bin/env python

import argparse
import ntpath
import os
import posixpath
import time

def main():
    parser = argparse.ArgumentParser(description='Update universal playlist library')
    parser.add_argument('--daemon', '-D', action='store_true', help='run as daemon')
    parser.add_argument('--debug', '-x', action='store_true', help='print debugging info')
    parser.add_argument('--location', '-l', action='store', default=os.getcwd(),
                        help='playlists location (default: current directory)')
    args = parser.parse_args()

    en = Ensemble(args.location, args.debug)

    if args.debug:
        print("Config file dump:")
        print("OSs': {0}".format(en.oss))
        print("Types: {0}".format(en.types))

    en.make_formats()

    if args.daemon:
        while True:
            en.update()
            time.sleep(60)
    else:
        en.update()

class Ensemble:
    def __init__(self, location, debug=False):
        self.raw_dir = os.path.join(location, "local")
        self.debug = debug
        self.location = location

        config = None
        try:
            config = open(os.path.join(location, "ensemble.config"))
            exec(config.read())
            self.oss = oss
            self.types = types
            self.local_prefix = local_prefix
        except IOError as error:
            print("Config file not found!")
            os._exit(1)
        finally:
            if config is not None:
                config.close()

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
        prefix = self.oss[os_]
        inf = open(os.path.join(dest, playlist), "r")
        outf = open(raw_file, "w")

        for line in inf:
            # Strip newline
            line = line[:-1]

            if self.debug:
                print("Input line: {0}".format(line))
                print("Prefix line: {0}".format(prefix))

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
                line = line[(len(prefix) + 1):]
            else:
                print("Skipping file: '{0}', does not have valid prefix".format(line))
                continue

            if self.debug:
                print("Formated line: {0}".format(line))

            # Check if file exists
            if not os.path.isfile(os.path.join(self.local_prefix, line)):
                print("Skipping file: '{0}', does not exist in library".format(line))
                continue

            outf.write("{0}\n".format(line))

        inf.close()
        outf.close()

        # Copy new raw to other types (including source)
        if self.debug:
            print("Converting all for playlist {0}".format(name))
        self.convert_all(name)

        # Make raw type be newest
        os.utime(raw_file, None)

    def convert_all(self, playlist):
        for os_ in self.oss:
            for type_ in self.types:
                dest = os.path.join(self.location, os_ + "_" + type_)
                prefix = self.oss[os_]
                inf = open(os.path.join(self.raw_dir, playlist), "r")
                outf = open(os.path.join(dest, playlist + "." + type_), "w")

                if type_ == "pls":
                    outf.write("[playlist]\n")
                    i = 0

                for line in inf:
                    if os_ == "nix":
                        line = posixpath.abspath(posixpath.join(prefix, line))
                    elif os_ == "win":
                        line = ntpath.abspath(ntpath.join(prefix, line))

                    if type_ == "pls":
                        i += 1
                        line = "File" + str(i) + "=" + line

                    outf.write(line)

                if type_ == "pls":
                    outf.write("NumberOfEntries=" + str(i) + "\n")

                inf.close()
                outf.close()

if __name__ == "__main__":
    main()
