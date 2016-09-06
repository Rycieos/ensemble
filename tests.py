#!/usr/bin/env py.test

import ensemble
import os
import pytest
import shutil
import time

def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

@pytest.fixture
def en(request):
    en = ensemble.Ensemble(".")

    def close():
        shutil.rmtree("android_m3u", ignore_errors=True)
        shutil.rmtree("android_pls", ignore_errors=True)
        shutil.rmtree("linux_m3u", ignore_errors=True)
        shutil.rmtree("linux_pls", ignore_errors=True)
        shutil.rmtree("win_m3u", ignore_errors=True)
        shutil.rmtree("win_pls", ignore_errors=True)
        shutil.rmtree("local", ignore_errors=True)
        shutil.rmtree("music", ignore_errors=True)
    request.addfinalizer(close)
    return en

def test_config_check():
    failed = False
    try:
        ensemble.Ensemble("foo")
    except IOError:
        failed = True
    assert failed

def test_config(en):
    assert os.path.exists("ensemble.config")

    assert en.oss is not None
    assert en.types is not None
    assert en.debug is not None
    assert en.raw_dir is not None
    assert en.local_prefix is not None
    assert en.location is not None

def test_formats(en):
    en.make_formats()

    assert os.path.exists("android_m3u")
    assert os.path.exists("android_pls")
    assert os.path.exists("linux_m3u")
    assert os.path.exists("linux_pls")
    assert os.path.exists("win_m3u")
    assert os.path.exists("win_pls")
    assert os.path.exists("local")

def test_update_check(en):
    en.make_formats()

    touch(os.path.join("win_m3u", "foo.m3u"))
    time.sleep(.01)
    touch(os.path.join("local", "foo"))
    time.sleep(.01)
    touch(os.path.join("linux_m3u", "foo.m3u"))

    assert en.needs_update("linux_m3u", "foo.m3u")
    assert not en.needs_update("win_m3u", "foo.m3u")

def test_file_check(en):
    en.make_formats()

    touch(os.path.join("linux_m3u", "foo.m3u"))
    en.update_playlist("linux", "linux_m3u", "foo.m3u")
    assert os.path.exists("local/foo")
    assert os.path.exists("win_pls/foo.pls")

def test_update(en):
    en.make_formats()

    touch(os.path.join("linux_m3u", "foo.m3u"))
    en.update()
    assert os.path.exists("linux_m3u/foo.m3u")
    assert os.path.exists("local/foo")
    assert os.path.exists("win_pls/foo.pls")

def test_convert_all(en):
    en.make_formats()

    touch(os.path.join("local", "foo"))
    en.convert_all("foo")
    assert not en.needs_update("win_m3u", "foo.m3u")

def test_music_check(en):
    en.make_formats()

    outf = open("linux_m3u/foo.m3u", "w")
    outf.write("/media/music/bar.mp3\n")
    outf.close()

    en.update_playlist("linux", "linux_m3u", "foo.m3u")

    inf = open("local/foo")
    found = False
    for line in inf:
        if line.strip() == "bar.mp3":
            found = True
    inf.close()

    assert not found

    os.makedirs("music")
    touch("music/bar.mp3")

    outf = open("linux_m3u/foo.m3u", "w")
    outf.write("/media/music/bar.mp3\n")
    outf.close()

    en.update_playlist("linux", "linux_m3u", "foo.m3u")

    inf = open("local/foo")
    found = False
    for line in inf:
        if line.strip() == "bar.mp3":
            found = True
    inf.close()

    assert found

def test_whitespace(en):
    en.make_formats()
    os.makedirs("music")
    touch("music/foo bar.mp3")

    outf = open("linux_m3u/foo bar.m3u", "w")
    outf.write("/media/music/foo bar.mp3\n")
    outf.close()

    en.update_playlist("linux", "linux_m3u", "foo bar.m3u")

    inf = open("local/foo bar")
    found = False
    for line in inf:
        if line.strip() == "foo bar.mp3":
            found = True
    inf.close()

    assert found

def test_main(en):
    ensemble.main(['--debug'])
    assert os.path.exists("win_pls")
    assert os.path.exists("local")
