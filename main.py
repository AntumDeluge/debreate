# -*- coding: utf-8 -*-

## \package main

# MIT licensing
# See: docs/LICENSE.txt


import os, shutil, subprocess, webbrowser, wx
from urllib2 import HTTPError
from urllib2 import URLError

from dbr.about              import AboutDialog
from dbr.config             import ConfCode
from dbr.config             import GetDefaultConfigValue
from dbr.config             import ReadConfig
from dbr.config             import WriteConfig
from dbr.custom             import OpenFile
from dbr.custom             import SaveFile
from dbr.custom             import StatusBar
from dbr.functions          import GetCurrentVersion
from dbr.language           import GT
from dbr.log                import DebugEnabled
from dbr.log                import Logger
from dbr.moduleaccess       import ModuleAccessCtrl
from dbr.quickbuild         import QuickBuild
from dbr.wizard             import Wizard
from globals.application    import APP_homepage
from globals.application    import APP_project_gh
from globals.application    import APP_project_sf
from globals.application    import AUTHOR_email
from globals.application    import AUTHOR_name
from globals.application    import VERSION_string
from globals.application    import VERSION_tuple
from globals.bitmaps        import ICON_CLOCK
from globals.bitmaps        import ICON_GLOBE
from globals.bitmaps        import ICON_LOGO
from globals.commands       import CMD_gvfs_trash
from globals.commands       import CMD_xdg_open
from globals.ident          import ID_BUILD
from globals.ident          import ID_CHANGELOG
from globals.ident          import ID_CONTROL
from globals.ident          import ID_COPYRIGHT
from globals.ident          import ID_DEPENDS
from globals.ident          import ID_DIALOGS
from globals.ident          import ID_FILES
from globals.ident          import ID_GREETING
from globals.ident          import ID_MENU
from globals.ident          import ID_MENU_TT
from globals.ident          import ID_SCRIPTS
from globals.paths          import PATH_app
from globals.paths          import PATH_local
from globals.project        import PROJECT_ext
from globals.project        import PROJECT_txt
from globals.wizardhelper   import FieldEnabled
from wiz_bin.build          import Panel as PanelBuild
from wiz_bin.changelog      import Panel as PanelChangelog
from wiz_bin.control        import Panel as PanelControl
from wiz_bin.copyright      import Panel as PanelCopyright
from wiz_bin.depends        import Panel as PanelDepends
from wiz_bin.files          import Panel as PanelFiles
from wiz_bin.info           import Panel as PanelInfo
from wiz_bin.menu           import Panel as PanelMenu
from wiz_bin.scripts        import Panel as PanelScripts


# Options menu
ID_LOG_DIR_OPEN = wx.NewId()

# Debian Policy Manual IDs
ID_DPM = wx.NewId()
ID_DPMCtrl = wx.NewId()
ID_DPMLog = wx.NewId()
ID_UPM = wx.NewId()
ID_Lintian = wx.NewId()
ID_Launchers = wx.NewId()

# Misc. IDs
ID_QBUILD = wx.NewId()
ID_UPDATE = wx.NewId()

default_title = GT(u'Debreate - Debian Package Builder')


## TODO: Doxygen
class MainWindow(wx.Frame, ModuleAccessCtrl):
    def __init__(self, pos, size):
        wx.Frame.__init__(self, None, wx.ID_ANY, default_title, pos, size)
        ModuleAccessCtrl.__init__(self, __name__)
        
        # Make sure that this frame is set as the top window
        if not wx.GetApp().GetTopWindow() == self:
            Logger.Debug(__name__, GT(u'Not set as top window'))
            
            wx.GetApp().SetTopWindow(self)
        
        if DebugEnabled():
            self.SetTitle(u'{} ({})'.format(default_title, GT(u'debugging')))
        
        self.SetMinSize((640,400))
        
        # ----- Set Titlebar Icon
        self.main_icon = wx.Icon(u'{}/bitmaps/debreate64.png'.format(PATH_app), wx.BITMAP_TYPE_PNG)
        self.SetIcon(self.main_icon)
        
        # ----- Status Bar
        self.stat_bar = StatusBar(self)
        
        # ----- File Menu
        menu_file = wx.Menu()
        
        mitm_new = wx.MenuItem(menu_file, wx.ID_NEW, GT(u'New project'),
                help=GT(u'Start a new project'))
        mitm_open = wx.MenuItem(menu_file, wx.ID_OPEN, GT(u'Open'),
                help=GT(u'Open a previously saved project'))
        mitm_save = wx.MenuItem(menu_file, wx.ID_SAVE, GT(u'Save'),
                help=GT(u'Save current project'))
        mitm_saveas = wx.MenuItem(menu_file, wx.ID_SAVEAS, GT(u'Save as'),
                help=GT(u'Save current project with a new filename'))
        
        # Quick Build
        self.QuickBuild = wx.MenuItem(menu_file, ID_QBUILD, GT(u'Quick Build'),
                GT(u'Build a package from an existing build tree'))
        self.QuickBuild.SetBitmap(ICON_CLOCK)
        
        mitm_quit = wx.MenuItem(menu_file, wx.ID_EXIT, GT(u'Quit'),
                help=GT(u'Exit Debreate'))
        
        menu_file.AppendItem(mitm_new)
        menu_file.AppendItem(mitm_open)
        menu_file.AppendItem(mitm_save)
        menu_file.AppendItem(mitm_saveas)
        menu_file.AppendSeparator()
        menu_file.AppendItem(self.QuickBuild)
        menu_file.AppendSeparator()
        menu_file.AppendItem(mitm_quit)
        
        wx.EVT_MENU(self, wx.ID_NEW, self.OnNewProject)
        wx.EVT_MENU(self, wx.ID_OPEN, self.OnOpenProject)
        wx.EVT_MENU(self, wx.ID_SAVE, self.OnSaveProject)
        wx.EVT_MENU(self, wx.ID_SAVEAS, self.OnSaveProject)
        wx.EVT_MENU(self, ID_QBUILD, self.OnQuickBuild)
        wx.EVT_MENU(self, wx.ID_EXIT, self.OnQuit)
        wx.EVT_CLOSE(self, self.OnQuit) #custom close event shows a dialog box to confirm quit
        
        # ----- Page Menu
        self.menu_page = wx.Menu()
        
        p_info = wx.MenuItem(self.menu_page, ID_GREETING, GT(u'Information'),
                GT(u'Go to Information section'), kind=wx.ITEM_RADIO)
        p_ctrl = wx.MenuItem(self.menu_page, ID_CONTROL, GT(u'Control'),
                GT(u'Go to Control section'), kind=wx.ITEM_RADIO)
        p_deps = wx.MenuItem(self.menu_page, ID_DEPENDS, GT(u'Dependencies'),
                GT(u'Go to Dependencies section'), kind=wx.ITEM_RADIO)
        p_files = wx.MenuItem(self.menu_page, ID_FILES, GT(u'Files'),
                GT(u'Go to Files section'), kind=wx.ITEM_RADIO)
        p_scripts = wx.MenuItem(self.menu_page, ID_SCRIPTS, GT(u'Scripts'),
                GT(u'Go to Scripts section'), kind=wx.ITEM_RADIO)
        p_changelog = wx.MenuItem(self.menu_page, ID_CHANGELOG, GT(u'Changelog'),
                GT(u'Go to Changelog section'), kind=wx.ITEM_RADIO)
        p_copyright = wx.MenuItem(self.menu_page, ID_COPYRIGHT, GT(u'Copyright'),
                GT(u'Go to Copyright section'), kind=wx.ITEM_RADIO)
        p_menu = wx.MenuItem(self.menu_page, ID_MENU, GT(u'Menu Launcher'),
                GT(u'Go to Menu launcher section'), kind=wx.ITEM_RADIO)
        p_build = wx.MenuItem(self.menu_page, ID_BUILD, GT(u'Build'),
                GT(u'Go to Build section'), kind=wx.ITEM_RADIO)
        
        self.menu_page.AppendItem(p_info)
        self.menu_page.AppendItem(p_ctrl)
        self.menu_page.AppendItem(p_deps)
        self.menu_page.AppendItem(p_files)
        self.menu_page.AppendItem(p_scripts)
        self.menu_page.AppendItem(p_changelog)
        self.menu_page.AppendItem(p_copyright)
        self.menu_page.AppendItem(p_menu)
        self.menu_page.AppendItem(p_build)
        
        # ----- Options Menu
        self.menu_opt = wx.Menu()
        
        # Show/Hide tooltips
        self.opt_tooltips = wx.MenuItem(self.menu_opt, ID_MENU_TT, GT(u'Show tooltips'),
                GT(u'Show or hide tooltips'), kind=wx.ITEM_CHECK)
        wx.EVT_MENU(self, ID_MENU_TT, self.OnToggleToolTips)
        
        # A bug with wx 2.8 does not allow tooltips to be toggled off
        if wx.MAJOR_VERSION > 2:
            self.menu_opt.AppendItem(self.opt_tooltips)
        
        if self.menu_opt.FindItemById(ID_MENU_TT):
            show_tooltips = ReadConfig(u'tooltips')
            if show_tooltips != ConfCode.KEY_NO_EXIST:
                self.opt_tooltips.Check(show_tooltips)
            
            else:
                self.opt_tooltips.Check(GetDefaultConfigValue(u'tooltips'))
            
            self.OnToggleToolTips()
        
        # Dialogs options
        cust_dias = wx.MenuItem(self.menu_opt, ID_DIALOGS, GT(u'Use custom dialogs'),
            GT(u'Use system or custom save/open dialogs'), kind=wx.ITEM_CHECK)
        
        wx.EVT_MENU(self, ID_DIALOGS, self.OnEnableCustomDialogs)
        
        if CMD_gvfs_trash:
            self.menu_opt.AppendItem(cust_dias)
        
        # *** Option Menu: open logs directory *** #
        
        if CMD_xdg_open:
            opt_logs_open = wx.MenuItem(self.menu_opt, ID_LOG_DIR_OPEN, GT(u'Open logs directory'))
            self.menu_opt.AppendItem(opt_logs_open)
            
            wx.EVT_MENU(self, ID_LOG_DIR_OPEN, self.OnLogDirOpen)
        
        # ----- Help Menu
        menu_help = wx.Menu()
        
        # ----- Version update
        m_version_check = wx.MenuItem(menu_help, ID_UPDATE, GT(u'Check for update'),
                GT(u'Check if a new version is available for download'))
        m_version_check.SetBitmap(ICON_LOGO)
        
        menu_help.AppendItem(m_version_check)
        menu_help.AppendSeparator()
        
        wx.EVT_MENU(self, ID_UPDATE, self.OnCheckUpdate)
        
        # Menu with links to the Debian Policy Manual webpages
        self.menu_policy = wx.Menu()
        
        m_dpm = wx.MenuItem(self.menu_policy, ID_DPM, GT(u'Debian Policy Manual'),
                u'http://www.debian.org/doc/debian-policy')
        m_dpm.SetBitmap(ICON_GLOBE)
        m_dpm_Ctrl = wx.MenuItem(self.menu_policy, ID_DPMCtrl, GT(u'Control files'),
                u'http://www.debian.org/doc/debian-policy/ch-controlfields.html')
        m_dpm_Ctrl.SetBitmap(ICON_GLOBE)
        m_dpm_Log = wx.MenuItem(self.menu_policy, ID_DPMLog, GT(u'Changelog'),
                u'http://www.debian.org/doc/debian-policy/ch-source.html#s-dpkgchangelog')
        m_dpm_Log.SetBitmap(ICON_GLOBE)
        m_upm = wx.MenuItem(self.menu_policy, ID_UPM, GT(u'Ubuntu Policy Manual'),
                u'http://people.canonical.com/~cjwatson/ubuntu-policy/policy.html/')
        m_upm.SetBitmap(ICON_GLOBE)
        # FIXME: Use wx.NewId()
        m_deb_src = wx.MenuItem(self.menu_policy, 222, GT(u'Building debs from source'),
                u'http://www.quietearth.us/articles/2006/08/16/Building-deb-package-from-source') # This is here only temporarily for reference
        m_deb_src.SetBitmap(ICON_GLOBE)
        m_lintain_tags = wx.MenuItem(self.menu_policy, ID_Lintian, GT(u'Lintian tags explanation'),
                u'http://lintian.debian.org/tags-all.html')
        m_lintain_tags.SetBitmap(ICON_GLOBE)
        m_launchers = wx.MenuItem(self.menu_policy, ID_Launchers, GT(u'Launchers / Desktop entries'),
                u'https://www.freedesktop.org/wiki/Specifications/desktop-entry-spec/')
        m_launchers.SetBitmap(ICON_GLOBE)
        
        self.menu_policy.AppendItem(m_dpm)
        self.menu_policy.AppendItem(m_dpm_Ctrl)
        self.menu_policy.AppendItem(m_dpm_Log)
        self.menu_policy.AppendItem(m_upm)
        self.menu_policy.AppendItem(m_deb_src)
        self.menu_policy.AppendItem(m_lintain_tags)
        self.menu_policy.AppendItem(m_launchers)
        
        lst_policy_ids = (
            ID_DPM,
            ID_DPMCtrl,
            ID_DPMLog,
            ID_UPM,
            222,
            ID_Lintian,
            ID_Launchers,
            )
        
        for ID in lst_policy_ids:
            wx.EVT_MENU(self, ID, self.OpenPolicyManual)
        
        m_help = wx.MenuItem(menu_help, wx.ID_HELP, GT(u'Help'), GT(u'Open a usage document'))
        m_about = wx.MenuItem(menu_help, wx.ID_ABOUT, GT(u'About'), GT(u'About Debreate'))
        
        menu_help.AppendMenu(-1, GT(u'Reference'), self.menu_policy)
        menu_help.AppendSeparator()
        menu_help.AppendItem(m_help)
        menu_help.AppendItem(m_about)
        
        wx.EVT_MENU(self, wx.ID_HELP, self.OnHelp)
        wx.EVT_MENU(self, wx.ID_ABOUT, self.OnAbout)
        
        menubar = wx.MenuBar()
        self.SetMenuBar(menubar)
        
        menubar.Append(menu_file, GT(u'File'))
        menubar.Append(self.menu_page, GT(u'Page'))
        
        if self.menu_opt.GetMenuItemCount():
            menubar.Append(self.menu_opt, GT(u'Options'))
        
        menubar.Append(menu_help, GT(u'Help'))
        
        # ***** END MENUBAR ***** #
        
        self.wizard = Wizard(self) # Binary
        
        self.page_info = PanelInfo(self.wizard)
        self.page_control = PanelControl(self.wizard)
        self.page_depends = PanelDepends(self.wizard)
        self.page_files = PanelFiles(self.wizard)
        self.page_scripts = PanelScripts(self.wizard)
        self.page_clog = PanelChangelog(self.wizard)
        self.page_cpright = PanelCopyright(self.wizard)
        self.page_menu = PanelMenu(self.wizard)
        self.page_build = PanelBuild(self.wizard)
        
        self.all_pages = (
            self.page_control, self.page_depends, self.page_files, self.page_scripts,
            self.page_clog, self.page_cpright, self.page_menu, self.page_build
            )
        
        bin_pages = (
            self.page_info, self.page_control, self.page_depends, self.page_files, self.page_scripts,
            self.page_clog, self.page_cpright, self.page_menu, self.page_build
            )
        
        self.wizard.SetPages(bin_pages)
        
        lst_pages = (
            p_info,
            p_ctrl,
            p_deps,
            p_files,
            p_scripts,
            p_changelog,
            p_copyright,
            p_menu,
            p_build,
            )
        
        for p in lst_pages:
            wx.EVT_MENU(self, p.GetId(), self.GoToPage)
        
        # ----- Layout
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.wizard, 1, wx.EXPAND)
        
        self.SetAutoLayout(True)
        self.SetSizer(self.main_sizer)
        self.Layout()
        
        # Saving
        # First item is name of saved file displayed in title
        # Second item is actual path to project file
        self.saved_project = wx.EmptyString
    
    
    ## Retrieves the Wizard instance
    #  
    #  \return
    #        dbr.wizard.Wizard
    def GetWizard(self):
        return self.wizard
    
    
    ## Changes wizard page
    #  
    #  \param event
    #        \b \e wx.MenuEvent|int : The event or integer to use as page ID
    def GoToPage(self, event=None):
        if isinstance(event, int):
            event_id = event
        
        else:
            event_id = event.GetId()
        
        self.wizard.ShowPage(event_id)
    
    
    ## TODO: Doxygen
    def IsNewProject(self):
        title = self.GetTitle()
        if title == default_title:
            return True
        
        else:
            return False
    
    
    ## TODO: Doxygen
    def IsSaved(self):
        title = self.GetTitle()
        if title[-1] == u'*':
            return False
        
        else:
            return True
    
    
    ## Opens a dialog box with information about the program
    def OnAbout(self, event=None):
        about = AboutDialog(self)
        
        about.SetGraphic(u'{}/bitmaps/debreate64.png'.format(PATH_app))
        about.SetVersion(VERSION_string)
        about.SetDescription(GT(u'A package builder for Debian based systems'))
        about.SetAuthor(AUTHOR_name)
        
        about.SetWebsites((
            (GT(u'Homepage'), APP_homepage),
            (GT(u'GitHub Project'), APP_project_gh),
            (GT(u'Sourceforge Project'), APP_project_sf),
        ))
        
        about.AddJobs(
            AUTHOR_name,
            (
                GT(u'Head Developer'),
                GT(u'Packager'),
                u'{} (es, it)'.format(GT(u'Translation')),
            ),
            AUTHOR_email
        )
        
        about.AddJobs(
            u'Hugo Posnic',
            (
                GT(u'Code Contributor'),
                GT(u'Website Designer & Author'),
            ),
            u'hugo.posnic@gmail.com'
        )
        
        about.AddJob(u'Lander Usategui San Juan', GT(u'General Contributor'), u'lander@erlerobotics.com')
        
        about.AddTranslator(u'Karim Oulad Chalha', u'herr.linux88@gmail.com', u'ar', )
        about.AddTranslator(u'Philippe Dalet', u'philippe.dalet@ac-toulouse.fr', u'fr')
        about.AddTranslator(u'Zhmurkov Sergey', u'zhmsv@yandex.ru', u'ru')
        
        about.SetChangelog()
        
        about.SetLicense()
        
        about.ShowModal()
        about.Destroy()
    
    
    ## Checks for new release availability
    def OnCheckUpdate(self, event=None):
        if u'-dev' in VERSION_string:
            wx.MessageDialog(self, GT(u'Update checking not supported in development versions'),
                    GT(u'Update'), wx.OK|wx.ICON_INFORMATION).ShowModal()
            return
        
        wx.SafeYield()
        current = GetCurrentVersion()
        Logger.Debug(__name__, GT(u'URL request result: {}').format(current))
        if type (current) == URLError or type(current) == HTTPError:
            current = unicode(current)
            wx.MessageDialog(self, current, GT(u'Error'), wx.OK|wx.ICON_ERROR).ShowModal()
        
        elif isinstance(current, tuple) and current > VERSION_tuple:
            current = u'{}.{}.{}'.format(current[0], current[1], current[2])
            l1 = GT(u'Version {} is available!').format(current)
            l2 = GT(u'Would you like to go to Debreate\'s website?')
            update = wx.MessageDialog(self, u'{}\n\n{}'.format(l1, l2), GT(u'Debreate'), wx.YES_NO|wx.ICON_INFORMATION).ShowModal()
            if (update == wx.ID_YES):
                wx.LaunchDefaultBrowser(APP_homepage)
        
        elif isinstance(current, (unicode, str)):
            err_msg = GT(u'An error occurred attempting to retrieve version from remote website:')
            err_msg = u'{}\n\n{}'.format(err_msg, current)
            
            Logger.Error(__name__, err_msg)
            
            err = wx.MessageDialog(self, err_msg,
                    GT(u'Error'), wx.OK|wx.ICON_INFORMATION)
            err.CenterOnParent()
            err.ShowModal()
        
        else:
            err = wx.MessageDialog(self, GT(u'Debreate is up to date!'), GT(u'Debreate'), wx.OK|wx.ICON_INFORMATION)
            err.CenterOnParent()
            err.ShowModal()
    
    
    ## Writes dialog settings to config
    def OnEnableCustomDialogs(self, event=None):
        WriteConfig(u'dialogs', self.UseCustomDialogs())
    
    
    ## Action to take when 'Help' is selected from the help menu
    #  
    #  First tries to open pdf help file. If fails tries
    #  to open html help file. If fails opens debreate usage
    #  webpage
    def OnHelp(self, event=None):
        wx.Yield()
        status = subprocess.call([u'xdg-open', u'{}/docs/usage.pdf'.format(PATH_app)])
        if status:
            wx.Yield()
            status = subprocess.call([u'xdg-open', u'{}/docs/usage'.format(PATH_app)])
        
        if status:
            wx.Yield()
            webbrowser.open(u'http://debreate.sourceforge.net/usage')
    
    
    ## Opens the logs directory in the system's default file manager
    def OnLogDirOpen(self, event=None):
        Logger.Debug(__name__, GT(u'Opening log directory ...'))
        
        subprocess.check_output([CMD_xdg_open, u'{}/logs'.format(PATH_local)], stderr=subprocess.STDOUT)
    
    
    ## TODO: Doxygen
    def OnNewProject(self, event=None):
        self.ResetPages()
    
    
    ## TODO: Doxygen
    def OnOpenProject(self, event=None):
        cont = False
        projects_filter = u'|*.{};*.{}'.format(PROJECT_ext, PROJECT_txt)
        d = GT(u'Debreate project files')
        if self.UseCustomDialogs():
            dia = OpenFile(self, GT(u'Open Debreate Project'))
            dia.SetFilter(u'{}{}'.format(d, projects_filter))
            if dia.DisplayModal():
                cont = True
        
        else:
            dia = wx.FileDialog(self, GT(u'Open Debreate Project'), os.getcwd(), u'',
                    u'{}{}'.format(d, projects_filter), wx.FD_CHANGE_DIR)
            if dia.ShowModal() == wx.ID_OK:
                cont = True
        
        if cont:
            # Abort
            if self.saved_project and not self.ResetPages():
                return
            
            # Get the path and set the saved project
            self.saved_project = dia.GetPath()
            
            FILE_BUFFER = open(self.saved_project, u'r')
            data = FILE_BUFFER.read()
            FILE_BUFFER.close()
            
            filename = os.path.split(self.saved_project)[1]
            
            self.OpenProject(data, filename)
    
    
    ## TODO: Doxygen
    def OnQuickBuild(self, event=None):
        QB = QuickBuild(self)
        QB.ShowModal()
        QB.Destroy()
    
    
    ## Shows a dialog to confirm quit and write window settings to config file
    def OnQuit(self, event=None):
        confirm = wx.MessageDialog(self, GT(u'You will lose any unsaved information'), GT(u'Quit?'),
                                   wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        if confirm.ShowModal() == wx.ID_OK:
            confirm.Destroy()
            
            maximized = self.IsMaximized()
            WriteConfig(u'maximize', maximized)
            
            if maximized:
                WriteConfig(u'position', GetDefaultConfigValue(u'position'))
                WriteConfig(u'size', GetDefaultConfigValue(u'size'))
                WriteConfig(u'center', True)
            
            else:
                WriteConfig(u'position', self.GetPositionTuple())
                WriteConfig(u'size', self.GetSizeTuple())
                WriteConfig(u'center', False)
            
            WriteConfig(u'workingdir', os.getcwd())
            
            self.Destroy()
        
        else:
            confirm.Destroy()
    
    
    ## TODO: Doxygen
    def OnSaveProject(self, event=None):
        event_id = event.GetId()
        
        def SaveIt(path):
                # Gather data from different pages
                data = (self.page_control.GatherData(), self.page_files.GatherData(),
                        self.page_scripts.GatherData(), self.page_clog.GatherData(),
                        self.page_cpright.GatherData(), self.page_menu.GatherData(),
                        self.page_build.GatherData())
                
                # Create a backup of the project
                overwrite = False
                if os.path.isfile(path):
                    backup = u'{}.backup'.format(path)
                    shutil.copy(path, backup)
                    overwrite = True
                
                savefile = open(path, u'w')
                
                # This try statement can be removed when unicode support is enabled
                try:
                    savefile.write(u'[DEBREATE-{}]\n{}'.format(VERSION_string, u'\n'.join(data)))
                    savefile.close()
                    if overwrite:
                        os.remove(backup)
                
                except UnicodeEncodeError:
                    serr = GT(u'Save failed')
                    uni = GT(u'Unfortunately Debreate does not support unicode yet. Remove any non-ASCII characters from your project.')
                    UniErr = wx.MessageDialog(self, u'{}\n\n{}'.format(serr, uni), GT(u'Unicode Error'), style=wx.OK|wx.ICON_EXCLAMATION)
                    UniErr.ShowModal()
                    savefile.close()
                    if overwrite:
                        os.remove(path)
                        # Restore project backup
                        shutil.move(backup, path)
        
        
        ## TODO: Doxygen
        def OnSaveAs():
            dbp = u'|*.dbp'
            d = GT(u'Debreate project files')
            cont = False
            if self.UseCustomDialogs():
                dia = SaveFile(self, GT(u'Save Debreate Project'), u'dbp')
                dia.SetFilter(u'{}{}'.format(d, dbp))
                if dia.DisplayModal():
                    cont = True
                    filename = dia.GetFilename()
                    if filename.split(u'.')[-1] == u'dbp':
                        filename = u'.'.join(filename.split(u'.')[:-1])
                    
                    self.saved_project = u'{}/{}.dbp'.format(dia.GetPath(), filename)
            
            else:
                dia = wx.FileDialog(self, GT(u'Save Debreate Project'), os.getcwd(), u'', u'{}{}'.format(d, dbp),
                                        wx.FD_SAVE|wx.FD_CHANGE_DIR|wx.FD_OVERWRITE_PROMPT)
                if dia.ShowModal() == wx.ID_OK:
                    cont = True
                    filename = dia.GetFilename()
                    if filename.split(u'.')[-1] == u'dbp':
                        filename = u'.'.join(filename.split(u'.')[:-1])
                    
                    self.saved_project = u'{}/{}.dbp'.format(os.path.split(dia.GetPath())[0], filename)
            
            if cont:
                SaveIt(self.saved_project)
        
        if event_id == wx.ID_SAVE:
            # Define what to do if save is pressed
            # If project already exists, don't show dialog
            if not self.IsSaved() or self.saved_project == wx.EmptyString or not os.path.isfile(self.saved_project):
                OnSaveAs()
            
            else:
                SaveIt(self.saved_project)
        
        else:
            # If save as is press, show the save dialog
            OnSaveAs()
    
    
    ## Shows or hides tooltips
    def OnToggleToolTips(self, event=None):
        enabled = self.opt_tooltips.IsChecked()
        wx.ToolTip.Enable(enabled)
        
        WriteConfig(u'tooltips', enabled)
    
    
    ## Opens web links from the help menu
    def OpenPolicyManual(self, event=None):
        if isinstance(event, wx.CommandEvent):
            event_id = event.GetId()
        
        elif isinstance(event, int):
            event_id = event
        
        else:
            Logger.Error(__name__,
                    u'Cannot open policy manual link with object type {}'.format(type(event)))
            
            return
        
        url = self.menu_policy.GetHelpString(event_id)
        webbrowser.open(url)
    
    
    ## TODO: Doxygen
    def OpenProject(self, data, filename):
        lines = data.split(u'\n')
        app = lines[0].split(u'-')[0].split(u'[')[1]
        if app != u'DEBREATE':
            bad_file = wx.MessageDialog(self, GT(u'Not a valid Debreate project'), GT(u'Error'),
                    style=wx.OK|wx.ICON_ERROR)
            bad_file.ShowModal()
        
        else: 
            # *** Get Control Data *** #
            control_data = data.split(u'<<CTRL>>\n')[1].split(u'\n<</CTRL>>')[0]
            depends_data = self.page_control.SetFieldData(control_data)
            self.page_depends.SetFieldData(depends_data)
            
            # *** Get Files Data *** #
            files_data = data.split(u'<<FILES>>\n')[1].split(u'\n<</FILES>>')[0]
            self.page_files.SetFieldData(files_data)
            
            # *** Get Scripts Data *** #
            scripts_data = data.split(u'<<SCRIPTS>>\n')[1].split(u'\n<</SCRIPTS>>')[0]
            self.page_scripts.SetFieldData(scripts_data)
            
            # *** Get Changelog Data *** #
            clog_data = data.split(u'<<CHANGELOG>>\n')[1].split(u'\n<</CHANGELOG>>')[0]
            self.page_clog.SetChangelog(clog_data)
            
            # *** Get Copyright Data *** #
            try:
                cpright_data = data.split(u'<<COPYRIGHT>>\n')[1].split(u'\n<</COPYRIGHT')[0]
                self.page_cpright.SetCopyright(cpright_data)
            
            except IndexError:
                pass
            
            # *** Get Menu Data *** #
            menu_data = data.split(u'<<MENU>>\n')[1].split(u'\n<</MENU>>')[0]
            self.page_menu.SetLauncherData(menu_data, enabled=True)
            
            # Get Build Data
            build_data = data.split(u'<<BUILD>>\n')[1].split(u'\n<</BUILD')[0]#.split(u'\n')
            self.page_build.SetFieldData(build_data)
    
    
    ## TODO: Doxygen
    def ResetPages(self):
        dia = wx.MessageDialog(self, GT(u'You will lose any unsaved information\n\nContinue?'),
                GT(u'Start New Project'), wx.YES_NO|wx.NO_DEFAULT)
        if dia.ShowModal() == wx.ID_YES:
            for page in self.all_pages:
                page.ResetAllFields()
            self.SetTitle(default_title)
            
            # Reset the saved project field so we know that a project file doesn't exists
            self.saved_project = wx.EmptyString
            
            return True
        
        return False
    
    
    ## TODO: Doxygen
    def SetSavedStatus(self, status):
        if status: # If status is changing to unsaved this is True
            title = self.GetTitle()
            if self.IsSaved() and title != default_title:
                self.SetTitle(u'{}*'.format(title))
    
    
    ## TODO: Doxygen
    def UseCustomDialogs(self):
        cust_dias = self.menu_opt.FindItemById(ID_DIALOGS)
        
        # This needs to be checked first to avoid PyAssertionError in wx 3.0
        if not cust_dias:
            return False
        
        return cust_dias.IsChecked()
