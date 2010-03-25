import wx
import wxmpl

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
