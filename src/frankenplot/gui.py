#
# frankenplot.gui: wxPython elements
#

import copy
import fnmatch
import os.path
import re
import sys
import math

import matplotlib

import numpy as np

import wx
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ListCtrlAutoWidthMixin

# FIXME: provisional, remove soon
import wxmpl
import xdp

from mpl_toolkits.mplot3d import Axes3D, axes3d

from frankenplot import (data as fdata,
                         defaults,
                         exceptions as exc,
                         expression,
                         util,
			 script,
                         __version__)
from expression import ArbitraryExpression, ChannelExpression, RefExpression, ROIExpression, SampleExpression, TransExpression

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
            roi = int(self.roi_selector.GetStringSelection())
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
            roi_number = int(self.roi_selector.GetStringSelection())
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
        self.roi_selector = wx.Choice(parent=self, choices=rois)
        self.Bind(wx.EVT_CHOICE, self.OnSelectROI, self.roi_selector)
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
        self.main_sizer.Add(cm_sizer, flag=wx.EXPAND)

        self.cm_items = (self.chan_prev_btn, self.chan_sel,
                         self.chan_next_btn, self.enable_chan_cb)

    def _init_plot_options(self):
        box = wx.StaticBox(parent=self, id=wx.ID_ANY, label="Plot Options")
        sizer = wx.StaticBoxSizer(box=box, orient=wx.VERTICAL)

        self.corr_cb = wx.CheckBox(parent=self, id=wx.ID_ANY, label="Use corrected ROIs")
        self.corr_cb.SetValue(defaults.fluor_mode.corrected)
        self.Bind(wx.EVT_CHECKBOX, self.OnCorrected, self.corr_cb)

        self.norm_cb = wx.CheckBox(parent=self, id=wx.ID_ANY, label="Normalize data")
        self.norm_cb.SetValue(defaults.fluor_mode.normalize)
        self.Bind(wx.EVT_CHECKBOX, self.OnNormalize, self.norm_cb)

        sizer.Add(self.corr_cb)
        sizer.Add(self.norm_cb)

        self.main_sizer.Add(sizer, flag=wx.EXPAND)

    def _plot(self):
        """Plot using the given parameters based on the current mode

        """
        if self.in_sum_mode():
            self._plot_roi()
        elif self.in_channel_mode():
            self._plot_channel()
        else:
            raise UnknownPlotModeException()

    def _plot_roi(self):
        try:
            roi = int(self.roi_selector.GetStringSelection())
        except ValueError:
            # if there's no value in the ROI selector, don't plot anything
            # (this happens on startup)
            return

        normalize = self.norm_cb.GetValue()
        corrected = self.corr_cb.GetValue()

        expr = ROIExpression(roi, normalize=normalize, corrected=corrected)
        self.app.plot(expr, groups=self._get_groups())

    def _plot_channel(self):
        roi = int(self.roi_selector.GetStringSelection())
        channel = int(self.chan_sel.GetValue())

        normalize = self.norm_cb.GetValue()
        corrected = self.corr_cb.GetValue()

        expr = ChannelExpression(roi=roi, channel=channel,
                                 normalize=normalize, corrected=corrected)
        self.app.plot(expr)

    def _get_groups(self):
        """Fluorescence Mode-specific groups

        Since we don't want to modify the application-wide ROI groups since
        users would expect to have an ROI group expand to all channels when
        not in Fluoresence Mode, we need to make of copy of app.groups and
        then remove the columns corresponding to disabled channels from all of
        the ROI groups (%corr_roi_* and %roi_*) from the copy.
        """

        groups = copy.deepcopy(self.app.groups)

        # remove disabled channels from each ROI group
        for channel, state in self.channel_state.iteritems():
            if state:
                continue

            # remove the channel from each ROI group
            for group_name in self.app.roi_group_names:
                roi, corrected = util.parse_roi_group_name(group_name)
                group = groups[group_name]

                # determine the column name for the ROI+channel combination
                col = util.get_data_column_name(roi, channel, corrected)

                group.discard(col)

        return groups

    def OnSelectROI(self, e):
        self._plot()

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
        self._plot_roi()

    def in_sum_mode(self):
        return self.mode == self.SUM_MODE

    def in_channel_mode(self):
        return self.mode == self.CHANNEL_MODE

    def OnNormalize(self, e):
        """Handle toggling of 'Normalize data' checkbox

        """
        self._plot()

    def OnCorrected(self, e):
        self._plot()

    def OnPageDeselected(self, e):
        pass

    def OnPageSelected(self, e):
        self._plot()

# ============================================================================

class TransControlsPanel(PlotControlPanel):
    """Controls for Transmission Mode

    """

    SAMPLE_MODE = 1
    REF_MODE = 2
    CUSTOM_COLS_MODE = 3
    CUSTOM_EXPR_MODE = 4

    class CustomColsPanel(wx.Panel):
        def __init__(self, parent, id, app, **kwargs):
            wx.Panel.__init__(self, parent, id, **kwargs)
            self.parent = parent
            self.app = app

            self._init_gui_elements()

        def _init_gui_elements(self):
            box = wx.StaticBox(self, wx.ID_ANY, "Column Ratio Expression")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            grid = wx.GridBagSizer(5, 2)

            cols = ["$" + col for col in self.app.columns]
            groups = self.app.groups.keys()
            choices = util.natural_sort(cols + groups)

            # I_t
            grid.Add(wx.StaticText(self, wx.ID_ANY, "Numerator:"), (0,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.it_cb = wx.ComboBox(self, choices=choices, size=(150, 27))
            grid.Add(self.it_cb, (0,1))

            # I_o
            grid.Add(wx.StaticText(self, wx.ID_ANY, "Denominator:"), (1,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.io_cb = wx.ComboBox(self, choices=choices, size=(150, 27))
            grid.Add(self.io_cb, (1,1))

            self.log_cb = wx.CheckBox(self, wx.ID_ANY, "take logarithm")
            grid.Add(self.log_cb, (2,1))

            # Need a timer to automatically replot
            self.autoplotTimer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.OnPlot, self.autoplotTimer)
            self.autoplot_cb = wx.CheckBox(self, wx.ID_ANY, "autoplot")
            self.autoplot_cb.Bind(wx.EVT_CHECKBOX, self.toggleAutoplot)
            grid.Add(self.autoplot_cb, (3,1))

            self.plot_btn = wx.Button(self, wx.ID_ANY, "Plot")
            self.Bind(wx.EVT_BUTTON, self.OnPlot, self.plot_btn)
            grid.Add(self.plot_btn, (4,1), span=(1,2))

            sizer.Add(grid)
            self.SetSizer(sizer)
            sizer.Fit(self)

        def toggleAutoplot(self, event):
            if self.autoplot_cb.IsChecked():
                every_second = 1000 # 1000 milliseconds
                self.autoplotTimer.Start(every_second)
            else:
                self.autoplotTimer.Stop()

        def _plot(self):
            # remove the preceding dollar signs
            Io = self.io_cb.GetValue()[1:]
            It = self.it_cb.GetValue()[1:]

            self.parent._set_custom_values(Io, It)

            if self.log_cb.IsChecked():
                expr_str = defaults.trans_mode.log_expr
            else:
                expr_str = defaults.trans_mode.scalar_expr

            expr_str = expr_str % dict(Io="$"+Io, It="$"+It)

            expr = ArbitraryExpression(expr_str)
            self.app.plot(expr)

        def OnPlot(self, e):
            self._plot()

    class CustomExprPanel(wx.Panel):
        def __init__(self, parent, id, app, **kwargs):
            wx.Panel.__init__(self, parent, id, **kwargs)
            self.app = app

            self._init_gui_elements()

        def _init_gui_elements(self):
            box = wx.StaticBox(self, wx.ID_ANY, "Custom Expression")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            grid = wx.GridBagSizer(2, 2)

            # expr_txt
            grid.Add(wx.StaticText(self, wx.ID_ANY, "Expression:"), (0,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.expr_txt = wx.TextCtrl(self, size=(150, 27.5),
                    style=wx.TE_PROCESS_ENTER)
            self.Bind(wx.EVT_TEXT_ENTER, self.OnPlot, self.expr_txt)
            grid.Add(self.expr_txt, (0,1))

            self.plot_btn = wx.Button(self, wx.ID_ANY, "Plot")
            self.Bind(wx.EVT_BUTTON, self.OnPlot, self.plot_btn)
            grid.Add(self.plot_btn, (1,1))

            sizer.Add(grid)
            self.SetSizer(sizer)
            sizer.Fit(self)

        def _plot(self):
            expr = ArbitraryExpression(self.expr_txt.GetValue())
            self.app.plot(expr)

        def OnPlot(self, e):
            self._plot()

    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

        self._init_gui_elements()

        # start in column mode by default
        self.mode = self.CUSTOM_COLS_MODE

        # find suitable columns to use
        cols = ["$" + col for col in self.app.columns]
        groups = self.app.groups.keys()
        choices = util.natural_sort(cols + groups)

        if len(choices) <= 1:
            print "Warning: not enough columns in this datafile!\n"

        if ("$"+defaults.trans_mode.samp_mode.Io in choices) and ("$"+defaults.trans_mode.samp_mode.It in choices):
            self._set_custom_values(defaults.trans_mode.samp_mode.Io,
                                defaults.trans_mode.samp_mode.It)
        else:
            self._set_custom_values((choices[0])[1:],(choices[1])[1:])

    def _init_gui_elements(self):
    	panel = self.panel = wx.Panel(parent=self, id=wx.ID_ANY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = sizer

        #these are no longer options
        """
        # sample transmission
        self.samp_rb = wx.RadioButton(panel, wx.ID_ANY, "Sample transmission",
                style=wx.RB_GROUP)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnSampMode, self.samp_rb)
        sizer.Add(self.samp_rb)

        # reference transmission
        self.ref_rb = wx.RadioButton(panel, wx.ID_ANY, "Reference transmission")
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRefMode, self.ref_rb)
        sizer.Add(self.ref_rb)
        """

        """
        # custom columns
        self.custom_cols_rb = wx.RadioButton(self.panel, wx.ID_ANY, "Custom columns")
        self.Bind(wx.EVT_RADIOBUTTON, self.OnCustomColsMode, self.custom_cols_rb)
        sizer.Add(self.custom_cols_rb)
        """

        self.custom_cols_panel = self.CustomColsPanel(self, wx.ID_ANY, self.app)
        sizer.Add(self.custom_cols_panel, flag=wx.EXPAND)

        """
        # custom expression
        self.custom_expr_rb = wx.RadioButton(panel, wx.ID_ANY, "Custom expression")
        self.Bind(wx.EVT_RADIOBUTTON, self.OnCustomExprMode, self.custom_expr_rb)
        self.sizer.Add(self.custom_expr_rb)
        """

        self.custom_expr_panel = self.CustomExprPanel(self, wx.ID_ANY, self.app)
        self.sizer.Add(self.custom_expr_panel)

        # size and fit
        panel.SetSizer(sizer)
        sizer.Fit(panel)

    def in_sample_mode(self):
        return self.mode == self.SAMPLE_MODE

    def in_ref_mode(self):
        return self.mode == self.REF_MODE

    def in_custom_cols_mode(self):
        return self.mode == self.CUSTOM_COLS_MODE

    def in_custom_expr_mode(self):
        return self.mode == self.CUSTOM_EXPR_MODE

    def _plot_sample(self):
        expr = SampleExpression()
        self.app.plot(expr)

    def _plot_ref(self):
        expr = RefExpression()
        self.app.plot(expr)

    def _plot_custom_cols(self):
        self.custom_cols_panel._plot()

    def _plot_custom_expr(self):
        self.custom_expr_panel._plot()

    def _set_custom_values(self, Io, It):
        Io = "$" + Io
        It = "$" + It

        print "Io, It:", Io, It

        if self.custom_cols_panel.log_cb.IsChecked():
            expr = defaults.trans_mode.log_expr
        else:
            expr = defaults.trans_mode.scalar_expr

        expr = expr % dict(Io=Io, It=It)
        self.custom_cols_panel.io_cb.SetValue(Io)
        self.custom_cols_panel.it_cb.SetValue(It)
        self.custom_expr_panel.expr_txt.SetValue(expr)

    def OnSampMode(self, e):
        self.mode = self.SAMPLE_MODE

        self.custom_cols_panel.Disable()
        self.custom_expr_panel.Disable()

        self._set_custom_values(defaults.trans_mode.samp_mode.Io,
                                defaults.trans_mode.samp_mode.It)

        try:
            self._plot_sample()
        except xdp.errors.ColumnNameError:
            # FIXME: do something better? move back to previous selection?
            pass

    def OnRefMode(self, e):
        self.mode = self.REF_MODE

        self.custom_cols_panel.Disable()
        self.custom_expr_panel.Disable()

        self._set_custom_values(defaults.trans_mode.ref_mode.Io,
                                defaults.trans_mode.ref_mode.It)

        try:
            self._plot_ref()
        except xdp.errors.ColumnNameError:
            # FIXME: do something better? move back to previous selection?
            pass

    def OnCustomColsMode(self, e):
        self.mode = self.CUSTOM_COLS_MODE

        self.custom_cols_panel.Enable()
        self.custom_expr_panel.Disable()

        self.custom_cols_panel.io_cb.SetFocus()

        self._plot_custom_cols()

    def OnCustomExprMode(self, e):
        self.mode = self.CUSTOM_EXPR_MODE

        self.custom_expr_panel.Enable()
        self.custom_cols_panel.Disable()

        self.custom_expr_panel.expr_txt.SetFocus()

        self._plot_custom_cols()

    def OnPageSelected(self, e):
        if self.in_sample_mode():
            self._plot_sample()
        elif self.in_ref_mode():
            self._plot_ref()
        elif self.in_custom_cols_mode():
            self._plot_custom_cols()
        elif self.in_custom_expr_mode():
            self._plot_custom_expr()
        else:
            # FIXME use better exception
            raise Exception("unknown mode")


# ============================================================================

class CMapControlsPanel(PlotControlPanel):
    """Controls for Colormap Mode

    """
    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

        self._init_gui_elements()

    def _init_gui_elements(self):
        panel = wx.Panel(self, wx.ID_ANY)

        sizer = wx.GridBagSizer(2, 2)

        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Expression: "), (0,0),
                flag=wx.ALIGN_CENTER_VERTICAL)
        self.expr_txt = wx.TextCtrl(panel, size=(150, 27.5),
                style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnPlot, self.expr_txt)
        sizer.Add(self.expr_txt, (0,1))

        self.plot_btn = wx.Button(panel, label="Plot")
        self.Bind(wx.EVT_BUTTON, self.OnPlot, self.plot_btn)
        sizer.Add(self.plot_btn, (1,1))

        panel.SetSizer(sizer)
        sizer.Fit(panel)
        self.panel = panel

    def _plot(self):
        expr_s = self.expr_txt.GetValue()
        if expr_s:
            expr = ArbitraryExpression(expr_s)
            self.app.plot(expr)

    def OnPlot(self, e):
        self._plot()

    def OnPageSelected(self, e):
        self._plot()
        self.expr_txt.SetFocus()

# ============================================================================

class ScriptControlsPanel(PlotControlPanel):
    """Controls for Script Mode

    """

    class ScanInfoPanel(wx.Panel):
        def __init__(self, parent, id, app, **kwargs):
            wx.Panel.__init__(self, parent, id, **kwargs)

	    #flag to lock the data so it cannot change
	    self.locked = False

            self.parent = parent
            self.app = app

            self._init_gui_elements()

        def _init_gui_elements(self):
            box = wx.StaticBox(self, wx.ID_ANY, "Scan Info")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            grid = wx.GridBagSizer(3, 2)

            # Scan Name
            grid.Add(wx.StaticText(self, wx.ID_ANY, "Scan:"), (0,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.scan_txt = wx.TextCtrl(self, size=(150, 27.5),
                    style=wx.TE_PROCESS_ENTER)
	    self.scan_txt.Bind(wx.EVT_TEXT, self.OnScanChange)
            grid.Add(self.scan_txt, (0,1))

            # X
            grid.Add(wx.StaticText(self, wx.ID_ANY, "X:"), (1,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.x_txt = wx.TextCtrl(self, size=(150, 27.5),
                    style=wx.TE_PROCESS_ENTER)
	    self.x_txt.Bind(wx.EVT_TEXT, self.OnXChange)
            grid.Add(self.x_txt, (1,1))

            # Y
            grid.Add(wx.StaticText(self, wx.ID_ANY, "Y:"), (2,0),
                    flag=wx.ALIGN_CENTER_VERTICAL)
            self.y_txt = wx.TextCtrl(self, size=(150, 27.5),
                    style=wx.TE_PROCESS_ENTER)
	    self.y_txt.Bind(wx.EVT_TEXT, self.OnYChange)
            grid.Add(self.y_txt, (2,1))

            sizer.Add(grid)
            self.SetSizer(sizer)
            sizer.Fit(self)

	    # bind key event to retreive mouse postion for script generation
	    wxmpl.EVT_POINT(self.app.main_window.plot_panel, self.app.main_window.plot_panel.GetId(), self.onPoint)

        def _plot(self):
            # remove the preceding dollar signs
            Io = self.io_cb.GetValue()[1:]
            It = self.it_cb.GetValue()[1:]

            self.parent._set_custom_values(Io, It)

            expr = TransExpression(Io, It)
            self.app.plot(expr)

        def OnPlot(self, e):
            self._plot()

	#triggered when the user selects a point to scan script mode
	def onPoint(self, event):
	    self.x_txt.SetValue(str(math.floor(event.xdata)))
	    self.y_txt.SetValue(str(math.floor(event.ydata)))

	def RetrieveData(self):
	    self.scan_txt.SetValue(self.app.current_scan.scan)
	    self.x_txt.SetValue(str(self.app.current_scan.x))
	    self.y_txt.SetValue(str(self.app.current_scan.y))

	def OnScanChange(self, event):
	    self.app.current_scan.scan = self.scan_txt.GetValue()

	    selection = self.parent.scan_box.GetSelection()

	    self.parent.scan_box.SetString(selection, str(selection) + ": " +
	       self.app.current_scan.scan + " (" + str(self.app.current_scan.x) + ", " + str(self.app.current_scan.x) + ")")

	    self.app.scan_script.default_name = self.app.current_scan.scan

	def OnXChange(self, event):
	    try:
		value = float(self.x_txt.GetValue())
		self.app.current_scan.x = value
	    except ValueError:
		pass

	    self.OnScanChange(None)
	

	def OnYChange(self, event):
	    try:
		value = float(self.y_txt.GetValue())
		self.app.current_scan.y = value
	    except ValueError:
		pass

	    self.OnScanChange(None)

    def __init__(self, parent, id, app, **kwargs):
        PlotControlPanel.__init__(self, parent, id, app, **kwargs)

        self._init_gui_elements()

    def _init_gui_elements(self):
        panel = wx.Panel(self, wx.ID_ANY)

	grid = wx.GridBagSizer()

        #grid = wx.GridBagSizer()

	# make a choice box with all of the diferent scans in it
	scan_choices = self.app.scan_script.ChoiceList()
	self.scan_box = wx.ListBox(self, choices=scan_choices, size = (230, 100), style = wx.LB_SINGLE)
        grid.Add(self.scan_box, (0,0))

	# register selections of the choice box
	self.scan_box.Bind(wx.EVT_LISTBOX, self.OnChoiceScan)

	self.scan_info_panel = self.ScanInfoPanel(self, wx.ID_ANY, self.app)
        #self.scan_info_panel.Disable()
        grid.Add(self.scan_info_panel, (1,0))

	btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.add_button = wx.Button(self, label="Add New",size=(100,27))
	self.add_button.Bind(wx.EVT_BUTTON, self.OnAddNewScan)
	btn_sizer.Add(self.add_button)

	#bind the main window menu item to this
	self.app.main_window.Bind(wx.EVT_MENU, self.OnAddNewScan, self.app.main_window.add_new_scan_item)

        self.clear_button = wx.Button(self, label="Clear All",size=(100,27))
	self.clear_button.Bind(wx.EVT_BUTTON, self.OnClearScript)
	btn_sizer.Add(self.clear_button)

	grid.Add(btn_sizer, (2,0))

        grid.Add(wx.StaticText(self, wx.ID_ANY, "Filename:\n(leave blank for file selector dialog)"), (3,0),
            flag=wx.ALIGN_CENTER_VERTICAL)

        self.filename_txt = wx.TextCtrl(self, size=(150, 27.5),
       	    style=wx.TE_PROCESS_ENTER)
	grid.Add(self.filename_txt, (4,0))

        self.write_to_file_button = wx.Button(self, label="Write Script to File",size=(150,27))
	self.write_to_file_button.Bind(wx.EVT_BUTTON, self.OnWriteFile)
	grid.Add(self.write_to_file_button, (5,0))

	#sizer.Add(grid,flag=wx.EXPAND)
        #self.SetSizer(sizer)
	self.SetSizer(grid)
        self.Fit()

    def _plot(self):
	pass

    def OnPlot(self, e):
        self._plot()

    def OnChoiceScan(self, event):
	selection = self.scan_box.GetSelection()
	if selection < 0:
	    return

	self.app.current_scan = self.app.scan_script.scans[selection]

	self.ResetScanList(selection)

    def OnAddNewScan(self, event):
	self.app.current_scan = self.app.scan_script.AddNewScan()

	self.ResetScanList(self.scan_box.GetCount())

    def ResetScanList(self, selection_number):
	self.scan_box.Clear()

	scan_list = self.app.scan_script.ChoiceList()

	for scan in scan_list:
	    self.scan_box.Append(scan)

	self.scan_box.SetSelection(selection_number)

	# reset the panel to reflect the selected scan
	self.scan_info_panel.RetrieveData()	

    def OnClearScript(self, event):
	self.app.current_scan = self.app.scan_script.ClearAllScans()

	self.ResetScanList(0)

    def OnWriteFile(self, event):
	#try to get filename from this text window
	filename = self.filename_txt.GetValue()

	#if the filename from the textbox is empty, open a file name chooser window
	if filename == "":
	    filename = wx.FileSelector('Save Script',
		parent=self, flags=wx.SAVE|wx.OVERWRITE_PROMPT)

	# if the filename chooser window fails, just return with and error message box
	if not filename:
            wx.MessageBox('did not save script file', 'script',
                parent=self, style=wx.OK)
	    return

        try:
	    script_file = open(filename, 'w')

	    script_file.write(self.app.scan_script.ToString())

	    script_file.close()
        except IOError, e:
            if e.strerror:
                err = e.strerror
            else:
                err = e

            wx.MessageBox('Could not save file: %s' % err, 'Error - script',
                parent=self, style=wx.OK|wx.ICON_ERROR)

	    return

        wx.MessageBox('file saved: ' + filename, 'Success - script',
                parent=self, style=wx.OK)
	
	return

    def OnPageSelected(self, e):
        self._plot()

# ============================================================================

class PlotControlsFrame(wx.Frame):
    def __init__(self, parent, id, app, size=(250,350), **kwargs):
        wx.Frame.__init__(self, parent, id, title="Plot Controls", size=size, **kwargs)

        self.parent = parent
        self.app = app

        self.cb = PlotControlsCB(parent=self, id=wx.ID_ANY, app=app)

class PlotControlsCB(wx.Choicebook):
    PAGES = (
	("Transmission Mode", TransControlsPanel),
        ("Fluorescence Mode", FluorControlsPanel),
        ("Colormap Mode", CMapControlsPanel),
	("Script Mode", ScriptControlsPanel),
    )

    PAGES = (
	("Expression Mode", TransControlsPanel),
	("Script Mode", ScriptControlsPanel),
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

class PlotBoundsDialog(wx.Dialog):
    def __init__(self, parent, id, app, **kwargs):
        wx.Dialog.__init__(self, parent, id, "Set Plot Range", **kwargs)

        #retain reference to app
        self.app = app

        # set sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

	sizer = wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(wx.StaticText(self, wx.ID_ANY, "Upper Bounds: "))
        self.upper_txt = wx.TextCtrl(self, size=(150, 27.5))
	self.upper_txt.SetValue(str(self.app.plot_panel.plot_opts["upper_bound"]))
	sizer.Add(self.upper_txt)
	main_sizer.Add(sizer)

	sizer = wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(wx.StaticText(self, wx.ID_ANY, "Lower Bounds: "))
        self.lower_txt = wx.TextCtrl(self, size=(150, 27.5))
	self.lower_txt.SetValue(str(self.app.plot_panel.plot_opts["lower_bound"]))
	sizer.Add(self.lower_txt)
	main_sizer.Add(sizer)

        self.clear_button = wx.Button(self, label="Clear Bounds",size=(150,27))
	self.clear_button.Bind(wx.EVT_BUTTON, self.OnClearBounds)
	main_sizer.Add(self.clear_button)

	sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cancel_button = wx.Button(self, label="Cancel",size=(75,27))
	self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancel)
	sizer.Add(self.cancel_button)
        self.ok_button = wx.Button(self, label="OK",size=(75,27))
	self.ok_button.Bind(wx.EVT_BUTTON, self.OnOK)
	sizer.Add(self.ok_button)
	main_sizer.Add(sizer)

        #set sizer
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)

    def SafeFloat(self, string):
	try:
	    return float(string)
	except ValueError:
	    return None

    def OnClearBounds(self, event):
	self.upper_bound = None
	self.lower_bound = None

	self.EndModal(wx.ID_OK)

    def OnOK(self, event):
	self.upper_bound = self.SafeFloat(self.upper_txt.GetValue())
	self.lower_bound = self.SafeFloat(self.lower_txt.GetValue())

	self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
	self.EndModal(wx.ID_CANCEL)

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

        self.axes_2d = None
        self.axes_3d = None

        self.axes = None

        self.frame_3d = wx.Frame(self,wx.ID_ANY, title = "3D Window",*args,**kwargs)
        self.panel_3d = wxmpl.PlotPanel(self.frame_3d, wx.ID_ANY,*args,**kwargs)

        # lay out frame of 3d frame
        sizer = wx.GridBagSizer()
        sizer.Add(self.panel_3d, pos=(1,1))
        self.SetSizer(sizer)
        self.Fit()

        self.frame_3d.Show(False)

        # colorbar instance variables
        self.img = None
        self.cb = None

        self.first_time = True

    def plot(self, z_expr, **kwargs):
        x_name = kwargs.pop("x_name", defaults.x_name)
        y_name = kwargs.pop("y_name", defaults.y_name)
        title = kwargs.pop("title", defaults.title)
        colormap = kwargs.pop("colormap", defaults.colormap)
        groups = kwargs.pop("groups", self.app.groups)
        mode_3d = kwargs.pop("mode_3d", False)
        yaw_3d = kwargs.pop("yaw_3d",30.0)
        pitch_3d = kwargs.pop("pitch_3d",60.0)
        upper_bound = kwargs.pop("upper_bound",None)
        lower_bound = kwargs.pop("lower_bound",None)

        # attempt to read file again
        try:
            self.app.hdr, self.app.data = xdp.io.readFile(self.app.filename)
        except IOError, e:
            if e.strerror:
                util.fatal_error('could not load `%s\': %s', self.app.filename, e.strerror)
            else:
                util.fatal_error('could not load `%s\': %s', self.app.filename, e)

	    #remove negative numbers from the data in order to prevent taking the logarithm of a negative number
        util.remove_negatives(self.app.data)

        if not self.first_time:
            # get string form of expression
            z_expr_s = str(z_expr)

            # replace groups in the expression with their constituent columns
            z_expr_s = expression.expand_groups(z_expr_s, groups)
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

            #constrain data to be within the upper and lower bounds
            if not upper_bound == None:
                z[z>upper_bound] = upper_bound
            if not lower_bound == None:
                z[z<lower_bound] = lower_bound

            #show or hide 3d window
            self.frame_3d.Show(mode_3d)

            if mode_3d:
                fig = self.panel_3d.get_figure()
                fig.clear()

                #if self.axes_3d == None:
                self.axes_3d = Axes3D(fig, elev = pitch_3d, azim = yaw_3d)

                axes = self.axes_3d

                #prepare x and y arrays for the 3d surface plot
                x_grid, y_grid = np.meshgrid(x,y)
                #do surface plot
                surf = axes.plot_surface(x_grid,y_grid,z, rstride = int(math.ceil(len(x)/25.0)), cstride = int(math.ceil(len(y)/25.0)), cmap=colormap)

                axes.set_title(title)
                axes.set_ylabel(y_name)

                # force a redraw of the figure
                axes.figure.canvas.draw()
            
            fig = self.get_figure()

            if self.axes_2d == None:
                self.axes_2d = fig.gca()

            axes = self.axes_2d

            if matplotlib.__version__ >= '0.81':
                axes.yaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
                axes.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(5))

                axes.xaxis.set_major_formatter(matplotlib.ticker.OldScalarFormatter())
                axes.xaxis.set_major_locator(matplotlib.ticker.LinearLocator(3))

            # plot the data and colorbar
            extent = min(x), max(x), min(y), max(y)

            # if we're replotting the image, update the colorbar
            if self.img:
                # we need to update both the image's data and the colorbar's data
                self.img.set_data(z)
                self.img.set_extent(extent)
                self.cb.set_array(z)

                # update the colormap
                self.img.set_cmap(getattr(matplotlib.cm, colormap))

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

            axes.set_title(title)
            axes.set_ylabel(y_name)

            # force a redraw of the figure
            axes.figure.canvas.draw()

            # call on_plot callback
            z_expr.on_plot(fig, self.app)
        self.first_time = False

        # save current plot parameters for later retrieval
        self.plot_opts["first_time"] = False
        self.plot_opts["x_name"] = x_name
        self.plot_opts["y_name"] = y_name
        self.plot_opts["z_expr"] = z_expr
        self.plot_opts["colormap"] = colormap
        self.plot_opts["title"] = title
        self.plot_opts["mode_3d"] = mode_3d
        self.plot_opts["yaw_3d"] = yaw_3d
        self.plot_opts["pitch_3d"] = pitch_3d
        self.plot_opts["upper_bound"] = upper_bound
        self.plot_opts["lower_bound"] = lower_bound

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

        # add subpanels to App namespace
        self.app.plot_panel = self.plot_panel

        # misc initialisation
        self._initialise_printer()
        self._create_menus()

        # lay out frame
        sizer = wx.GridBagSizer()
        sizer.Add(self.plot_panel, pos=(1,1))
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

        item = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q',
            'Exit frankenplot')
        self.Bind(wx.EVT_MENU, self.OnMenuFileExit, item)

        # Edit menu
        editMenu = wx.Menu()
        menuBar.Append(editMenu, "&Edit")

        item = editMenu.Append(id=wx.ID_ANY, text="Plot Tit&le...",
                help="Edit plot title")
        self.Bind(wx.EVT_MENU, self.OnMenuEditPlotTitle, item)

        item = editMenu.Append(id=wx.ID_ANY, text="Col&ormap...",
                help="Edit plot colormap")
        self.Bind(wx.EVT_MENU, self.OnMenuEditColormap, item)

        editMenu.AppendSeparator()

        item = editMenu.Append(wx.ID_ANY, "Cha&nnels...",
            "Edit channels")
        self.Bind(wx.EVT_MENU, self.OnMenuEditChannels, item)
        item.Enable(False)

        item = editMenu.Append(wx.ID_ANY, "&Columns...",
            "Select displayed columns")
        self.Bind(wx.EVT_MENU, self.OnMenuSelectColumns, item)
        item.Enable(False)

        editMenu.AppendSeparator()

        #ADD NEW SCAN menu item shortcut, see script panel.init_gui
        item = editMenu.Append(wx.ID_ANY, "&Add New Script\tCtrl+A",
            "Edit channels")
        self.add_new_scan_item = item
        # this is bound at script_panel.init_gui

        item = editMenu.Append(id=wx.ID_ANY, text="Plot &Range...\tCtrl+R",
                help="Edit plotting range")
        self.Bind(wx.EVT_MENU, self.OnMenuEditRange, item)


        # View menu
        view_menu = wx.Menu()
        menuBar.Append(view_menu, "&View")

        item = view_menu.Append(wx.ID_ANY, "Plot &Controls",
                help="Toggle Plot Controls window", kind=wx.ITEM_CHECK)
        item.Check(True)
        self.Bind(wx.EVT_MENU, self.OnMenuViewPlotControls, item)
        self.view_plot_ctrls_item = item

        item = view_menu.Append(wx.ID_ANY, "Plot 3&D",
                help="Toggle 3D View", kind=wx.ITEM_CHECK)
        item.Check(False)
        self.Bind(wx.EVT_MENU, self.OnMenuViewPlot3D, item)
        self.view_plot_3d_item = item

        item = view_menu.Append(wx.ID_ANY, "Move 3D Camera &Right\tCtrl-L",
            "yaw 3d camera 30 degrees to the right")
        self.Bind(wx.EVT_MENU, self.OnMenuViewRight, item)

        item = view_menu.Append(wx.ID_ANY, "Move 3D Camera &Left\tCtrl-J",
            "yaw 3d camera 30 degrees to the left")
        self.Bind(wx.EVT_MENU, self.OnMenuViewLeft, item)

        item = view_menu.Append(wx.ID_ANY, "Move 3D Camera &Up\tCtrl-I",
            "pitch 3d camera 30 degrees up")
        self.Bind(wx.EVT_MENU, self.OnMenuViewUp, item)

        item = view_menu.Append(wx.ID_ANY, "Move 3D Camera &Down\tCtrl-K",
            "pitch 3d camera 30 degrees down")
        self.Bind(wx.EVT_MENU, self.OnMenuViewDown, item)

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

    def OnMenuFileExit(self, evt):
        """
        Handles File->Exit menu events.
        """
        self.app.Exit()

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
        message = "Plot Title:"
        title = "Edit Plot Title"
        value = str(self.app.plot_panel.plot_opts["title"])

        dlg = wx.TextEntryDialog(self, message, title, value)

        if dlg.ShowModal() == wx.ID_OK:
            self.app.plot_panel.change_plot(title=dlg.GetValue())

        dlg.Destroy()

    def OnMenuEditRange(self, e):
        dlg = PlotBoundsDialog(self, wx.ID_ANY, self.app)

        if (dlg.ShowModal() == wx.ID_OK):
	    self.app.plot_panel.change_plot(upper_bound = dlg.upper_bound, lower_bound = dlg.lower_bound)

        dlg.Destroy()

    def OnMenuViewPlotControls(self, e):
        self.app.plot_ctrls.Show(self.view_plot_ctrls_item.IsChecked())

    def OnMenuViewPlot3D(self, e):
        self.app.plot_panel.change_plot(mode_3d = self.view_plot_3d_item.IsChecked())

    def OnMenuViewRight(self, e):
        value = self.app.plot_panel.plot_opts["yaw_3d"]
        self.app.plot_panel.change_plot(yaw_3d=value + 30.0)

    def OnMenuViewLeft(self, e):
        value = self.app.plot_panel.plot_opts["yaw_3d"]
        self.app.plot_panel.change_plot(yaw_3d=value - 30.0)

    def OnMenuViewUp(self, e):
        value = self.app.plot_panel.plot_opts["pitch_3d"]
        self.app.plot_panel.change_plot(pitch_3d=value + 30.0)

    def OnMenuViewDown(self, e):
        value = self.app.plot_panel.plot_opts["pitch_3d"]
        self.app.plot_panel.change_plot(pitch_3d=value - 30.0)

    def OnMenuEditColormap(self, e):
        message = "Choose colormap:"
        title = "Edit Colormap"
        choices = defaults.colormaps
        dlg = wx.SingleChoiceDialog(self, message, title, choices,
                wx.CHOICEDLG_STYLE)

        # set the selection to the current colormap
        dlg.SetSelection(choices.index(self.app.plot_panel.plot_opts["colormap"]))

        if dlg.ShowModal() == wx.ID_OK:
            self.app.plot_panel.change_plot(colormap=dlg.GetStringSelection())

        dlg.Destroy()

    def get_figure(self):
        return self.plot_panel.get_figure()

    def plot(self, *args, **kwargs):
        return self.plot_panel.plot(*args, **kwargs)

# ============================================================================
"""
class 3DViewWindow(wx.Frame):
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
"""
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

	    #remove negative numbers from the data in order to prevent taking the logarithm of a negative number
        util.remove_negatives(self.data)

        self.columns = self.data.getColumnNames()

        # self.rois is a dict: 'roi' => list (of columns)
        # self.channels is a list of channels
        self.rois, self.corr_rois, self.channels = self._parse_columns(self.columns)

        # initialise groups (dict: group name (str) => members (set))
        self.groups = {}

        # ROI group names (%roi_1, ... , %roi_N, %corr_roi_1, ... , %corr_roi_N)
        self.roi_group_names = []

        # create the ROI groups
        self._create_roi_groups(self.rois, corrected=False)
        self._create_roi_groups(self.corr_rois, corrected=True)

	    # create scan script
        self.scan_script = script.Script()
        self.current_scan = self.scan_script.AddNewScan()

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
