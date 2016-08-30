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
    global args
    args = parser.parse_args()

    global oss, types, local_prefix
    oss, types, local_prefix = load_config()

    # Setup shortcuts
    global raw_dir
    raw_dir = os.path.join(args.location, "local")

    if args.debug:
        print("Config file dump:")
        print("OSs': {0}".format(oss))
        print("Types: {0}".format(types))

    make_formats()

    if args.daemon:
        while True:
            update()
            time.sleep(60)
    else:
        update()

def load_config():
    try:
        config = open(os.path.join(args.location, "ensemble.config"))
        exec(config.read())
        return (oss, types, local_prefix)
    except IOError as error:
        print("Config file not found!")
        os._exit(1)
    finally:
        config.close()

def make_formats():
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
    for os_ in oss:
        for type_ in types:
            format_ = os_ + "_" + type_
            if args.debug:
                print("Playlist format discovered: {0}".format(format_))
            dest = os.path.join(args.location, format_)
            if not os.path.exists(dest):
                if args.debug:
                    print("Making directory {0}".format(dest))
                os.makedirs(dest)

def update():
    for os_ in oss:
        for type_ in types:
            dest = os.path.join(args.location, os_ + "_" + type_)

            for fn in os.listdir(dest):
                name, ext = os.path.splitext(fn)
                ext = ext[1:]

                # Check if this file is the type that should be here
                if ext != type_:
                    if args.debug:
                        print("Found file {0} with wrong extension".format(fn))
                        print("Had: {0}, should be: {1}".format(ext, type_))
                    continue

                if os.path.isfile(os.path.join(raw_dir, name)):
                    # Have playlist, check it
                    if needs_update(dest, fn):
                        update_playlist(os_, dest, fn)
                else:
                    # Don't have, create it
                    update_playlist(os_, dest, fn)

def needs_update(dest, playlist):
    name = os.path.splitext(playlist)[0]
    return os.path.getmtime(os.path.join(dest, playlist)) \
               > os.path.getmtime(os.path.join(raw_dir, name))

def update_playlist(os_, dest, playlist):
    name, ext = os.path.splitext(playlist)
    ext = ext[1:]
    print("Updating playlist {0}".format(name))
    raw_file = os.path.join(raw_dir, name)

    # Copy new playlist to raw
    inf = open(os.path.join(dest, playlist), "r")
    outf = open(raw_file, "w")

    for line in inf:
        # Strip newline
        line = line[:-1]

        if args.debug:
            print("Input line: {0}".format(line))
            print("Prefix line: {0}".format(oss[os_]))

        if ext == "pls":
            # Check for pls header
            if not line.startswith("File"):
                if args.debug:
                    print("Skipping non-file line")
                continue
            # Remove pls File number
            line = line[(line.index('=') + 1):]
            if args.debug:
                print("After stripping pls: {0}".format(line))

        # Strip os prefix
        if line.startswith(oss[os_]):
            line = line[(len(oss[os_]) + 1):]
        else:
            print("Skipping file: '{0}', does not have valid prefix".format(line))
            continue

        if args.debug:
            print("Formated line: {0}".format(line))

        # Check if file exists
        if not os.path.isfile(os.path.join(local_prefix, line)):
            print("Skipping file: '{0}', does not exist in library".format(line))
            continue

        outf.write("{0}\n".format(line))

    inf.close()
    outf.close()

    # Copy new raw to other types (including source)
    if args.debug:
        print("Converting all for playlist {0}".format(name))
    convert_all(name)

    # Make raw type be newest
    os.utime(raw_file, None)

def convert_all(playlist):
    for os_ in oss:
        for type_ in types:
            dest = os.path.join(args.location, os_ + "_" + type_)
            inf = open(os.path.join(raw_dir, playlist), "r")
            outf = open(os.path.join(dest, playlist + "." + type_), "w")

            if type_ == "pls":
                outf.write("[playlist]\n")
                i = 0

            for line in inf:
                if os_ == "nix":
                    line = posixpath.abspath(posixpath.join(oss[os_], line))
                elif os_ == "win":
                    line = ntpath.abspath(ntpath.join(oss[os_], line))

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
