# -*- coding: utf-8 -*-

## \package wiz_bin.control

# MIT licensing
# See: docs/LICENSE.txt


import os, wx
from wx.combo import OwnerDrawnComboBox

from dbr.buttons            import ButtonBrowse64
from dbr.buttons            import ButtonPreview64
from dbr.buttons            import ButtonSave64
from dbr.charctrl           import CharCtrl
from dbr.custom             import OpenFile
from dbr.custom             import SaveFile
from dbr.functions          import FieldEnabled
from dbr.functions          import TextIsEmpty
from dbr.language           import GT
from dbr.log                import Logger
from dbr.panel              import BorderedPanel
from dbr.textinput          import MultilineTextCtrlPanel
from globals.ident          import FID_ARCH
from globals.ident          import FID_EMAIL
from globals.ident          import FID_LIST
from globals.ident          import FID_MAINTAINER
from globals.ident          import FID_PACKAGE
from globals.ident          import FID_VERSION
from globals.ident          import ID_CONTROL
from globals.ident          import ID_DEPENDS
from globals.tooltips       import SetPageToolTips
from globals.wizardhelper   import GetField


## This panel displays the field input of the control file
class Panel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, ID_CONTROL, name=GT(u'Control'))
        
        self.SetScrollbars(0, 20, 0, 0)
        
        pnl_bg = wx.Panel(self)
        
        # Buttons to open, save, & preview control file
        btn_open = ButtonBrowse64(pnl_bg)
        btn_save = ButtonSave64(pnl_bg)
        btn_preview = ButtonPreview64(pnl_bg)
        
        # *** Required fields *** #
        
        pnl_require = BorderedPanel(pnl_bg)
        
        txt_package = wx.StaticText(pnl_require, label=GT(u'Package'), name=u'package')
        txt_package.req = True
        ti_package = CharCtrl(pnl_require, FID_PACKAGE, name=txt_package.Name)
        ti_package.req = True
        
        txt_version = wx.StaticText(pnl_require, label=GT(u'Version'), name=u'version')
        txt_version.req = True
        ti_version = CharCtrl(pnl_require, FID_VERSION, name=txt_version.Name)
        ti_version.req = True
        
        txt_maintainer = wx.StaticText(pnl_require, label=GT(u'Maintainer'), name=u'maintainer')
        txt_maintainer.req = True
        ti_maintainer = wx.TextCtrl(pnl_require, FID_MAINTAINER, name=txt_maintainer.Name)
        ti_maintainer.req = True
        
        txt_email = wx.StaticText(pnl_require, label=GT(u'Email'), name=u'email')
        txt_email.req = True
        ti_email = wx.TextCtrl(pnl_require, FID_EMAIL, name=txt_email.Name)
        ti_email.req = True
        
        opts_arch = (
            u'all', u'alpha', u'amd64', u'arm', u'arm64', u'armeb', u'armel',
            u'armhf', u'avr32', u'hppa', u'i386', u'ia64', u'lpia', u'm32r',
            u'm68k', u'mips', u'mipsel', u'powerpc', u'powerpcspe', u'ppc64',
            u's390', u's390x', u'sh3', u'sh3eb', u'sh4', u'sh4eb', u'sparc',
            u'sparc64',
            )
        
        txt_arch = wx.StaticText(pnl_require, label=GT(u'Architecture'), name=u'architecture')
        sel_arch = wx.Choice(pnl_require, FID_ARCH, choices=opts_arch, name=txt_arch.Name)
        sel_arch.default = 0
        sel_arch.SetSelection(sel_arch.default)
        
        # *** Recommended fields *** #
        
        pnl_recommend = BorderedPanel(pnl_bg)
        
        ti_section_opt = (
            u'admin', u'cli-mono', u'comm', u'database', u'devel', u'debug',
            u'doc', u'editors', u'electronics', u'embedded', u'fonts', u'games',
            u'gnome', u'graphics', u'gnu-r', u'gnustep', u'hamradio', u'haskell',
            u'httpd', u'interpreters', u'java', u'kde', u'kernel', u'libs',
            u'libdevel', u'lisp', u'localization', u'mail', u'math',
            u'metapackages', u'misc', u'net', u'news', u'ocaml', u'oldlibs',
            u'otherosfs', u'perl', u'php', u'python', u'ruby', u'science',
            u'shells', u'sound', u'tex', u'text', u'utils', u'vcs', u'video',
            u'web', u'x11', u'xfce', u'zope',
            )
        
        txt_section = wx.StaticText(pnl_recommend, label=GT(u'Section'), name=u'section')
        ti_section = OwnerDrawnComboBox(pnl_recommend, choices=ti_section_opt, name=txt_section.Name)
        
        opts_priority = (
            u'optional', u'standard', u'important', u'required', u'extra',
            )
        
        txt_priority = wx.StaticText(pnl_recommend, label=GT(u'Priority'), name=u'priority')
        sel_priority = wx.Choice(pnl_recommend, choices=opts_priority, name=txt_priority.Name)
        sel_priority.default = 0
        sel_priority.SetSelection(sel_priority.default)
        
        txt_synopsis = wx.StaticText(pnl_recommend, label=GT(u'Short Description'), name=u'synopsis')
        ti_synopsis = wx.TextCtrl(pnl_recommend, name=txt_synopsis.Name)
        
        txt_description = wx.StaticText(pnl_recommend, label=GT(u'Long Description'), name=u'description')
        self.ti_description = MultilineTextCtrlPanel(pnl_recommend, name=txt_description.Name)
        
        # *** Optional fields *** #
        
        pnl_option = BorderedPanel(pnl_bg)
        
        txt_source = wx.StaticText(pnl_option, label=GT(u'Source'), name=u'source')
        ti_source = wx.TextCtrl(pnl_option, name=txt_source.Name)
        
        txt_homepage = wx.StaticText(pnl_option, label=GT(u'Homepage'), name=u'homepage')
        ti_homepage = wx.TextCtrl(pnl_option, name=txt_homepage.Name)
        
        opts_essential = (
            u'yes', u'no',
            )
        
        txt_essential = wx.StaticText(pnl_option, label=GT(u'Essential'), name=u'essential')
        sel_essential = wx.Choice(pnl_option, choices=opts_essential, name=txt_essential.Name)
        sel_essential.default = 1
        sel_essential.SetSelection(sel_essential.default)
        
        # List all widgets to check if fields have changed after keypress
        # This is for determining if the project is saved
        self.grp_keypress = {
            ti_package: wx.EmptyString,
            ti_version: wx.EmptyString,
            }
        
        self.grp_input = (
            ti_package,
            ti_version,
            ti_maintainer,  # Maintainer must be listed before email
            ti_email,
            ti_section,
            ti_source,
            ti_homepage,
            ti_synopsis,
            self.ti_description,
            )
        
        self.grp_select = (
            sel_arch,
            sel_priority,
            sel_essential,
            )
        
        SetPageToolTips(self)
        
        # *** Layout *** #
        
        TEXT_FLAG = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT
        
        # Buttons
        layt_buttons = wx.BoxSizer(wx.HORIZONTAL)
        layt_buttons.Add(btn_open, 0)
        layt_buttons.Add(btn_save, 0)
        layt_buttons.Add(btn_preview, 0)
        
        # Required fields
        layt_require = wx.FlexGridSizer(0, 4, 5, 5)
        layt_require.AddGrowableCol(1)
        layt_require.AddGrowableCol(3)
        
        layt_require.AddMany((
            (txt_package, 0, TEXT_FLAG|wx.LEFT|wx.TOP, 5),
            (ti_package, 0, wx.EXPAND|wx.TOP, 5),
            (txt_version, 0, TEXT_FLAG|wx.TOP, 5),
            (ti_version, 0, wx.EXPAND|wx.TOP|wx.RIGHT, 5),
            (txt_maintainer, 0, TEXT_FLAG|wx.LEFT, 5),
            (ti_maintainer, 0, wx.EXPAND),
            (txt_email, 0, TEXT_FLAG),
            (ti_email, 0, wx.EXPAND|wx.RIGHT, 5),
            (txt_arch, 0, TEXT_FLAG|wx.LEFT|wx.BOTTOM, 5),
            (sel_arch, 0, wx.BOTTOM, 5),
            ))
        
        pnl_require.SetSizer(layt_require)
        pnl_require.SetAutoLayout(True)
        pnl_require.Layout()
        
        # Recommended fields
        layt_recommend = wx.GridBagSizer(5, 5)
        layt_recommend.SetCols(4)
        layt_recommend.AddGrowableCol(1)
        layt_recommend.AddGrowableRow(3)
        
        layt_recommend.Add(txt_section, (0, 2), flag=TEXT_FLAG|wx.TOP, border=5)
        layt_recommend.Add(ti_section, (0, 3), flag=wx.RIGHT|wx.TOP, border=5)
        layt_recommend.Add(txt_synopsis, (0, 0), (1, 2), wx.ALIGN_BOTTOM|wx.LEFT, 5)
        layt_recommend.Add(ti_synopsis, (1, 0), (1, 2), wx.EXPAND|wx.LEFT, 5)
        layt_recommend.Add(txt_priority, (1, 2), flag=TEXT_FLAG)
        layt_recommend.Add(sel_priority, (1, 3), flag=wx.RIGHT, border=5)
        layt_recommend.Add(txt_description, (2, 0), (1, 2), wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        layt_recommend.Add(self.ti_description, (3, 0), (1, 4),
                wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        
        pnl_recommend.SetSizer(layt_recommend)
        pnl_recommend.SetAutoLayout(True)
        pnl_recommend.Layout()
        
        # Optional fields
        layt_option = wx.FlexGridSizer(0, 4, 5, 5)
        
        layt_option.AddGrowableCol(1)
        layt_option.AddGrowableCol(3)
        layt_option.AddSpacer(5)
        layt_option.AddSpacer(5)
        layt_option.AddSpacer(5)
        layt_option.AddSpacer(5)
        layt_option.AddMany((
            (txt_source, 0, TEXT_FLAG|wx.LEFT, 5),
            (ti_source, 0, wx.EXPAND),
            (txt_homepage, 0, TEXT_FLAG),
            (ti_homepage, 0, wx.EXPAND|wx.RIGHT, 5),
            (txt_essential, 0, TEXT_FLAG|wx.LEFT|wx.BOTTOM, 5),
            (sel_essential, 1, wx.BOTTOM, 5),
            ))
        
        pnl_option.SetSizer(layt_option)
        pnl_option.SetAutoLayout(True)
        pnl_option.Layout()
        
        # Main background panel sizer
        # FIXME: Is background panel (pnl_bg) necessary
        layt_bg = wx.BoxSizer(wx.VERTICAL)
        layt_bg.Add(layt_buttons, 0, wx.ALL, 5)
        layt_bg.Add(wx.StaticText(pnl_bg, label=GT(u'Required')), 0, wx.LEFT, 5)
        layt_bg.Add(pnl_require, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        layt_bg.Add(wx.StaticText(pnl_bg, label=GT(u'Recommended')), 0, wx.TOP|wx.LEFT, 5)
        layt_bg.Add(pnl_recommend, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        layt_bg.Add(wx.StaticText(pnl_bg, label=GT(u'Optional')), 0, wx.TOP|wx.LEFT, 5)
        layt_bg.Add(pnl_option, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        
        pnl_bg.SetAutoLayout(True)
        pnl_bg.SetSizer(layt_bg)
        pnl_bg.Layout()
        
        # Page's main sizer
        layt_main = wx.BoxSizer(wx.VERTICAL)
        layt_main.Add(pnl_bg, 1, wx.EXPAND)
        
        self.SetAutoLayout(True)
        self.SetSizer(layt_main)
        self.Layout()
        
        # *** Event Handlers *** #
        
        btn_open.Bind(wx.EVT_BUTTON, self.OnBrowse)
        btn_save.Bind(wx.EVT_BUTTON, self.OnSave)
        btn_preview.Bind(wx.EVT_BUTTON, self.OnPreview)
        
        for widget in self.grp_keypress:
            wx.EVT_KEY_DOWN(widget, self.OnKeyDown)
            wx.EVT_KEY_UP(widget, self.OnKeyUp)
    
    
    ## Saving project
    def GatherData(self):
        data = self.GetCtrlInfo()
        return u'<<CTRL>>\n{}<</CTRL>>'.format(data)
    
    
    ## TODO: Doxygen
    def GetCtrlInfo(self):
        pg_depends = wx.GetApp().GetTopWindow().GetWizard().GetPage(ID_DEPENDS)
        
        ctrl_list = []
        synopsis = None
        description = None
        # Email will be set if maintainer changed to True
        maintainer = False
        
        # Text input fields
        for field in self.grp_input:
            field_name = field.GetName().title()
            field_value = field.GetValue()
            
            if FieldEnabled(field) and not TextIsEmpty(field_value):
                Logger.Debug(__name__, GT(u'Exporting {} field').format(field_name))
                
                # Strip leading & trailing spaces, tabs, & newlines
                field_value = field_value.strip(u' \t\n')
                
                if field_name == u'Synopsis':
                    synopsis = u'{}: {}'.format(u'Description', field_value)
                    continue
                
                if field_name == u'Description':
                    description = field_value.split(u'\n')
                    for line_index in range(len(description)):
                        # Remove trailing whitespace
                        description[line_index] = description[line_index].rstrip()
                        
                        if TextIsEmpty(description[line_index]):
                            # Empty lines are formatted with one space indentation & a period
                            description[line_index] = u' .'
                        
                        else:
                            # All other lines are formatted with one space indentation
                            description[line_index] = u' {}'.format(description[line_index])
                    
                    description = u'\n'.join(description)
                    continue
                
                if field_name in (u'Package', u'Version'):
                    # Don't allow whitespace in package name & version
                    ctrl_list.append(u'{}: {}'.format(field_name, u'-'.join(field_value.split(u' '))))
                    continue
                
                if field_name == u'Email':
                    if maintainer and ctrl_list:
                        # Append email to end of maintainer string
                        for ctrl_index in range(len(ctrl_list)):
                            if ctrl_list[ctrl_index].startswith(u'Maintainer: '):
                                Logger.Debug(__name__, u'Found maintainer')
                                ctrl_list[ctrl_index] = u'{} <{}>'.format(ctrl_list[ctrl_index], field_value)
                                break
                    
                    continue
                
                # Don't use 'continue' on this statement
                if field_name == u'Maintainer':
                    maintainer = True
                
                # The rest of the fields
                ctrl_list.append(u'{}: {}'.format(field_name, field_value))
        
        # Selection box fields
        for field in self.grp_select:
            field_name = field.GetName().title()
            field_value = field.GetStringSelection()
            
            if FieldEnabled(field) and not TextIsEmpty(field_value):
                Logger.Debug(__name__, GT(u'Exporting {} field').format(field_name))
                
                # Strip leading & trailing spaces, tabs, & newlines
                field_value = field_value.strip(u' \t\n')
                
                ctrl_list.append(u'{}: {}'.format(field_name, field_value))
        
        # Dependencies & conflicts
        dep_list = [] # Depends
        pre_list = [] # Pre-Depends
        rec_list = [] # Recommends
        sug_list = [] # Suggests
        enh_list = [] # Enhances
        con_list = [] # Conflicts
        rep_list = [] # Replaces
        brk_list = [] # Breaks
        
        all_deps = {
            u'Depends': dep_list,
            u'Pre-Depends': pre_list,
            u'Recommends': rec_list,
            u'Suggests': sug_list,
            u'Enhances': enh_list,
            u'Conflicts': con_list,
            u'Replaces': rep_list,
            u'Breaks': brk_list,
            }
        
        # Get amount of items to add
        dep_area = GetField(pg_depends, FID_LIST)
        dep_count = dep_area.GetItemCount()
        count = 0
        while count < dep_count:
            # Get each item from dependencies page
            dep_type = dep_area.GetItem(count, 0).GetText()
            dep_val = dep_area.GetItem(count, 1).GetText()
            for item in all_deps:
                if dep_type == item:
                    all_deps[item].append(dep_val)
            
            count += 1
        
        for item in all_deps:
            if len(all_deps[item]) != 0:
                ctrl_list.append(u'{}: {}'.format(item, u', '.join(all_deps[item])))
        
        if synopsis:
            ctrl_list.append(synopsis)
            
            # Long description is only added if synopsis is not empty
            if description:
                ctrl_list.append(description)
        
        # dpkg requires empty newline at end of file
        ctrl_list.append(u'\n')
        
        return u'\n'.join(ctrl_list)
    
    
    ## TODO: Doxygen
    def OnBrowse(self, event=None):
        cont = False
        if wx.GetApp().GetTopWindow().cust_dias.IsChecked():
            dia = OpenFile(self)
            if dia.DisplayModal():
                cont = True
        
        else:
            dia = wx.FileDialog(self, GT(u'Open File'), os.getcwd(), style=wx.FD_CHANGE_DIR)
            if dia.ShowModal() == wx.ID_OK:
                cont = True
        
        if cont:
            file_path = dia.GetPath()
            
            FILE_BUFFER = open(file_path, u'r')
            control_data = FILE_BUFFER.read()
            FILE_BUFFER.close()
            
            page_depends = wx.GetApp().GetTopWindow().GetWizard().GetPage(ID_DEPENDS)
            
            # Reset fields to default before opening
            self.ResetAllFields()
            page_depends.ResetAllFields()
            
            depends_data = self.SetFieldData(control_data)
            page_depends.SetFieldData(depends_data)
    
    
    ## Determins if project has been modified
    def OnKeyDown(self, event=None):
        for widget in self.grp_keypress:
            self.grp_keypress[widget] = widget.GetValue()
        
        if event:
            event.Skip()
    
    
    ## TODO: Doxygen
    def OnKeyUp(self, event=None):
        main_window = wx.GetApp().GetTopWindow()
        
        modified = False
        for widget in self.grp_keypress:
            if widget.GetValue() != self.grp_keypress[widget]:
                modified = True
        
        main_window.SetSavedStatus(modified)
        
        if event:
            event.Skip()
    
    
    ## Show a preview of the control file
    def OnPreview(self, event=None):
        control = self.GetCtrlInfo()
        
        # Ensure only one empty newline at end of preview (same as actual output)
        control = control.rstrip(u'\n') + u'\n'
        
        dia = wx.Dialog(self, title=GT(u'Control File Preview'), size=(500,400))
        preview = MultilineTextCtrlPanel(dia, style=wx.TE_READONLY)
        preview.SetValue(control)
        
        dia_sizer = wx.BoxSizer(wx.VERTICAL)
        dia_sizer.Add(preview, 1, wx.EXPAND|wx.ALL, 5)
        
        dia.SetSizer(dia_sizer)
        dia.Layout()
        
        dia.ShowModal()
        dia.Destroy()
    
    
    ## TODO: Doxygen
    def OnSave(self, event=None):
        main_window = wx.GetApp().GetTopWindow()
        
        # Get data to write to control file
        control = self.GetCtrlInfo()
        
        cont = False
        
        # Open a "Save Dialog"
        if main_window.cust_dias.IsChecked():
            dia = SaveFile(self, GT(u'Save Control Information'))
            dia.SetFilename(u'control')
            if dia.DisplayModal():
                cont = True
                path = u'{}/{}'.format(dia.GetPath(), dia.GetFilename())
        
        else:
            dia = wx.FileDialog(self, u'Save Control Information', os.getcwd(),
                style=wx.FD_SAVE|wx.FD_CHANGE_DIR|wx.FD_OVERWRITE_PROMPT)
            dia.SetFilename(u'control')
            
            if dia.ShowModal() == wx.ID_OK:
                cont = True
                path = dia.GetPath()
        
        if cont:
            FILE_BUFFER = open(path, u'w')
            FILE_BUFFER.write(control)
            FILE_BUFFER.close()
    
    
    ## TODO: Doxygen
    #  
    #  FIXME: Unfinished???
    def ReLayout(self):
        # Organize all widgets correctly
        lc_width = self.coauth.GetSize()[0]
        self.coauth.SetColumnWidth(0, lc_width/2)
    
    
    ## TODO: Doxygen
    def ResetAllFields(self):
        for I in self.grp_input:
            I.Clear()
        
        for S in self.grp_select:
            S.SetSelection(S.default)
    
    
    ## Opening Project/File & Setting Fields
    def SetFieldData(self, data):
        # Decode to unicode string if input is byte string
        if isinstance(data, str):
            data = data.decode(u'utf-8')
        
        # Strip leading & traling spaces, tabs, & newlines
        data = data.strip(u' \t\n')
        control_data = data.split(u'\n')
        
        # Store Dependencies
        depends_containers = (
            [u'Depends'],
            [u'Pre-Depends'],
            [u'Recommends'],
            [u'Suggests'],
            [u'Enhances'],
            [u'Conflicts'],
            [u'Replaces'],
            [u'Breaks'],
            )
        
        # Anything left over is dumped into this list then into the description field
        description = []
        
        for line in control_data:
            if u': ' in line:
                key = line.split(u': ')
                value = u': '.join(key[1:]) # For dependency fields that have ": " in description
                key = key[0]
                
                Logger.Debug(__name__, u'Found key: {}'.format(key))
                
                # Catch Maintainer
                if key == u'Maintainer':
                    maintainer = value
                    email = None
                    
                    if u'<' in maintainer and maintainer.endswith(u'>'):
                        maintainer = maintainer.split(u'<')
                        email = maintainer[1].strip(u' <>\t')
                        maintainer = maintainer[0].strip(u' \t')
                    
                    for I in self.grp_input:
                        input_name = I.GetName().title()
                        
                        if input_name == u'Maintainer':
                            I.SetValue(maintainer)
                            continue
                        
                        if input_name == u'Email':
                            I.SetValue(email)
                            # NOTE: Maintainer should be listed before email in input list
                            break
                    
                    continue
                
                # Set the rest of the input fields
                for I in self.grp_input:
                    input_name = I.GetName().title()
                    if input_name == u'Synopsis':
                        input_name = u'Description'
                    
                    if key == input_name:
                        I.SetValue(value)
                
                # Set the wx.Choice fields
                for S in self.grp_select:
                    if key == S.GetName().title():
                        S.SetStringSelection(value)
                
                # Set dependencies
                for container in depends_containers:
                    if container and key == container[0]:
                        for dep in value.split(u', '):
                            container.append(dep)
            
            else:
                # Description
                if line.startswith(u' .'):
                    # Add a blank line for lines beginning with a period
                    description.append(wx.EmptyString)
                    continue
                
                if not TextIsEmpty(line) and line.startswith(u' '):
                    # Remove the first space generated in the description
                    description.append(line[1:])
                    continue
                
                if not TextIsEmpty(line):
                    description.append(line)
        
        # Put leftovers in long description
        self.ti_description.SetValue(u'\n'.join(description))
        
        # Return depends data to parent to be sent to page_depends
        return depends_containers
