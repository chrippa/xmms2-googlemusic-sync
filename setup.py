#!/usr/bin/env python

from setuptools import setup, find_packages

version = "1.0"

setup(name="xmms2-googlemusic-sync",
      version=version,
      description="Sync your Google Music library with XMMS2",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="GPL",
      packages=["xmms2gmusic"],
      package_dir={'': 'src'},
      entry_points={
          "console_scripts": ["xmms2-googlemusic-sync=xmms2gmusic.cli:main"]
      },
      install_requires="gmusicapi"
)

