import copy
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
    def __init__(self, app, **kwargs):
        self.app = app
        wxmpl.PlotFrame.__init__(self, **kwargs)

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
        frame = SelectColumnsFrame(parent=self, id=wx.ID_ANY,
            title="Select Columns", app=self.app)
        frame.Show(True)

class SelectColumnsFrame(wx.Frame):
    def __init__(self, parent, id, title, app, **kwargs):
        self.app = app

        wx.Frame.__init__(self, parent, id, title, **kwargs)

        # use GridBagSizer
        grid = wx.GridBagSizer(hgap=5, vgap=5)

        # ROI selector
        item = wx.StaticText(self, label="ROI:")
        grid.Add(item, pos=(0, 0))

        rois = [str(roi) for roi in app.rois.keys()]
        value = str(app.plot_opts["roi_number"])
        self.roi_combo = wx.ComboBox(self, value=value, choices=rois)
        grid.Add(self.roi_combo, pos=(0, 1))
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectROI, self.roi_combo)

        # column selection
        self.columns_box = wx.ListBox(self, style=wx.LB_MULTIPLE)
        grid.Add(self.columns_box, pos=(1, 1))
        self._set_columns(roi_number=int(self.roi_combo.GetValue()))

        # save button
        self.save_button = wx.Button(self, label="Save")
        self.Bind(wx.EVT_BUTTON, self.OnSaveClick, self.save_button)
        grid.Add(self.save_button, pos=(2, 0))

        # cancel button
        self.cancel_button = wx.Button(self, label="Cancel")
        self.Bind(wx.EVT_BUTTON, self.OnCancelClick, self.cancel_button)
        grid.Add(self.cancel_button, pos=(2, 1))

        self.SetSizerAndFit(grid)

    def _set_columns(self, roi_number):
        columns = self.app.rois[roi_number]
        self.columns_box.Set(columns)
        self.columns = columns

        # select columns that are currently active
        selected_columns = dict((k, 1) for k in self.app.plot_opts["columns"])
        for i, v in enumerate(columns):
            if v in selected_columns:
                self.columns_box.SetSelection(i)

    def OnSaveClick(self, e):
        roi = int(self.roi_combo.GetValue())

        columns = self.columns_box.GetSelections()
        column_names = []
        for col in columns:
            column_names.append(self.columns[col])

        self.app.change_plot(roi_number=roi, columns=column_names)

        self.Close(True)

    def OnCancelClick(self, e):
        self.Close(True)

    def OnSelectROI(self, e):
        roi_number = int(self.roi_combo.GetValue())
        self._set_columns(roi_number)

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

        self.columns = self.data.getColumnNames()
        self.rois = self.__parse_rois(self.columns)

        self.plot_opts = dict()

        wxmpl.PlotApp.__init__(self, **kwargs)

    def OnInit(self):
        self.frame = panel = PlotFrame(parent=None, id=wx.ID_ANY,
            title=self.title, size=self.size, dpi=self.dpi,
            cursor=self.cursor, location=self.location,
            crosshairs=self.crosshairs, selection=self.selection,
            zoom=self.zoom, app=self)

        if self.ABOUT_TITLE is not None:
            panel.ABOUT_TITLE = self.ABOUT_TITLE

        if self.ABOUT_MESSAGE is not None:
            panel.ABOUT_MESSAGE = self.ABOUT_MESSAGE

        panel.Show(True)
        return True

    def plot(self, x_name, y_name, z_name, normalize=True, colormap="hot",
             roi_number=0, columns=None):

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

        # determine the columns to plot if no columns were specified
        if columns is None:
            columns = self.rois[roi_number]
            if not columns:
                fatal_error('`%s\' contains no data for ROI %d',
                    os.path.basename(fileName), roi_number)

        # calculate z
        zExpr = '+'.join(['$'+x for x in columns])
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

        axes.figure.canvas.draw()

        # save current plot parameters for later retrieval
        self.plot_opts["x_name"] = x_name
        self.plot_opts["y_name"] = y_name
        self.plot_opts["z_name"] = z_name
        self.plot_opts["normalize"] = normalize
        self.plot_opts["colormap"] = colormap
        self.plot_opts["roi_number"] = roi_number
        self.plot_opts["columns"] = columns

    def change_plot(self, **kwargs):
        opts = copy.copy(self.plot_opts)
        opts.update(kwargs)
        self.plot(**opts)

    def __parse_rois(self, columns):
        roi_re = re.compile(r"corr_roi\d+_(\d+)")
        rois = dict()

        search = roi_re.search
        for col in columns:
            match = search(col)
            if match:
                roi = int(match.group(1))
                rois.setdefault(roi, []).append(col)

        return rois
