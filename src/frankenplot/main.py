#
# frankenplot.main: entry point into frankenplot
#

import optparse
import sys

import frankenplot
from frankenplot import defaults, expression, gui, util

# ============================================================================

def legacy_i_callback(option, opt_str, value, parser):
    print >>sys.stderr, "DEPRECATION WARNING: the '-i' option is deprecated; please use '-z'"
    parser.values.zName = value

def parse_arguments(args):
    USAGE = '%prog [OPTIONS...] FILE [ROI-NUMBER]'
    VERSION = '%prog ' + frankenplot.__version__ + ', by Ken McIvor <mcivor@iit.edu>'
    parser = optparse.OptionParser(usage=USAGE, version=VERSION)

    parser.add_option('-i',
        action='callback', type='string', callback=legacy_i_callback,
        help=optparse.SUPPRESS_HELP, metavar='N')

    parser.add_option('-x',
        action='store', type='string', dest='xName', default=defaults.x_name,
        help='x-axis column name ("%s" is default)' % defaults.x_name, metavar='N')

    parser.add_option('-y',
        action='store', type='string', dest='yName', default=defaults.y_name,
        help='y-axis column name ("%s" is default)' % defaults.y_name, metavar='N')

    parser.add_option('-z',
        action='store', type='string', dest='zName',
        default=defaults.fluor_mode.z_name,
        help='z-axis column name ("%s" is default)' % defaults.fluor_mode.z_name,
        metavar='N')

    # FIXME move to Edit -> Preferences
    parser.add_option('-n',
        action='store_false', dest='normalize', default=True,
        help='disable Io normalization')

    parser.add_option('-m',
        action='store', dest='colormap', default=defaults.colormap,
        help=('color map (%s)' % ', '.join(defaults.colormaps)), metavar='C')

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
            util.fatal_error('invalid ROI number "%s"', repr(args[1])[1:-1])

        if roiNumber < 0:
            util.fatal_error('invalid ROI number "%s"', repr(args[1])[1:-1])

    cm = opts.colormap.lower()
    if cm not in defaults.colormaps:
        fatal_error('invalid color map "%s"', opts.colormap)
    else:
        opts.colormap = cm

    return opts, (fileName, roiNumber)

def run(arguments):
    opts, args = parse_arguments(arguments)
    filename, roi_number = args

    # update plot defaults based on arguments
    defaults.x_name = opts.xName
    defaults.y_name = opts.yName
    defaults.fluor_mode.z_name = opts.zName
    defaults.fluor_mode.normalize = opts.normalize

    app = gui.PlotApp(filename=filename)

    """
    z_expr = expression.ROIExpression(roi_number)
    app.plot(z_expr)
    """

    app.MainLoop()
