# MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL

# Copyright (c) 2012-2013, Monash e-Research Centre (Monash University, Australia)
# All rights reserved.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# In addition, redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# -  Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# -  Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# -  Neither the name of the Monash University nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. SEE THE
# GNU GENERAL PUBLIC LICENSE FOR MORE DETAILS.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# Enquires: help@massive.org.au

import sys
import wx

LAUNCHER_VNC_OPTIONS_CONNECTION_TAB_INDEX = 0
LAUNCHER_VNC_OPTIONS_GLOBALS_TAB_INDEX = 1 
LAUNCHER_VNC_OPTIONS_AUTHENTICATION_TAB_INDEX = 2
LAUNCHER_VNC_OPTIONS_SHARING_TAB_INDEX = 3

class LauncherOptionsDialog(wx.Dialog):
    def __init__(self, parent, id, title, vncOptions, tabIndex):
        wx.Dialog.__init__(self, parent, id, title, 
            style=wx.DEFAULT_DIALOG_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX | wx.MAXIMIZE_BOX),name="optionsDialog")

        self.vncOptions = vncOptions
        self.tabIndex = tabIndex

        self.okClicked = False
       
        self.CenterOnParent()
        
        self.notebookContainerPanel = wx.Panel(self, wx.ID_ANY)

        self.tabbedView = wx.Notebook(self.notebookContainerPanel, wx.ID_ANY, style=(wx.NB_TOP))
        notebookContainerPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=15, hgap=5)

        notebookContainerPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        self.smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        if self.smallFont.GetPointSize() > 11:
            self.smallFont.SetPointSize(11)

        # Connection tab

        self.connectionPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.connectionPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=15, hgap=25)

        self.connectionLeftBorderPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionLeftBorderPanel)

        self.connectionLeftPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        if sys.platform.startswith("darwin"):
            self.connectionPanelSizer.Add(self.connectionLeftPanel, flag=wx.EXPAND|wx.TOP, border=0)
        else:
            self.connectionPanelSizer.Add(self.connectionLeftPanel, flag=wx.EXPAND|wx.TOP, border=15)
        self.connectionLeftPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)

        self.connectionRightPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        if sys.platform.startswith("darwin"):
            self.connectionPanelSizer.Add(self.connectionRightPanel, flag=wx.EXPAND|wx.TOP, border=0)
        else:
            self.connectionPanelSizer.Add(self.connectionRightPanel, flag=wx.EXPAND|wx.TOP, border=15)
        self.connectionRightPanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)

        self.connectionRightBorderPanel = wx.Panel(self.connectionPanel, wx.ID_ANY)
        self.connectionPanelSizer.Add(self.connectionRightBorderPanel)

        # Encoding group box

        self.encodingMethodsPresets = {}
        JPEG_CHROMINANCE_SUBSAMPLING_NONE_SLIDER_VALUE = 4
        self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)'] = \
            { \
                'jpeg_compression': True, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_NONE_SLIDER_VALUE, \
                'jpeg_image_quality': 95, \
                'enableZlibCompressionLevelWidgets': False, \
                'zlib_compression_level': 0 \
            }
        JPEG_CHROMINANCE_SUBSAMPLING_2X_SLIDER_VALUE = 3 
        self.encodingMethodsPresets['Tight + Medium Quality JPEG'] = \
            { \
                'jpeg_compression': True, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_2X_SLIDER_VALUE, \
                'jpeg_image_quality': 80, \
                'enableZlibCompressionLevelWidgets': False, \
                'zlib_compression_level': 0 \
            }
        JPEG_CHROMINANCE_SUBSAMPLING_4X_SLIDER_VALUE = 2 
        self.encodingMethodsPresets['Tight + Low Quality JPEG (WAN)'] = \
            { \
                'jpeg_compression': True, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_4X_SLIDER_VALUE, \
                'jpeg_image_quality': 30, \
                'enableZlibCompressionLevelWidgets': False, \
                'zlib_compression_level': 0 \
            }
        self.encodingMethodsPresets['Lossless Tight (Gigabit)'] = \
            { \
                'jpeg_compression': False, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_NONE_SLIDER_VALUE, \
                'jpeg_image_quality': 100, \
                'enableZlibCompressionLevelWidgets': True, \
                'zlib_compression_level': 0 \
            }
        self.encodingMethodsPresets['Lossless Tight + Zlib (WAN)'] = \
            { \
                'jpeg_compression': False, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_NONE_SLIDER_VALUE, \
                'jpeg_image_quality': 100, \
                'enableZlibCompressionLevelWidgets': True, \
                'zlib_compression_level': 1 \
            }
        self.encodingMethodsPresets['Custom'] = \
            { \
                'jpeg_compression': True, \
                'jpeg_chrominance_subsampling': JPEG_CHROMINANCE_SUBSAMPLING_NONE_SLIDER_VALUE, \
                'jpeg_image_quality': 95, \
                'enableZlibCompressionLevelWidgets': True, \
                'zlib_compression_level': 0 \
            }

        self.encodingPanel = wx.Panel(self.connectionLeftPanel, wx.ID_ANY)
        self.connectionLeftPanelSizer.Add(self.encodingPanel, flag=wx.EXPAND)

        self.encodingGroupBox = wx.StaticBox(self.encodingPanel, wx.ID_ANY, label="Encoding")
        self.encodingGroupBox.SetFont(self.smallFont)
        self.encodingGroupBoxSizer = wx.StaticBoxSizer(self.encodingGroupBox, wx.VERTICAL)
        self.encodingPanel.SetSizer(self.encodingGroupBoxSizer)

        self.innerEncodingPanel = wx.Panel(self.encodingPanel, wx.ID_ANY)
        self.innerEncodingPanelSizer = wx.FlexGridSizer(rows=10, cols = 1, vgap=5,hgap=5)
        self.innerEncodingPanel.SetSizer(self.innerEncodingPanelSizer)

        self.encodingMethodLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Encoding method:")
        self.innerEncodingPanelSizer.Add(self.encodingMethodLabel)
        self.encodingMethodLabel.SetFont(self.smallFont)
       
        self.encodingMethodsPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.encodingMethodsPanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5,hgap=5)
        self.encodingMethodsPanel.SetSizer(self.encodingMethodsPanelSizer)
        emptySpace = wx.StaticText(self.encodingMethodsPanel, wx.ID_ANY, "   ")
        self.encodingMethodsPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.encodingMethods = ['Tight + Perceptually Lossless JPEG (LAN)', 
            'Tight + Medium Quality JPEG', 
            'Tight + Low Quality JPEG (WAN)', 
            'Lossless Tight (Gigabit)', 
            'Lossless Tight + Zlib (WAN)']
        self.encodingMethodsComboBox = wx.Choice(self.encodingMethodsPanel, wx.ID_ANY, choices=self.encodingMethods)
        self.encodingMethodsComboBox.SetFont(self.smallFont)
        self.encodingMethodsComboBox.SetStringSelection('Tight + Perceptually Lossless JPEG (LAN)')
        self.encodingMethodsComboBox.Bind(wx.EVT_CHOICE, self.onSelectEncodingMethodFromComboBox)
        self.encodingMethodsPanelSizer.Add(self.encodingMethodsComboBox, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=2)

        self.encodingMethodsPanel.SetSizerAndFit(self.encodingMethodsPanelSizer)
        self.innerEncodingPanelSizer.Add(self.encodingMethodsPanel, flag=wx.EXPAND)

        self.jpegCompressionCheckBox = wx.CheckBox(self.innerEncodingPanel, wx.ID_ANY, "Allow JPEG compression")
        #self.jpegCompressionCheckBox.SetValue(True)
        self.jpegCompressionCheckBox.SetValue(self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['jpeg_compression'])
        if 'jpeg_compression' in vncOptions:
            self.jpegCompressionCheckBox.SetValue(vncOptions['jpeg_compression'])
        self.jpegCompressionCheckBox.SetFont(self.smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegCompressionCheckBox)

        self.jpegChrominanceSubsamplingLevel = {1:"Gray", 2:"4x", 3:"2x", 4:"None"}
        self.jpegChrominanceSubsamplingCommandLineString = {1:"gray", 2:"4x", 3:"2x", 4:"1x"}

        #self.jpegChrominanceSubsamplingLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG chrominance subsampling:    None")
        self.jpegChrominanceSubsamplingLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG chrominance subsampling:    " + self.jpegChrominanceSubsamplingLevel[self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['jpeg_chrominance_subsampling']])
        self.jpegChrominanceSubsamplingLabel.SetFont(self.smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegChrominanceSubsamplingLabel)

        self.jpegChrominanceSubsamplingPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.jpegChrominanceSubsamplingPanelSizer = wx.FlexGridSizer(rows=2, cols=4, vgap=5,hgap=5)
        self.jpegChrominanceSubsamplingPanel.SetSizer(self.jpegChrominanceSubsamplingPanelSizer)
        emptySpace = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "   ")
        self.jpegChrominanceSubsamplingPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.fastLabel = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "fast")
        self.fastLabel.SetFont(self.smallFont)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.fastLabel, flag=wx.EXPAND)

        self.jpegChrominanceSubsamplingSlider = wx.Slider(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.jpegChrominanceSubsamplingSlider)

        self.bestLabel = wx.StaticText(self.jpegChrominanceSubsamplingPanel, wx.ID_ANY, "best")
        self.bestLabel.SetFont(self.smallFont)
        self.jpegChrominanceSubsamplingPanelSizer.Add(self.bestLabel, flag=wx.EXPAND)

        self.jpegChrominanceSubsamplingPanel.SetSizerAndFit(self.jpegChrominanceSubsamplingPanelSizer)
        self.jpegChrominanceSubsamplingSlider.SetMin(1)
        self.jpegChrominanceSubsamplingSlider.SetMax(4)
        #self.jpegChrominanceSubsamplingSlider.SetValue(4)
        self.jpegChrominanceSubsamplingSlider.SetValue(self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['jpeg_chrominance_subsampling'])
        self.jpegChrominanceSubsamplingSlider.SetTickFreq(1)
        if 'jpeg_chrominance_subsampling' in vncOptions:
            for jpeg_chrominance_subsampling_slider_value in range(1, 4):
                if vncOptions['jpeg_chrominance_subsampling']==self.jpegChrominanceSubsamplingCommandLineString[jpeg_chrominance_subsampling_slider_value]:
                    self.jpegChrominanceSubsamplingSlider.SetValue(jpeg_chrominance_subsampling_slider_value)
            self.jpegChrominanceSubsamplingSlider.SetLabel("JPEG chrominance subsampling:    " + self.jpegChrominanceSubsamplingLevel[self.jpegChrominanceSubsamplingSlider.GetValue()])
        self.jpegChrominanceSubsamplingSlider.Bind(wx.EVT_SLIDER, self.onAdjustEncodingMethodSliders)
        self.innerEncodingPanelSizer.Add(self.jpegChrominanceSubsamplingPanel, flag=wx.EXPAND)

        #self.jpegImageQualityLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG image quality:    95", style=wx.TE_READONLY)
        self.jpegImageQualityLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "JPEG image quality:    " + str(self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['jpeg_image_quality']), style=wx.TE_READONLY)
        self.jpegImageQualityLabel.SetFont(self.smallFont)
        self.innerEncodingPanelSizer.Add(self.jpegImageQualityLabel)

        self.jpegImageQualityPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.jpegImageQualityPanelSizer = wx.FlexGridSizer(rows=2, cols=4, vgap=5,hgap=5)
        self.jpegImageQualityPanel.SetSizer(self.jpegImageQualityPanelSizer)
        emptySpace = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "   ")
        self.jpegImageQualityPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.poorImageQualityLabel = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "poor")
        self.poorImageQualityLabel.SetFont(self.smallFont)
        self.jpegImageQualityPanelSizer.Add(self.poorImageQualityLabel, flag=wx.EXPAND)

        self.jpegImageQualitySlider = wx.Slider(self.jpegImageQualityPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.jpegImageQualitySlider.SetMin(1)
        self.jpegImageQualitySlider.SetMax(100)
        #self.jpegImageQualitySlider.SetValue(95)
        self.jpegImageQualitySlider.SetTickFreq(10)
        self.jpegImageQualitySlider.SetValue(self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['jpeg_image_quality'])
        if 'jpeg_image_quality' in vncOptions:
            self.jpegImageQualitySlider.SetValue(int(vncOptions['jpeg_image_quality']))
            self.jpegImageQualityLabel.SetLabel("JPEG image quality:    " + str(self.jpegImageQualitySlider.GetValue()))
        self.jpegImageQualitySlider.Bind(wx.EVT_SLIDER, self.onAdjustEncodingMethodSliders)
        self.jpegImageQualityPanelSizer.Add(self.jpegImageQualitySlider)

        self.bestImageQualityLabel = wx.StaticText(self.jpegImageQualityPanel, wx.ID_ANY, "best")
        self.bestImageQualityLabel.SetFont(self.smallFont)
        self.jpegImageQualityPanelSizer.Add(self.bestImageQualityLabel, flag=wx.EXPAND)

        self.jpegImageQualityPanel.SetSizerAndFit(self.jpegImageQualityPanelSizer)
        self.innerEncodingPanelSizer.Add(self.jpegImageQualityPanel, flag=wx.EXPAND)

        self.zlibCompressionLevel = {0:"None", 1:"1"}
        self.zlibCompressionLevelCommandLineString = {0:"0", 1:"1"}

        #self.zlibCompressionLevelLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Zlib compression level:     1")
        #self.zlibCompressionLevelLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Zlib compression level:     None")
        self.zlibCompressionLevelLabel = wx.StaticText(self.innerEncodingPanel, wx.ID_ANY, "Zlib compression level:     " + self.zlibCompressionLevel[self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['zlib_compression_level']])
        self.zlibCompressionLevelLabel.SetFont(self.smallFont)
        self.zlibCompressionLevelLabel.Disable()
        self.innerEncodingPanelSizer.Add(self.zlibCompressionLevelLabel)

        self.zlibCompressionLevelPanel = wx.Panel(self.innerEncodingPanel, wx.ID_ANY)
        self.zlibCompressionLevelPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=5,hgap=5)
        self.zlibCompressionLevelPanel.SetSizer(self.zlibCompressionLevelPanelSizer)
        emptySpace = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "   ")
        self.zlibCompressionLevelPanelSizer.Add(emptySpace, flag=wx.EXPAND)

        self.fastZlibCompressionLabel = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "fast")
        self.fastZlibCompressionLabel.SetFont(self.smallFont)
        self.fastZlibCompressionLabel.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.fastZlibCompressionLabel, flag=wx.EXPAND)

        self.zlibCompressionLevelSlider = wx.Slider(self.zlibCompressionLevelPanel, wx.ID_ANY, style=wx.SL_AUTOTICKS | wx.SL_HORIZONTAL)
        self.zlibCompressionLevelSlider.SetMin(0)
        self.zlibCompressionLevelSlider.SetMax(1)
        #self.zlibCompressionLevelSlider.SetValue(1)
        self.zlibCompressionLevelSlider.SetValue(self.encodingMethodsPresets['Tight + Perceptually Lossless JPEG (LAN)']['zlib_compression_level'])
        self.zlibCompressionLevelSlider.SetTickFreq(1)
        if 'zlib_compression_level' in vncOptions:
            self.zlibCompressionLevelSlider.SetValue(int(vncOptions['zlib_compression_level']))
            self.zlibCompressionLevelSlider.SetLabel("Zlib compression level:     " + self.zlibCompressionLevel[self.zlibCompressionLevelSlider.GetValue()])
        self.zlibCompressionLevelSlider.Bind(wx.EVT_SLIDER, self.onAdjustEncodingMethodSliders)
        self.zlibCompressionLevelSlider.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.zlibCompressionLevelSlider)

        self.bestZlibCompressionLabel = wx.StaticText(self.zlibCompressionLevelPanel, wx.ID_ANY, "best")
        self.bestZlibCompressionLabel.SetFont(self.smallFont)
        self.bestZlibCompressionLabel.Disable()
        self.zlibCompressionLevelPanelSizer.Add(self.bestZlibCompressionLabel, flag=wx.EXPAND)

        self.zlibCompressionLevelPanel.SetSizerAndFit(self.zlibCompressionLevelPanelSizer)
        self.zlibCompressionLevelPanel.Disable()
        self.innerEncodingPanelSizer.Add(self.zlibCompressionLevelPanel, flag=wx.EXPAND)

        self.copyRectEncodingCheckBox = wx.CheckBox(self.innerEncodingPanel, wx.ID_ANY, "Allow CopyRect encoding")
        self.copyRectEncodingCheckBox.SetValue(True)
        self.copyRectEncodingCheckBox.SetFont(self.smallFont)
        self.innerEncodingPanelSizer.Add(self.copyRectEncodingCheckBox)

        self.innerEncodingPanel.SetSizerAndFit(self.innerEncodingPanelSizer)
        self.encodingGroupBoxSizer.Add(self.innerEncodingPanel, flag=wx.EXPAND)
        self.encodingPanel.SetSizerAndFit(self.encodingGroupBoxSizer)

        # Ensure that the encoding methods combo box is set to the 
        # appropriate preset, based on the values of the sliders.
        self.onAdjustEncodingMethodSliders(None)

        # Restrictions group box

        self.restrictionsPanel = wx.Panel(self.connectionLeftPanel, wx.ID_ANY)
        self.connectionLeftPanelSizer.Add(self.restrictionsPanel, flag=wx.EXPAND)

        self.restrictionsGroupBox = wx.StaticBox(self.restrictionsPanel, wx.ID_ANY, label="Restrictions")
        self.restrictionsGroupBox.SetFont(self.smallFont)
        self.restrictionsGroupBoxSizer = wx.StaticBoxSizer(self.restrictionsGroupBox, wx.VERTICAL)
        self.restrictionsPanel.SetSizer(self.restrictionsGroupBoxSizer)

        self.innerRestrictionsPanel = wx.Panel(self.restrictionsPanel, wx.ID_ANY)
        self.innerRestrictionsPanelSizer = wx.FlexGridSizer(rows=2, cols = 1, vgap=5,hgap=5)
        self.innerRestrictionsPanel.SetSizer(self.innerRestrictionsPanelSizer)

        self.viewOnlyCheckBox = wx.CheckBox(self.innerRestrictionsPanel, wx.ID_ANY, "View only (inputs ignored)")
        self.viewOnlyCheckBox.SetValue(False)
        if 'view_only' in vncOptions:
            self.viewOnlyCheckBox.SetValue(vncOptions['view_only'])
        self.innerRestrictionsPanelSizer.Add(self.viewOnlyCheckBox)
        self.viewOnlyCheckBox.SetFont(self.smallFont)
        
        self.disableClipboardTransferCheckBox = wx.CheckBox(self.innerRestrictionsPanel, wx.ID_ANY, "Disable clipboard transfer")
        self.disableClipboardTransferCheckBox.SetValue(False)
        if 'disable_clipboard_transfer' in vncOptions:
            self.disableClipboardTransferCheckBox.SetValue(vncOptions['disable_clipboard_transfer'])
        if not sys.platform.startswith("win"):
            self.disableClipboardTransferCheckBox.SetValue(False)
            self.disableClipboardTransferCheckBox.Disable()
        self.innerRestrictionsPanelSizer.Add(self.disableClipboardTransferCheckBox)
        self.disableClipboardTransferCheckBox.SetFont(self.smallFont)
        
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
        self.displayGroupBox.SetFont(self.smallFont)
        self.displayGroupBoxSizer = wx.StaticBoxSizer(self.displayGroupBox, wx.VERTICAL)
        self.displayPanel.SetSizer(self.displayGroupBoxSizer)

        self.innerDisplayPanel = wx.Panel(self.displayPanel, wx.ID_ANY)
        self.innerDisplayPanelSizer = wx.FlexGridSizer(rows=5, cols = 1, vgap=5,hgap=5)
        self.innerDisplayPanel.SetSizer(self.innerDisplayPanelSizer)

        self.scaleByPanel = wx.Panel(self.innerDisplayPanel, wx.ID_ANY)
        self.scaleByPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5,hgap=5)
        self.scaleByPanel.SetSizer(self.scaleByPanelSizer)

        self.scaleByLabel = wx.StaticText(self.scaleByPanel, wx.ID_ANY, "Scale by:   ")
        self.scaleByLabel.SetFont(self.smallFont)
        self.scaleByPanelSizer.Add(self.scaleByLabel, flag=wx.ALIGN_CENTER)

        scaleOptions = [
            '25',
            '50',
            '75',
            '90',
            '100', 
            '125', 
            '150',
            '200',
            'Auto']
        self.scaleByComboBox = wx.Choice(self.scaleByPanel, wx.ID_ANY, choices=scaleOptions)
        SCALE_OPTION_100_PERCENT = 4
        self.scaleByComboBox.SetSelection(SCALE_OPTION_100_PERCENT)
        if 'scale' in vncOptions:
            self.scaleByComboBox.SetStringSelection(vncOptions['scale'])
        self.scaleByComboBox.SetFont(self.smallFont)
        self.scaleByPanelSizer.Add(self.scaleByComboBox, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=2)

        self.percentageSignLabel = wx.StaticText(self.scaleByPanel, wx.ID_ANY, "  %")
        self.percentageSignLabel.SetFont(self.smallFont)
        self.scaleByPanelSizer.Add(self.percentageSignLabel, flag=wx.ALIGN_CENTER)

        self.scaleByPanel.SetSizerAndFit(self.scaleByPanelSizer)
        self.innerDisplayPanelSizer.Add(self.scaleByPanel, flag=wx.EXPAND)

        if not sys.platform.startswith("win"):
            self.scaleByPanel.Disable()
            self.scaleByLabel.Disable()
            self.scaleByComboBox.Disable()
            self.percentageSignLabel.Disable()

        self.doubleBufferingCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Double buffering")
        self.doubleBufferingCheckBox.SetValue(True)
        if 'double_buffering' in vncOptions:
            self.doubleBufferingCheckBox.SetValue(vncOptions['double_buffering'])
        self.innerDisplayPanelSizer.Add(self.doubleBufferingCheckBox)
        self.doubleBufferingCheckBox.SetFont(self.smallFont)
        
        self.fullScreenModeCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Full-screen mode")
        self.fullScreenModeCheckBox.SetValue(False)
        if 'full_screen_mode' in vncOptions:
            self.fullScreenModeCheckBox.SetValue(vncOptions['full_screen_mode'])
        self.innerDisplayPanelSizer.Add(self.fullScreenModeCheckBox)
        self.fullScreenModeCheckBox.SetFont(self.smallFont)
        
        self.spanModePanel = wx.Panel(self.innerDisplayPanel, wx.ID_ANY)
        self.spanModePanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5,hgap=5)
        self.spanModePanel.SetSizer(self.spanModePanelSizer)

        self.spanModeLabel = wx.StaticText(self.spanModePanel, wx.ID_ANY, "Span mode:   ")
        self.spanModeLabel.SetFont(self.smallFont)
        self.spanModePanelSizer.Add(self.spanModeLabel, flag=wx.ALIGN_CENTER)

        spanModes = [
            'Primary monitor only',
            'All monitors',
            'Automatic']
        self.spanModeComboBox = wx.Choice(self.spanModePanel, wx.ID_ANY, choices=spanModes)
        SPAN_MODE_AUTOMATIC = 2
        self.spanModeComboBox.SetSelection(SPAN_MODE_AUTOMATIC)
        self.spanModeCommandLineString = {0:"primary", 1:"all", 2:"auto"}
        if 'span' in vncOptions:
            if vncOptions['span']=='primary':
                self.spanModeComboBox.SetStringSelection('Primary monitor only')
            if vncOptions['span']=='all':
                self.spanModeComboBox.SetStringSelection('All monitors')
            if vncOptions['span']=='auto':
                self.spanModeComboBox.SetStringSelection('Automatic')
        self.spanModeComboBox.SetFont(self.smallFont)
        self.spanModePanelSizer.Add(self.spanModeComboBox, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=2)

        self.spanModePanel.SetSizerAndFit(self.spanModePanelSizer)
        self.innerDisplayPanelSizer.Add(self.spanModePanel, flag=wx.EXPAND)

        if not sys.platform.startswith("win"):
            self.spanModePanel.Disable()
            self.spanModeLabel.Disable()
            self.spanModeComboBox.Disable()

        self.deiconifyOnRemoteBellEventCheckBox = wx.CheckBox(self.innerDisplayPanel, wx.ID_ANY, "Deiconify on remote Bell event")
        #self.deiconifyOnRemoteBellEventCheckBox.SetValue(False)
        self.deiconifyOnRemoteBellEventCheckBox.SetValue(True)
        if 'deiconify_on_remote_bell_event' in vncOptions:
            self.deiconifyOnRemoteBellEventCheckBox.SetValue(vncOptions['deiconify_on_remote_bell_event'])
        self.innerDisplayPanelSizer.Add(self.deiconifyOnRemoteBellEventCheckBox)
        self.deiconifyOnRemoteBellEventCheckBox.SetFont(self.smallFont)
        
        self.innerDisplayPanel.SetSizerAndFit(self.innerDisplayPanelSizer)
        self.displayGroupBoxSizer.Add(self.innerDisplayPanel, flag=wx.EXPAND)
        self.displayPanel.SetSizerAndFit(self.displayGroupBoxSizer)

        # Mouse group box

        self.mousePanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.mousePanel, flag=wx.EXPAND)

        self.mouseGroupBox = wx.StaticBox(self.mousePanel, wx.ID_ANY, label="Mouse")
        self.mouseGroupBox.SetFont(self.smallFont)
        self.mouseGroupBoxSizer = wx.StaticBoxSizer(self.mouseGroupBox, wx.VERTICAL)
        self.mousePanel.SetSizer(self.mouseGroupBoxSizer)

        self.innerMousePanel = wx.Panel(self.mousePanel)
        self.innerMousePanelSizer = wx.FlexGridSizer(rows=2, cols = 1, vgap=5,hgap=5)
        self.innerMousePanel.SetSizer(self.innerMousePanelSizer)

        self.emulate3ButtonsWith2ButtonClickCheckBox = wx.CheckBox(self.innerMousePanel, wx.ID_ANY, "Emulate 3 buttons (with 2-button click)")
        if sys.platform.startswith("win"):
            self.emulate3ButtonsWith2ButtonClickCheckBox.SetValue(True)
            if 'emulate3' in vncOptions:
                self.emulate3ButtonsWith2ButtonClickCheckBox.SetValue(vncOptions['emulate3'])
        self.innerMousePanelSizer.Add(self.emulate3ButtonsWith2ButtonClickCheckBox)
        self.emulate3ButtonsWith2ButtonClickCheckBox.SetFont(self.smallFont)
        
        self.swapMouseButtons2And3CheckBox = wx.CheckBox(self.innerMousePanel, wx.ID_ANY, "Swap mouse buttons 2 and 3")
        self.swapMouseButtons2And3CheckBox.SetValue(False)
        if sys.platform.startswith("win"):
            if 'swapmouse' in vncOptions:
                self.swapMouseButtons2And3CheckBox.SetValue(vncOptions['swapmouse'])
        self.innerMousePanelSizer.Add(self.swapMouseButtons2And3CheckBox)
        self.swapMouseButtons2And3CheckBox.SetFont(self.smallFont)
        
        self.innerMousePanel.SetSizerAndFit(self.innerMousePanelSizer)
        self.mouseGroupBoxSizer.Add(self.innerMousePanel, flag=wx.EXPAND)
        self.mousePanel.SetSizerAndFit(self.mouseGroupBoxSizer)

        if not sys.platform.startswith("win"):
            self.mousePanel.Disable()
            self.mouseGroupBox.Disable()
            self.innerMousePanel.Disable()
            self.emulate3ButtonsWith2ButtonClickCheckBox.Disable()
            self.swapMouseButtons2And3CheckBox.Disable()

        # Mouse cursor group box

        self.mouseCursorPanel = wx.Panel(self.connectionRightPanel, wx.ID_ANY)
        self.connectionRightPanelSizer.Add(self.mouseCursorPanel, flag=wx.EXPAND)

        self.mouseCursorGroupBox = wx.StaticBox(self.mouseCursorPanel, wx.ID_ANY, label="Mouse cursor")
        self.mouseCursorGroupBox.SetFont(self.smallFont)
        self.mouseCursorGroupBoxSizer = wx.StaticBoxSizer(self.mouseCursorGroupBox, wx.VERTICAL)
        self.mouseCursorPanel.SetSizer(self.mouseCursorGroupBoxSizer)

        self.innerMouseCursorPanel = wx.Panel(self.mouseCursorPanel, wx.ID_ANY)
        self.innerMouseCursorPanelSizer = wx.FlexGridSizer(rows=3, cols = 1, vgap=5,hgap=5)
        self.innerMouseCursorPanel.SetSizer(self.innerMouseCursorPanelSizer)

        self.trackRemoteCursorLocallyRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Track remote cursor locally")
        self.trackRemoteCursorLocallyRadioButton.SetValue(True)
        if 'track_remote_cursor_locally' in vncOptions:
            self.trackRemoteCursorLocallyRadioButton.SetValue(vncOptions['track_remote_cursor_locally'])
        self.innerMouseCursorPanelSizer.Add(self.trackRemoteCursorLocallyRadioButton)
        self.trackRemoteCursorLocallyRadioButton.SetFont(self.smallFont)
        
        self.letRemoteServerDealWithMouseCursorRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Let remote server deal with mouse cursor")
        self.letRemoteServerDealWithMouseCursorRadioButton.SetValue(False)
        if 'let_remote_server_deal_with_mouse_cursor' in vncOptions:
            self.letRemoteServerDealWithMouseCursorRadioButton.SetValue(vncOptions['let_remote_server_deal_with_mouse_cursor'])
        self.innerMouseCursorPanelSizer.Add(self.letRemoteServerDealWithMouseCursorRadioButton)
        self.letRemoteServerDealWithMouseCursorRadioButton.SetFont(self.smallFont)
        
        self.dontShowRemoteCursorRadioButton = wx.RadioButton(self.innerMouseCursorPanel, wx.ID_ANY, "Don't show remote cursor")
        self.dontShowRemoteCursorRadioButton.SetValue(False)
        if 'dont_show_remote_cursor' in vncOptions:
            self.dontShowRemoteCursorRadioButton.SetValue(vncOptions['dont_show_remote_cursor'])
        self.innerMouseCursorPanelSizer.Add(self.dontShowRemoteCursorRadioButton)
        self.dontShowRemoteCursorRadioButton.SetFont(self.smallFont)
        
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
        if 'request_shared_session' in vncOptions:
            self.requestSharedSessionCheckBox.SetValue(vncOptions['request_shared_session'])
        self.requestSharedSessionPanelSizer.Add(self.requestSharedSessionCheckBox)
        self.requestSharedSessionCheckBox.SetFont(self.smallFont)
        
        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))
        self.requestSharedSessionPanelSizer.Add(wx.Panel(self.requestSharedSessionPanel, wx.ID_ANY))

        self.requestSharedSessionPanel.SetSizerAndFit(self.requestSharedSessionPanelSizer)

        # Connection panels

        self.connectionLeftPanel.SetSizerAndFit(self.connectionLeftPanelSizer)
        self.connectionRightPanel.SetSizerAndFit(self.connectionRightPanelSizer)
        self.connectionPanel.SetSizerAndFit(self.connectionPanelSizer)
        self.connectionPanel.Layout()

        # Globals tab
        
        self.globalsPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.globalsPanelSizer = wx.FlexGridSizer(rows=5, cols=1, vgap=15, hgap=15)

        self.globalsTopBorderPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsTopBorderPanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=25)

        self.globalsTopPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsTopPanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=25)
        self.globalsTopPanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5, hgap=25)

        self.globalsMiddlePanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsMiddlePanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=25)
        self.globalsMiddlePanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)

        self.globalsBottomPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsBottomPanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=25)
        self.globalsBottomPanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)

        self.globalsBottomBorderPanel = wx.Panel(self.globalsPanel, wx.ID_ANY)
        self.globalsPanelSizer.Add(self.globalsBottomBorderPanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=25)

        if sys.platform.startswith("darwin"):
            self.globalsPanelSizer.SetFlexibleDirection(wx.VERTICAL)
            self.globalsTopPanelSizer.SetFlexibleDirection(wx.VERTICAL)
            self.globalsMiddlePanelSizer.SetFlexibleDirection(wx.VERTICAL)
            self.globalsBottomPanelSizer.SetFlexibleDirection(wx.VERTICAL)

            self.globalsPanelSizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)
            self.globalsTopPanelSizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)
            self.globalsMiddlePanelSizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)
            self.globalsBottomPanelSizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_ALL)

        # Interface options group box

        self.interfaceOptionsPanel = wx.Panel(self.globalsTopPanel, wx.ID_ANY)
        self.globalsTopPanelSizer.Add(self.interfaceOptionsPanel, flag=wx.EXPAND)

        self.interfaceOptionsGroupBox = wx.StaticBox(self.interfaceOptionsPanel, wx.ID_ANY, label="Interface Options")
        self.interfaceOptionsGroupBox.SetFont(self.smallFont)
        #self.interfaceOptionsGroupBoxSizer = wx.StaticBoxSizer(self.interfaceOptionsGroupBox, wx.VERTICAL)
        self.interfaceOptionsGroupBoxSizer = wx.StaticBoxSizer(self.interfaceOptionsGroupBox, wx.HORIZONTAL)
        self.interfaceOptionsPanel.SetSizer(self.interfaceOptionsGroupBoxSizer)

        self.innerInterfaceOptionsPanel = wx.Panel(self.interfaceOptionsPanel, wx.ID_ANY)
        self.innerInterfaceOptionsPanelSizer = wx.FlexGridSizer(rows=5, cols=1, vgap=5,hgap=5)
        self.innerInterfaceOptionsPanel.SetSizer(self.innerInterfaceOptionsPanelSizer)

        self.showToolbarsByDefaultCheckBox = wx.CheckBox(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Show toolbars by default")
        if sys.platform.startswith("win"):
            self.showToolbarsByDefaultCheckBox.SetValue(True)
            if 'toolbar' in vncOptions:
                self.showToolbarsByDefaultCheckBox.SetValue(vncOptions['toolbar'])
        else:
            self.showToolbarsByDefaultCheckBox.SetValue(False)
            self.showToolbarsByDefaultCheckBox.Disable()
        self.innerInterfaceOptionsPanelSizer.Add(self.showToolbarsByDefaultCheckBox)
        self.showToolbarsByDefaultCheckBox.SetFont(self.smallFont)
        
        self.warnWhenSwitchingToFullScreenModeCheckBox = wx.CheckBox(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Warn when switching to full-screen mode")
        self.warnWhenSwitchingToFullScreenModeCheckBox.SetValue(True)
        self.innerInterfaceOptionsPanelSizer.Add(self.warnWhenSwitchingToFullScreenModeCheckBox)
        self.warnWhenSwitchingToFullScreenModeCheckBox.SetFont(self.smallFont)
        
        self.numberOfConnectionsToRememberPanel = wx.Panel(self.innerInterfaceOptionsPanel, wx.ID_ANY)
        self.numberOfConnectionsToRememberPanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5,hgap=5)
        self.numberOfConnectionsToRememberPanel.SetSizer(self.numberOfConnectionsToRememberPanelSizer)

        self.numberOfConnectionsToRememberLabel = wx.StaticText(self.numberOfConnectionsToRememberPanel, wx.ID_ANY, "Number of connections to remember:   ")
        self.numberOfConnectionsToRememberLabel.SetFont(self.smallFont)
        self.numberOfConnectionsToRememberPanelSizer.Add(self.numberOfConnectionsToRememberLabel, flag=wx.ALIGN_CENTER_VERTICAL)

        if sys.platform.startswith("win"):
            self.numberOfConnectionsToRememberSpinCtrl = wx.SpinCtrl(self.numberOfConnectionsToRememberPanel, value='32')
        else:
            self.numberOfConnectionsToRememberSpinCtrl = wx.SpinCtrl(self.numberOfConnectionsToRememberPanel, value='0')
        self.numberOfConnectionsToRememberSpinCtrl.SetFont(self.smallFont)
        self.numberOfConnectionsToRememberPanelSizer.Add(self.numberOfConnectionsToRememberSpinCtrl, wx.EXPAND|wx.TOP|wx.BOTTOM, border=2)
        
        self.numberOfConnectionsToRememberPanel.SetSizerAndFit(self.numberOfConnectionsToRememberPanelSizer)
        self.innerInterfaceOptionsPanelSizer.Add(self.numberOfConnectionsToRememberPanel, flag=wx.EXPAND)

        self.clearTheListOfSavedConnectionsButton = wx.Button(self.innerInterfaceOptionsPanel, wx.ID_ANY, "Clear the list of saved connections")
        self.innerInterfaceOptionsPanelSizer.Add(self.clearTheListOfSavedConnectionsButton)
        self.clearTheListOfSavedConnectionsButton.SetFont(self.smallFont)
        
        self.innerInterfaceOptionsPanelSizer.Add(wx.Panel(self.innerInterfaceOptionsPanel, wx.ID_ANY))

        self.innerInterfaceOptionsPanel.SetSizerAndFit(self.innerInterfaceOptionsPanelSizer)
        self.interfaceOptionsGroupBoxSizer.Add(self.innerInterfaceOptionsPanel, flag=wx.EXPAND)
        self.interfaceOptionsPanel.SetSizerAndFit(self.interfaceOptionsGroupBoxSizer)

        if not sys.platform.startswith("win"):
            self.interfaceOptionsPanel.Disable()
            self.interfaceOptionsGroupBox.Disable()
            self.showToolbarsByDefaultCheckBox.Disable()
        self.warnWhenSwitchingToFullScreenModeCheckBox.Disable()
        self.numberOfConnectionsToRememberPanel.Disable()
        self.numberOfConnectionsToRememberLabel.Disable()
        self.numberOfConnectionsToRememberSpinCtrl.Disable()
        self.clearTheListOfSavedConnectionsButton.Disable()

        # Local cursor shape group box

        self.localCursorShapePanel = wx.Panel(self.globalsTopPanel, wx.ID_ANY)
        self.globalsTopPanelSizer.Add(self.localCursorShapePanel, flag=wx.EXPAND)

        self.localCursorShapeGroupBox = wx.StaticBox(self.localCursorShapePanel, wx.ID_ANY, label="Local cursor shape")
        self.localCursorShapeGroupBox.SetFont(self.smallFont)
        #self.localCursorShapeGroupBoxSizer = wx.StaticBoxSizer(self.localCursorShapeGroupBox, wx.VERTICAL)
        self.localCursorShapeGroupBoxSizer = wx.StaticBoxSizer(self.localCursorShapeGroupBox, wx.HORIZONTAL)
        self.localCursorShapePanel.SetSizer(self.localCursorShapeGroupBoxSizer)

        self.innerLocalCursorShapePanel = wx.Panel(self.localCursorShapePanel, wx.ID_ANY)
        self.innerLocalCursorShapePanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5,hgap=5)
        self.innerLocalCursorShapePanel.SetSizer(self.innerLocalCursorShapePanelSizer)

        spacingRightOfRadioButtons = 60

        self.dotCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Dot cursor")
        if sys.platform.startswith("win"):
            self.dotCursorRadioButton.SetValue(True)
            if 'dotcursor' in vncOptions:
                self.dotCursorRadioButton.SetValue(vncOptions['dotcursor'])
        self.innerLocalCursorShapePanelSizer.Add(self.dotCursorRadioButton, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfRadioButtons)
        self.dotCursorRadioButton.SetFont(self.smallFont)
        
        self.smallDotCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Small dot cursor")
        self.innerLocalCursorShapePanelSizer.Add(self.smallDotCursorRadioButton, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfRadioButtons)
        self.smallDotCursorRadioButton.SetFont(self.smallFont)
        if sys.platform.startswith("win"):
            if 'smalldotcursor' in vncOptions:
                self.smallDotCursorRadioButton.SetValue(vncOptions['smalldotcursor'])
        
        self.normalArrowRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "Normal arrow")
        self.innerLocalCursorShapePanelSizer.Add(self.normalArrowRadioButton, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfRadioButtons)
        self.normalArrowRadioButton.SetFont(self.smallFont)
        if sys.platform.startswith("win"):
            if 'normalcursor' in vncOptions:
                self.normalArrowRadioButton.SetValue(vncOptions['normalcursor'])
        
        self.noLocalCursorRadioButton = wx.RadioButton(self.innerLocalCursorShapePanel, wx.ID_ANY, "No local cursor")
        self.innerLocalCursorShapePanelSizer.Add(self.noLocalCursorRadioButton, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfRadioButtons)
        self.noLocalCursorRadioButton.SetFont(self.smallFont)
        if sys.platform.startswith("win"):
            if 'nocursor' in vncOptions:
                self.noLocalCursorRadioButton.SetValue(vncOptions['nocursor'])

        self.innerLocalCursorShapePanel.SetSizerAndFit(self.innerLocalCursorShapePanelSizer)
        self.localCursorShapeGroupBoxSizer.Add(self.innerLocalCursorShapePanel, flag=wx.EXPAND)
        self.localCursorShapePanel.SetSizerAndFit(self.localCursorShapeGroupBoxSizer)

        if not sys.platform.startswith("win"):
            self.localCursorShapePanel.Disable()
            self.innerLocalCursorShapePanel.Disable()
            self.dotCursorRadioButton.Disable()
            self.smallDotCursorRadioButton.Disable()
            self.normalArrowRadioButton.Disable()
            self.noLocalCursorRadioButton.Disable()

        # Listening mode group box

        self.listeningModePanel = wx.Panel(self.globalsMiddlePanel, wx.ID_ANY)
        self.globalsMiddlePanelSizer.Add(self.listeningModePanel, flag=wx.EXPAND)

        self.listeningModeGroupBox = wx.StaticBox(self.listeningModePanel, wx.ID_ANY, label="Listening mode")
        self.listeningModeGroupBox.SetFont(self.smallFont)
        self.listeningModeGroupBoxSizer = wx.StaticBoxSizer(self.listeningModeGroupBox, wx.VERTICAL)
        self.listeningModePanel.SetSizer(self.listeningModeGroupBoxSizer)

        self.innerListeningModePanel = wx.Panel(self.listeningModePanel, wx.ID_ANY)
        self.innerListeningModePanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5,hgap=5)
        self.innerListeningModePanel.SetSizer(self.innerListeningModePanelSizer)

        self.acceptReverseVncConnectionsOnTcpPortPanel = wx.Panel(self.innerListeningModePanel, wx.ID_ANY)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5,hgap=5)
        self.acceptReverseVncConnectionsOnTcpPortPanel.SetSizer(self.acceptReverseVncConnectionsOnTcpPortPanelSizer)

        self.acceptReverseVncConnectionsOnTcpPortLabel = wx.StaticText(self.acceptReverseVncConnectionsOnTcpPortPanel, wx.ID_ANY, "Accept reverse VNC connection on TCP port:   ")
        self.acceptReverseVncConnectionsOnTcpPortLabel.SetFont(self.smallFont)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortLabel, flag=wx.ALIGN_CENTER_VERTICAL)

        self.acceptReverseVncConnectionsOnTcpPortSpinCtrl = wx.SpinCtrl(self.acceptReverseVncConnectionsOnTcpPortPanel, value='5500', size=(70,-1))
        self.acceptReverseVncConnectionsOnTcpPortSpinCtrl.SetFont(self.smallFont)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortSpinCtrl, flag=wx.TOP|wx.BOTTOM,border=2)
        self.acceptReverseVncConnectionsOnTcpPortPanelSizer.Add(wx.Panel(self.acceptReverseVncConnectionsOnTcpPortPanel, wx.ID_ANY), flag=wx.EXPAND)
        
        self.acceptReverseVncConnectionsOnTcpPortPanel.SetSizerAndFit(self.acceptReverseVncConnectionsOnTcpPortPanelSizer)
        spacingRightOfSpinCtrl = 175
        self.innerListeningModePanelSizer.Add(self.acceptReverseVncConnectionsOnTcpPortPanel, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfSpinCtrl)

        self.innerListeningModePanel.SetSizerAndFit(self.innerListeningModePanelSizer)
        self.listeningModeGroupBoxSizer.Add(self.innerListeningModePanel, flag=wx.EXPAND)
        self.listeningModePanel.SetSizerAndFit(self.listeningModeGroupBoxSizer)

        self.listeningModePanel.Disable()
        self.listeningModeGroupBox.Disable()
        self.acceptReverseVncConnectionsOnTcpPortPanel.Disable()
        self.acceptReverseVncConnectionsOnTcpPortLabel.Disable()
        self.acceptReverseVncConnectionsOnTcpPortSpinCtrl.Disable()
        
        # Logging group box

        self.loggingPanel = wx.Panel(self.globalsBottomPanel, wx.ID_ANY)
        self.globalsBottomPanelSizer.Add(self.loggingPanel, flag=wx.EXPAND)

        self.loggingGroupBox = wx.StaticBox(self.loggingPanel, wx.ID_ANY, label="Logging")
        self.loggingGroupBox.SetFont(self.smallFont)
        self.loggingGroupBoxSizer = wx.StaticBoxSizer(self.loggingGroupBox, wx.VERTICAL)
        self.loggingPanel.SetSizer(self.loggingGroupBoxSizer)

        self.innerLoggingPanel = wx.Panel(self.loggingPanel, wx.ID_ANY)
        self.innerLoggingPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5,hgap=5)
        self.innerLoggingPanel.SetSizer(self.innerLoggingPanelSizer)

        self.writeLogToAFileCheckBox = wx.CheckBox(self.innerLoggingPanel, wx.ID_ANY, "Write log to a file:")
        if 'writelog' in vncOptions:
            self.writeLogToAFileCheckBox.SetValue(vncOptions['writelog'])
        self.innerLoggingPanelSizer.Add(self.writeLogToAFileCheckBox, flag=wx.EXPAND)
        self.writeLogToAFileCheckBox.SetFont(self.smallFont)
        self.writeLogToAFileCheckBox.Bind(wx.EVT_CHECKBOX, self.onToggleWriteLogToAFileCheckBox)

        if sys.platform.startswith("darwin"):
            self.vncViewerLogFilenameTextField = wx.TextCtrl(self.innerLoggingPanel, wx.ID_ANY, "vncviewer.log", size=(400,-1))
        else:
            self.vncViewerLogFilenameTextField = wx.TextCtrl(self.innerLoggingPanel, wx.ID_ANY, "vncviewer.log", size=(300,-1))
        if 'logfile' in vncOptions:
            self.vncViewerLogFilenameTextField.SetValue(vncOptions['logfile'])
        self.vncViewerLogFilenameTextField.Disable()
        self.innerLoggingPanelSizer.Add(self.vncViewerLogFilenameTextField, flag=wx.EXPAND)
        self.vncViewerLogFilenameTextField.SetFont(self.smallFont)

        spacingRightOfBrowseButton = 10
        self.browseButton = wx.Button(self.innerLoggingPanel, wx.ID_ANY, "Browse...")
        self.browseButton.Disable()
        self.innerLoggingPanelSizer.Add(self.browseButton, flag=wx.EXPAND|wx.RIGHT, border=spacingRightOfBrowseButton)
        self.browseButton.SetFont(self.smallFont)
        self.browseButton.Bind(wx.EVT_BUTTON, self.onBrowse)

        self.verbosityLevelLabel = wx.StaticText(self.innerLoggingPanel, wx.ID_ANY, "Verbosity level:")
        self.verbosityLevelLabel.Disable()
        self.innerLoggingPanelSizer.Add(self.verbosityLevelLabel, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.verbosityLevelLabel.SetFont(self.smallFont)

        self.verbosityLevelSpinCtrl = wx.SpinCtrl(self.innerLoggingPanel, value='0')
        self.verbosityLevelSpinCtrl.Disable()
        self.verbosityLevelSpinCtrl.SetFont(self.smallFont)
        if 'loglevel' in vncOptions:
            self.verbosityLevelSpinCtrl.SetValue(int(vncOptions['loglevel']))
        self.innerLoggingPanelSizer.Add(self.verbosityLevelSpinCtrl)
        
        self.innerLoggingPanel.SetSizerAndFit(self.innerLoggingPanelSizer)
        self.loggingGroupBoxSizer.Add(self.innerLoggingPanel, flag=wx.EXPAND)
        self.loggingPanel.SetSizerAndFit(self.loggingGroupBoxSizer)

        if not sys.platform.startswith("win"):
            self.loggingPanel.Disable()
            self.loggingGroupBox.Disable()
            self.innerLoggingPanel.Disable()
            self.verbosityLevelLabel.Disable()
            self.verbosityLevelSpinCtrl.Disable()
            self.vncViewerLogFilenameTextField.Disable()
            self.browseButton.Disable()

        # Globals panels

        self.globalsTopPanel.SetSizerAndFit(self.globalsTopPanelSizer)
        self.globalsMiddlePanel.SetSizerAndFit(self.globalsMiddlePanelSizer)
        self.globalsBottomPanel.SetSizerAndFit(self.globalsBottomPanelSizer)
        self.globalsPanel.SetSizerAndFit(self.globalsPanelSizer)

        self.globalsPanel.Layout()

        # Privacy tab

        self.authPanel = wx.Panel(self.tabbedView,wx.ID_ANY)
        self.authPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.authPanel.Fit()
        choices=["Use my SSH Key Pair","Use my password"]
        if sys.platform.startswith("darwin"):
            self.authPanel.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        rb=wx.RadioBox(self.authPanel,wx.ID_ANY,majorDimension=1,name="auth_mode",label="Authentication Mode",choices=choices)
        self.authPanel.GetSizer().Add(rb,flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,border=15)
#        explanation = "The Launcher's preferred mode of operating (\"private mode\") involves creating a \"~/.ssh/MassiveLauncherKey\" private key file within your home directory, " + \
#                        "and using an SSH Agent (e.g. PuTTY's Pageant) to load the private key into memory, so that you don't need to enter your password " + \
#                        "every time you run the Launcher.\n\n" + \
#                        "If you are running the Launcher on a shared computer (e.g. if you are using a \"Guest\") account, then you should use \"public mode\". " + \
#                        "When running in \"public mode\", you will need to enter your password every time you run the Launcher.\n\n"
        explanation = """
When we communicate with the desktop we use a cryptographic token called an RSA Key Pair. You can either generate a permanent key pair, and store it on your computer, or use your password to generate a temporary keypair each time you use the launcher.

If you use a permanent SSH key pair, you will be asked to unlock your keys the first time you use the Launcher after a reboot. Thereafter you won't be asked for a password. This method is advisable if you are the only person who uses this account to log into your computer.

If you use a password to authenticate, a new keypair will be generated each time you use the launcher, and you will need to re-enter your password each time you connect. This method is advisable if multiple people share this computer (as in a computer lab).
"""


 #       explanation = "The Launcher's preferred mode of operating (\"private mode\") involves creating a \"~/.ssh/MassiveLauncherKey\" private key file within your home directory, and using an SSH Agent (e.g. PuTTY's Pageant) to load the private key into memory, so that you don't need to enter your password every time you run the Launcher.\nIf you are running the Launcher on a shared computer (e.g. if you are using a \"Guest\") account, then you should use \"public mode\". When running in \"public mode\", you will need to enter your password every time you run the Launcher."
                        #"Future versions of the Launcher may have the ability to manage multiple private key files from within a single " + \
                        #"\"Guest\" account, so it may then be possible to run the Launcher in \"private mode\" from within a \"Guest\" " + \
                        #"account."
        self.authModeExplanation = wx.StaticText(self.authPanel, wx.ID_ANY, explanation)
        self.authModeExplanation.SetFont(self.smallFont)
        # Here we hint that the size of the Static Text will not be included in calculating the size of the optionsDialog.
        # The Static text will expand and wrap anyway
        self.authModeExplanation.SetMinSize(wx.Size(1,1))
        self.authPanel.GetSizer().Add(self.authModeExplanation, proportion=1,flag=wx.EXPAND|wx.ALL, border=15)
        self.authPanel.Layout()
        var='auth_mode'
        if var in vncOptions:
            auth_mode = self.FindWindowByName(var)
            auth_mode.SetSelection(int(vncOptions[var]))
            # Fire the event manually, as this will control enabled/disabled of some menu items
            nextevent = wx.CommandEvent(wx.wxEVT_COMMAND_RADIOBOX_SELECTED, auth_mode.GetId())
            nextevent.SetEventObject(auth_mode)
            wx.PostEvent(auth_mode.GetEventHandler(),nextevent)

#        self.privacyPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
#        self.privacyPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=15, hgap=25)
#
#        self.privacyLeftBorderPanel = wx.Panel(self.privacyPanel, wx.ID_ANY)
#        self.privacyPanelSizer.Add(self.privacyLeftBorderPanel)
#
#        self.privacyMainPanel = wx.Panel(self.privacyPanel, wx.ID_ANY)
#        self.privacyPanelSizer.Add(self.privacyMainPanel, flag=wx.EXPAND|wx.TOP, border=15)
#        self.privacyMainPanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)
#
#        self.privacyRightBorderPanel = wx.Panel(self.privacyPanel, wx.ID_ANY)
#        self.privacyPanelSizer.Add(self.privacyRightBorderPanel)
#
#        # Private Public Mode group box
#
#        #choices=["Private mode (a passphrase-protected private key file will remain on this computer after the Launcher exits)","Public mode (to be used when running the Launcher from a shared \"Guest\" account)"]
#        #self.temporaryKeyRadioBox=wx.RadioBox(self.privacyMainPanel,wx.ID_ANY,majorDimension=1,name="auth_mode",label="Privacy Options",choices=choices)
#        self.privatePublicModePanel = wx.Panel(self.privacyMainPanel, wx.ID_ANY)
#        self.privacyMainPanelSizer.Add(self.privatePublicModePanel, flag=wx.EXPAND)
#
#        self.privatePublicModeGroupBox = wx.StaticBox(self.privatePublicModePanel, wx.ID_ANY, label="Privacy Options")
#        self.privatePublicModeGroupBox.SetFont(self.smallFont)
#        self.privatePublicModeGroupBoxSizer = wx.StaticBoxSizer(self.privatePublicModeGroupBox, wx.VERTICAL)
#        self.privatePublicModePanel.SetSizer(self.privatePublicModeGroupBoxSizer)
#
#        self.innerPrivatePublicModePanel = wx.Panel(self.privatePublicModePanel, wx.ID_ANY)
#        self.innerPrivatePublicModePanelSizer = wx.FlexGridSizer(rows=3, cols = 1, vgap=5,hgap=5)
#        self.innerPrivatePublicModePanel.SetSizer(self.innerPrivatePublicModePanelSizer)
#
#        self.privateModeRadioButton = wx.RadioButton(self.innerPrivatePublicModePanel, wx.ID_ANY, "Private mode (a passphrase-protected private key file will remain on this computer after the Launcher exits)")
#        self.privateModeRadioButton.SetValue(True)
#        if 'private_mode' in vncOptions:
#            self.privateModeRadioButton.SetValue(vncOptions['private_mode'])
#        self.innerPrivatePublicModePanelSizer.Add(self.privateModeRadioButton)
#        self.privateModeRadioButton.SetFont(self.smallFont)
#
#        self.publicModeRadioButton = wx.RadioButton(self.innerPrivatePublicModePanel, wx.ID_ANY, "Public mode (to be used when running the Launcher from a shared \"Guest\" account)")
#        self.publicModeRadioButton.SetValue(False)
#        if 'public_mode' in vncOptions:
#            self.publicModeRadioButton.SetValue(vncOptions['public_mode'])
#        self.innerPrivatePublicModePanelSizer.Add(self.publicModeRadioButton)
#        self.publicModeRadioButton.SetFont(self.smallFont)
#
#        explanation = "The Launcher's preferred mode of operating (\"private mode\") involves creating a \"~/.ssh/MassiveLauncherKey\" private key file within your home directory, " + \
#                        "and using an SSH Agent (e.g. PuTTY's Pageant) to load the private key into memory, so that you don't need to enter your password " + \
#                        "every time you run the Launcher.\n\n" + \
#                        "If you are running the Launcher on a shared computer (e.g. if you are using a \"Guest\") account, then you should use \"public mode\". " + \
#                        "When running in \"public mode\", you will need to enter your password every time you run the Launcher.\n\n"
#                        #"Future versions of the Launcher may have the ability to manage multiple private key files from within a single " + \
#                        #"\"Guest\" account, so it may then be possible to run the Launcher in \"private mode\" from within a \"Guest\" " + \
#                        #"account."
#        self.privatePublicModeExplanationLabel = wx.StaticText(self.innerPrivatePublicModePanel, wx.ID_ANY, explanation)
#        width = self.privateModeRadioButton.GetSize().width
#        self.privatePublicModeExplanationLabel.Wrap(width)
#        self.innerPrivatePublicModePanelSizer.Add(self.privatePublicModeExplanationLabel, flag=wx.TOP, border=15)
#        self.privatePublicModeExplanationLabel.SetFont(self.smallFont)
#       
#        self.innerPrivatePublicModePanel.SetSizerAndFit(self.innerPrivatePublicModePanelSizer)
#        self.privatePublicModeGroupBoxSizer.Add(self.innerPrivatePublicModePanel, flag=wx.EXPAND)
#        self.privatePublicModePanel.SetSizerAndFit(self.privatePublicModeGroupBoxSizer)
#
#        self.privacyMainPanel.SetSizerAndFit(self.privacyMainPanelSizer)
#        self.privacyPanel.SetSizerAndFit(self.privacyPanelSizer)
#        self.privacyPanel.Layout()

        # Sharing tab

        self.fileSharingPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.fileSharingPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=15, hgap=25)

        self.fileSharingLeftBorderPanel = wx.Panel(self.fileSharingPanel, wx.ID_ANY)
        self.fileSharingPanelSizer.Add(self.fileSharingLeftBorderPanel)

        self.fileSharingMainPanel = wx.Panel(self.fileSharingPanel, wx.ID_ANY)
        self.fileSharingPanelSizer.Add(self.fileSharingMainPanel, flag=wx.EXPAND|wx.TOP, border=15)
        self.fileSharingMainPanelSizer = wx.FlexGridSizer(rows=1, cols=1, vgap=5, hgap=5)

        self.fileSharingRightBorderPanel = wx.Panel(self.fileSharingPanel, wx.ID_ANY)
        self.fileSharingPanelSizer.Add(self.fileSharingRightBorderPanel)

        # Share Local Home Folder group box

        self.shareLocalHomeFolderPanel = wx.Panel(self.fileSharingMainPanel, wx.ID_ANY)
        self.fileSharingMainPanelSizer.Add(self.shareLocalHomeFolderPanel, flag=wx.EXPAND)

        self.makeLocalFolderAvailableOnRemoteDesktopGroupBox = wx.StaticBox(self.shareLocalHomeFolderPanel, wx.ID_ANY, label="Make local folder available on remote desktop")
        self.makeLocalFolderAvailableOnRemoteDesktopGroupBox.SetFont(self.smallFont)
        self.makeLocalFolderAvailableOnRemoteDesktopGroupBoxSizer = wx.StaticBoxSizer(self.makeLocalFolderAvailableOnRemoteDesktopGroupBox, wx.VERTICAL)
        self.shareLocalHomeFolderPanel.SetSizer(self.makeLocalFolderAvailableOnRemoteDesktopGroupBoxSizer)

        self.innerShareLocalHomeFolderPanel = wx.Panel(self.shareLocalHomeFolderPanel, wx.ID_ANY)
        self.innerShareLocalHomeFolderPanelSizer = wx.FlexGridSizer(rows=2, cols = 1, vgap=5,hgap=5)
        self.innerShareLocalHomeFolderPanel.SetSizer(self.innerShareLocalHomeFolderPanelSizer)

        self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox = wx.CheckBox(self.innerShareLocalHomeFolderPanel, wx.ID_ANY, "Share local home directory on remote desktop")
        self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox.SetValue(False)
        if 'share_local_home_directory_on_remote_desktop' in vncOptions:
            self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox.SetValue(vncOptions['share_local_home_directory_on_remote_desktop'])

        self.innerShareLocalHomeFolderPanelSizer.Add(self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox)
        self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox.SetFont(self.smallFont)
       
        self.innerShareLocalHomeFolderPanel.SetSizerAndFit(self.innerShareLocalHomeFolderPanelSizer)
        self.makeLocalFolderAvailableOnRemoteDesktopGroupBoxSizer.Add(self.innerShareLocalHomeFolderPanel, flag=wx.EXPAND)
        self.shareLocalHomeFolderPanel.SetSizerAndFit(self.makeLocalFolderAvailableOnRemoteDesktopGroupBoxSizer)

        self.fileSharingMainPanel.SetSizerAndFit(self.fileSharingMainPanelSizer)
        self.fileSharingPanel.SetSizerAndFit(self.fileSharingPanelSizer)
        self.fileSharingPanel.Layout()


        # Adding Connection tab and Globals tab to tabbed view
        self.tabbedView.AddPage(self.connectionPanel, "Connection")
        self.tabbedView.AddPage(self.globalsPanel, "Globals")
        self.tabbedView.AddPage(self.authPanel, "Authentication")
        self.tabbedView.AddPage(self.fileSharingPanel, "Sharing")

        self.tabbedView.SetSelection(self.tabIndex)
       
        # Buttons panel

        self.buttonsPanel = wx.Panel(self.notebookContainerPanel, wx.ID_ANY)
        notebookContainerPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, border=10)

        cancelButton = wx.Button(self.buttonsPanel, wx.ID_ANY, "Cancel")
        okButton = wx.Button(self.buttonsPanel, wx.ID_ANY, "OK")
        
        buttonsPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5, hgap=5)
        buttonsPanelSizer.Add(wx.StaticText(self.buttonsPanel, wx.ID_ANY, "     "))
        buttonsPanelSizer.Add(cancelButton)
        buttonsPanelSizer.Add(okButton)
        buttonsPanelSizer.Add(wx.StaticText(self.buttonsPanel, wx.ID_ANY, "     "))
        self.buttonsPanel.SetAutoLayout(True)
        self.buttonsPanel.SetSizerAndFit(buttonsPanelSizer) 

        okButton.Bind(wx.EVT_BUTTON, self.onOK)
        cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)
     
        self.notebookContainerPanel.SetSizerAndFit(notebookContainerPanelSizer)

        self.Fit()
        #width=self.tabbedView.GetSize().width
        #print "rewrapping to width %s"%width
        #self.authModeExplanation.Wrap(width)
        self.Fit()
        self.Layout()

    def getVncOptions(self):
        return self.vncOptions

    def setVncOptions(self):
        return

    def onCancel(self, event):
        self.okClicked = False
        #self.Close(True)
        self.Show(False)
        self.EndModal(wx.CANCEL)

    def onOK(self, event):
        self.okClicked = True
        self.vncOptions['jpeg_compression'] = self.jpegCompressionCheckBox.GetValue()
        self.vncOptions['jpeg_chrominance_subsampling'] = self.jpegChrominanceSubsamplingCommandLineString[self.jpegChrominanceSubsamplingSlider.GetValue()]
        self.vncOptions['jpeg_image_quality'] = str(self.jpegImageQualitySlider.GetValue())
        self.vncOptions['zlib_compression_enabled'] = self.zlibCompressionLevelSlider.IsEnabled()
        self.vncOptions['zlib_compression_level'] = self.zlibCompressionLevelCommandLineString[self.zlibCompressionLevelSlider.GetValue()]
        self.vncOptions['view_only'] = self.viewOnlyCheckBox.GetValue()
        self.vncOptions['disable_clipboard_transfer'] = self.disableClipboardTransferCheckBox.GetValue()
        if sys.platform.startswith("win"):
            self.vncOptions['scale'] = self.scaleByComboBox.GetStringSelection()
            self.vncOptions['span'] = self.spanModeCommandLineString[self.spanModeComboBox.GetSelection()]
        self.vncOptions['double_buffering'] = self.doubleBufferingCheckBox.GetValue()
        self.vncOptions['full_screen_mode'] = self.fullScreenModeCheckBox.GetValue()
        self.vncOptions['deiconify_on_remote_bell_event'] = self.deiconifyOnRemoteBellEventCheckBox.GetValue()
        if sys.platform.startswith("win"):
            self.vncOptions['emulate3'] = self.emulate3ButtonsWith2ButtonClickCheckBox.GetValue()
            self.vncOptions['swapmouse'] = self.swapMouseButtons2And3CheckBox.GetValue()
        self.vncOptions['track_remote_cursor_locally'] = self.trackRemoteCursorLocallyRadioButton.GetValue()
        self.vncOptions['let_remote_server_deal_with_mouse_cursor'] = self.letRemoteServerDealWithMouseCursorRadioButton.GetValue()
        self.vncOptions['dont_show_remote_cursor'] = self.dontShowRemoteCursorRadioButton.GetValue()
        self.vncOptions['request_shared_session'] = self.requestSharedSessionCheckBox.GetValue()
        if sys.platform.startswith("win"):
            self.vncOptions['toolbar'] = self.showToolbarsByDefaultCheckBox.GetValue()
            self.vncOptions['dotcursor'] = self.dotCursorRadioButton.GetValue()
            self.vncOptions['smalldotcursor'] = self.smallDotCursorRadioButton.GetValue()
            self.vncOptions['normalcursor'] = self.normalArrowRadioButton.GetValue()
            self.vncOptions['nocursor'] = self.noLocalCursorRadioButton.GetValue()
            self.vncOptions['writelog'] = self.writeLogToAFileCheckBox.GetValue()
            self.vncOptions['loglevel'] = str(self.verbosityLevelSpinCtrl.GetValue())
            self.vncOptions['logfile'] = self.vncViewerLogFilenameTextField.GetValue()
        self.vncOptions['share_local_home_directory_on_remote_desktop'] = self.shareLocalHomeDirectoryOnRemoteDesktopCheckBox.GetValue()
        self.vncOptions['auth_mode']=self.FindWindowByName('auth_mode').GetSelection()
        self.Show(False)
        self.EndModal(wx.OK)
      
    def enableZlibCompressionLevelWidgets(self):
        self.zlibCompressionLevelLabel.Enable()
        self.fastZlibCompressionLabel.Enable()
        self.zlibCompressionLevelSlider.Enable()
        self.bestZlibCompressionLabel.Enable()
        self.zlibCompressionLevelPanel.Enable()
        self.zlibCompressionPanelEnabled = True

    def disableZlibCompressionLevelWidgets(self):
        self.zlibCompressionLevelLabel.Disable()
        self.fastZlibCompressionLabel.Disable()
        self.zlibCompressionLevelSlider.Disable()
        self.bestZlibCompressionLabel.Disable()
        self.zlibCompressionLevelPanel.Disable()
        self.zlibCompressionPanelEnabled = False
 
    def onSelectEncodingMethodFromComboBox(self, event):
        encodingMethodPresetString = self.encodingMethodsComboBox.GetStringSelection()
        self.jpegCompressionCheckBox.SetValue(self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_compression'])
        self.jpegChrominanceSubsamplingSlider.SetValue(self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_chrominance_subsampling'])
        self.jpegChrominanceSubsamplingLabel.SetLabel("JPEG chrominance subsampling:    " + self.jpegChrominanceSubsamplingLevel[self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_chrominance_subsampling']])
        self.jpegImageQualitySlider.SetValue(self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_image_quality'])
        self.jpegImageQualityLabel.SetLabel("JPEG image quality:    " + str(self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_image_quality']))
        if self.encodingMethodsPresets[encodingMethodPresetString]['enableZlibCompressionLevelWidgets'] == True:
            self.enableZlibCompressionLevelWidgets()
        else:
            self.disableZlibCompressionLevelWidgets()
        self.zlibCompressionLevelSlider.SetValue(self.encodingMethodsPresets[encodingMethodPresetString]['zlib_compression_level'])
        self.zlibCompressionLevelLabel.SetLabel("Zlib compression level:     " + self.zlibCompressionLevel[self.encodingMethodsPresets[encodingMethodPresetString]['zlib_compression_level']])

    def onToggleWriteLogToAFileCheckBox(self, event):
        self.vncViewerLogFilenameTextField.Enable(self.writeLogToAFileCheckBox.GetValue())
        self.browseButton.Enable(self.writeLogToAFileCheckBox.GetValue())
        self.verbosityLevelLabel.Enable(self.writeLogToAFileCheckBox.GetValue())
        self.verbosityLevelSpinCtrl.Enable(self.writeLogToAFileCheckBox.GetValue())

    def onAdjustEncodingMethodSliders(self, event):

        jpegCompressionCheckBoxValue = self.jpegCompressionCheckBox.GetValue()
        jpegChrominanceSubsamplingSliderValue = self.jpegChrominanceSubsamplingSlider.GetValue()
        jpegImageQualitySliderValue = self.jpegImageQualitySlider.GetValue()
        zlibCompressionLevelSliderValue = self.zlibCompressionLevelSlider.GetValue()

        self.jpegChrominanceSubsamplingLabel.SetLabel("JPEG chrominance subsampling:    " + self.jpegChrominanceSubsamplingLevel[jpegChrominanceSubsamplingSliderValue])
        self.jpegImageQualityLabel.SetLabel("JPEG image quality:    " + str(jpegImageQualitySliderValue))
        self.zlibCompressionLevelLabel.SetLabel("Zlib compression level:     " + self.zlibCompressionLevel[zlibCompressionLevelSliderValue])

        # We need to check whether the values of the sliders match
        # the current preset value in the encoding methods combo box.  
        # If so, select it, if not, add Custom if necessary and select it.
        # If the values don't match the currently selected preset, but they
        # do match another preset, we should update the combo-box selection.

        self.encodingMethodsComboBox.SetStringSelection("Tight + Perceptually Lossless JPEG (LAN)")
        for encodingMethod in self.encodingMethods:
            if (jpegCompressionCheckBoxValue==self.encodingMethodsPresets[encodingMethod]['jpeg_compression'] and \
                    jpegChrominanceSubsamplingSliderValue==self.encodingMethodsPresets[encodingMethod]['jpeg_chrominance_subsampling'] and \
                    jpegImageQualitySliderValue==self.encodingMethodsPresets[encodingMethod]['jpeg_image_quality'] and \
                    zlibCompressionLevelSliderValue==self.encodingMethodsPresets[encodingMethod]['zlib_compression_level']):
                self.encodingMethodsComboBox.SetStringSelection(encodingMethod)
                if "Lossless" in encodingMethod and "Perceptually" not in encodingMethod:  
                    self.enableZlibCompressionLevelWidgets()
                else:
                    self.disableZlibCompressionLevelWidgets()

        encodingMethodPresetString = self.encodingMethodsComboBox.GetStringSelection()

        if jpegChrominanceSubsamplingSliderValue!=self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_chrominance_subsampling'] or \
                jpegImageQualitySliderValue!=self.encodingMethodsPresets[encodingMethodPresetString]['jpeg_image_quality'] or \
                (self.encodingMethodsPresets[encodingMethodPresetString]['enableZlibCompressionLevelWidgets'] == True and zlibCompressionLevelSliderValue!=self.encodingMethodsPresets[encodingMethodPresetString]['zlib_compression_level']):
            if "Custom" not in self.encodingMethodsComboBox.GetItems():
                self.encodingMethodsComboBox.Append("Custom")
            self.encodingMethodsComboBox.SetStringSelection("Custom")
            self.enableZlibCompressionLevelWidgets()
        else:
            CUSTOM_INDEX = 4
            if "Custom" in self.encodingMethodsComboBox.GetItems():
                self.encodingMethodsComboBox.Delete(CUSTOM_INDEX)

    def onBrowse(self, event):
        filters = 'TurboVNC log files (*.log)|*.log'
        saveFileDialog = wx.FileDialog ( None, message = 'TurboVNC log file...', wildcard = filters, style = wx.SAVE)
        if saveFileDialog.ShowModal() == wx.ID_OK:
            global turboVncLogFilePath
            turboVncLogFilePath = saveFileDialog.GetPath()
            self.vncViewerLogFilenameTextField.WriteText(turboVncLogFilePath)

class turboVncOptions(wx.App):
    def OnInit(self):
        frame = wx.Frame(None, wx.ID_ANY)
        frame.Show(True)
        vncOptions = {}
        #dialog = LauncherOptionsDialog(frame, wx.ID_ANY, "TurboVNC Viewer Options", vncOptions)
        dialog = LauncherOptionsDialog(frame, wx.ID_ANY, "Preferences", vncOptions)
        dialog.ShowModal()
        return True

