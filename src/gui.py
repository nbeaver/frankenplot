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
        self.Bind(wx.EVT_MENU, self.OnMenuEditColumns, item)

        # Help menu
        helpMenu = wx.Menu()
        menuBar.Append(helpMenu, '&Help')

        item = helpMenu.Append(wx.ID_ANY, '&About...', 
            'Display version information')
        self.Bind(wx.EVT_MENU, self.OnMenuHelpAbout, item)

    def OnMenuEditColumns(self, evt):
        pass

class EditColumnsFrame(wx.Frame):
    pass

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
