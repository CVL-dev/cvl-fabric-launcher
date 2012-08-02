import wx

ID_About = 100
ID_Exit = 101

class MainWindow(wx.Frame):
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, size=(680,480),
            style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX | wx.MAXIMIZE_BOX))
       
        self.Center()
        
        menuFile = wx.Menu()
        menuFile.Append(ID_Exit, "E&xit")
        
        menuHelp = wx.Menu()
        menuHelp.Append(ID_About, "&About")
        
        menu_bar = wx.MenuBar()
        menu_bar.Append(menuFile, "&File")
        menu_bar.Append(menuHelp, "&Help")
        self.SetMenuBar(menu_bar)
        
        wx.EVT_MENU(self, ID_Exit, self.onExit)
       
        self.notebookContainerPanel = wx.Panel(self, wx.ID_ANY)

        self.tabbedView = wx.Notebook(self.notebookContainerPanel, wx.ID_ANY, style=(wx.NB_TOP))
        notebookContainerPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=15, hgap=15)
        notebookContainerPanelSizer.Add(wx.StaticText(self.notebookContainerPanel, wx.ID_ANY, "     "))
        notebookContainerPanelSizer.Add(self.tabbedView, flag=wx.EXPAND)
        notebookContainerPanelSizer.Add(wx.StaticText(self.notebookContainerPanel, wx.ID_ANY, "     "))

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        smallFont.SetPointSize(11)

        # Connection tab

        self.connectionPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.connectionPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=15, hgap=15)

        self.connectionLeftBorderPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionLeftBorderPanel)

        self.connectionLeftPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionLeftPanel, flag=wx.EXPAND)
        self.connectionLeftPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)

        self.connectionRightPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionRightPanel, flag=wx.EXPAND)
        self.connectionRightPanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)

        self.connectionRightBorderPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionRightBorderPanel)

        # Encoding group box

        self.encodingPanel = wx.Panel(self.connectionLeftPanel, wx.ID_ANY)
        self.connectionLeftPanelSizer.Add(self.encodingPanel, flag=wx.EXPAND)

        self.encodingGroupBox = wx.StaticBox(self.encodingPanel, wx.ID_ANY, label="Encoding")
        self.encodingGroupBox.SetFont(smallFont)
        self.encodingGroupBoxSizer = wx.StaticBoxSizer(self.encodingGroupBox, wx.VERTICAL)
        self.encodingPanel.SetSizer(self.encodingGroupBoxSizer)

        self.innerEncodingPanel = wx.Panel(self.encodingPanel, wx.ID_ANY)
        self.innerEncodingPanelSizer = wx.FlexGridSizer(rows=10, cols = 1, vgap=5,hgap=5)
        self.innerEncodingPanel.SetSizer(self.innerEncodingPanelSizer)

        self.encodingMethodLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Encoding method:")
        self.innerEncodingPanelSizer.Add(self.encodingMethodLabel)
        self.encodingMethodLabel.SetFont(smallFont)
       
        self.encodingMethodsPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.encodingMethodsPanelSizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5,hgap=5)
        self.encodingMethodsPanel.SetSizer(self.encodingMethodsPanelSizer)
        emptySpace = wx.StaticText(self.encodingMethodsPanel, wx.ID_ANY, "   ")
        self.encodingMethodsPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        encodingMethods = ['Tight + Perceptually Lossless JPEG (LAN)', '???', '???', '???', '???']
        self.encodingMethodsComboBox = wx.Choice(self.encodingMethodsPanel, wx.ID_ANY,
            choices=encodingMethods, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.encodingMethodsComboBox.SetFont(smallFont)
        self.encodingMethodsPanelSizer.Add(self.encodingMethodsComboBox, flag=wx.EXPAND)

        # This shouldn't be necessary but, otherwise the bottom border of the combo-box is clipped on my Mac.
        self.encodingMethodsPanelSizer.Add(wx.Panel(self.encodingMethodsPanel, wx.ID_ANY))

        self.encodingMethodsPanel.SetSizerAndFit(self.encodingMethodsPanelSizer)
        self.innerEncodingPanelSizer.Add(self.encodingMethodsPanel, flag=wx.EXPAND)

        self.jpegCompressionCheckBox = wx.CheckBox(self.innerEncodingPanel, wx.ID_ANY, "Allow JPEG compression")
        self.jpegCompressionCheckBox.SetValue(True)
        self.jpegCompressionCheckBox.SetFont(smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegCompressionCheckBox)

        self.jpegChrominanceSubsamplingLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG chrominance subsampling:    None")
        self.jpegChrominanceSubsamplingLabel.SetFont(smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegChrominanceSubsamplingLabel)

        self.jpegChrominanceSubsamplingPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.jpegChrominanceSubsamplingPanelSizer = wx.FlexGridSizer(rows=2, cols=4, vgap=5,hgap=5)
        self.jpegChrominanceSubsamplingPanel.SetSizer(self.jpegChrominanceSubsamplingPanelSizer)
        emptySpace = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "   ")
        self.jpegChrominanceSubsamplingPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.fastLabel = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "fast")
        self.fastLabel.SetFont(smallFont)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.fastLabel, flag=wx.EXPAND)

        self.jpegChrominanceSubsamplingSlider = wx.Slider(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.jpegChrominanceSubsamplingSlider)

        self.bestLabel = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "best")
        self.bestLabel.SetFont(smallFont)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.bestLabel, flag=wx.EXPAND)

        self.jpegChrominanceSubsamplingPanel.SetSizerAndFit(self.jpegChrominanceSubsamplingPanelSizer)
        self.innerEncodingPanelSizer.Add(self.jpegChrominanceSubsamplingPanel, flag=wx.EXPAND)

        self.jpegImageQualityLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG image quality:    95")
        self.jpegImageQualityLabel.SetFont(smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegImageQualityLabel)

        self.jpegImageQualityPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.jpegImageQualityPanelSizer = wx.FlexGridSizer(rows=2, cols=4, vgap=5,hgap=5)
        self.jpegImageQualityPanel.SetSizer(self.jpegImageQualityPanelSizer)
        emptySpace = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "   ")
        self.jpegImageQualityPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.poorImageQualityLabel = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "poor")
        self.poorImageQualityLabel.SetFont(smallFont)
        self.jpegImageQualityPanelSizer.Add(self.poorImageQualityLabel, flag=wx.EXPAND)

        self.jpegImageQualitySlider = wx.Slider(self.jpegImageQualityPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.jpegImageQualityPanelSizer.Add(self.jpegImageQualitySlider)

        self.bestImageQualityLabel = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "best")
        self.bestImageQualityLabel.SetFont(smallFont)
        self.jpegImageQualityPanelSizer.Add(self.bestImageQualityLabel, flag=wx.EXPAND)

        self.jpegImageQualityPanel.SetSizerAndFit(self.jpegImageQualityPanelSizer)
        self.innerEncodingPanelSizer.Add(self.jpegImageQualityPanel, flag=wx.EXPAND)

        self.zlibCompressionLevelLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Zlib compression level:     1")
        self.zlibCompressionLevelLabel.SetFont(smallFont)
        self.zlibCompressionLevelLabel.Disable()
        self.innerEncodingPanelSizer.Add(self.zlibCompressionLevelLabel)

        self.zlibCompressionLevelPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.zlibCompressionLevelPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=5,hgap=5)
        self.zlibCompressionLevelPanel.SetSizer(self.zlibCompressionLevelPanelSizer)
        emptySpace = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "   ")
        self.zlibCompressionLevelPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.fastZlibCompressionLabel = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "fast")
        self.fastZlibCompressionLabel.SetFont(smallFont)
        self.fastZlibCompressionLabel.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.fastZlibCompressionLabel, flag=wx.EXPAND)

        self.zlibCompressionLevelSlider = wx.Slider(self.zlibCompressionLevelPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.zlibCompressionLevelSlider.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.zlibCompressionLevelSlider)

        self.bestZlibCompressionLabel = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "best")
        self.bestZlibCompressionLabel.SetFont(smallFont)
        self.bestZlibCompressionLabel.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.bestZlibCompressionLabel, flag=wx.EXPAND)

        self.zlibCompressionLevelPanel.SetSizerAndFit(self.zlibCompressionLevelPanelSizer)
        self.zlibCompressionLevelPanel.Disable()
        self.innerEncodingPanelSizer.Add(self.zlibCompressionLevelPanel, flag=wx.EXPAND)

        self.copyRectEncodingCheckBox = wx.CheckBox(self.innerEncodingPanel, wx.ID_ANY, "Allow CopyRect encoding")
        self.copyRectEncodingCheckBox.SetValue(True)
        self.copyRectEncodingCheckBox.SetFont(smallFont)
        self.innerEncodingPanelSizer.Add(self.copyRectEncodingCheckBox)

        self.innerEncodingPanel.SetSizerAndFit(self.innerEncodingPanelSizer)
        self.encodingGroupBoxSizer.Add(self.innerEncodingPanel, flag=wx.EXPAND)
        self.encodingPanel.SetSizerAndFit(self.encodingGroupBoxSizer)

        # Restrictions group box

        self.restrictionsPanel = wx.Panel(self.connectionLeftPanel, wx.ID_ANY)
        self.connectionLeftPanelSizer.Add(self.restrictionsPanel, flag=wx.EXPAND)

        self.restrictionsGroupBox = wx.StaticBox(self.restrictionsPanel, wx.ID_ANY, label="Restrictions")
        self.restrictionsGroupBox.SetFont(smallFont)
        self.restrictionsGroupBoxSizer = wx.StaticBoxSizer(self.restrictionsGroupBox, wx.VERTICAL)
        self.restrictionsPanel.SetSizer(self.restrictionsGroupBoxSizer)

        self.innerRestrictionsPanel = wx.Panel(self.restrictionsPanel, wx.ID_ANY)
        self.innerRestrictionsPanelSizer = wx.FlexGridSizer(rows=2, cols = 1, vgap=5,hgap=5)
        self.innerRestrictionsPanel.SetSizer(self.innerRestrictionsPanelSizer)

        self.viewOnlyCheckBox = wx.CheckBox(self.innerRestrictionsPanel, wx.ID_ANY, "View only (inputs ignored)")
        self.viewOnlyCheckBox.SetValue(False)
        self.innerRestrictionsPanelSizer.Add(self.viewOnlyCheckBox)
        self.viewOnlyCheckBox.SetFont(smallFont)
        
        self.disableClipboardTransferCheckBox = wx.CheckBox(self.innerRestrictionsPanel, wx.ID_ANY, "Disable clipboard transfer")
        self.disableClipboardTransferCheckBox.SetValue(False)
        self.innerRestrictionsPanelSizer.Add(self.disableClipboardTransferCheckBox)
        self.disableClipboardTransferCheckBox.SetFont(smallFont)
        
        self.innerRestrictionsPanel.SetSizerAndFit(self.innerRestrictionsPanelSizer)
        self.restrictionsGroupBoxSizer.Add(self.innerRestrictionsPanel, flag=wx.EXPAND)
        self.restrictionsPanel.SetSizerAndFit(self.restrictionsGroupBoxSizer)

        # Bottom border panel

        self.bottomBorderPanel = wx.Panel(self.connectionLeftPanel, wx.ID_ANY)
        self.connectionLeftPanelSizer.Add(self.bottomBorderPanel, flag=wx.EXPAND)

        # Display group box

        self.displayPanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.displayPanel, flag=wx.EXPAND)

        self.displayGroupBox = wx.StaticBox(self.displayPanel, wx.ID_ANY, label="Display")
        self.displayGroupBox.SetFont(smallFont)
        self.displayGroupBoxSizer = wx.StaticBoxSizer(self.displayGroupBox, wx.VERTICAL)
        self.displayPanel.SetSizer(self.displayGroupBoxSizer)

        self.innerDisplayPanel = wx.Panel(self.displayPanel, wx.ID_ANY)
        self.innerDisplayPanelSizer = wx.FlexGridSizer(rows=5, cols = 1, vgap=5,hgap=5)
        self.innerDisplayPanel.SetSizer(self.innerDisplayPanelSizer)

        self.scaleByPanel = wx.Panel(self.innerDisplayPanel, wx.ID_ANY)
        self.scaleByPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5,hgap=5)
        self.scaleByPanel.SetSizer(self.scaleByPanelSizer)

        self.scaleByLabel = wx.StaticText(self.scaleByPanel, wx.ID_ANY, "Scale by:   ")
        self.scaleByLabel.SetFont(smallFont)
        self.scaleByPanelSizer.Add(self.scaleByLabel, flag=wx.ALIGN_CENTER)

        scaleOptions = ['100', '???', '???', '???', '???']
        self.scaleByComboBox = wx.Choice(self.scaleByPanel, wx.ID_ANY,
            choices=scaleOptions, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.scaleByComboBox.SetFont(smallFont)
        self.scaleByPanelSizer.Add(self.scaleByComboBox, flag=wx.EXPAND)

        self.percentageSignLabel = wx.StaticText(self.scaleByPanel, wx.ID_ANY, "  %")
        self.percentageSignLabel.SetFont(smallFont)
        self.scaleByPanelSizer.Add(self.percentageSignLabel, flag=wx.ALIGN_CENTER)

        # This shouldn't be necessary but, otherwise the bottom border of the combo-box is clipped on my Mac.
        self.scaleByPanelSizer.Add(wx.Panel(self.scaleByPanel, wx.ID_ANY))

        self.scaleByPanel.SetSizerAndFit(self.scaleByPanelSizer)
        self.innerDisplayPanelSizer.Add(self.scaleByPanel, flag=wx.EXPAND)

        self.doubleBufferingCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Double buffering")
        self.doubleBufferingCheckBox.SetValue(True)
        self.innerDisplayPanelSizer.Add(self.doubleBufferingCheckBox)
        self.doubleBufferingCheckBox.SetFont(smallFont)
        
        self.fullScreenModeCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Full-screen mode")
        self.fullScreenModeCheckBox.SetValue(False)
        self.innerDisplayPanelSizer.Add(self.fullScreenModeCheckBox)
        self.fullScreenModeCheckBox.SetFont(smallFont)
        
        self.spanModePanel = wx.Panel(self.innerDisplayPanel, wx.ID_ANY)
        self.spanModePanelSizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5,hgap=5)
        self.spanModePanel.SetSizer(self.spanModePanelSizer)

        self.spanModeLabel = wx.StaticText(self.spanModePanel, wx.ID_ANY, "Span mode:   ")
        self.spanModeLabel.SetFont(smallFont)
        self.spanModePanelSizer.Add(self.spanModeLabel, flag=wx.ALIGN_CENTER)

        spanModes = ['Automatic', '???', '???', '???', '???']
        self.spanModeComboBox = wx.Choice(self.spanModePanel, wx.ID_ANY,
            choices=spanModes, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.spanModeComboBox.SetFont(smallFont)
        self.spanModePanelSizer.Add(self.spanModeComboBox, flag=wx.EXPAND)

        # This shouldn't be necessary but, otherwise the bottom border of the combo-box is clipped on my Mac.
        self.spanModePanelSizer.Add(wx.Panel(self.spanModePanel, wx.ID_ANY))

        self.spanModePanel.SetSizerAndFit(self.spanModePanelSizer)
        self.innerDisplayPanelSizer.Add(self.spanModePanel, flag=wx.EXPAND)

        self.deiconifyOnRemoteBellEventCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Deiconify on remote Bell event")
        self.deiconifyOnRemoteBellEventCheckBox.SetValue(False)
        self.innerDisplayPanelSizer.Add(self.deiconifyOnRemoteBellEventCheckBox)
        self.deiconifyOnRemoteBellEventCheckBox.SetFont(smallFont)
        
        self.innerDisplayPanel.SetSizerAndFit(self.innerDisplayPanelSizer)
        self.displayGroupBoxSizer.Add(self.innerDisplayPanel, flag=wx.EXPAND)
        self.displayPanel.SetSizerAndFit(self.displayGroupBoxSizer)

        # Mouse group box

        self.mousePanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.mousePanel, flag=wx.EXPAND)

        self.mouseGroupBox = wx.StaticBox(self.mousePanel, wx.ID_ANY, label="Mouse")
        self.mouseGroupBox.SetFont(smallFont)
        self.mouseGroupBoxSizer = wx.StaticBoxSizer(self.mouseGroupBox, wx.VERTICAL)
        self.mousePanel.SetSizer(self.mouseGroupBoxSizer)

        self.innerMousePanel = wx.Panel(self.mousePanel)
        self.innerMousePanelSizer = wx.FlexGridSizer(rows=2, cols = 1, vgap=5,hgap=5)
        self.innerMousePanel.SetSizer(self.innerMousePanelSizer)

        self.emulate3ButtonsWith2ButtonClickCheckBox = wx.CheckBox(self.innerMousePanel, wx.ID_ANY, "Emulate 3 buttons (with 2-button click)")
        self.emulate3ButtonsWith2ButtonClickCheckBox.SetValue(True)
        self.innerMousePanelSizer.Add(self.emulate3ButtonsWith2ButtonClickCheckBox)
        self.emulate3ButtonsWith2ButtonClickCheckBox.SetFont(smallFont)
        
        self.swapMouseButtons2And3CheckBox = wx.CheckBox(self.innerMousePanel, wx.ID_ANY, "Swap mouse buttons 2 and 3")
        self.swapMouseButtons2And3CheckBox.SetValue(False)
        self.innerMousePanelSizer.Add(self.swapMouseButtons2And3CheckBox)
        self.swapMouseButtons2And3CheckBox.SetFont(smallFont)
        
        self.innerMousePanel.SetSizerAndFit(self.innerMousePanelSizer)
        self.mouseGroupBoxSizer.Add(self.innerMousePanel, flag=wx.EXPAND)
        self.mousePanel.SetSizerAndFit(self.mouseGroupBoxSizer)

        # Mouse cursor group box

        self.mouseCursorPanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.mouseCursorPanel, flag=wx.EXPAND)

        self.mouseCursorGroupBox = wx.StaticBox(self.mouseCursorPanel, wx.ID_ANY, label="Mouse cursor")
        self.mouseCursorGroupBox.SetFont(smallFont)
        self.mouseCursorGroupBoxSizer = wx.StaticBoxSizer(self.mouseCursorGroupBox, wx.VERTICAL)
        self.mouseCursorPanel.SetSizer(self.mouseCursorGroupBoxSizer)

        self.innerMouseCursorPanel = wx.Panel(self.mouseCursorPanel, wx.ID_ANY)
        self.innerMouseCursorPanelSizer = wx.FlexGridSizer(rows=3, cols = 1, vgap=5,hgap=5)
        self.innerMouseCursorPanel.SetSizer(self.innerMouseCursorPanelSizer)

        self.trackRemoteCursorLocallyRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Track remote cursor locally")
        self.trackRemoteCursorLocallyRadioButton.SetValue(True)
        self.innerMouseCursorPanelSizer.Add(self.trackRemoteCursorLocallyRadioButton)
        self.trackRemoteCursorLocallyRadioButton.SetFont(smallFont)
        
        self.letRemoteServerDealWithMouseCursorRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Let remote server deal with mouse cursor")
        self.letRemoteServerDealWithMouseCursorRadioButton.SetValue(False)
        self.innerMouseCursorPanelSizer.Add(self.letRemoteServerDealWithMouseCursorRadioButton)
        self.letRemoteServerDealWithMouseCursorRadioButton.SetFont(smallFont)
        
        self.dontShowRemoteCursorRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Don't show remote cursor")
        self.dontShowRemoteCursorRadioButton.SetValue(False)
        self.innerMouseCursorPanelSizer.Add(self.dontShowRemoteCursorRadioButton)
        self.dontShowRemoteCursorRadioButton.SetFont(smallFont)
        
        self.innerMouseCursorPanel.SetSizerAndFit(self.innerMouseCursorPanelSizer)
        self.mouseCursorGroupBoxSizer.Add(self.innerMouseCursorPanel, flag=wx.EXPAND)
        self.mouseCursorPanel.SetSizerAndFit(self.mouseCursorGroupBoxSizer)

        # Request shared session checkbox.

        self.requestSharedSessionPanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.requestSharedSessionPanel, flag=wx.EXPAND)

        self.requestSharedSessionPanel = wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY)
        self.requestSharedSessionPanelSizer = wx.FlexGridSizer(rows=3, cols=2, vgap=5, hgap=5)
        self.requestSharedSessionPanel.SetSizer(self.requestSharedSessionPanelSizer)

        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))
        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))

        self.requestSharedSessionPanelSizer.Add(wx.StaticText(self.requestSharedSessionPanel, wx.ID_ANY, "  "))

        self.requestSharedSessionCheckBox = wx.CheckBox(self.requestSharedSessionPanel, wx.ID_ANY, "Request shared session")
        self.requestSharedSessionCheckBox.SetValue(True)
        self.requestSharedSessionPanelSizer.Add(self.requestSharedSessionCheckBox)
        self.requestSharedSessionCheckBox.SetFont(smallFont)
        
        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))
        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))

        self.requestSharedSessionPanel.SetSizerAndFit(self.requestSharedSessionPanelSizer)

        # Connection panels

        self.connectionLeftPanel.SetSizerAndFit(self.connectionLeftPanelSizer)
        self.connectionRightPanel.SetSizerAndFit(self.connectionRightPanelSizer)
        self.connectionPanel.SetSizerAndFit(self.connectionPanelSizer)

        # Globals tab
        
        self.globalsPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.globalsPanelSizer = wx.FlexGridSizer(rows=5, cols=1, vgap=15, hgap=15)

        self.globalsTopBorderPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsTopBorderPanel)

        self.globalsTopPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsTopPanel, flag=wx.EXPAND)
        self.globalsTopPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=15)

        self.globalsMiddlePanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsMiddlePanel, flag=wx.EXPAND)
        self.globalsMiddlePanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)

        self.globalsBottomPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsBottomPanel, flag=wx.EXPAND)
        self.globalsBottomPanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)

        self.globalsBottomBorderPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsBottomBorderPanel)

        # Interface options group box

        self.interfaceOptionsPanel = wx.Panel(self.globalsTopPanel, wx.ID_ANY)
        self.globalsTopPanelSizer.Add(self.interfaceOptionsPanel, flag=wx.EXPAND)

        self.interfaceOptionsGroupBox = wx.StaticBox(self.interfaceOptionsPanel, wx.ID_ANY, label="Interface Options")
        self.interfaceOptionsGroupBox.SetFont(smallFont)
        self.interfaceOptionsGroupBoxSizer = wx.StaticBoxSizer(self.interfaceOptionsGroupBox, wx.VERTICAL)
        self.interfaceOptionsPanel.SetSizer(self.interfaceOptionsGroupBoxSizer)

        self.innerInterfaceOptionsPanel = wx.Panel(self.interfaceOptionsPanel, wx.ID_ANY)
        self.innerInterfaceOptionsPanelSizer = wx.FlexGridSizer(rows=5, cols=1, vgap=5,hgap=5)
        self.innerInterfaceOptionsPanel.SetSizer(self.innerInterfaceOptionsPanelSizer)

        self.showToolbarsByDefaultCheckBox = wx.CheckBox(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Show toolbars by default")
        self.showToolbarsByDefaultCheckBox.SetValue(True)
        self.innerInterfaceOptionsPanelSizer.Add(self.showToolbarsByDefaultCheckBox)
        self.showToolbarsByDefaultCheckBox.SetFont(smallFont)
        
        self.warnWhenSwitchingToFullScreenModeCheckBox = wx.CheckBox(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Warn when switching to full-screen mode")
        self.warnWhenSwitchingToFullScreenModeCheckBox.SetValue(True)
        self.innerInterfaceOptionsPanelSizer.Add(self.warnWhenSwitchingToFullScreenModeCheckBox)
        self.warnWhenSwitchingToFullScreenModeCheckBox.SetFont(smallFont)
        
        self.numberOfConnectionsToRememberPanel = wx.Panel(self.innerInterfaceOptionsPanel, wx.ID_ANY)
        self.numberOfConnectionsToRememberPanelSizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5,hgap=5)
        self.numberOfConnectionsToRememberPanel.SetSizer(self.numberOfConnectionsToRememberPanelSizer)

        self.numberOfConnectionsToRememberLabel = wx.StaticText(self.numberOfConnectionsToRememberPanel, wx.ID_ANY, "Number of connections to remember:   ")
        self.numberOfConnectionsToRememberLabel.SetFont(smallFont)
        self.numberOfConnectionsToRememberPanelSizer.Add(self.numberOfConnectionsToRememberLabel, flag=wx.ALIGN_CENTER_VERTICAL)

        self.numberOfConnectionsToRememberSpinCtrl = wx.SpinCtrl(self.numberOfConnectionsToRememberPanel, value='32')
        self.numberOfConnectionsToRememberSpinCtrl.SetFont(smallFont)
        self.numberOfConnectionsToRememberPanelSizer.Add(self.numberOfConnectionsToRememberSpinCtrl)
        
        # This shouldn't be necessary but, otherwise the bottom border of the combo-box is clipped on my Mac.
        self.numberOfConnectionsToRememberPanelSizer.Add(wx.Panel(self.numberOfConnectionsToRememberPanel, wx.ID_ANY))

        self.numberOfConnectionsToRememberPanel.SetSizerAndFit(self.numberOfConnectionsToRememberPanelSizer)
        self.innerInterfaceOptionsPanelSizer.Add(self.numberOfConnectionsToRememberPanel, flag=wx.EXPAND)

        self.clearTheListOfSavedConnectionsButton = wx.Button(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Clear the list of saved connections")
        self.innerInterfaceOptionsPanelSizer.Add(self.clearTheListOfSavedConnectionsButton)
        self.clearTheListOfSavedConnectionsButton.SetFont(smallFont)
        
        self.innerInterfaceOptionsPanelSizer.Add(wx.Panel(self.innerInterfaceOptionsPanel, wx.ID_ANY))

        self.innerInterfaceOptionsPanel.SetSizerAndFit(self.innerInterfaceOptionsPanelSizer)
        self.interfaceOptionsGroupBoxSizer.Add(self.innerInterfaceOptionsPanel, flag=wx.EXPAND)
        self.interfaceOptionsPanel.SetSizerAndFit(self.interfaceOptionsGroupBoxSizer)

        # Local cursor shape group box

        self.localCursorShapePanel = wx.Panel(self.globalsTopPanel, wx.ID_ANY)
        self.globalsTopPanelSizer.Add(self.localCursorShapePanel, flag=wx.EXPAND)

        self.localCursorShapeGroupBox = wx.StaticBox(self.localCursorShapePanel, wx.ID_ANY, label="Local cursor shape")
        self.localCursorShapeGroupBox.SetFont(smallFont)
        self.localCursorShapeGroupBoxSizer = wx.StaticBoxSizer(self.localCursorShapeGroupBox, wx.VERTICAL)
        self.localCursorShapePanel.SetSizer(self.localCursorShapeGroupBoxSizer)

        self.innerLocalCursorShapePanel = wx.Panel(self.localCursorShapePanel, wx.ID_ANY)
        self.innerLocalCursorShapePanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5,hgap=5)
        self.innerLocalCursorShapePanel.SetSizer(self.innerLocalCursorShapePanelSizer)

        self.dotCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Dot cursor")
        self.dotCursorRadioButton.SetValue(True)
        self.innerLocalCursorShapePanelSizer.Add(self.dotCursorRadioButton)
        self.dotCursorRadioButton.SetFont(smallFont)
        
        self.smallDotCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Small dot cursor")
        self.innerLocalCursorShapePanelSizer.Add(self.smallDotCursorRadioButton)
        self.smallDotCursorRadioButton.SetFont(smallFont)
        
        self.normalArrowRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Normal arrow")
        self.innerLocalCursorShapePanelSizer.Add(self.normalArrowRadioButton)
        self.normalArrowRadioButton.SetFont(smallFont)
        
        self.noLocalCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "No local cursor")
        self.innerLocalCursorShapePanelSizer.Add(self.noLocalCursorRadioButton)
        self.noLocalCursorRadioButton.SetFont(smallFont)

        self.innerLocalCursorShapePanel.SetSizerAndFit(self.innerLocalCursorShapePanelSizer)
        self.localCursorShapeGroupBoxSizer.Add(self.innerLocalCursorShapePanel, flag=wx.EXPAND)
        self.localCursorShapePanel.SetSizerAndFit(self.localCursorShapeGroupBoxSizer)

        # Listening mode group box

        self.listeningModePanel = wx.Panel(self.globalsMiddlePanel, wx.ID_ANY)
        self.globalsMiddlePanelSizer.Add(self.listeningModePanel, flag=wx.EXPAND)

        self.listeningModeGroupBox = wx.StaticBox(self.listeningModePanel, wx.ID_ANY, label="Listening mode")
        self.listeningModeGroupBox.SetFont(smallFont)
        self.listeningModeGroupBoxSizer = wx.StaticBoxSizer(self.listeningModeGroupBox, wx.VERTICAL)
        self.listeningModePanel.SetSizer(self.listeningModeGroupBoxSizer)

        self.innerListeningModePanel = wx.Panel(self.listeningModePanel, wx.ID_ANY)
        self.innerListeningModePanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5,hgap=5)
        self.innerListeningModePanel.SetSizer(self.innerListeningModePanelSizer)

        self.acceptReverseVncConnectionsOnTcpPortPanel = wx.Panel(self.innerListeningModePanel, wx.ID_ANY)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5,hgap=5)
        self.acceptReverseVncConnectionsOnTcpPortPanel.SetSizer(self.acceptReverseVncConnectionsOnTcpPortPanelSizer)

        self.acceptReverseVncConnectionsOnTcpPortLabel = wx.StaticText(self.acceptReverseVncConnectionsOnTcpPortPanel, wx.ID_ANY, "Accept reverse VNC connection on TCP port:   ")
        self.acceptReverseVncConnectionsOnTcpPortLabel.SetFont(smallFont)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortLabel, flag=wx.ALIGN_CENTER_VERTICAL)

        self.acceptReverseVncConnectionsOnTcpPortSpinCtrl = wx.SpinCtrl(self.acceptReverseVncConnectionsOnTcpPortPanel, value='5500', size=(70,-1))
        self.acceptReverseVncConnectionsOnTcpPortSpinCtrl.SetFont(smallFont)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortSpinCtrl)
        
        # This shouldn't be necessary but, otherwise the bottom border of the combo-box is clipped on my Mac.
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(wx.Panel(self.acceptReverseVncConnectionsOnTcpPortPanel, wx.ID_ANY))

        self.acceptReverseVncConnectionsOnTcpPortPanel.SetSizerAndFit(self.acceptReverseVncConnectionsOnTcpPortPanelSizer)
        self.innerListeningModePanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortPanel, flag=wx.EXPAND)

        self.innerListeningModePanel.SetSizerAndFit(self.innerListeningModePanelSizer)
        self.listeningModeGroupBoxSizer.Add(self.innerListeningModePanel, flag=wx.EXPAND)
        self.listeningModePanel.SetSizerAndFit(self.listeningModeGroupBoxSizer)

        # Logging group box

        self.loggingPanel = wx.Panel(self.globalsBottomPanel, wx.ID_ANY)
        self.globalsBottomPanelSizer.Add(self.loggingPanel, flag=wx.EXPAND)

        self.loggingGroupBox = wx.StaticBox(self.loggingPanel, wx.ID_ANY, label="Logging")
        self.loggingGroupBox.SetFont(smallFont)
        self.loggingGroupBoxSizer = wx.StaticBoxSizer(self.loggingGroupBox, wx.VERTICAL)
        self.loggingPanel.SetSizer(self.loggingGroupBoxSizer)

        self.innerLoggingPanel = wx.Panel(self.loggingPanel, wx.ID_ANY)
        self.innerLoggingPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5,hgap=5)
        self.innerLoggingPanel.SetSizer(self.innerLoggingPanelSizer)

        self.writeLogToAFileCheckBox = wx.CheckBox(self.innerLoggingPanel, wx.ID_ANY, "Write log to a file:")
        self.innerLoggingPanelSizer.Add(self.writeLogToAFileCheckBox)
        self.writeLogToAFileCheckBox.SetFont(smallFont)

        self.vncViewerLogFilenameTextField = wx.StaticText(self.innerLoggingPanel, wx.ID_ANY, "vncviewer.log")
        self.innerLoggingPanelSizer.Add(self.vncViewerLogFilenameTextField)
        self.vncViewerLogFilenameTextField.SetFont(smallFont)

        self.browseButton = wx.Button(self.innerLoggingPanel, wx.ID_ANY, "Browse...")
        self.browseButton.Disable()
        self.innerLoggingPanelSizer.Add(self.browseButton)
        self.browseButton.SetFont(smallFont)

        self.verbosityLevelLabel = wx.StaticText(self.innerLoggingPanel, wx.ID_ANY, "Verbosity level:")
        self.verbosityLevelLabel.Disable()
        self.innerLoggingPanelSizer.Add(self.verbosityLevelLabel)
        self.verbosityLevelLabel.SetFont(smallFont)

        self.innerLoggingPanel.SetSizerAndFit(self.innerLoggingPanelSizer)
        self.loggingGroupBoxSizer.Add(self.innerLoggingPanel, flag=wx.EXPAND)
        self.loggingPanel.SetSizerAndFit(self.loggingGroupBoxSizer)

        # Globals panels

        self.globalsTopPanel.SetSizerAndFit(self.globalsTopPanelSizer)
        self.globalsMiddlePanel.SetSizerAndFit(self.globalsMiddlePanelSizer)
        self.globalsBottomPanel.SetSizerAndFit(self.globalsBottomPanelSizer)
        self.globalsPanel.SetSizerAndFit(self.globalsPanelSizer)

        # Adding Connection tab and Globals tab to tabbed view
        self.tabbedView.AddPage(self.connectionPanel, "Connection")
        self.tabbedView.AddPage(self.globalsPanel, "Globals")
       
        # Buttons panel

        notebookContainerPanelSizer.Add(wx.StaticText(self.notebookContainerPanel, wx.ID_ANY, "     "))
        self.buttonsPanel = wx.Panel(self.notebookContainerPanel, wx.ID_ANY)
        notebookContainerPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        notebookContainerPanelSizer.Add(wx.StaticText(self.notebookContainerPanel, wx.ID_ANY, "     "))

        okButton = wx.Button(self.buttonsPanel, wx.ID_ANY, "OK")
        cancelButton = wx.Button(self.buttonsPanel, wx.ID_ANY, "Cancel")
        
        buttonsPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5, hgap=5)
        buttonsPanelSizer.Add(wx.StaticText(self.buttonsPanel, wx.ID_ANY, "     "))
        buttonsPanelSizer.Add(okButton)
        buttonsPanelSizer.Add(cancelButton)
        buttonsPanelSizer.Add(wx.StaticText(self.buttonsPanel, wx.ID_ANY, "     "))
        self.buttonsPanel.SetAutoLayout(True)
        self.buttonsPanel.SetSizerAndFit(buttonsPanelSizer) 

        okButton.Bind(wx.EVT_BUTTON, self.onOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)
     
        self.notebookContainerPanel.SetSizer(notebookContainerPanelSizer)

        self.Layout()

        
    def onExit(self, event):
        self.Close(True)
    
    def onOK(self, event):
        self.Close(True)
        
    def onCancel(self, event):
        self.Close(True)
        #import sys
        #sys.exit(0)


class wx11vnc(wx.App):
    def OnInit(self):
        frame = MainWindow(None, wx.ID_ANY, "TurboVNC Viewer Options")
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

app = wx11vnc(0)
app.MainLoop()  

