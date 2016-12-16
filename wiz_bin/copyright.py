# -*- coding: utf-8 -*-

## \package wiz_bin.copyright

# MIT licensing
# See: docs/LICENSE.txt


import os, wx

from dbr.dialogs            import ConfirmationDialog
from dbr.error              import ShowError
from dbr.functions          import GetLongestLine
from dbr.functions          import GetSystemLicensesList
from dbr.functions          import GetYear
from dbr.functions          import RemovePreWhitespace
from dbr.functions          import TextIsEmpty
from dbr.language           import GT
from dbr.log                import Logger
from dbr.templates          import GetLicenseTemplateFile
from dbr.templates          import GetLicenseTemplatesList
from dbr.templates          import application_licenses_path
from dbr.templates          import local_licenses_path
from dbr.textinput          import MonospaceTextArea
from globals                import ident
from globals.constants      import system_licenses_path
from globals.tooltips       import SetPageToolTips
from globals.wizardhelper   import GetTopWindow


# Globals
copyright_header = GT(u'Copyright © {} <copyright holder(s)> [<email>]')


## Copyright page
class Panel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, ident.COPYRIGHT, name=GT(u'Copyright'))
        
        self.SetScrollbars(0, 20, 0, 0)
        
        # FIXME: Update license templates list when template is generated
        # FIXME: Ignore symbolic links
        opts_licenses = GetSystemLicensesList()
        
        # FIXME: Change variable name to 'self.builtin_licenses
        self.opts_local_licenses = GetLicenseTemplatesList()
        
        # Do not use local licenses if already located on system
        for lic in opts_licenses:
            if lic in self.opts_local_licenses:
                self.opts_local_licenses.remove(lic)
        
        # Add the remaining licenses to the selection list
        for lic in self.opts_local_licenses:
            opts_licenses.append(lic)
        
        opts_licenses.sort(key=unicode.lower)
        
        ## A list of available license templates
        self.sel_templates = wx.Choice(self, choices=opts_licenses, name=u'list»')
        self.sel_templates.default = 0
        self.sel_templates.SetSelection(self.sel_templates.default)
        
        btn_template = wx.Button(self, label=GT(u'Generate Template'), name=u'full»')
        self.btn_template_simple = wx.Button(self, label=GT(u'Generate Simple Template'), name=u'simple»')
        
        if not self.sel_templates.GetCount():
            self.sel_templates.Enable(False)
            btn_template.Enable(False)
            self.btn_template_simple.Enable(False)
        
        ## Area where license text is displayed
        self.dsp_copyright = MonospaceTextArea(self, name=u'license')
        self.dsp_copyright.EnableDropTarget()
        
        SetPageToolTips(self)
        
        if self.sel_templates.IsEnabled():
            self.OnSelectTemplate(self.sel_templates)
        
        # *** Layout *** #
        
        lyt_buttons = wx.BoxSizer(wx.HORIZONTAL)
        lyt_buttons.Add(btn_template, 1)
        lyt_buttons.Add(self.btn_template_simple, 1)
        
        lyt_label = wx.BoxSizer(wx.HORIZONTAL)
        lyt_label.Add(
            wx.StaticText(self, label=GT(u'Available Templates')),
            0,
            wx.TOP|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER,
            5
        )
        lyt_label.Add(self.sel_templates, 0, wx.TOP, 5)
        lyt_label.Add(lyt_buttons, 1, wx.LEFT, 150)
        
        lyt_main = wx.BoxSizer(wx.VERTICAL)
        lyt_main.AddSpacer(10)
        lyt_main.Add(lyt_label, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        lyt_main.Add(self.dsp_copyright, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        
        self.SetAutoLayout(True)
        self.SetSizer(lyt_main)
        self.Layout()
        
        # *** Event handlers *** #
        
        self.sel_templates.Bind(wx.EVT_CHOICE, self.OnSelectTemplate)
        
        btn_template.Bind(wx.EVT_BUTTON, self.CopyFullTemplate)
        self.btn_template_simple.Bind(wx.EVT_BUTTON, self.GenerateSimpleTemplate)
    
    
    ## TODO: Doxygen
    def CopyFullTemplate(self, event=None):
        selected_template = self.sel_templates.GetStringSelection()
        template_file = self.GetLicensePath(selected_template)
        
        if self.DestroyLicenseText():
            main_window = GetTopWindow()
            
            if not os.path.isfile(template_file):
                ShowError(main_window, u'{}: {}'.format(GT(u'Could not locate license file'), template_file))
                return
            
            Logger.Debug(__name__, u'Copying license {}'.format(template_file))
            
            FILE_BUFFER = open(template_file, u'r')
            license_text = RemovePreWhitespace(FILE_BUFFER.read())
            FILE_BUFFER.close()
            
            # Number defines how many empty lines to add after the copyright header
            # Boolean/Integer defines whether copyright header should be centered/offset
            add_header = {
                u'Artistic': (1, True),
                u'BSD': (0, False),
            }
            
            template_name = os.path.basename(template_file)
            if template_name in add_header:
                license_text = license_text.split(u'\n')
                
                empty_lines = add_header[template_name][0]
                for L in range(empty_lines):
                    license_text.insert(0, wx.EmptyString)
                
                header = copyright_header.format(GetYear())
                
                center_header = add_header[template_name][1]
                if center_header:
                    Logger.Debug(__name__, u'Centering header...')
                    
                    offset = 0
                    
                    # Don't use isinstance() here because boolean is an instance of integer
                    if type(center_header) == int:
                        offset = center_header
                    
                    else:
                        longest_line = GetLongestLine(license_text)
                        
                        Logger.Debug(__name__, u'Longest line: {}'.format(longest_line))
                        
                        header_length = len(header)
                        if header_length < longest_line:
                            offset = (longest_line - header_length) / 2
                    
                    if offset:
                        Logger.Debug(__name__, u'Offset: {}'.format(offset))
                        
                        header = u'{}{}'.format(u' ' * offset, header)
                
                # Special changes for BSD license
                if template_name == u'BSD':
                    line_index = 0
                    for LI in license_text:
                        if u'copyright (c)' in LI.lower():
                            license_text[line_index] = header
                            
                            break
                        
                        line_index += 1
                
                else:
                    license_text.insert(0, header)
                
                license_text = u'\n'.join(license_text)
            
            self.dsp_copyright.Clear()
            self.dsp_copyright.SetValue(license_text)
            
            self.dsp_copyright.SetInsertionPoint(0)
        
        self.dsp_copyright.SetFocus()
    
    
    ## TODO: Doxygen
    def DestroyLicenseText(self):
        if not TextIsEmpty(self.dsp_copyright.GetValue()):
            warn_msg = GT(u'This will destroy all license text. Do you want to continue?')
            warn_msg = u'{}\n\n{}'.format(warn_msg, GT(u'Continue?'))
            
            if ConfirmationDialog(GetTopWindow(), text=warn_msg).ShowModal() not in (wx.ID_OK, wx.OK):
                return False
        
        return True
    
    
    ## TODO: Doxygen
    def ExportPage(self):
        return self.GetCopyright()
    
    
    ## TODO: Doxygen
    def GatherData(self):
        data = self.GetCopyright()
        return u'<<COPYRIGHT>>\n{}\n<</COPYRIGHT>>'.format(data)
    
    
    ## TODO: Doxygen
    def GenerateSimpleTemplate(self, event=None):
        if self.DestroyLicenseText():
            self.dsp_copyright.Clear()
            
            license_path = u'{}/{}'.format(system_licenses_path, self.sel_templates.GetString(self.sel_templates.GetSelection()))
            
            self.dsp_copyright.WriteText(copyright_header.format(GetYear()))
            self.dsp_copyright.WriteText(license_path)
            
            self.dsp_copyright.SetInsertionPoint(0)
        
        self.dsp_copyright.SetFocus()
    
    
    ## TODO: Doxygen
    #  
    #  FIXME: Deprecated/Unused
    def GenerateTemplate(self, l_name):
        Logger.Debug(__name__, u'Generating template')
        
        if self.DestroyLicenseText():
            self.dsp_copyright.Clear()
            
            l_path = GetLicenseTemplateFile(l_name)
            
            if l_path:
                l_data = open(l_path)
                l_lines = l_data.read().split(u'\n')
                l_data.close()
                
                year_delims = (
                    u'<year>',
                    u'<years>',
                    u'<year(s)>',
                    u'<date>',
                    u'<dates>',
                    u'<date(s)>',
                )
                
                substitutions = {
                    u'Copyright (C)': u'Copyright (REMOVEME) ©',
                    year_delims: str(GetYear()),
                }
                
                l_index = 0
                for LI in l_lines:
                    for RPLC in substitutions:
                        if isinstance(RPLC, (tuple, list)):
                            for S in RPLC:
                                if S in LI:
                                    new_str = substitutions[RPLC]
                                    
                                    Logger.Debug(__name__,
                                            u'License template string substitution from list: {} ➜ {}'.format(S, new_str))
                                    
                                    l_lines[l_index] = LI.replace(S, new_str)
                        
                        else:
                            if RPLC in LI:
                                new_str = substitutions[RPLC]
                                
                                Logger.Debug(__name__,
                                        u'License template string substitution from string: {} ➜ {}'.format(RPLC, new_str))
                                
                                l_lines[l_index] = LI.replace(RPLC, new_str)
                        
                        l_index += 1
                '''
                for DEL in year_delims:
                    l_index = 0
                    for LI in l_lines:
                        if DEL in LI:
                            l_lines[l_index] = str(GetYear()).join(LI.split(DEL))
                        
                        l_index += 1
                '''
                
                self.dsp_copyright.SetValue(u'\n'.join(l_lines))
                
                self.dsp_copyright.SetInsertionPoint(0)
        
        self.dsp_copyright.SetFocus()
    
    
    ## TODO: Doxygen
    def GetCopyright(self):
        return self.dsp_copyright.GetValue()
    
    
    ## TODO: Doxygen
    def GetLicensePath(self, template_name):
        # User templates have priority
        license_path = u'{}/{}'.format(local_licenses_path, template_name)
        if os.path.isfile(license_path):
            return license_path
        
        license_path = u'{}/{}'.format(system_licenses_path, template_name)
        if os.path.isfile(license_path):
            return license_path
        
        license_path = u'{}/{}'.format(application_licenses_path, template_name)
        if os.path.isfile(license_path):
            return license_path
        
        return None
    
    
    ## Tells the app whether this page should be added to build
    def IsBuildExportable(self):
        return not TextIsEmpty(self.dsp_copyright.GetValue())
    
    
    ## Enables/Disables simple template button
    #  
    #  Simple template generation is only available
    #  for system  licenses.
    def OnSelectTemplate(self, event=None):
        if isinstance(event, wx.Choice):
            choice = event
        
        else:
            choice = event.GetEventObject()
        
        template = choice.GetString(choice.GetSelection())
        
        if template in self.opts_local_licenses:
            self.btn_template_simple.Disable()
        
        else:
            self.btn_template_simple.Enable()
        
        self.SetTemplateToolTip()
    
    
    ## Resets all page fields to default values
    def ResetAllFields(self):
        self.dsp_copyright.Clear()
        
        if self.sel_templates.IsEnabled():
            self.sel_templates.SetSelection(self.sel_templates.default)
            self.OnSelectTemplate(self.sel_templates)
    
    
    ## Sets the text of the displayed copyright
    def SetCopyright(self, data):
        self.dsp_copyright.SetValue(data)
    
    
    ## TODO: Doxygen
    def SetTemplateToolTip(self):
        license_name = self.sel_templates.GetString(self.sel_templates.GetSelection())
        license_path = self.GetLicensePath(license_name)
        
        if license_path:
            self.sel_templates.SetToolTip(wx.ToolTip(license_path))
            return
        
        self.sel_templates.SetToolTip(None)
