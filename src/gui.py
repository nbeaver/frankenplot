import copy
import fnmatch
import re
import sys

import matplotlib.cm
import matplotlib.numerix as nx
import wx
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ListCtrlAutoWidthMixin

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

class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin, ListCtrlAutoWidthMixin):
    class CheckListCtrlIterator(object):
        def __init__(self, coll, i=0):
            self.coll = coll
            self.i = i

        def __iter__(self):
            return self

        def next(self):
            item = self.coll.GetNextItem(self.i-1, wx.LIST_NEXT_ALL)

            if item == -1:
                raise StopIteration
            else:
                self.i += 1
                return self.i-1, self.coll.GetItem(item)


    def __init__(self, parent, **kwargs):
        style = kwargs.pop("style", wx.LC_REPORT | wx.SUNKEN_BORDER |
                           wx.LC_NO_HEADER)
        wx.ListCtrl.__init__(self, parent, style=style, **kwargs)
        CheckListCtrlMixin.__init__(self)
        ListCtrlAutoWidthMixin.__init__(self)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._OnSelect, self)

        self._reset()

    def __iter__(self):
        return self.CheckListCtrlIterator(self)

    def AppendStringItem(self, label, check=True):
        return CheckListCtrl.InsertStringItem(self, sys.maxint, label, check)

    def ClearAll(self):
        self._reset()
        wx.ListCtrl.ClearAll(self)

    def DeleteAllItems(self):
        self._reset()
        wx.ListCtrl.DeleteAllItems(self)

    def DeleteItem(self, item_id):
        del self._items[self.GetItemText(item_id)]
        wx.ListCtrl.DeleteItem(item_id)

    def Filter(self, pattern):
        if len(pattern) == 0:
            pattern = "*"
        else:
            pattern = "*%s*" % (pattern)

        columns = fnmatch.filter(self._items.keys(), pattern)
        self.ShowItemStrings(columns)

    def GetCheckedItems(self):
        return [item for (id, item) in self if self.IsChecked(id)]

    def GetItems(self):
        return [item for (id, item) in self]

#    def InsertImageStringItem(self, *args, **kwargs):
#        raise NotImplementedError

    def InsertItem(self, *args, **kwargs):
        raise NotImplementedError

    def InsertStringItem(self, index, label, check=True):
        self._items[label] = check
        id = self.InsertStringItem(index, label)
        self.CheckItem(id, check=bool(check))
        return id

    def SetItem(self, *args, **kwargs):
        raise NotImplementedError

    def SetItemStrings(self, labels):
        self.DeleteAllItems()

        for label, checked in sorted(labels.iteritems()):
            id = self.AppendStringItem(label, checked)

        self._items = labels

    def SetItemText(self, item_id, label):
        checked = self._items.pop(self.GetItemText(item_id))
        self._items[label] = checked
        wx.ListCtrl.SetItemText(self, item_id, label)

    def ShowItemStrings(self, wanted_items):
        wx.ListCtrl.DeleteAllItems(self)
        wanted_items = dict((k, True) for k in wanted_items)

        for item, checked in sorted(self._items.iteritems()):
            if item in wanted_items:
                self.AppendStringItem(item, checked)

    def _OnSelect(self, e):
        id = e.GetIndex()
        self.ToggleItem(id)

    def _reset(self):
        self._items = dict()

class SelectColumnsFrame(wx.Frame):
    def __init__(self, parent, id, title, app, **kwargs):
        self.app = app

        wx.Frame.__init__(self, parent, id, title, **kwargs)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # column filter
        self.column_filter = wx.TextCtrl(self, size=(200, 27.5))
        self.column_filter.SetFocus()
        self.Bind(wx.EVT_TEXT, self._OnUpdateFilter, self.column_filter)
        main_sizer.Add(self.column_filter)

        # column selection
        col_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(col_sizer)

        self.columns_list = CheckListCtrl(self, size=(200, 300))
        self.columns_list.InsertColumn(0, "Data Column")
        self._set_columns_list()
        col_sizer.Add(self.columns_list)

        # ROI selector
#        item = wx.StaticText(self, label="ROI:")
#        grid.Add(item, pos=(0, 0))

        rois = [str(roi) for roi in app.rois.keys()]
        value = str(app.plot_opts["roi_number"])
        self.roi_combo = wx.ComboBox(self, value=value, choices=rois)
        main_sizer.Add(self.roi_combo)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectROI, self.roi_combo)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSelectROI, self.roi_combo)

        # buttons
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(buttons_sizer)

        # save button
        self.save_button = wx.Button(self, label="Save")
        self.Bind(wx.EVT_BUTTON, self.OnSaveClick, self.save_button)
        buttons_sizer.Add(self.save_button)

        # cancel button
        self.cancel_button = wx.Button(self, label="Cancel")
        self.Bind(wx.EVT_BUTTON, self.OnCancelClick, self.cancel_button)
        buttons_sizer.Add(self.cancel_button)


        self.SetSizer(main_sizer)
        self.SetAutoLayout(True)
        main_sizer.Fit(self)
        self.Show()

    def _set_columns_list(self):
        columns = dict()
        for col in self.app.data.getColumnNames():
            # FIXME: don't hardcode "corr_roi"
            if not col.startswith("corr_roi"):
                continue

            columns[col] = col in self.app.plot_opts["columns"]

        self.columns_list.SetItemStrings(columns)

    def OnSaveClick(self, e):
        roi = int(self.roi_combo.GetValue())
        columns = [c.GetText() for c in self.columns_list.GetCheckedItems()]

        self.app.change_plot(roi_number=roi, columns=columns)

        self.Close(True)

    def OnCancelClick(self, e):
        self.Close(True)

    def OnSelectROI(self, e):
        roi_number = int(self.roi_combo.GetValue())
        self._set_columns(roi_number)

    def _OnUpdateFilter(self, e):
        pattern = self.column_filter.GetValue()
        self.columns_list.Filter(pattern)

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
