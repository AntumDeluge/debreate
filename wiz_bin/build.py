# -*- coding: utf-8 -*-

## \package wiz_bin.build

# MIT licensing
# See: docs/LICENSE.txt


import commands, os, shutil, subprocess, wx

from dbr.buttons            import ButtonBuild64
from dbr.custom             import OutputLog
from dbr.custom             import SaveFile
from dbr.dialogs            import DetailedMessageDialog
from dbr.dialogs            import ShowErrorDialog
from dbr.dialogs            import ShowMessageDialog
from dbr.functions          import TextIsEmpty
from dbr.language           import GT
from dbr.log                import DebugEnabled
from dbr.log                import Logger
from dbr.md5                import MD5Hasher
from dbr.panel              import BorderedPanel
from dbr.progress           import PD_DEFAULT_STYLE
from dbr.progress           import ProgressDialog
from globals.bitmaps        import ICON_INFORMATION
from globals.commands       import CMD_dpkgdeb
from globals.commands       import CMD_fakeroot
from globals.commands       import CMD_gdebi_gui
from globals.commands       import CMD_lintian
from globals.commands       import CMD_md5sum
from globals.commands       import CMD_system_installer
from globals.errorcodes     import dbrerrno
from globals.ident          import FID_ARCH
from globals.ident          import FID_EMAIL
from globals.ident          import FID_MAINTAINER
from globals.ident          import FID_PACKAGE
from globals.ident          import FID_VERSION
from globals.ident          import ID_BUILD
from globals.ident          import ID_CHANGELOG
from globals.ident          import ID_CONTROL
from globals.ident          import ID_COPYRIGHT
from globals.ident          import ID_FILES
from globals.ident          import ID_MENU
from globals.ident          import ID_SCRIPTS
from globals.paths          import ConcatPaths
from globals.tooltips       import SetPageToolTips
from globals.wizardhelper   import FieldEnabled
from globals.wizardhelper   import GetField
from globals.wizardhelper   import GetPage
from globals.wizardhelper   import GetTopWindow
from globals.wizardhelper   import UseCustomDialogs


## Build page
class Panel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, ID_BUILD, name=GT(u'Build'))
        
        self.SetScrollbars(0, 20, 0, 0)
        
        # ----- Extra Options
        
        pnl_options = BorderedPanel(self)
        
        self.chk_md5 = wx.CheckBox(pnl_options, label=GT(u'Create md5sums file'))
        # The » character denotes that an alternate tooltip should be shown if the control is disabled
        self.chk_md5.tt_name = u'md5»'
        self.chk_md5.SetName(u'MD5')
        self.chk_md5.default = False
        
        if not CMD_md5sum:
            self.chk_md5.Disable()
        
        # For creating md5sum hashes
        self.md5 = MD5Hasher(self.chk_md5)
        
        # Deletes the temporary build tree
        self.chk_rmstage = wx.CheckBox(pnl_options, label=GT(u'Delete build tree'))
        self.chk_rmstage.SetName(u'rmstage')
        self.chk_rmstage.default = True
        self.chk_rmstage.SetValue(self.chk_rmstage.default)
        
        # Checks the output .deb for errors
        self.chk_lint = wx.CheckBox(pnl_options, label=GT(u'Check package for errors with lintian'))
        self.chk_lint.tt_name = u'lintian»'
        self.chk_lint.SetName(u'LINTIAN')
        self.chk_lint.default = True
        
        if not CMD_lintian:
            self.chk_lint.Disable()
        
        else:
            self.chk_lint.SetValue(self.chk_lint.default)
        
        # Installs the deb on the system
        self.chk_install = wx.CheckBox(pnl_options, label=GT(u'Install package after build'))
        self.chk_install.tt_name = u'install»'
        self.chk_install.SetName(u'INSTALL')
        self.chk_install.default = False
        
        if not CMD_gdebi_gui:
            self.chk_install.Enable(False)
        
        btn_build = ButtonBuild64(self)
        btn_build.SetName(u'build')
        
        # Display log
        dsp_log = OutputLog(self)
        
        SetPageToolTips(self)
        
        # *** Layout *** #
        
        lyt_options = wx.BoxSizer(wx.VERTICAL)
        lyt_options.AddMany((
            (self.chk_md5, 0, wx.LEFT|wx.RIGHT, 5),
            (self.chk_rmstage, 0, wx.LEFT|wx.RIGHT, 5),
            (self.chk_lint, 0, wx.LEFT|wx.RIGHT, 5),
            (self.chk_install, 0, wx.LEFT|wx.RIGHT, 5)
            ))
        
        pnl_options.SetSizer(lyt_options)
        pnl_options.SetAutoLayout(True)
        pnl_options.Layout()
        
        lyt_buttons = wx.BoxSizer(wx.HORIZONTAL)
        lyt_buttons.Add(btn_build, 1)
        
        lyt_main = wx.BoxSizer(wx.VERTICAL)
        lyt_main.AddSpacer(10)
        lyt_main.Add(wx.StaticText(self, label=GT(u'Extra Options')), 0,
                wx.ALIGN_LEFT|wx.ALIGN_BOTTOM|wx.LEFT, 5)
        lyt_main.Add(pnl_options, 0, wx.LEFT, 5)
        lyt_main.AddSpacer(5)
        lyt_main.AddSpacer(5)
        lyt_main.Add(lyt_buttons, 0, wx.ALIGN_CENTER)
        lyt_main.Add(dsp_log, 2, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        
        self.SetAutoLayout(True)
        self.SetSizer(lyt_main)
        self.Layout()
        
        # *** Event handlers *** #
        
        btn_build.Bind(wx.EVT_BUTTON, self.OnBuild)
    
    
    ## The actual build process
    #  
    #  \param task_list
    #        \b \e dict : Task string IDs & page data
    #  \param build_path
    #        \b \e unicode|str : Directory where .deb will be output
    #  \param filename
    #        \b \e unicode|str : Basename of output file without .deb extension
    #  \return
    #        \b \e dbrerror : SUCCESS if build completed successfully
    def Build(self, task_list, build_path, filename):
        # Other mandatory tasks that will be processed
        mandatory_tasks = (
            u'stage',
            u'install_size',
            u'control',
            u'build',
            )
        
        # Add other mandatory tasks
        for T in mandatory_tasks:
            task_list[T] = None
        
        task_count = len(task_list)
        
        # Add each file for updating progress dialog
        if u'files' in task_list:
            task_count += len(task_list[u'files'])
        
        # Add each script for updating progress dialog
        if u'scripts' in task_list:
            task_count += len(task_list[u'scripts'])
        
        if DebugEnabled():
            task_msg = GT(u'Total tasks: {}').format(task_count)
            print(u'DEBUG: [{}] {}'.format(__name__, task_msg))
            for T in task_list:
                print(u'\t{}'.format(T))
        
        create_changelog = u'changelog' in task_list
        create_copyright = u'copyright' in task_list
        
        pg_control = GetPage(ID_CONTROL)
        pg_menu = GetPage(ID_MENU)
        
        stage_dir = u'{}/{}__dbp__'.format(build_path, filename)
        
        if os.path.isdir(u'{}/DEBIAN'.format(stage_dir)):
            c = u'rm -r "{}"'.format(stage_dir)
            if commands.getstatusoutput(c.encode(u'utf-8'))[0]:
                err_msg = GT(u'Could not free stage directory: {}').format(stage_dir)
                wx.MessageDialog(self, err_msg, GT(u'Cannot Continue'),
                        style=wx.OK|wx.ICON_ERROR).ShowModal()
                
                return (dbrerrno.EEXIST, None)
        
        # Actual path to new .deb
        deb = u'"{}/{}.deb"'.format(build_path, filename)
        
        progress = 0
        
        task_msg = GT(u'Preparing build tree')
        Logger.Debug(__name__, task_msg)
        
        wx.Yield()
        build_progress = ProgressDialog(GetTopWindow(), GT(u'Building'), task_msg,
                maximum=task_count,
                style=PD_DEFAULT_STYLE|wx.PD_ELAPSED_TIME|wx.PD_ESTIMATED_TIME|wx.PD_CAN_ABORT)
        
        # Make a fresh build tree
        os.makedirs(u'{}/DEBIAN'.format(stage_dir))
        progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        def UpdateProgress(current_task, message=None):
            task_eval = u'{} / {}'.format(current_task, task_count)
            
            if message:
                Logger.Debug(__name__, u'{} ({})'.format(message, task_eval))
                
                wx.Yield()
                build_progress.Update(current_task, message)
                
                return
            
            wx.Yield()
            build_progress.Update(current_task)
        
        # *** Files *** #
        if u'files' in task_list:
            UpdateProgress(progress, GT(u'Copying files'))
            
            files_data = task_list[u'files']
            for FILE in files_data:
                # Create new directories
                new_dir = u'{}{}'.format(stage_dir, FILE.split(u' -> ')[2])
                if not os.path.isdir(new_dir):
                    os.makedirs(new_dir)
                
                # Get FILE path
                FILE = FILE.split(u' -> ')[0]
                
                # Remove asteriks from exectuables
                exe = False
                if FILE[-1] == u'*':
                    exe = True
                    FILE = FILE[:-1]
                
                # Copy files
                copy_path = u'{}/{}'.format(new_dir, os.path.split(FILE)[1])
                shutil.copy(FILE, copy_path)
                
                # Set FILE permissions
                if exe:
                    os.chmod(copy_path, 0755)
                
                else:
                    os.chmod(copy_path, 0644)
                
                # Individual files
                progress += 1
                UpdateProgress(progress)
            
            # Entire file task
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        package = GetField(pg_control, FID_PACKAGE).GetValue()
        
        # Make sure that the dirctory is available in which to place documentation
        if create_changelog or create_copyright:
            doc_dir = u'{}/usr/share/doc/{}'.format(stage_dir, package)
            if not os.path.isdir(doc_dir):
                os.makedirs(doc_dir)
        
        # *** Changelog *** #
        if create_changelog:
            UpdateProgress(progress, GT(u'Creating changelog'))
            
            # If changelog will be installed to default directory
            changelog_target = task_list[u'changelog'][0]
            if changelog_target == u'STANDARD':
                changelog_target = ConcatPaths((u'{}/usr/share/doc'.format(stage_dir), package))
            
            else:
                changelog_target = ConcatPaths((stage_dir, changelog_target))
            
            if not os.path.isdir(changelog_target):
                os.makedirs(changelog_target)
            
            FILE_BUFFER = open(u'{}/changelog'.format(changelog_target), u'w')
            FILE_BUFFER.write(task_list[u'changelog'][1].encode(u'utf-8'))
            FILE_BUFFER.close()
            
            c = u'gzip -n --best "{}/changelog"'.format(changelog_target)
            clog_status = commands.getstatusoutput(c.encode(u'utf-8'))
            if clog_status[0]:
                clog_error = GT(u'Could not create changelog')
                changelog_error = wx.MessageDialog(self, u'{}\n\n{}'.format(clog_error, clog_status[1]),
                        GT(u'Error'), wx.OK)
                changelog_error.ShowModal()
            
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** Copyright *** #
        if create_copyright:
            UpdateProgress(progress, GT(u'Creating copyright'))
            
            FILE_BUFFER = open(u'{}/usr/share/doc/{}/copyright'.format(stage_dir, package), u'w')
            FILE_BUFFER.write(task_list[u'copyright'].encode(u'utf-8'))
            FILE_BUFFER.close()
            
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # Characters that should not be in filenames
        invalid_chars = (u' ', u'/')
        
        # *** Menu launcher *** #
        if u'launcher' in task_list:
            UpdateProgress(progress, GT(u'Creating menu launcher'))
            
            # This might be changed later to set a custom directory
            menu_dir = u'{}/usr/share/applications'.format(stage_dir)
            
            menu_filename = pg_menu.GetOutputFilename()
            
            # Remove invalid characters from filename
            for char in invalid_chars:
                menu_filename = menu_filename.replace(char, u'_')
            
            if not os.path.isdir(menu_dir):
                os.makedirs(menu_dir)
            
            FILE_BUFFER = open(u'{}/{}.desktop'.format(menu_dir, menu_filename), u'w')
            FILE_BUFFER.write(u'\n'.join(task_list[u'launcher']).encode(u'utf-8'))
            FILE_BUFFER.close()
            
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** md5sums file *** #
        # Good practice to create hashes before populating DEBIAN directory
        if u'md5sums' in task_list:
            UpdateProgress(progress, GT(u'Creating md5sums'))
            
            if not self.md5.WriteMd5(build_path, stage_dir, parent=build_progress):
                # Couldn't call md5sum command
                build_progress.Cancel()
            
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** Scripts *** #
        if u'scripts' in task_list:
            UpdateProgress(progress, GT(u'Creating scripts'))
            
            scripts = task_list[u'scripts']
            for script_name, script_text in scripts:
                script_filename = ConcatPaths((u'{}/DEBIAN'.format(stage_dir), script_name))
                
                FILE_BUFFER = open(script_filename, u'w')
                FILE_BUFFER.write(script_text.encode(u'utf-8'))
                FILE_BUFFER.close()
                
                # Make sure scipt path is wrapped in quotes to avoid whitespace errors
                os.chmod(script_filename, 0755)
                os.system((u'chmod +x "{}"'.format(script_filename)))
                
                # Individual scripts
                progress += 1
                UpdateProgress(progress)
            
            # Entire script task
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** Control file *** #
        UpdateProgress(progress, GT(u'Getting installed size'))
        
        # Get installed-size
        installed_size = os.popen((u'du -hsk "{}"'.format(stage_dir))).readlines()
        installed_size = installed_size[0].split(u'\t')
        installed_size = installed_size[0]
        
        # Insert Installed-Size into control file
        control_data = pg_control.ExportPage().split(u'\n')
        control_data.insert(2, u'Installed-Size: {}'.format(installed_size))
        
        progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # Create final control file
        UpdateProgress(progress, GT(u'Creating control file'))
        
        # dpkg fails if there is no newline at end of file
        if control_data and control_data[-1] != u'\n':
            control_data.append(u'\n')
        
        control_data = u'\n'.join(control_data)
        
        FILE_BUFFER = open(u'{}/DEBIAN/control'.format(stage_dir), u'w')
        FILE_BUFFER.write(control_data.encode(u'utf-8'))
        FILE_BUFFER.close()
        
        progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** Final build *** #
        UpdateProgress(progress, GT(u'Running dpkg'))
        
        working_dir = os.path.split(stage_dir)[0]
        c_tree = os.path.split(stage_dir)[1]
        deb_package = u'{}.deb'.format(filename)
        
        # Move the working directory becuase dpkg seems to have problems with spaces in path
        os.chdir(working_dir)
        build_status = commands.getstatusoutput((u'{} {} -b "{}" "{}"'.format(CMD_fakeroot, CMD_dpkgdeb, c_tree, deb_package)))
        
        progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** Delete staged directory *** #
        if u'rmstage' in task_list:
            UpdateProgress(progress, GT(u'Removing temp directory'))
            
            if commands.getstatusoutput((u'rm -r "{}"'.format(stage_dir)).encode(u'utf-8'))[0]:
                wx.MessageDialog(build_progress, GT(u'An error occurred when trying to delete the build tree'),
                        GT(u'Error'), style=wx.OK|wx.ICON_EXCLAMATION)
            
            progress += 1
        
        if build_progress.WasCancelled():
            build_progress.Destroy()
            return (dbrerrno.ECNCLD, None)
        
        # *** ERROR CHECK
        if u'lintian' in task_list:
            UpdateProgress(progress, GT(u'Checking package for errors'))
            
            errors = commands.getoutput((u'{} {}'.format(CMD_lintian, deb)))
            
            if errors != wx.EmptyString:
                e1 = GT(u'Lintian found some issues with the package.')
                e2 = GT(u'Details saved to {}').format(filename)
                
                FILE_BUFFER = open(u'{}/{}.lintian'.format(build_path, filename), u'w')
                FILE_BUFFER.write(errors.encode(u'utf-8'))
                FILE_BUFFER.close()
                
                DetailedMessageDialog(build_progress, GT(u'Lintian Errors'),
                        ICON_INFORMATION, u'{}\n{}.lintian'.format(e1, e2), errors).ShowModal()
            
            progress += 1
        
        # Close progress dialog
        wx.Yield()
        build_progress.Update(progress)
        build_progress.Destroy()
        
        # Build completed successfullly
        if not build_status[0]:
            return (dbrerrno.SUCCESS, deb_package)
        
        # Build failed
        return (build_status[0], None)
    
    
    ## TODO: Doxygen
    #  
    #  \return
    #        \b \e tuple : Return code & build details
    def BuildPrep(self):
        # List of tasks for build process
        # 'stage' should be very first task
        task_list = {}
        
        # Control page
        pg_control = GetPage(ID_CONTROL)
        fld_package = GetField(pg_control, FID_PACKAGE)
        fld_version = GetField(pg_control, FID_VERSION)
        fld_maint = GetField(pg_control, FID_MAINTAINER)
        fld_email = GetField(pg_control, FID_EMAIL)
        fields_control = (
            fld_package,
            fld_version,
            fld_maint,
            fld_email,
            )
        
        # Menu launcher page
        pg_launcher = GetPage(ID_MENU)
        
        # Check to make sure that all required fields have values
        required = list(fields_control)
        
        if pg_launcher.IsBuildExportable():
            task_list[u'launcher'] = pg_launcher.ExportPage()
            
            required.append(pg_launcher.ti_name)
            
            if not pg_launcher.chk_filename.GetValue():
                required.append(pg_launcher.ti_filename)
        
        for item in required:
            if TextIsEmpty(item.GetValue()):
                field_name = GT(item.GetName().title())
                page_name = pg_control.GetName()
                if item not in fields_control:
                    page_name = pg_launcher.GetName()
                
                return (dbrerrno.FEMPTY, u'{} ➜ {}'.format(page_name, field_name))
        
        # Get information from control page for default filename
        package = fld_package.GetValue()
        # Remove whitespace
        package = package.strip(u' \t')
        package = u'-'.join(package.split(u' '))
        
        version = fld_version.GetValue()
        # Remove whitespace
        version = version.strip(u' \t')
        version = u''.join(version.split())
        
        arch = GetField(pg_control, FID_ARCH).GetStringSelection()
        
        cont = False
        
        # Dialog for save destination
        ttype = GT(u'Debian packages')
        if UseCustomDialogs():
            save_dia = SaveFile(self)
            save_dia.SetFilter(u'{}|*.deb'.format(ttype))
            save_dia.SetFilename(u'{}_{}_{}.deb'.format(package, version, arch))
            if save_dia.DisplayModal():
                cont = True
                build_path = save_dia.GetPath()
                filename = save_dia.GetFilename().split(u'.deb')[0]
        
        else:
            save_dia = wx.FileDialog(self, GT(u'Save'), os.getcwd(), wx.EmptyString, u'{}|*.deb'.format(ttype),
                    wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR)
            save_dia.SetFilename(u'{}_{}_{}.deb'.format(package, version, arch))
            if save_dia.ShowModal() == wx.ID_OK:
                cont = True
                build_path = os.path.split(save_dia.GetPath())[0]
                filename = os.path.split(save_dia.GetPath())[1].split(u'.deb')[0]
        
        if not cont:
            return (dbrerrno.ECNCLD, None)
        
        # Control, menu, & build pages not added to this list
        page_checks = (
            (ID_FILES, u'files'),
            (ID_SCRIPTS, u'scripts'),
            (ID_CHANGELOG, u'changelog'),
            (ID_COPYRIGHT, u'copyright'),
            )
        
        # Install step is not added to this list
        # 'control' should be after 'md5sums'
        # 'build' should be after 'control'
        other_checks = (
            (self.chk_md5, u'md5sums'),
            (self.chk_rmstage, u'rmstage'),
            (self.chk_lint, u'lintian'),
            )
        
        prep_task_count = len(page_checks) + len(other_checks)
        
        progress = 0
        
        wx.Yield()
        prebuild_progress = ProgressDialog(GetTopWindow(), GT(u'Preparing to build'),
                maximum=prep_task_count)
        
        if wx.MAJOR_VERSION < 3:
            # Resize dialog for better fit
            pb_size = prebuild_progress.GetSizeTuple()
            pb_size = (pb_size[0]+200, pb_size[1])
            prebuild_progress.SetSize(pb_size)
            prebuild_progress.CenterOnParent()
        
        for PID, id_string in page_checks:
            wx.Yield()
            prebuild_progress.Update(progress, GT(u'Checking {}').format(id_string))
            
            wizard_page = GetPage(PID)
            if wizard_page.IsBuildExportable():
                task_list[id_string] = wizard_page.ExportPage()
            
            progress += 1
        
        for task_check, id_string in other_checks:
            wx.Yield()
            prebuild_progress.Update(progress, GT(u'Testing for: {}').format(task_check.GetLabel()))
            
            if task_check.GetValue():
                task_list[id_string] = None
            
            progress += 1
        
        # Close progress dialog
        wx.Yield()
        prebuild_progress.Update(progress)
        prebuild_progress.Destroy()
        
        return (dbrerrno.SUCCESS, (task_list, build_path, filename))
    
    
    ## TODO: Doxygen
    def GatherData(self):
        build_list = []
        
        if self.chk_md5.GetValue():
            build_list.append(u'1')
        
        else:
            build_list.append(u'0')
        
        if self.chk_rmstage.GetValue():
            build_list.append(u'1')
        
        else:
            build_list.append(u'0')
        
        if self.chk_lint.GetValue():
            build_list.append(u'1')
        
        else:
            build_list.append(u'0')
        
        return u'<<BUILD>>\n{}\n<</BUILD>>'.format(u'\n'.join(build_list))
    
    
    ## Installs the built .deb package onto the system
    #  
    #  Uses the system's package installer:
    #    gdebi if available or dpkg
    #  
    #  Shows a success dialog if installed. Otherwise shows an
    #  error dialog.
    #  \param package
    #        \b \e unicode|str : Path to package to be installed
    def InstallPackage(self, package):
        if not CMD_system_installer:
            ShowErrorDialog(
                GT(u'Cannot install package'),
                GT(u'A compatible package manager could not be found on the system'),
                __name__,
                warn=True
                )
            
            return
        
        Logger.Info(__name__, GT(u'Attempting to install package: {}').format(package))
        Logger.Info(__name__, GT(u'Installing with {}').format(CMD_system_installer))
        
        install_output = None
        install_cmd = (CMD_system_installer, package,)
        
        wx.Yield()
        if CMD_system_installer == CMD_gdebi_gui:
            install_output = subprocess.Popen(install_cmd)
        
        # Command appears to not have been executed correctly
        if install_output == None:
            ShowErrorDialog(
                GT(u'Could not install package: {}'),
                GT(u'An unknown error occurred'),
                __name__
                )
            
            return
        
        # Command executed but did not return success code
        if install_output.returncode:
            err_details = (
                GT(u'Process returned code {}').format(install_output.returncode),
                GT(u'Command executed: {}').format(u' '.join(install_cmd)),
                )
            
            ShowErrorDialog(
                GT(u'An error occurred during installation'),
                u'\n'.join(err_details),
                __name__
                )
            
            return
        
        # TODO: This code is kept for future purposes
        # Gdebi Gtk uses a GUI so no need to show a dialog of our own
        if CMD_system_installer != CMD_gdebi_gui:
            # Command executed & returned successfully
            ShowMessageDialog(
                GT(u'Package was installed to system'),
                GT(u'Success')
                )
    
    
    ## TODO: Doxygen
    def OnBuild(self, event=None):
        ret_code, build_prep = self.BuildPrep()
        
        if ret_code == dbrerrno.ECNCLD:
            return
        
        if ret_code == dbrerrno.FEMPTY:
            err_dia = wx.MessageDialog(self,
                    u'{}\n{}'.format(GT(u'One of the required fields is empty'), build_prep),
                    GT(u'Cannot Continue'), wx.OK|wx.ICON_WARNING)
            err_dia.ShowModal()
            err_dia.Destroy()
            
            return
        
        if ret_code == dbrerrno.SUCCESS:
            task_list, build_path, filename = build_prep
            
            ret_code, deb_package = self.Build(task_list, build_path, filename)
            
            # FIXME: Check .deb package timestamp to confirm build success
            if ret_code == dbrerrno.SUCCESS:
                wx.MessageDialog(self, GT(u'Package created successfully'), GT(u'Success'),
                        style=wx.OK|wx.ICON_INFORMATION).ShowModal()
                
                # Installing the package
                if FieldEnabled(self.chk_install) and self.chk_install.GetValue():
                    self.InstallPackage(deb_package)
                
                return
            
            wx.MessageDialog(self, GT(u'Package build failed'), GT(u'Error'),
                    style=wx.OK|wx.ICON_ERROR).ShowModal()
    
    
    ## TODO: Doxygen
    def ResetAllFields(self):
        self.chk_install.SetValue(False)
        # chk_md5 should be reset no matter
        self.chk_md5.SetValue(False)
        if CMD_md5sum:
            self.chk_md5.Enable()
        
        else:
            self.chk_md5.Disable()
        
        self.chk_rmstage.SetValue(True)
        if CMD_lintian:
            self.chk_lint.Enable()
            self.chk_lint.SetValue(True)
        
        else:
            self.chk_lint.Disable()
            self.chk_lint.SetValue(False)
    
    
    ## TODO: Doxygen
    def SetFieldData(self, data):
        self.ResetAllFields()
        build_data = data.split(u'\n')
        if CMD_md5sum:
            self.chk_md5.SetValue(int(build_data[0]))
        
        self.chk_rmstage.SetValue(int(build_data[1]))
        if CMD_lintian:
            self.chk_lint.SetValue(int(build_data[2]))
    
    
    ## TODO: Doxygen
    def SetSummary(self, event=None):
        main_window = wx.GetApp().GetTopWindow()
        
        # Make sure the page is not destroyed so no error is thrown
        if self:
            # Set summary when "Build" page is shown
            # Get the file count
            files_total = main_window.page_files.dest_area.GetItemCount()
            f = GT(u'File Count')
            file_count = u'{}: {}'.format(f, files_total)
            # Scripts to make
            scripts_to_make = []
            scripts = ((u'preinst', main_window.page_scripts.chk_preinst),
                (u'postinst', main_window.page_scripts.chk_postinst),
                (u'prerm', main_window.page_scripts.chk_prerm),
                (u'postrm', main_window.page_scripts.chk_postrm))
            
            for script in scripts:
                if script[1].IsChecked():
                    scripts_to_make.append(script[0])
            
            s = GT(u'Scripts')
            if len(scripts_to_make):
                scripts_to_make = u'{}: {}'.format(s, u', '.join(scripts_to_make))
            
            else:
                scripts_to_make = u'{}: 0'.format(s)
            
            self.summary.SetValue(u'\n'.join((file_count, scripts_to_make)))
