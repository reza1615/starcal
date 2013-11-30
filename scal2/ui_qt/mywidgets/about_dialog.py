# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2012 Saeed Rasooli <saeed.gnu@gmail.com>
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

from scal2.utils import toUnicode
from scal2.locale_man import tr as _

from scal2 import core

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

class AboutDialog(qt.QWidget):
    def __init__(self):
        qt.QWidget.__init__(self)
        self.name = ''
        self.version = ''
        self.credits = {}
        self.license = ''
        self.wrap_license = False
        self.website = ''
        self.logo = ''
        ##################
        #self.setAttribute(qc.Qt.WA_DeleteOnClose)
    def set_name(self, name):
        self.name = name
        #if is_visible()
        #self.update
    def set_version(self, version):
        self.version = toUnicode(version)
    def set_title(self, title):
        self.setWindowTitle(toUnicode(title))
    def set_authors(self, authors):
        self.credits[_('Written by')] = [toUnicode(a) for a in authors]
    def set_documenters(documenters):
        self.credits[_('Documented by')] = [toUnicode(a) for a in documenters]
    def set_artists(artists):
        self.credits[_('Translated by')] = [toUnicode(a) for a in artists]
    def set_comments(self, comments):
        self.comments = toUnicode(comments)
    def set_license(self, license):
        self.license = toUnicode(license)
    def set_wrap_license(self, wrap_license):
        self.wrap_license = wrap_license
    def set_website(self, website):
        self.website = website
    def set_logo(self, logo):
        self.logo = toUnicode(logo)
        self.setWindowIcon(qt.QIcon(logo))
    def make_dialog(self):
        vbox = qt.QVBoxLayout()
        vbox.setMargin(15)
        if self.logo:
            label = qt.QLabel()
            label.setPixmap(qt.QPixmap(self.logo))
            label.setAlignment(qc.Qt.AlignHCenter)
            vbox.addWidget(label, qc.Qt.AlignHCenter)
        if self.name or self.version:
            label = qt.QLabel(u'<span style="font-weight:bold;font-size:x-large;">%s %s</span>'%(self.name, self.version))
            label.setTextInteractionFlags(qc.Qt.TextSelectableByMouse | qc.Qt.TextSelectableByKeyboard)
            label.setAlignment(qc.Qt.AlignHCenter)
            label.setLayoutDirection(qc.Qt.LeftToRight)
            vbox.addWidget(label, qc.Qt.AlignHCenter)
        if self.comments:
            label = qt.QLabel(self.comments)
            label.setTextInteractionFlags(qc.Qt.TextSelectableByMouse | qc.Qt.TextSelectableByKeyboard)
            label.setAlignment(qc.Qt.AlignHCenter)
            vbox.addWidget(label, qc.Qt.AlignHCenter)
        if self.website:
            label = qt.QLabel('<a href="%s">%s</a>'%(self.website,self.website))
            label.setTextInteractionFlags(qc.Qt.LinksAccessibleByMouse | qc.Qt.LinksAccessibleByKeyboard)
            label.setAlignment(qc.Qt.AlignHCenter)
            label.setLayoutDirection(qc.Qt.LeftToRight)
            self.connect(label, qc.SIGNAL('linkActivated(const QString&)'), core.openUrl)
            vbox.addWidget(label, qc.Qt.AlignHCenter)
        bbox = qt.QHBoxLayout()
        bbox.setMargin(0)
        if len(self.credits)>0:
            win = qt.QDialog(self)
            self.winCred = win
            tabw = qt.QTabWidget(self)
            for (key, value) in self.credits.items():
                tb = qt.QTextBrowser(win)
                tb.setText('\n'.join(value))
                tabw.addTab(tb, key)
            closeBtn = qt.QPushButton(_('_Close'))
            self.connect(closeBtn, qc.SIGNAL('clicked()'), lambda: self.winCred.close())
            vboxWin = qt.QVBoxLayout()
            vboxWin.setMargin(0)
            bboxWin = qt.QHBoxLayout()
            bboxWin.setMargin(0)
            vboxWin.addWidget(tabw)
            bboxWin.addStretch()
            bboxWin.addWidget(closeBtn)
            vboxWin.addLayout(bboxWin)
            win.setLayout(vboxWin)
            ###############
            creditsBtn = qt.QPushButton(_('C_redits'))
            self.connect(creditsBtn, qc.SIGNAL('clicked()'), lambda: self.winCred.show())
            bbox.addWidget(creditsBtn)
        if self.license:
            win = qt.QDialog(self)
            self.winLic = win
            tb = qt.QTextBrowser(win)
            tb.setText(self.license)
            #tb.setLineWrapMode(qt.QTextEdit.WidgetWidth)
            #tb.setLineWrapColumnOrWidth(200)
            closeBtn = qt.QPushButton(_('_Close'))
            self.connect(closeBtn, qc.SIGNAL('clicked()'), lambda: self.winLic.close())
            vboxWin = qt.QVBoxLayout()
            vboxWin.setMargin(0)
            bboxWin = qt.QHBoxLayout()
            bboxWin.setMargin(0)
            vboxWin.addWidget(tb)
            bboxWin.addStretch()
            bboxWin.addWidget(closeBtn)
            vboxWin.addLayout(bboxWin)
            win.setLayout(vboxWin)
            met = tb.fontMetrics()
            win.resize(met.averageCharWidth()*60, met.height()*20)
            ###############
            licenseBtn = qt.QPushButton(_('_License'))
            self.connect(licenseBtn, qc.SIGNAL('clicked()'), lambda: self.winLic.show())
            bbox.addWidget(licenseBtn)
        bbox.addStretch()
        closeBtn = qt.QPushButton(_('_Close'))
        self.connect(closeBtn, qc.SIGNAL('clicked()'), lambda: self.close())
        bbox.addWidget(closeBtn)
        vbox.addLayout(bbox)
        ############################
        #vbox.setAlignment(qc.Qt.AlignHCenter)
        self.setLayout(vbox)
    def show(self):
        print('show()')
        self.make_dialog()
        qt.QWidget.show(self)
    def close(self):##????????????
        self.hide()
    #def exec_(self):
    #    print 'exec_'
    #    self.make_dialog()
    #    qt.QDialog.exec_(self)

