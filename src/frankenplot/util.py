#
# frankenplot.util: miscellaneous utility functions
#

import re

# ============================================================================

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
