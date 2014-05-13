#
# frankenplot.util: miscellaneous utility functions
#

import os
import re
import sys

from frankenplot import exceptions
from frankenplot import defaults

# ============================================================================

# replace all negative numbers in the xdp dataset with zereos
def remove_negatives(xdp_data):
    for column in xdp_data.getColumnNames():
	# ignore x and y axis data
	if column == defaults.x_name or column == defaults.y_name:
	    continue
	for index,element in enumerate(xdp_data.get(column)):
	    if element <= 1.0:
		xdp_data.get(column)[index] = 1.0
	

def fatal_error(msg, *args):
    if args:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]),
            (msg % args))
    else:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]), msg)
    sys.exit(1)

def natural_sort(lst):
    """Sort a list in natural, human order

    Based on: http://nedbatchelder.com/blog/200712/human_sorting.html"""

    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(lst, key=alphanum_key)

def get_data_column_name(roi, channel, corrected):
    if corrected:
        stem = "corr_roi"
    else:
        stem = "roi"

    return "%s%d_%d" % (stem, channel, roi)

def get_roi_group_name(roi, corrected):
    if corrected:
        stem = "corr_roi"
    else:
        stem = "roi"

    return "%%%s_%d" % (stem, roi)

roi_re = re.compile(r"(corr_)?roi(\d+)_(\d+)")
def parse_data_column_name(col):
    match = roi_re.search(col)

    try:
        corrected, channel, roi = match.groups()
    except AttributeError:
        s = "Invalid data column name: '%s'" % col
        raise exceptions.InvalidDataColumnNameException(s)

    return int(roi), int(channel), bool(corrected)

ROI_GROUP_RE = re.compile(r"(corr_)?roi_(\d+)")
def parse_roi_group_name(name):
    match = ROI_GROUP_RE.search(name)
    try:
        corrected, roi = match.groups()
    except AttributeError:
        raise ValueError("invalid ROI group name: '%s'" % name)

    return int(roi), bool(corrected)
