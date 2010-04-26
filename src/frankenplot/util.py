#
# frankenplot.util: miscellaneous utility functions
#

import os
import re
import sys

from frankenplot import exceptions

# ============================================================================

def fatal_error(msg, *args):
    if args:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]),
            (msg % args))
    else:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]), msg)
    sys.exit(1)

def get_data_column_name(roi, channel):
    return "corr_roi%d_%d" % (channel, roi)

def natural_sort(lst):
    """Sort a list in natural, human order

    Based on: http://nedbatchelder.com/blog/200712/human_sorting.html"""

    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(lst, key=alphanum_key)

roi_re = re.compile(r"corr_roi(\d+)_(\d+)")
def parse_data_column_name(col):
    match = roi_re.search(col)

    try:
        channel, roi = match.groups()
    except AttributeError:
        s = "Invalid data column name: '%s'" % col
        raise exceptions.InvalidDataColumnNameException(s)

    return int(roi), int(channel)
