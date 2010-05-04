#
# frankenplot.gui: wxPython elements
#

import copy
import fnmatch
import os.path
import re
import sys

import matplotlib

import wx
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ListCtrlAutoWidthMixin

# FIXME: provisional, remove soon
import wxmpl
import xdp

from frankenplot import data as fdata, exceptions as exc, util, __version__

# ============================================================================

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

    def CheckAllShown(self):
        for id, item in self:
            self.CheckItem(id, check=True)

    def CheckItem(self, id, check=True):
        label = self.GetItem(id).GetText()
        self._items[label] = check
        CheckListCtrlMixin.CheckItem(self, id, check)

    def CheckItemStrings(self, items, check=True):
        for label in items:
            id = self.FindItem(-1, label)
            if id == -1:
                raise NonExistentItemException
            else:
                self.CheckItem(id, check)

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

        # FIXME: there is a better way to do this
        keys = util.natural_sort(labels.keys())
        for label in keys:
            checked = labels[label]
            id = self.AppendStringItem(label, checked)

        self._items = labels

    def SetItemText(self, item_id, label):
        checked = self._items.pop(self.GetItemText(item_id))
        self._items[label] = checked
        wx.ListCtrl.SetItemText(self, item_id, label)

    def ShowItemStrings(self, wanted_items):
        wx.ListCtrl.DeleteAllItems(self)

        for label in util.natural_sort(wanted_items):
            self.AppendStringItem(label, check=self._items[label])

    def UncheckAll(self):
        for label in self._items:
            id = self.FindItem(-1, label)
            if id == -1:
                self._items[label] = False
            else:
                self.CheckItem(id, check=False)

    def UncheckAllShown(self):
        for id, item in self:
            self.CheckItem(id, check=False)

    def _OnSelect(self, e):
        id = e.GetIndex()
        self.ToggleItem(id)

    def _reset(self):
        self._items = dict()

# ============================================================================

# FIXME: this is broken since the Great Reorganisation of 2010
class SelectColumnsFrame(wx.Frame):
    def __init__(self, parent, id, title, **kwargs):
        wx.Frame.__init__(self, parent, id, title, size=(500, 500), **kwargs)

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

        # select/deselect all buttons
        col_buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        col_sizer.Add(col_buttons_sizer)

        size = (90, 30)
        self.select_all_button = wx.Button(self, label="Select All",
                                           size=size)
        self.Bind(wx.EVT_BUTTON, self.OnSelectAll, self.select_all_button)
        col_buttons_sizer.Add(self.select_all_button)

        self.deselect_all_button = wx.Button(self, label="Deselect All",
                                             size=size)
        self.Bind(wx.EVT_BUTTON, self.OnDeselectAll, self.deselect_all_button)
        col_buttons_sizer.Add(self.deselect_all_button)

        # quick select
        box = wx.StaticBox(self, label="Quick Select")
        qs_super_sizer = wx.StaticBoxSizer(box, orient=wx.HORIZONTAL)
        main_sizer.Add(qs_super_sizer, flag=wx.EXPAND)
        qs_sizer = wx.GridSizer(2, 2)
        qs_super_sizer.Add(qs_sizer)

        rois = [str(roi) for roi in app.rois.keys()]

        # ROI filter
        qs_sizer.Add(wx.StaticText(self, label="Filter by ROI:"),
                             flag=wx.ALIGN_CENTER_VERTICAL)

        self.roi_filter = wx.ComboBox(self, choices=rois)
        qs_sizer.Add(self.roi_filter)
        self.Bind(wx.EVT_COMBOBOX, self.OnFilterROI, self.roi_filter)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnFilterROI, self.roi_filter)

        # ROI selector
        qs_sizer.Add(wx.StaticText(self, label="Select ROI:"),
                             flag=wx.ALIGN_CENTER_VERTICAL)

        self.roi_selector = wx.ComboBox(self, choices=rois)
        qs_sizer.Add(self.roi_selector)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectROI, self.roi_selector)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSelectROI, self.roi_selector)

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
        try:
            roi = int(self.roi_selector.GetValue())
        except ValueError:
            # FIXME: come up with a better dummy value
            roi = 0

        columns = [c.GetText() for c in self.columns_list.GetCheckedItems()]

        self.app.change_plot(roi_number=roi, columns=columns)

        self.Close(True)

    def OnCancelClick(self, e):
        self.Close(True)

    def OnDeselectAll(self, e):
        self.columns_list.UncheckAllShown()

    def OnSelectAll(self, e):
        self.columns_list.CheckAllShown()

    def OnFilterROI(self, e):
        try:
            roi_number = int(self.roi_filter.GetValue())
        except ValueError:
            return

        pattern = "corr_roi*_%d" % (roi_number)
        self.column_filter.SetValue(pattern)

    def OnSelectROI(self, e):
        try:
            roi_number = int(self.roi_selector.GetValue())
        except ValueError:
            return

        self.column_filter.SetValue("")
        self.columns_list.UncheckAll()

        # FIXME: move pattern elsewhere
        pattern = "corr_roi*%d" % (roi_number)

        # FIXME: don't use CheckListCtrl._items; possibly implement
        # CheckListCtrl.FilterByPattern()?
        columns = fnmatch.filter(self.columns_list._items.keys(), pattern)
        self.columns_list.CheckItemStrings(columns)

    def _OnUpdateFilter(self, e):
        pattern = self.column_filter.GetValue()
        self.columns_list.Filter(pattern)


# ============================================================================

class PlotControlPanel(wx.Panel):
    SUM_MODE = 1
    CHANNEL_MODE = 2

    def __init__(self, parent, id, app, **kwargs):
        wx.Panel.__init__(self, parent, id, **kwargs)

        self.parent = parent
        self.app = app

        self.channels = self.parent.plot_panel.channels
        self.channel_nums = self.channels.keys()

        self.main_sizer = main_sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.GridBagSizer()

        # ROI selector
        rois = [str(i) for i in sorted(self.parent.plot_panel.rois.keys())]
        self.roi_selector = wx.ComboBox(parent=self, choices=rois)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectROI, self.roi_selector)
        sizer.Add(wx.StaticText(parent=self, label="ROI:"), pos=(0,0),
                flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.roi_selector, pos=(0,1))

        main_sizer.Add(sizer, flag=wx.EXPAND)

        # draw mode selector
        mode_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.sum_rb = wx.RadioButton(parent=self, id=wx.ID_ANY, label="Sum",
                style=wx.RB_GROUP)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSumMode, self.sum_rb)
        self.chan_rb = wx.RadioButton(parent=self, id=wx.ID_ANY,
                label="Channel")
        self.Bind(wx.EVT_RADIOBUTTON, self.OnChanMode, self.chan_rb)

        mode_sizer.Add(self.sum_rb)
        mode_sizer.Add(self.chan_rb)

        sizer.Add(wx.StaticText(parent=self, label="Mode:"), pos=(1,0),
                flag=wx.ALIGN_TOP)
        sizer.Add(mode_sizer, pos=(1,1))

        # draw channel mode controls
        self._init_chan_mode_ctrls()

        # draw plot options
        box = wx.StaticBox(parent=self, id=wx.ID_ANY, label="Plot Options")
        sizer = wx.StaticBoxSizer(box=box, orient=wx.VERTICAL)
        self.corr_cb = wx.CheckBox(parent=self, id=wx.ID_ANY, label="Use corrected ROIs")
        # FIXME: get the proper default value
        self.corr_cb.SetValue(True)
        self.corr_cb.Disable()
        self.norm_cb = wx.CheckBox(parent=self, id=wx.ID_ANY, label="Normalize data")
        self.Bind(wx.EVT_CHECKBOX, self.OnNormalize, self.norm_cb)

        sizer.Add(self.corr_cb)
        sizer.Add(self.norm_cb)
        main_sizer.Add(sizer, flag=wx.EXPAND)

        # size
        self.SetSizer(main_sizer)
        self.Fit()

        # set default state
        self._set_sum_mode()
        # FIXME: get the proper default value
        self.norm_cb.SetValue(True)

    def _init_chan_mode_ctrls(self):
        box = wx.StaticBox(parent=self, id=wx.ID_ANY, label="Channel Select")
        cm_sizer = wx.StaticBoxSizer(box=box, orient=wx.VERTICAL)

        # channel selector
        self.chan_sel = wx.ComboBox(parent=self,
                                    choices=[str(c) for c in self.channel_nums])

        self.Bind(wx.EVT_COMBOBOX, self.OnSelectChan, self.chan_sel)
        cm_sizer.Add(self.chan_sel)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.chan_prev_btn = wx.Button(parent=self, label="<--")
        self.Bind(wx.EVT_BUTTON, self.OnPrevChan, self.chan_prev_btn)
        self.chan_next_btn = wx.Button(parent=self, label="-->")
        self.Bind(wx.EVT_BUTTON, self.OnNextChan, self.chan_next_btn)

        sizer.Add(self.chan_prev_btn)
        sizer.Add(self.chan_next_btn)

        cm_sizer.Add(sizer)

        self.enable_chan_cb = wx.CheckBox(parent=self, id=wx.ID_ANY,
                                          label="Enable channel")
        self.Bind(wx.EVT_CHECKBOX, self.OnEnableChan, self.enable_chan_cb)
        cm_sizer.Add(self.enable_chan_cb)

        # add to main sizer
        self.main_sizer.Add(cm_sizer)

        self.cm_sizer = cm_sizer

        self.cm_items = (self.chan_prev_btn, self.chan_sel,
                         self.chan_next_btn, self.enable_chan_cb)

    def OnSelectROI(self, e):
        roi = int(self.roi_selector.GetValue())

        if self.in_sum_mode():
            self.parent.plot_panel.change_plot(roi_number=roi, columns=False)
        elif self.in_channel_mode():
            self.parent.plot_panel.plot_channel(channel=self.cur_channel, roi=roi)

    def OnNextChan(self, e):
        self._set_channel(self.cur_channel + 1)

    def OnPrevChan(self, e):
        self._set_channel(self.cur_channel - 1)

    def OnSelectChan(self, e):
        self._set_channel(int(self.chan_sel.GetValue()))

    def OnEnableChan(self, e):
        self.channels[self.cur_channel] = self.enable_chan_cb.GetValue()

    def _set_channel(self, channel):
        if not self.in_channel_mode():
            # FIXME: use a better exception
            raise Exception("Changing channels is not allowed when not in Channel mode")

        # set channel enabled checkbox to appropriate state
        self.enable_chan_cb.SetValue(self.channels[channel])

        # store new channel in internal state
        self.cur_channel = channel

        # update the channel selector dropdown
        self.chan_sel.SetValue(str(channel))

        # disable prev/next buttons when at first/last channel
        if self.cur_channel == self.channel_nums[0]:
            self.chan_prev_btn.Disable()
        else:
            self.chan_prev_btn.Enable()
        if self.cur_channel == self.channel_nums[-1]:
            self.chan_next_btn.Disable()
        else:
            self.chan_next_btn.Enable()

        # update plot to show only the active channel
        self.parent.plot_panel.plot_channel(self.cur_channel)

    def OnChanMode(self, e): self._set_chan_mode()
    def _set_chan_mode(self):
        self.mode = self.CHANNEL_MODE

        # enable elements in the "Channel Select" box
        for item in self.cm_items:
            item.Enable()

        # initialise channel selector to previous state; if there is no
        # previous state, start at the first channel
        try:
            self._set_channel(self.cur_channel)
        except AttributeError:
            self._set_channel(self.channel_nums[0])

        # update plot to show only the active channel
        self.parent.plot_panel.plot_channel(self.cur_channel)

    def OnSumMode(self, e): self._set_sum_mode()
    def _set_sum_mode(self):
        self.mode = self.SUM_MODE

        # disable elements in the "Channel Select" box
        for item in self.cm_items:
            item.Disable()

        # update plot to show the active ROI
        roi = self.roi_selector.GetValue()
        if roi:
            self.parent.plot_panel.change_plot(roi_number=int(roi), columns=False)

    def in_sum_mode(self):
        return self.mode == self.SUM_MODE

    def in_channel_mode(self):
        return self.mode == self.CHANNEL_MODE

    def OnNormalize(self, e):
        """Handle toggling of 'Normalize data' checkbox

        """
        self.parent.plot_panel.change_plot(normalize=self.norm_cb.GetValue())

# ============================================================================

class PlotPanel(wxmpl.PlotPanel):
    def __init__(self, parent, id, data, app, *args, **kwargs):
        wxmpl.PlotPanel.__init__(self, parent, id, *args, **kwargs)

        self.app = app
        self.parent = parent
        self.data = data

        # self.rois is a dict(roi) => [columns]
        # self.channels is a dict(channel) => bool (enabled/disabled)
        self.rois, self.channels = self._parse_columns(self.data.getColumnNames())

        self.plot_opts = dict()

        # colorbar instance variables
        self.img = None
        self.cb = None

    # FIXME: move these default values somewhere else
    def plot(self, x_name, y_name, z_name, normalize=True, colormap="hot",
             roi_number=0, columns=None, title=""):
        # fetch x
        try:
            x_col = self.data.getColumn(x_name)
        except xdp.ColumnNameError:
            util.fatal_error('invalid x-axis column name "%s"', repr(x_name)[1:-1])

        # fetch y
        try:
            y_col = self.data.getColumn(y_name)
        except xdp.ColumnNameError:
            util.fatal_error('invalid y-axis column name "%s"', repr(x_name)[1:-1])

        # determine which columns to plot
        if not columns:
            columns = []
            for col in self.rois[roi_number]:
                roi, channel = util.parse_data_column_name(col)
                if self.channels[channel]:
                    columns.append(col)

        # calculate z
        zExpr = '+'.join(['$'+x for x in columns])
        if normalize:
            if self.data.hasColumn(z_name):
                zExpr = '(%s)/$%s' % (zExpr, z_name)
            else:
                util.fatal_error('invalid z-axis column name "%s"', repr(z_name)[1:-1])
        z_col = self.data.evaluate(zExpr)
        x, y, z = fdata.makeXYZ(x_col, y_col, z_col)

        # set up axes
        fig = self.get_figure()
        axes = fig.gca()

        if matplotlib.__version__ >= '0.81':
            axes.yaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
            axes.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(5))

            axes.xaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
            axes.xaxis.set_major_locator(matplotlib.ticker.LinearLocator(5))

        axes.set_title(title)
        axes.set_ylabel(y_name)

        # plot the data and colorbar
        extent = min(x), max(x), min(y), max(y)

        # if we're replotting the image, update the colorbar
        if self.img:
            # we need to update both the image's data and the colorbar's data
            self.img.set_data(z)
            self.cb.set_array(z)

            # recalculate limits of the colorbar
            self.cb.autoscale()

            # redraw the image
            self.img.changed()

        # otherwise, create a new colorbar
        else:
            self.img = axes.imshow(z, cmap=getattr(matplotlib.cm, colormap),
                        origin='lower', aspect='equal', interpolation='nearest',
                        extent=extent)
            self.cb = fig.colorbar(self.img, cax=None, orientation='vertical')

        # force a redraw of the figure
        axes.figure.canvas.draw()

        # save current plot parameters for later retrieval
        self.plot_opts["x_name"] = x_name
        self.plot_opts["y_name"] = y_name
        self.plot_opts["z_name"] = z_name
        self.plot_opts["normalize"] = normalize
        self.plot_opts["colormap"] = colormap
        self.plot_opts["roi_number"] = roi_number
        self.plot_opts["columns"] = columns
        self.plot_opts["title"] = title

        # update plot cp elements
        # FIXME: this should be subsumed into the new defaults location
        self.parent.plot_cp.roi_selector.SetValue(str(roi_number))

    def plot_channel(self, channel, roi=None):
        """Plot an individual channel.

        """

        if roi is None:
            roi = self.plot_opts["roi_number"]

        col = util.get_data_column_name(roi=roi, channel=channel)
        self.change_plot(columns=[col], roi_number=roi)

    def change_plot(self, **kwargs):
        """Update the current plot with the given parameters.

        Any parameters not specified in kwargs are left unchanged.

        """

        opts = copy.copy(self.plot_opts)
        opts.update(kwargs)
        self.plot(**opts)

    def _parse_columns(self, columns):
        channels = dict()
        rois = dict()

        for col in columns:
            try:
                roi, channel = util.parse_data_column_name(col)
            except exc.InvalidDataColumnNameException:
                continue

            channels[channel] = True
            rois.setdefault(roi, []).append(col)

        return rois, channels

# ============================================================================

class EditPlotTitleDialog(wx.Dialog):
    def __init__(self, parent, id, title="Edit Plot Title", **kwargs):
        wx.Dialog.__init__(self, parent, id, title, size=(300,75), **kwargs)
        self.parent = parent

        main_sizer = wx.GridBagSizer()

        main_sizer.Add(wx.StaticText(parent=self, label="Plot title: "),
                flag=wx.ALIGN_CENTER_VERTICAL, pos=(0,0))

        self.title_txt = wx.TextCtrl(parent=self, style=wx.TE_PROCESS_ENTER)
        self.title_txt.SetValue(self.parent.plot_panel.plot_opts["title"])
        self.Bind(wx.EVT_TEXT_ENTER, self.OnOK, self.title_txt)
        self.title_txt.SetMinSize((200, -1))
        main_sizer.Add(self.title_txt, pos=(0,1))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, label="OK", id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnOK, ok_btn)
        cancel_btn = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)

        sizer.Add(ok_btn)
        sizer.Add(cancel_btn)
        main_sizer.Add(sizer, pos=(1,1))

        self.SetSizer(main_sizer)

    def OnCancel(self, e):
        self.Close()

    def OnOK(self, e):
        self.parent.plot_panel.change_plot(title=self.title_txt.GetValue())
        self.Close()

class EditChannelsDialog(wx.Dialog):
    # FIXME: implement
    pass

# ============================================================================

class MainWindow(wx.Frame):
    ABOUT_TITLE = 'About frankenplot'
    ABOUT_MESSAGE = ('frankenplot %s\n' % __version__
        + 'Written by Ken McIvor <mcivor@iit.edu>\n'
        + 'Copyright (c) 2006--2010, Illinois Institute of Technology')

    def __init__(self, parent, id, title, data, app, **kwargs):
        wx.Frame.__init__(self, parent, id, title, **kwargs)

        # retain reference to App
        self.app = app

        # initialise subpanels
        self.plot_panel = PlotPanel(parent=self, id=wx.ID_ANY, data=data, app=app)
        self.plot_cp = PlotControlPanel(parent=self, id=wx.ID_ANY, app=app)

        # misc initialisation
        self._initialise_printer()
        self._create_menus()

        # lay out frame
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot_panel, proportion=1)
        sizer.Add(self.plot_cp)
        self.SetSizer(sizer)
        self.Fit()

    def _initialise_printer(self):
        printer_data = wx.PrintData()
        printer_data.SetPaperId(wx.PAPER_LETTER)

        if callable(getattr(printer_data, 'SetPrinterCommand', None)):
            printer_data.SetPrinterCommand(wxmpl.POSTSCRIPT_PRINTING_COMMAND)

        self.printer = wxmpl.FigurePrinter(self, printer_data)

    def _create_menus(self):
        # menu bar
        menuBar = wx.MenuBar()
        self.SetMenuBar(menuBar)

        # File menu
        fileMenu = wx.Menu()
        menuBar.Append(fileMenu, '&File')

        item = fileMenu.Append(wx.ID_OPEN, "&Open File...\tCtrl+O",
            "Open a different data file")
        item.Enable(False)

        fileMenu.AppendSeparator()

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

        item = editMenu.Append(id=wx.ID_ANY, text="Plot Tit&le...",
                help="Edit plot title")
        self.Bind(wx.EVT_MENU, self.OnMenuEditPlotTitle, item)

        # FIXME: implement
        item = editMenu.Append(id=wx.ID_ANY, text="Col&ormap...",
                help="Edit plot colormap")
        item.Enable(False)

        editMenu.AppendSeparator()

        item = editMenu.Append(wx.ID_ANY, "Cha&nnels...",
            "Edit channels")
        self.Bind(wx.EVT_MENU, self.OnMenuEditChannels, item)
        item.Enable(False)

        item = editMenu.Append(wx.ID_ANY, "&Columns...",
            "Select displayed columns")
        self.Bind(wx.EVT_MENU, self.OnMenuSelectColumns, item)
        item.Enable(False)

        # View menu
        view_menu = wx.Menu()
        menuBar.Append(view_menu, "&View")

        item = view_menu.Append(wx.ID_ANY, "Plot Controls",
                help="Toggle plot controls", kind=wx.ITEM_CHECK)
        item.Enable(False)

        # Help menu
        helpMenu = wx.Menu()
        menuBar.Append(helpMenu, '&Help')

        item = helpMenu.Append(wx.ID_ANY, '&About...',
            'Display version information')
        self.Bind(wx.EVT_MENU, self.OnMenuHelpAbout, item)

    def OnMenuFileSave(self, evt):
        """
        Handles File->Save menu events.
        """
        fileName = wx.FileSelector('Save Plot', default_extension='png',
            wildcard=('Portable Network Graphics (*.png)|*.png|'
                + 'Encapsulated Postscript (*.eps)|*.eps|All files (*.*)|*.*'),
            parent=self, flags=wx.SAVE|wx.OVERWRITE_PROMPT)

        if not fileName:
            return

        path, ext = os.path.splitext(fileName)
        ext = ext[1:].lower()

        if ext != 'png' and ext != 'eps':
            error_message = (
                'Only the PNG and EPS image formats are supported.\n'
                'A file extension of `png\' or `eps\' must be used.')
            wx.MessageBox(error_message, 'Error - plotit',
                parent=self, style=wx.OK|wx.ICON_ERROR)
            return

        try:
            self.plot_panel.print_figure(fileName)
        except IOError, e:
            if e.strerror:
                err = e.strerror
            else:
                err = e

            wx.MessageBox('Could not save file: %s' % err, 'Error - plotit',
                parent=self, style=wx.OK|wx.ICON_ERROR)

    def OnMenuFilePageSetup(self, evt):
        """
        Handles File->Page Setup menu events
        """
        self.printer.pageSetup()

    def OnMenuFilePrintPreview(self, evt):
        """
        Handles File->Print Preview menu events
        """
        self.printer.previewFigure(self.get_figure())

    def OnMenuFilePrint(self, evt):
        """
        Handles File->Print menu events
        """
        self.printer.printFigure(self.get_figure())

    def OnMenuFileClose(self, evt):
        """
        Handles File->Close menu events.
        """
        self.Close()

    def OnMenuHelpAbout(self, evt):
        """
        Handles Help->About menu events.
        """
        wx.MessageBox(self.ABOUT_MESSAGE, self.ABOUT_TITLE, parent=self,
            style=wx.OK)

    def OnMenuSelectColumns(self, evt):
        frame = SelectColumnsFrame(parent=self, id=wx.ID_ANY, title="Select Columns")
        frame.Show(True)

    def OnMenuEditChannels(self, e):
        dlg = EditChannelsDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def OnMenuEditPlotTitle(self, e):
        dlg = EditPlotTitleDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def get_figure(self):
        return self.plot_panel.get_figure()

    def plot(self, *args, **kwargs):
        return self.plot_panel.plot(*args, **kwargs)

# ============================================================================

class PlotApp(wx.App):
    def __init__(self, filename=None, **kwargs):
        self.filename = filename

        # FIXME: move to frankenplot.data
        # load the data file
        try:
            self.hdr, self.data = xdp.io.readFile(filename)
        except IOError, e:
            if e.strerror:
                util.fatal_error('could not load `%s\': %s', filename, e.strerror)
            else:
                util.fatal_error('could not load `%s\': %s', filename, e)
        # if filename is None, xdp.io.readFile raises:
        #     AttributeError: 'NoneType' object has no attribute 'rfind'
        except AttributeError:
            self.hdr = None
            self.data = None

        wx.App.__init__(self, **kwargs)

    def OnInit(self):
        self.main_window = MainWindow(parent=None,
                                      id=wx.ID_ANY,
                                      title="frankenplot",
                                      data=self.data)
        self.main_window.Show(True)
        return True

    def plot(self, *args, **kwargs):
        return self.main_window.plot(*args, **kwargs)
