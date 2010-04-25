#
# frankenplot.main: entry point into frankenplot
#

import optparse
import sys

import frankenplot
from frankenplot import gui, util

# ============================================================================

def parse_arguments(args):
    # matplotlib's color maps
    colormaps = ['autumn', 'bone', 'cool', 'copper', 'flag', 'gray', 'hot',
        'hsv', 'pink', 'prism', 'spring', 'summer', 'winter']

    USAGE = '%prog [OPTIONS...] FILE [ROI-NUMBER]'
    VERSION = '%prog ' + frankenplot.__version__ + ', by Ken McIvor <mcivor@iit.edu>'
    parser = optparse.OptionParser(usage=USAGE, version=VERSION)

    parser.add_option('-i',
        action='store', type='string', dest='zName',
        help='z-axis column name (legacy option; see -z for more details)', metavar='N')

    parser.add_option('-x',
        action='store', type='string', dest='xName', default='sam_hor',
        help='x-axis column name ("sam_hor" is default)', metavar='N')

    parser.add_option('-y',
        action='store', type='string', dest='yName', default='sam_vert',
        help='y-axis column name ("sam_vert" is default)', metavar='N')

    parser.add_option('-z',
        action='store', type='string', dest='zName', default='Io',
        help='z-axis column name ("Io" is default)', metavar='N')

    # FIXME move to Edit -> Preferences
    parser.add_option('-n',
        action='store_false', dest='normalize', default=True,
        help='disable Io normalization')

    parser.add_option('-m',
        action='store', dest='colormap', default='hot',
        help=('color map (%s)' % ', '.join(colormaps)), metavar='C')

    opts, args = parser.parse_args(args)
    if not 0 < len(args) < 3:
        parser.print_usage()
        sys.exit(1)

    # FIXME: most of this logic should be moved into f.data or f.gui
    fileName  = args[0]
    roiNumber = 0
    if len(args) == 2:
        try:
            roiNumber = int(args[1])
        except ValueError:
            fatal_error('invalid ROI number "%s"', repr(args[1])[1:-1])

        if roiNumber < 0:
            fatal_error('invalid ROI number "%s"', repr(args[1])[1:-1])

    cm = opts.colormap.lower()
    if cm not in colormaps:
        fatal_error('invalid color map "%s"', opts.colormap)
    else:
        opts.colormap = cm

    return opts, (fileName, roiNumber)

def run(arguments):
    opts, args = parse_arguments(arguments)
    filename, roi_number = args

    app = gui.PlotApp(filename=filename)
    app.plot(x_name=opts.xName, y_name=opts.yName, z_name=opts.zName,
                normalize=opts.normalize, colormap=opts.colormap,
                roi_number=roi_number)
    app.MainLoop()
