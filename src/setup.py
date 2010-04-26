#!/usr/bin/env python

from distutils.core import setup

setup(name="frankenplot",
      # FIXME: get this from frankenplot module
      version="2.0a1",
      description="Quick 'n dirty plotting of MRCAT XRF mapping data",
      author="Ken McIvor",
      author_email="mcivor@iit.edu",
      url="",
      packages=["frankenplot"],
      scripts=["bin/frankenplot"],
     )
