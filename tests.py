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
    return ensemble.Ensemble(".")

    def close():
        touch("test")
        shutil.rmtree("nix_m3u", ignore_errors=True)
        shutil.rmtree("nix_pls", ignore_errors=True)
        shutil.rmtree("win_m3u", ignore_errors=True)
        shutil.rmtree("win_pls", ignore_errors=True)
        shutil.rmtree("local", ignore_errors=True)
    request.addfinalizer(close)

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

    assert os.path.exists("win_m3u")
    assert os.path.exists("win_pls")
    assert os.path.exists("nix_m3u")
    assert os.path.exists("nix_pls")
    assert os.path.exists("local")

def test_update_check(en):
    en.make_formats()

    touch(os.path.join("win_m3u", "foo.m3u"))
    time.sleep(.01)
    touch(os.path.join("local", "foo"))
    time.sleep(.01)
    touch(os.path.join("nix_m3u", "foo.m3u"))

    assert en.needs_update("nix_m3u", "foo.m3u")
    assert not en.needs_update("win_m3u", "foo.m3u")
