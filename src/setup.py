#!/usr/bin/env python

from distutils.core import setup
from frankenplot import __version__

setup(name="frankenplot",
      version=__version__,
      description="Quick 'n dirty plotting of MRCAT XRF mapping data",
      author="Ken McIvor",
      author_email="mcivor@iit.edu",
      url="",
      packages=["frankenplot"],
      scripts=["bin/frankenplot"],
     )
