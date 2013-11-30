# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com>
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

import os, sys

from scal2.locale_man import tr as _

from scal2 import core
from scal2.core import deskDir

from scal2 import ui
from scal2.monthcal import getMonthStatus, getCurrentMonthStatus
from scal2.export import exportToHtml

from scal2.ui_qt.mywidgets import HBox, VBox
from scal2.ui_qt.mywidgets.multi_spin_box import YearMonthBox


from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc



class ExportDialog(qt.QFileDialog):
    def __init__(self, mainWin):
        self.mainWin = mainWin
        self.mcal = mainWin.mcal
        qt.QFileDialog.__init__(self)
        self.setAcceptMode(qt.QFileDialog.AcceptSave)
        self.setFileMode(qt.QFileDialog.AnyFile)## FIXME
        self.setOption(qt.QFileDialog.HideNameFilterDetails)
        self.setWindowTitle(_('Export to %s')%'HTML')
        self.vbox = VBox()
        ########
        hbox = HBox()
        hbox.addWidget(qt.QLabel(_('Month Range')))
        combo = qt.QComboBox()
        for t in ('Current Month', 'Whole Current Year', 'Custom'):
            combo.addItem(_(t))
        hbox.addWidget(combo)
        hbox.addWidget(qt.QLabel(''))
        self.combo = combo
        ###
        hbox2 = HBox()
        hbox2.addWidget(qt.QLabel(_('from month')))
        self.ymBox0 = YearMonthBox()
        hbox2.addWidget(self.ymBox0)
        hbox2.addWidget(qt.QLabel(''))
        hbox2.addWidget(qt.QLabel(_('to month')))
        self.ymBox1 = YearMonthBox()
        hbox2.addWidget(self.ymBox1)
        hbox.addWidget(hbox2)
        self.hbox2 = hbox2
        combo.setCurrentIndex(0)
        self.vbox.addWidget(hbox)
        ########
        self.layout().addWidget(self.vbox, 4, 0, 5, 2)## between rows 4 and 5, between columns 0 and 2 (before buttons)
        ########
        self.connect(combo, qc.SIGNAL('currentIndexChanged (int)'), self.comboChanged)
        self.connect(self, qc.SIGNAL('fileSelected (const QString&)'), self.save)
        try:
            self.setDirectory(deskDir)
        except:## FIXME
            pass
    def comboChanged(self, index=None, ym=None):
        if index is None:
            index = self.combo.currentIndex()
        if ym==None:
            ym = (ui.cell.year, ui.cell.month)
        if index==0:
            filename = 'calendar-%.4d-%.2d.html'%ym
            self.hbox2.hide()
        elif index==1:
            #self.fcw.set_current_name('calendar-%.4d.html'%ym[0])
            filename = 'calendar-%.4d.html'%ym[0]
            self.hbox2.hide()
        else:#elif index==2
            filename = 'calendar.html'
            self.hbox2.show()
        #self.fcw.set_current_name(filename)
        self.selectFile(filename)## FIXME
        ## select_region(0, -4) ## FIXME
    def closeEvent(self, event):
        self.hide()
        event.ignore()
    def done(self, i):
        self.hide()
    def save(self, path):
        print('save', path)
        self.setCursor(qc.Qt.WaitCursor)
        #while gtk.events_pending():## FIXME
        #    gtk.main_iteration_do(False)
        if path in (None, ''):
            return
        print('Exporting to html file "%s"'%path)
        i = self.combo.currentIndex()
        months = []
        module = core.modules[core.primaryMode]
        if i==0:
            s = getCurrentMonthStatus()
            months = [s]
            title = '%s %s'%(core.getMonthName(core.primaryMode, s.month, s.year), _(s.year))
        elif i==1:
            for i in xrange(1, 13):
                months.append(getMonthStatus(ui.cell.year, i))
            title = '%s %s'%(_('Calendar'), _(ui.cell.year))
        elif i==2:
            y0, m0 = self.ymBox0.getYM()
            y1, m1 = self.ymBox1.getYM()
            for ym in xrange(y0*12+m0-1, y1*12+m1):
                y, m = divmod(ym, 12)
                m += 1
                months.append(getMonthStatus(y, m))
            title = _('Calendar')
        exportToHtml(path, months, title)
        self.setCursor(qc.Qt.ArrowCursor)
        self.hide()
    def showDialog(self, year, month):
        self.comboChanged(ym=(year, month))
        self.ymBox0.setYM(year, month)
        self.ymBox1.setYM(year, month)
        self.resize(700, 400)
        self.show()## raise_()




