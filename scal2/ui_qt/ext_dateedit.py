# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/lgpl.txt>.
# Also avalable in /usr/share/common-licenses/LGPL on Debian systems
# or /usr/share/licenses/common/LGPL/license.txt on ArchLinux


import sys, os
from time import time, localtime

from math import ceil
iceil = lambda f: int(ceil(f))

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

from scal2.ui_qt.mywidgets.multi_spin_box import DateBox
from scal2.ui_qt.simplecal import SimpleCal

qloc = qc.QLocale()
qloc.setNumberOptions(qc.QLocale.OmitGroupSeparator)

def getAbsPos(widget):## Gets the absolute position of a widget in the screen
  p = widget.mapToGlobal(qc.QPoint(0,0))
  return (p.x(), p.y())

def getScreenSize():## Gets size(resolution) of screen
  geo = qt.QApplication.desktop().screenGeometry()
  return (geo.width(), geo.height())

class ExtDateEdit(qt.QWidget):
  '''
  Extended Date Edit: A high-level widget for user to input a date(in Jalali, Gregorian or Islamic)
  '''
  def __init__(self, parent=None):
    '''
    Initialize the widget
    @param parent=None: parent widget
    '''
    qt.QWidget.__init__(self, parent)
    #super(self.__class__, self).__init__(parent)## if no class will be derived from this widget
    self.datebox = DateBox()
    self.datebox.setParent(self)
    ####
    hbox = qt.QHBoxLayout()
    hbox.setContentsMargins(0, 0, 0, 0) ## left, top, right, bottom
    hbox.addWidget(self.datebox)
    self.popupButton = qt.QPushButton(self)
    self.popupButton.setParent(self)
    #self.popupButton.setCheckable(True) ## like GtkToggleButtton
    self.popupButton.setText('...') ## setIcon ????????
    #self.popupButton.connect(self.popupButton, qc.SIGNAL('toggled(bool)'), self._popupToggled)
    self.popupButton.connect(self.popupButton, qc.SIGNAL('clicked()'), self._popupClicked)
    #self.popupButton.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
    self.popupButton.setFixedWidth(20)
    hbox.addWidget(self.popupButton)
    self.setLayout(hbox)
    ####
    self.popup = qt.QFrame(self, qc.Qt.Popup | qc.Qt.Window)
    self.scal = SimpleCal(self.popup)
    self.selectToday()
    #self.scal.connect(self.scal, qc.SIGNAL('dayChange(int, int, int)'), self._calDayChange)
    self.scal.connect(self.scal, qc.SIGNAL('dayChange'), self._calDayChange)
  def _popupToggled(self, checked):
    'private, should not call by the programmer'
    if checked:
      x0, y0 = getAbsPos(self.popupButton)
      x = x0 + self.popupButton.width() - self.scal.width()
      y = y0 + self.popupButton.height()
      self.popup.move(x, y)
      self.popup.show()
    else:
      self.popup.hide()
    return False
  def _popupClicked(self):
    'private, should not call by the programmer'
    if self.popup.isVisible():
      self.popup.hide()
    else:
      self.scal.setDate(*self.datebox.getDate())
      x0, y0 = getAbsPos(self.popupButton)
      if x0<0:
        x0 = 0
      if y0<0:
        y0 = 0
      calW = self.scal.width()
      if self.layoutDirection()==qc.Qt.RightToLeft:
        x = min(getScreenSize()[0]-1, x0+calW) - calW
      else:
        x = max(0, x0 + self.popupButton.width() - calW)
      y = y0 + self.popupButton.height()
      self.popup.move(x, y)
      self.popup.show()
  def _calDayChange(self):#, year, month, day):
    'private, should not call by the programmer'
    self.datebox.setDate(*self.scal.getDate())
    #self.datebox.setDate(year, month, day)
    self.popup.hide()
  def getDate(self):
    '''
    get date that is entered in the Entry (LineEdit)
    @return: a tuple of (year, month, day)
    '''
    self.datebox.getDate()
  def setDate(self, year, month, day):
    '''
    set date to the Entry (LineEdit) and SimpleCal (popup) widget
    @param year:
    @param month:
    @param day:
    @return: None
    '''
    self.datebox.setDate((year, month, day))
    self.scal.setDate(year, month, day)
  def selectToday(self):
    'select today in the Entry (LineEdit) and SimpleCal (popup) widget'
    self.scal.selectToday()
    self.datebox.setDate(*self.scal.getDate())

if __name__=='__main__':
  app = qt.QApplication(sys.argv)
  app.setLayoutDirection(qc.Qt.RightToLeft)
  w = ExtDateEdit()
  w.show()
  sys.exit(app.exec_())


