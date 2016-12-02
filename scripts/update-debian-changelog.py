#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os, sys, errno, time

from scripts_globals import debian_files, GetInfoValue


# Ubuntu release
DIST = GetInfoValue('DIST')
URGENCY = GetInfoValue('URGENCY')
AUTHOR = GetInfoValue('AUTHOR')
EMAIL = GetInfoValue('EMAIL')

# Reading source log
if not os.path.isfile(debian_files['changelog']):
    print('ERROR: Source changelog does not exist, can\'t continue: {}'.format(debian_files['changelog']))
    
    sys.exit(errno.ENOENT)

TEMP = open(debian_files['changelog'], 'r')
changelog_data = TEMP.read().split('\n')
TEMP.close()

# Extract version number
version_string = changelog_data[0]

# Check for same version entry
entry_exists = False
TEMP = open(debian_files['changelog debian'], 'r')
if ' ({})'.format(version_string) in TEMP.read():
    entry_exists = True
TEMP.close()

if entry_exists:
    print('There is already an entry for version {}, exiting ...'.format(version_string))
    sys.exit(0)

cutoff_index = 0
for L in changelog_data:
    if not L.strip():
        # Reached a new segment
        cutoff_index = changelog_data.index(L)
        break

version_data = changelog_data[:cutoff_index]

# Format new entry
version_data[0] = 'debreate ({}) {}; urgency={}'.format(version_string, DIST, URGENCY)

for L in version_data:
    if L.startswith('- '):
        version_data[changelog_data.index(L)] = '    {}'.format(L[2:]).rstrip(' \t')
        continue
    
    # Preserve formatting/indentation of other lines (must begin with '- ', '* ', or '+ ')
    if L.strip(' \t')[:2] in ('- ', '* ', '+ '):
        version_data[changelog_data.index(L)] = '  {}'.format(L).rstrip(' \t')

# Add an asterix to first listed change
version_data[1] = version_data[1].replace('    ', '  * ')

version_data.insert(1, '')
version_data.append('')
version_data.append(' -- {} <{}>  {}'.format(AUTHOR, EMAIL, time.strftime('%a, %d %b %Y %H:%M:%S %z')))

version_data = '\n'.join(version_data)

print('Writing new changelog entry:\n\n{}'.format(version_data))

if os.path.isfile(debian_files['changelog debian']):
    TEMP = open(debian_files['changelog debian'], 'r')
    version_data = '{}\n\n\n{}'.format(version_data, TEMP.read())
    TEMP.close()

TEMP = open(debian_files['changelog debian'], 'w')
TEMP.write(version_data)
TEMP.close()
