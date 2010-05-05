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

from frankenplot import (data as fdata,
                         defaults,
                         exceptions as exc,
                         expression,
                         util,
                         __version__)
from expression import ArbitraryExpression, ChannelExpression, RefExpression, ROIExpression, SampleExpression

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
    def __init__(self, parent, id, app, **kwargs):
        wx.Panel.__init__(self, parent, id, **kwargs)

        self.parent = parent
        self.app = app

    def OnPageSelected(self, e):
        """Callback for when the page is selected in a Choicebook

        """
        pass

    def OnPageDeselected(self, e):
        """Callback for when the page is deselected in a Choicebook

        """
        pass

# ============================================================================

class FluorControlsPanel(PlotControlPanel):
    """Controls for Fluorescence Mode

    """

    SUM_MODE = 1
    CHANNEL_MODE = 2

    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

        self.channels = app.channels
        self.channel_state = dict((chan, True) for chan in self.channels)

        # initialise and lay out GUI elements
        self._init_gui_elements()

        # set default state
        self._set_sum_mode()
        # FIXME: get the proper default value
        self.norm_cb.SetValue(True)

    def _init_gui_elements(self):
        self.main_sizer = main_sizer = wx.BoxSizer(wx.VERTICAL)

        self._init_roi_selector()
        self._init_chan_mode_ctrls()
        self._init_plot_options()

        self.SetSizer(main_sizer)
        self.Fit()

    def _init_roi_selector(self):
        sizer = wx.GridBagSizer()

        # ROI selector
        # FIXME: allow switch between corrected/uncorrected ROIs
        rois = [str(i) for i in sorted(self.app.corr_rois.keys())]
        self.roi_selector = wx.ComboBox(parent=self, choices=rois)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectROI, self.roi_selector)
        sizer.Add(wx.StaticText(parent=self, label="ROI:"), pos=(0,0),
                flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.roi_selector, pos=(0,1))

        # mode selector
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

        self.main_sizer.Add(sizer, flag=wx.EXPAND)

    def _init_chan_mode_ctrls(self):
        box = wx.StaticBox(parent=self, id=wx.ID_ANY, label="Channel Select")
        cm_sizer = wx.StaticBoxSizer(box=box, orient=wx.VERTICAL)

        # channel selector
        self.chan_sel = wx.ComboBox(parent=self,
                                    choices=[str(c) for c in self.channels])

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

        self.cm_items = (self.chan_prev_btn, self.chan_sel,
                         self.chan_next_btn, self.enable_chan_cb)

    def _init_plot_options(self):
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

        self.main_sizer.Add(sizer, flag=wx.EXPAND)

    def _plot_roi(self):
        roi = int(self.roi_selector.GetValue())
        expr = ROIExpression(roi)
        self.app.plot(expr)

    def _plot_channel(self):
        roi = int(self.roi_selector.GetValue())
        channel = int(self.chan_sel.GetValue())
        expr = ChannelExpression(roi=roi, channel=channel)
        self.app.plot(expr)

    def OnSelectROI(self, e):
        roi = int(self.roi_selector.GetValue())

        if self.in_sum_mode():
            self._plot_roi()
        elif self.in_channel_mode():
            self._plot_channel()

    def OnNextChan(self, e):
        self._set_channel(self.cur_channel + 1)

    def OnPrevChan(self, e):
        self._set_channel(self.cur_channel - 1)

    def OnSelectChan(self, e):
        self._set_channel(int(self.chan_sel.GetValue()))

    def OnEnableChan(self, e):
        """Enable/disable a channel by updating group memberships

        """
        channel = int(self.chan_sel.GetValue())
        state = self.enable_chan_cb.GetValue()
        self.channel_state[channel] = state

        # update the membership of every ROI group
        # (%roi_1, ... , %roi_N, %corr_roi_1, ... , %corr_roi_N)
        for group_name in self.app.roi_group_names:
            roi, corrected = util.parse_roi_group_name(group_name)
            group = self.app.groups[group_name]

            col = util.get_data_column_name(roi, channel, corrected)

            if state:
                group.add(col)
            else:
                group.discard(col)

    def _set_channel(self, channel):
        if not self.in_channel_mode():
            # FIXME: use a better exception
            raise Exception("Changing channels is not allowed when not in Channel mode")

        # set channel enabled checkbox to appropriate state
        self.enable_chan_cb.SetValue(self.channel_state[channel])

        # store new channel in internal state
        self.cur_channel = channel

        # update the channel selector dropdown
        self.chan_sel.SetValue(str(channel))

        # disable prev/next buttons when at first/last channel
        if self.cur_channel == self.channels[0]:
            self.chan_prev_btn.Disable()
        else:
            self.chan_prev_btn.Enable()
        if self.cur_channel == self.channels[-1]:
            self.chan_next_btn.Disable()
        else:
            self.chan_next_btn.Enable()

        # update plot to show only the active channel
        self._plot_channel()

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
            self._set_channel(self.channels[0])

    def OnSumMode(self, e): self._set_sum_mode()
    def _set_sum_mode(self):
        self.mode = self.SUM_MODE

        # disable elements in the "Channel Select" box
        for item in self.cm_items:
            item.Disable()

        # update plot to show the active ROI
        roi = self.roi_selector.GetValue()
        if roi:
            self._plot_roi()

    def in_sum_mode(self):
        return self.mode == self.SUM_MODE

    def in_channel_mode(self):
        return self.mode == self.CHANNEL_MODE

    def OnNormalize(self, e):
        """Handle toggling of 'Normalize data' checkbox

        """
        expr = self.app.plot_panel.plot_opts["z_expr"]
        expr.normalize = self.norm_cb.GetValue()
        self.app.plot(expr)

    def OnPageDeselected(self, e):
        pass

    def OnPageSelected(self, e):
        if self.in_sum_mode():
            # ignore the ValueError that's raised when there's no ROI selected
            # and we want an ROI plot (occurs on startup when PlotApp is
            # initialised but there's no plot yet)
            try:
                self._plot_roi()
            except ValueError:
                if self.roi_selector.GetValue():
                    raise
        elif self.in_channel_mode():
            self._plot_channel()
        else:
            raise Exception("unknown mode")

# ============================================================================

class TransControlsPanel(PlotControlPanel):
    """Controls for Transmission Mode

    """

    SAMPLE_MODE = 1
    REF_MODE = 2
    CUSTOM_MODE = 3

    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

        self.id = id

        self._init_gui_elements()

        # start in sample mode by default
        self.mode = self.SAMPLE_MODE

    def _init_gui_elements(self):
        panel = wx.Panel(parent=self, id=wx.ID_ANY)

        grid = wx.FlexGridSizer(rows=3, cols=1)

        # sample transmission
        self.samp_rb = wx.RadioButton(panel, wx.ID_ANY, "Sample transmission",
                style=wx.RB_GROUP)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSampMode, self.samp_rb)
        grid.Add(self.samp_rb)

        # reference transmission
        self.ref_rb = wx.RadioButton(panel, wx.ID_ANY, "Reference transmission")
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRefMode, self.ref_rb)
        grid.Add(self.ref_rb)

        # custom
        self.custom_rb = wx.RadioButton(panel, wx.ID_ANY, "Custom")
        self.custom_rb.Disable()
        self.Bind(wx.EVT_RADIOBUTTON, self.OnCustomMode, self.custom_rb)
        grid.Add(self.custom_rb)

        panel.SetSizer(grid)
        grid.Fit(panel)
        self.panel = panel

    def in_sample_mode(self):
        return self.mode == self.SAMPLE_MODE

    def in_ref_mode(self):
        return self.mode == self.REF_MODE

    def in_custom_mode(self):
        return self.mode == self.CUSTOM_MODE

    def _plot_sample(self):
        expr = SampleExpression()
        self.app.plot(expr)

    def _plot_ref(self):
        expr = RefExpression()
        self.app.plot(expr)

    def _plot_custom(self):
        pass

    def OnSampMode(self, e):
        self.mode = self.SAMPLE_MODE
        try:
            self._plot_sample()
        except xdp.errors.ColumnNameError:
            # FIXME: do something better? move back to previous selection?
            pass

    def OnRefMode(self, e):
        self.mode = self.REF_MODE
        try:
            self._plot_ref()
        except xdp.errors.ColumnNameError:
            # FIXME: do something better? move back to previous selection?
            pass

    def OnCustomMode(self, e):
        self.mode = self.CUSTOM_MODE
        self._plot_custom()

    def OnPageSelected(self, e):
        if self.in_sample_mode():
            self._plot_sample()
        elif self.in_ref_mode():
            self._plot_ref()
        elif self.in_custom_mode():
            self._plot_custom()
        else:
            # FIXME use better exception
            raise Exception("unknown mode")


# ============================================================================

class CMapControlsPanel(PlotControlPanel):
    """Controls for Colormap Mode

    """
    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

# ============================================================================

class PlotControlsFrame(wx.Frame):
    def __init__(self, parent, id, app, **kwargs):
        wx.Frame.__init__(self, parent, id, title="Plot Controls", **kwargs)

        self.parent = parent
        self.app = app

        self.cb = PlotControlsCB(parent=self, id=wx.ID_ANY, app=app)

class PlotControlsCB(wx.Choicebook):
    PAGES = (
        ("Fluorescence Mode", FluorControlsPanel),
        ("Transmission Mode", TransControlsPanel),
        ("Colormap Mode", CMapControlsPanel),
    )

    def __init__(self, parent, id, app):
        wx.Choicebook.__init__(self, parent, id)

        self.parent = parent
        self.app = app

        self._init_pages()

    def _init_pages(self):
        # initialise pages
        for name, panel_cls in self.PAGES:
            panel = panel_cls(parent=self, id=wx.ID_ANY, app=self.app)
            self.AddPage(panel, name)

        # bind to page changes
        self.Bind(wx.EVT_CHOICEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_CHOICEBOOK_PAGE_CHANGED, self.OnPageChanged)

        # manually call the PAGE_CHANGED callback so any initialisation
        # routines run
        self.OnPageChanged(None)

    def OnPageChanging(self, e):
        # handle callbacks
        old_panel = self.GetCurrentPage()
        old_panel.OnPageDeselected(e)

    def OnPageChanged(self, e):
        new_panel = self.GetCurrentPage()

        # update app.plot_cp pointer
        self.app.plot_cp = new_panel

        # handle callbacks
        new_panel.OnPageSelected(e)

# ============================================================================


class PlotPanel(wxmpl.PlotPanel):
    def __init__(self, parent, id, data, app, *args, **kwargs):
        wxmpl.PlotPanel.__init__(self, parent, id, *args, **kwargs)

        self.app = app
        self.parent = parent
        self.data = data

        # dict for storing the parameters of the current plot so that it's
        # easy to change the plot later (see change_plot())
        self.plot_opts = dict()
        self.roi_plot_opts = dict()

        # colorbar instance variables
        self.img = None
        self.cb = None

    def plot(self, z_expr, **kwargs):
        x_name = kwargs.pop("x_name", defaults.x_name)
        y_name = kwargs.pop("y_name", defaults.y_name)
        title = kwargs.pop("title", defaults.title)
        colormap = kwargs.pop("colormap", defaults.colormap)

        # get string form of expression
        z_expr_s = str(z_expr)

        # replace groups in the expression with their constituent columns
        z_expr_s = expression.expand_groups(z_expr_s, self.app.groups)
        print z_expr_s

        # get the plot data
        x, y, z = None, None, None
        try:
            x, y, z = fdata.get_plot_data(self.app.data, x_name, y_name, z_expr_s)
        except xdp.errors.ColumnNameError, e:
            msg = "No such column in data file: '%s'" % e
            title = "Plot Error"

            dlg = wx.MessageDialog(self, msg, title, wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

            raise

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

        # call on_plot callback
        z_expr.on_plot(fig, self.app)

        # save current plot parameters for later retrieval
        self.plot_opts["x_name"] = x_name
        self.plot_opts["y_name"] = y_name
        self.plot_opts["z_expr"] = z_expr
        self.plot_opts["colormap"] = colormap
        self.plot_opts["title"] = title

    def change_plot(self, **kwargs):
        """Update the current plot with the given parameters.

        Any parameters not specified in kwargs are left unchanged.

        """

        opts = copy.copy(self.plot_opts)
        opts.update(kwargs)
        self.plot(**opts)

    def change_roi_plot(self, **kwargs):
        opts = copy.copy(self.roi_plot_opts)
        opts.update(self.plot_opts)
        opts.update(kwargs)
        self.plot_roi(**opts)

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



class ArbitraryExpressionDialog(wx.Dialog):
    def __init__(self, parent, id, app, title="Plot Arbitrary Expression", **kwargs):
        wx.Dialog.__init__(self, parent, id, title, size=(300,75), **kwargs)
        self.app = app
        self.parent = parent

        main_sizer = wx.GridBagSizer()

        main_sizer.Add(wx.StaticText(parent=self, label="Expression: "),
                flag=wx.ALIGN_CENTER_VERTICAL, pos=(0,0))

        self.expr_txt = wx.TextCtrl(parent=self, style=wx.TE_PROCESS_ENTER)
        self.expr_txt.SetValue(str(self.app.plot_panel.plot_opts["z_expr"]))
        self.Bind(wx.EVT_TEXT_ENTER, self.OnOK, self.expr_txt)
        self.expr_txt.SetMinSize((200, -1))
        main_sizer.Add(self.expr_txt, pos=(0,1))

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
        expr = ArbitraryExpression(self.expr_txt.GetValue())
        self.app.plot(expr)
        self.Close()

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

        # add subpanels to App namespace
        self.app.plot_panel = self.plot_panel

        # misc initialisation
        self._initialise_printer()
        self._create_menus()

        # lay out frame
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot_panel, proportion=1)
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

        # Plot menu
        plot_menu = wx.Menu()
        menuBar.Append(plot_menu, "&Plot")

        item = plot_menu.Append(wx.ID_ANY, "&Expression...\tCtrl+T",
            help="Plot arbitrary expression")
        self.Bind(wx.EVT_MENU, self.OnMenuPlotExpr, item)

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

    def OnMenuPlotExpr(self, e):
        dlg = ArbitraryExpressionDialog(parent=self, app=self.app, id=wx.ID_ANY)
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

        # self.rois is a dict: 'roi' => list (of columns)
        # self.channels is a list of channels
        self.rois, self.corr_rois, self.channels = self._parse_columns(self.data.getColumnNames())

        # initialise groups (dict: group name (str) => members (set))
        self.groups = {}

        # ROI group names (%roi_1, ... , %roi_N, %corr_roi_1, ... , %corr_roi_N)
        self.roi_group_names = []

        # create the ROI groups
        self._create_roi_groups(self.rois, corrected=False)
        self._create_roi_groups(self.corr_rois, corrected=True)

        wx.App.__init__(self, **kwargs)

    def OnInit(self):
        self.main_window = MainWindow(parent=None,
                                      id=wx.ID_ANY,
                                      title="frankenplot",
                                      data=self.data,
                                      app=self)
        self.main_window.Show(True)

        self.plot_ctrls = PlotControlsFrame(parent=None, id=wx.ID_ANY, app=self)
        self.plot_ctrls.Show(True)

        return True

    def plot(self, *args, **kwargs):
        return self.main_window.plot_panel.plot(*args, **kwargs)

    def _parse_columns(self, columns):
        channels = dict()
        rois = dict()
        corr_rois = dict()

        for col in columns:
            try:
                roi, channel, corrected = util.parse_data_column_name(col)
            except exc.InvalidDataColumnNameException:
                continue

            channels[channel] = True

            # associate the column with its ROI
            if corrected:
                d = corr_rois
            else:
                d = rois
            d.setdefault(roi, []).append(col)

        return rois, corr_rois, channels.keys()

    def _create_roi_groups(self, rois, corrected):
        for roi, cols in rois.iteritems():
            group_name = util.get_roi_group_name(roi, corrected)
            members = set(cols)
            self.add_group(group_name, members)
            self.roi_group_names.append(group_name)

    def add_group(self, group_name, members, overwrite=False):
        group = {group_name: members}

        if group_name in self.groups and not overwrite:
            raise ValueError("group already exists: '%s'" % group_name)

        self.groups.update(group)
