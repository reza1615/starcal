# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
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

#import time
#print time.time(), __file__

import os, sys

from scal2.locale_man import tr as _

from scal2 import core
from scal2.core import convert, getMonthName, getMonthLen

from scal2 import ui

from scal2.ui_qt.mywidgets.multi_spin_box import DateBox

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc


import gettext


def calcTextWidth(text, widget):
    n = len(text)
    met = widget.fontMetrics() ## OR met = widget.fontMetrics()
    w = 0
    for i in range(n):
        w += met.charWidth(text, i)
    return w


def newFixedLabel(text):
    label = qt.QLabel(text)
    label.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
    label.setFixedWidth(calcTextWidth(text, label))## *1.5 was needed for older Qt4 versions
    return label


class SelectDateDialog(qt.QWidget):
    def __init__(self):
        qt.QWidget.__init__(self)
        self.setWindowTitle(_('Select Date...'))
        self.vbox = qt.QVBoxLayout()
        #self.connect('delete-event', self.hideMe)
        ###### Reciving dropped day!
        self.setAcceptDrops(True)
        ######
        hbox = qt.QHBoxLayout()
        hbox.addWidget(newFixedLabel(_('Date Mode')))
        combo = qt.QComboBox()
        for m in core.modules:
            combo.addItem(_(m.desc))
        self.mode = core.primaryMode
        combo.setCurrentIndex(self.mode)
        self.connect(combo, qc.SIGNAL('currentIndexChanged(int)'), self.comboModeChanged)
        hbox.addWidget(combo)
        self.comboMode = combo
        self.vbox.addLayout(hbox)
        #######################
        hbox = qt.QHBoxLayout()
        wlist = []

        radio = qt.QRadioButton('', self)
        radio.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        radio.setChecked(True)
        self.connect(radio, qc.SIGNAL('clicked()'), self.radioChanged)
        hbox.addWidget(radio)
        self.radio1 = radio

        label = newFixedLabel(_('Year'))
        hbox.addWidget(label)
        wlist.append(label)

        spin = qt.QSpinBox()
        spin.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        spin.setRange(0, 10000)
        spin.setSingleStep(1) ## ??????????
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        self.connect(spin, qc.SIGNAL('changed()'), self.comboMonthChanged)
        hbox.addWidget(spin)
        wlist.append(spin)
        self.spinY = spin

        label = newFixedLabel(_('Month'))
        hbox.addWidget(label)
        wlist.append(label)
        combo = qt.QComboBox()
        module = core.modules[core.primaryMode]
        for i in xrange(12):
            combo.addItem(_(module.getMonthName(i+1, None)))## year=None means all months
        combo.setCurrentIndex(0)
        self.connect(combo, qc.SIGNAL('currentIndexChanged(int)'), self.comboMonthChanged)
        hbox.addWidget(combo)
        self.comboMonth = combo
        wlist.append(combo)

        label = newFixedLabel(_('Day'))
        hbox.addWidget(label)
        wlist.append(label)
        spin = qt.QSpinBox()
        spin.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        spin.setRange(1, 31)
        spin.setSingleStep(1) ## ??????????
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        hbox.addWidget(spin)
        self.spinD = spin
        wlist.append(spin)
        ###
        self.vbox.addLayout(hbox)
        self.wlist1 = wlist
        ########
        hbox = qt.QHBoxLayout()
        wlist = []
        ###
        radio = qt.QRadioButton('', self)
        radio.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(radio)
        self.connect(radio, qc.SIGNAL('clicked()'), self.radioChanged)
        self.radio2 = radio
        ###
        label = newFixedLabel('yyyy/mm/dd')
        hbox.addWidget(label)
        wlist.append(label)
        ###
        dateInput = DateBox() # hist_size=16
        ##self.connect(dateInput, qc.SIGNAL('editingFinished()'), self.ok)
        hbox.addWidget(dateInput)
        wlist.append(dateInput)
        self.dateInput = dateInput
        ###
        hbox.addStretch()
        ###
        self.vbox.addLayout(hbox)
        self.wlist2 = wlist
        #######
        bbox = qt.QDialogButtonBox(self)
        canB = bbox.addButton(qt.QDialogButtonBox.Cancel)
        okB = bbox.addButton(qt.QDialogButtonBox.Ok)
        self.connect(bbox, qc.SIGNAL('rejected()'), self.hide)
        self.connect(bbox, qc.SIGNAL('accepted()'), self.ok)
        """if ui.autoLocale:
            okB.set_label(_('_OK'))
            okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
            canB.set_label(_('_Cancel'))
            canB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL,gtk.ICON_SIZE_BUTTON))"""
        self.vbox.addWidget(bbox)
        #######
        #okB.connect('clicked', self.ok)
        #canB.connect('clicked', lambda: self.hide())
        self.radioChanged()
        #######
        self.setLayout(self.vbox)
    def dragRec(self, obj, context, x, y, selection, target_id, etime):
        text = selection.get_text()
        if text==None:
            return
        date = ui.parseDroppedDate(text)
        if date==None:
            print 'selectDateDialog: dropped text "%s"'%text
            return
        print 'selectDateDialog: dropped date: %d/%d/%d'%date
        mode = self.comboMode.currentIndex()
        if mode!=ui.dragGetMode:
            date = convert(date[0], date[1], date[2], ui.dragGetMode, mode)
        y, m, d = date
        self.spinY.setValue(y)
        self.comboMonth.setCurrentIndex(m-1)
        self.spinD.setValue(d)
        self.dateInput.setDate(y, m, d)
        #self.dateInput.addHistory()
        return True
    def show(self):
        ## Show a window that ask the date and set on the calendar
        mode = core.primaryMode
        y, m, d = ui.cell.dates[mode]
        self.setMode(mode)
        self.set(y, m, d)
        qt.QWidget.show(self)
    def closeEvent(self, event):
        self.hide()
        event.ignore()
    def set(self, y, m, d):
        self.spinY.setValue(y)
        self.comboMonth.setCurrentIndex(m-1)
        self.spinD.setValue(d)
        self.dateInput.setDate(y, m, d)
        #self.dateInput.addHistory()
    def setMode(self, mode):
        self.mode = mode
        module = core.modules[mode]
        combo = self.comboMonth
        combo.clear()
        for i in xrange(12):
            combo.addItem(_(module.getMonthName(i+1)))
        self.comboMode.setCurrentIndex(mode)
        self.spinD.setRange(1, core.modules[mode].maxMonthLen)
        self.dateInput.maxs = (9999, 12, module.maxMonthLen)
    def comboModeChanged(self, mode):
        #print 'comboModeChanged, index="%s"'%index
        pMode = self.mode
        pDate = self.get()
        module = core.modules[mode]
        if pDate==None:
            y, m, d = ui.cell.dates[mode]
        else:
            y0, m0, d0 = pDate
            y, m, d = convert(y0, m0, d0, pMode, mode)
        combo = self.comboMonth
        self.disconnect(combo, qc.SIGNAL('currentIndexChanged(int)'), self.comboMonthChanged)
        combo.clear()
        for i in xrange(12):
            combo.addItem(_(module.getMonthName(i+1, y)))
        self.connect(combo, qc.SIGNAL('currentIndexChanged(int)'), self.comboMonthChanged)
        self.spinD.setRange(1, module.maxMonthLen)
        self.dateInput.maxs = (9999, 12, module.maxMonthLen)
        self.set(y, m, d)
        self.mode = mode
    def comboMonthChanged(self, index=None):
        self.spinD.setRange(1, getMonthLen(
            int(self.spinY.value()),
            self.comboMonth.currentIndex() + 1,
            self.mode,
        ))
    def get(self):
        mode = self.comboMode.currentIndex()
        if self.radio1.isChecked():
            y0 = int(self.spinY.value())
            m0 = self.comboMonth.currentIndex() + 1
            d0 = int(self.spinD.value())
            return (y0, m0, d0)
        else:#elif self.radio2.isChecked():
            return self.dateInput.getDate()
        #else:
        #    return None
    def ok(self):
        mode = self.comboMode.currentIndex()
        if mode==None:
            return
        get = self.get()
        if get==None:
            return
        y0, m0, d0 = get
        if mode==core.primaryMode:
            y, m, d = (y0, m0, d0)
        else:
            y, m, d = convert(y0, m0, d0, mode, core.primaryMode)
        if not core.validDate(mode, y, m, d):
            print 'bad date: %s'%dateStr(mode, y, m, d)
            return
        self.emit(qc.SIGNAL('response-date'), y, m, d)
        self.hide()
        #self.dateInput.addHistory((y0, m0, d0))
        ##self.dateInput.addHistory((y, m, d))
    def radioChanged(self, widget=None):
        if self.radio1.isChecked():
            for w in self.wlist1:
                w.setEnabled(True)
            for w in self.wlist2:
                w.setEnabled(False)
        else:
            for w in self.wlist1:
                w.setEnabled(False)
            for w in self.wlist2:
                w.setEnabled(True)

'''
if __name__=='__main__':
    import time
    from scal2.locale_man import rtl
    app = qt.QApplication(sys.argv)
    if rtl:
        app.setLayoutDirection(qc.Qt.RightToLeft)
    dialog = SelectDateDialog()
    def response(year, month, day):
        print '%d/%d/%d\n'%(year, month, day)
        dialog.destroy()
        sys.exit(0)
    dialog.connect(dialog, qc.SIGNAL('response-date'), response)
    dialog.show(0, *time.localtime()[:3])
    sys.exit(app.exec_())
'''

