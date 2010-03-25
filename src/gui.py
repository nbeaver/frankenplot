import re
import sys

import matplotlib.cm
import matplotlib.numerix as nx
import wx

import wxmpl
import xdp.io

# FIXME: move these functions into PlotApp
def getNumberUnique(vect):
    """
    Return the number of times elements appear in the vector 'vect' without
    repeating the first element of the vector.

    This only works for vectors like '[0, 1, 2, 3, 0, 1, 2, 3]'.
    """
    i = 1
    num = 0
    start = vect[0]
    max = vect.shape[0]
    while i < max:
        if vect[i] == start:
            break
        else:
            i += 1
    return i


def makeXYZ(xCol, yCol, zCol):
    idxs = nx.arange(0, zCol.shape[0], 1)
    nX = getNumberUnique(xCol)
    if nX == 1: # Y varies: (0, 0, z), (0, 1, z), ...
        nY = getNumberUnique(yCol)
        nX = int(nx.ceil(yCol.shape[0] / float(nY)))
        y = yCol[0:nY]
        x = getUniqueSequence(xCol, nX)
        z = nx.zeros((nY, nX), nx.Float)
        z[:, :] = nx.minimum.reduce(zCol)
        for i in range(0, nX):
            zc = zCol[nY*i:nY*(i+1)]
            n  = zc.shape[0]
            z[0:n,i] = zc
    else: # X varies: (0, 0, z), (1, 0, z), ...
        nY = int(nx.ceil(xCol.shape[0] / float(nX)))
        x = xCol[0:nX]
        y = getUniqueSequence(yCol, nY)
        z = nx.zeros((nY, nX), nx.Float)
        z[:, :] = nx.minimum.reduce(zCol)
        for i in range(0, nY):
            zc = zCol[nX*i:nX*(i+1)]
            n  = zc.shape[0]
            z[i, 0:n] = zc
    return x, y, z


def getUniqueSequence(vect, count):
   """Return a Numeric array containing the at most the first 'count' unique
   elements from the vector 'vect'.

   The 'vect' must contain at least one element.

   This only works for vectors like '[0, 0, 1, 1, 2, 2, 3, 3]'.
   """
   i = 0
   curr = None
   unique = []
   max = vect.shape[0]

   while i < max:
       if vect[i] == curr:
           i += 1
       else:
           if len(unique) == count:
               break
           else:
               curr = vect[i]
               unique.append(curr)
               i += 1

   return nx.array(unique)


def fatal_error(msg, *args):
    if args:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]),
            (msg % args))
    else:
        print >> sys.stderr, '%s: %s' % (os.path.basename(sys.argv[0]), msg)
    sys.exit(1)


class PlotFrame(wxmpl.PlotFrame):
    def create_menus(self):
        # menu bar
        menuBar = wx.MenuBar()
        self.SetMenuBar(menuBar)

        # File menu
        fileMenu = wx.Menu()
        menuBar.Append(fileMenu, '&File')

        # FIXME: does "Ctrl+S" shortcut text show up as Cmd+S on Macs?
        item = fileMenu.Append(wx.ID_SAVEAS, "&Save As...\tCtrl+S",
            "Save a copy of the current plot")
        self.Bind(wx.EVT_MENU, self.OnMenuFileSave, item)

        fileMenu.AppendSeparator()

        if wx.Platform != '__WXMAC__':
            item = fileMenu.Append(wx.ID_ANY, "Page Set&up...",
                "Set the size and margins of the printed figure")
            self.Bind(wx.EVT_MENU, self.OnMenuFilePageSetup, item)

            item = fileMenu.Append(wx.ID_PREVIEW, 'Print Previe&w...',
                "Preview the print version of the current plot")
            self.Bind(wx.EVT_MENU, self.OnMenuFilePrintPreview, item)

        id = wx.NewId()
        item = fileMenu.Append(wx.ID_PRINT, '&Print...\tCtrl+P', 
            "Print the current plot")
        self.Bind(wx.EVT_MENU, self.OnMenuFilePrint, item)

        fileMenu.AppendSeparator()

        item = fileMenu.Append(wx.ID_CLOSE, '&Close Window\tCtrl+W',
            'Close the current plot window')
        self.Bind(wx.EVT_MENU, self.OnMenuFileClose, item)

        # Edit menu
        editMenu = wx.Menu()
        menuBar.Append(editMenu, "&Edit")

        item = editMenu.Append(wx.ID_ANY, "&Columns...",
            "Select displayed columns")
        self.Bind(wx.EVT_MENU, self.OnMenuSelectColumns, item)

        # Help menu
        helpMenu = wx.Menu()
        menuBar.Append(helpMenu, '&Help')

        item = helpMenu.Append(wx.ID_ANY, '&About...', 
            'Display version information')
        self.Bind(wx.EVT_MENU, self.OnMenuHelpAbout, item)

    def OnMenuSelectColumns(self, evt):
        frame = SelectColumnsFrame(parent=self, id=wx.ID_ANY, title="Select Columns")
        frame.Show(True)

class SelectColumnsFrame(wx.Frame):
    def __init__(self, parent, id, title, **kwargs):
        wx.Frame.__init__(self, parent, id, title, **kwargs)
        
        # axes selector
        columns = "a b c".split()
        xAxisCombo = wx.ComboBox(self, choices=columns, style=wx.CB_DROPDOWN)
        yAxisCombo = wx.ComboBox(self, choices=columns, style=wx.CB_DROPDOWN)

        # on save, replot

class PlotApp(wxmpl.PlotApp):
    def __init__(self, filename=None, **kwargs):
        self.filename = filename

        # load the data file
        try:
            self.hdr, self.data = xdp.io.readFile(filename)
        except IOError, e:
            if e.strerror:
                fatal_error('could not load `%s\': %s', fileName, e.strerror)
            else:
                fatal_error('could not load `%s\': %s', fileName, e)
        # if filename is None, xdp.io.readFile raises:
        #     AttributeError: 'NoneType' object has no attribute 'rfind'
        except AttributeError:
            self.hdr = None
            self.data = None

        wxmpl.PlotApp.__init__(self, **kwargs)

    def OnInit(self):
        self.frame = panel = PlotFrame(None, -1, self.title, self.size,
            self.dpi, self.cursor, self.location, self.crosshairs,
            self.selection, self.zoom)

        if self.ABOUT_TITLE is not None:
            panel.ABOUT_TITLE = self.ABOUT_TITLE

        if self.ABOUT_MESSAGE is not None:
            panel.ABOUT_MESSAGE = self.ABOUT_MESSAGE

        panel.Show(True)
        return True

    def plot(self, x_name, y_name, z_name, normalize=True, colormap="hot",
             roi_number=0):
        # fetch x
        try:
            x_col = self.data.getColumn(x_name)
        except xdp.ColumnNameError:
            fatal_error('invalid x-axis column name "%s"', repr(x_name)[1:-1])

        # fetch y
        try:
            y_col = self.data.getColumn(y_name)
        except xdp.ColumnNameError:
            fatal_error('invalid y-axis column name "%s"', repr(x_name)[1:-1])

        # find the corrected ROIs
        roipat = re.compile('corr_roi[0-9]+_%d' % roi_number)
        rois   = [x for x in self.data.getColumnNames() if roipat.match(x) is not None]
        if not rois:
            fatal_error('`%s\' contains no data for ROI %d',
                os.path.basename(fileName), roi_number)

        # calculate z
        zExpr = '+'.join(['$'+x for x in rois])
        if normalize:
            if self.data.hasColumn(z_name):
                zExpr = '(%s)/$%s' % (zExpr, z_name)
            else:
                fatal_error('invalid z-axis column name "%s"', repr(z_name)[1:-1])
        z_col = self.data.evaluate(zExpr)
        x, y, z = makeXYZ(x_col, y_col, z_col)

        # set up axes
        fig = self.get_figure()
        axes = fig.gca()

        if matplotlib.__version__ >= '0.81':
            axes.yaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
            axes.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(5))

            axes.xaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
            axes.xaxis.set_major_locator(matplotlib.ticker.LinearLocator(5))

        # FIXME
        axes.set_title('ROI %d of %s' % (roi_number, self.filename))
        axes.set_ylabel(y_name)

        # plot the data and colorbar
        extent = min(x), max(x), min(y), max(y)
        img = axes.imshow(z, cmap=getattr(matplotlib.cm, colormap),
                origin='lower', aspect='equal', interpolation='nearest',
                extent=extent)
        cb = fig.colorbar(img, cax=None, orientation='vertical')
