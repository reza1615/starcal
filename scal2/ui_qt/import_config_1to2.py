#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Saeed Rasooli <saeed.gnu@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Also avalable in /usr/share/common-licenses/GPL on Debian systems
# or /usr/share/licenses/common/GPL3/license.txt on ArchLinux


APP_DESC = 'StarCalendar'

import os, sys, shutil
from os.path import dirname
from os.path import join, isfile, isdir, exists

from scal2.path import *
from scal2.import_config_1to2 import importConfigFrom15, getOldVersion, langDir, langConfDir

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc
from scal2.ui_qt.mywidgets import HBox, VBox

app = qt.QApplication(sys.argv)


langNameList = []
langCodeList = []

langDefaultCode = ''

win = qt.QDialog()
win.setWindowTitle(APP_DESC+' - First Run')

win.setWindowIcon(qt.QIcon('%s/starcal2.png'%pixDir))
vboxL = qt.QVBoxLayout()
vboxL.setMargin(0)
win.setLayout(vboxL)

langHbox = HBox()
langHbox.addWidget(qt.QLabel('Select Language:'))


importCheckb = None
oldVersion = getOldVersion()
if oldVersion and '1.5.0' < oldVersion < '1.6.0':## FIXME
    importCheckb = qt.QCheckBox('Import configurations from %s %s'%(APP_DESC, oldVersion))
    importCheckb.connect(importCheckb, qc.SIGNAL('stateChanged (int)'), lambda state: langHbox.setEnabled(state!=qc.Qt.Checked))
    importCheckb.setCheckState(qc.Qt.Checked)
    vboxL.addWidget(importCheckb)


langCombo = qt.QComboBox()
for fname in os.listdir(langDir):
    fpath = join(langDir, fname)
    if not os.path.isfile(fpath):
        continue
    text = open(fpath).read().strip()
    if fname=='default':
        langDefaultCode = text
        continue
    langName = text.split('\n')[0]
    langNameList.append(langName)
    langCodeList.append(fname)

    langCombo.addItem(langName)

if langDefaultCode and (langDefaultCode in langCodeList):
    langCombo.setCurrentIndex(langCodeList.index(langDefaultCode))
else:
    langCombo.setCurrentIndex(0)

langHbox.addWidget(langCombo)
vboxL.addWidget(langHbox)


def accepted():
    if importCheckb and importCheckb.checkState()==qc.Qt.Checked:
        importConfigFrom15()
    else:
        i = langCombo.currentIndex()
        langCode = langCodeList[i]
        thisLangConfDir = join(langConfDir, langCode)
        #print('Setting language', langCode)
        if not os.path.isdir(confDir):
            os.mkdir(confDir, 0755)
        if os.path.isdir(thisLangConfDir):
            for fname in os.listdir(thisLangConfDir):
                src_path = join(thisLangConfDir, fname)
                dst_path = join(confDir, fname)
                if isdir(dst_path):
                    shutil.rmtree(dst_path)
                elif isfile(dst_path):
                    os.remove(dst_path)
                if isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy(src_path, dst_path)
        else:
            open(join(confDir, 'locale.conf'), 'w').write('lang=%r'%langCode)
    win.close()

bbox = qt.QDialogButtonBox(win)
canB = bbox.addButton(qt.QDialogButtonBox.Cancel)
okB = bbox.addButton(qt.QDialogButtonBox.Ok)
win.connect(bbox, qc.SIGNAL('rejected()'), lambda: win.close())
win.connect(bbox, qc.SIGNAL('accepted()'), accepted)
'''
okB.set_label(_('_OK'))
okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
canB.set_label(_('_Cancel'))
canB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL,gtk.ICON_SIZE_BUTTON))
'''
vboxL.addWidget(bbox)

win.exec_()

if not os.path.isdir(confDir):
    os.mkdir(confDir, 0755)

