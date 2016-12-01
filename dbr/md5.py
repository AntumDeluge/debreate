# -*- coding: utf-8 -*-

# Writing the md5sums file


import commands, os

from dbr.dialogs            import ErrorDialog
from dbr.language           import GT
from dbr.log                import Logger
from globals.commands       import CMD_md5sum
from globals.wizardhelper   import GetTopWindow


# FIXME: This module uses the following deprecated modules
# - commands


## Object for creating MD5 hashes
#  
#  \param control
#        \b \e wx.CheckBox : Translated label of this control is used for error dialog
class MD5Hasher:
    def __init__(self, control):
        self.md5_box_name = control.GetLabel()
    
    
    ## TODO: Doxygen
    def IsExecutable(self, filename):
        # Find out if the file is an executable
        executable = os.access(filename, os.X_OK) #another python version
        
        return bool(executable)
    
    
    ## TODO: Doxygen
    def WriteMd5(self, builddir, tempdir, parent=None):
        # Show an error if the 'md5sum' command does not exist
        # This is only a failsafe & should never happen
        if not CMD_md5sum:
            if not parent:
                parent = GetTopWindow()
            
            err_msg1 = GT(u'The "md5sum" command was not found on the system.')
            err_msg2 = GT(u'Uncheck the "{}" box.').format(self.md5_box_name)
            err_msg3 = GT(u'Please report this error to one of the following addresses:')
            err_url1 = u'https://github.com/AntumDeluge/debreate/issues'
            err_url2 = u'https://sourceforge.net/p/debreate/bugs/'
            
            Logger.Error(__name__,
                    u'{} {} {}\n\t{}\n\t{}'.format(err_msg1, err_msg2, err_msg3, err_url1, err_url2))
            
            md5_error = ErrorDialog(parent, u'{}\n{}\n\n{}'.format(err_msg1, err_msg2, err_msg3))
            md5_error.AddURL(err_url1)
            md5_error.AddURL(err_url2)
            md5_error.ShowModal()
            
            return False
        
        tempdir = tempdir.encode(u'utf-8')
        os.chdir(builddir)
        
        temp_list = []
        md5_list = [] # Final list used to write the md5sum file
        for ROOT, DIRS, FILES in os.walk(tempdir):
            for F in FILES:
                F = u'{}/{}'.format(ROOT, F)
                md5 = commands.getoutput((u'{} -t "{}"'.format(CMD_md5sum, F)))
                temp_list.append(md5)
        
        for item in temp_list:
            # Remove [tempdir] from the path name in the md5sum so that it has a
            # true unix path
            # e.g., instead of "/myfolder_temp/usr/local/bin", "/usr/local/bin"
            sum_split = item.split(u'{}/'.format(tempdir))
            sum_join = u''.join(sum_split)
            md5_list.append(sum_join)
        
        # Create the md5sums file in the "DEBIAN" directory
        FILE_BUFFER = open(u'{}/DEBIAN/md5sums'.format(tempdir), u'w')
        FILE_BUFFER.write(u'{}\n'.format(u'\n'.join(md5_list)))
        FILE_BUFFER.close()
        
        return True
