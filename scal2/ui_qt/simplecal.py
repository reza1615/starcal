# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Saeed Rasooli <saeed.gnu@gmail.com>
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


from scal2.locale_man import tr as _

from scal2 import core

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

qloc = qc.QLocale()
qloc.setNumberOptions(qc.QLocale.OmitGroupSeparator)


class Cell:## status and information of a cell
  def __init__(self):
    self.date = None ## (year, month, day)
    self.gray = 0
    self.holiday = False

class MonthStatus(list):
  def __init__(self):
    list.__init__(self)

class SimpleCal(qt.QWidget):
  '''
  A simple month browser calendar
  signals: dayChange
  '''
  calW = 320
  calH = 250
  leftMargin = 30
  topMargin = 30
  ###
  bgColor = qt.QColor(255, 255, 255, 255)
  borderTextColor = qt.QColor(0, 140, 0, 255)
  ###
  normDayColor = qt.QColor(0, 0, 0, 255)
  inactiveDayColor = qt.QColor(0, 0, 0, 100)
  holidayColor = qt.QColor(200, 0, 0, 255)
  #todayColor = ##??????????
  ###
  cursorBgColor = qt.QColor(255, 0, 0, 255) ## OR None
  cursorInColor = qt.QColor(255, 255, 255, 255) ## OR None
  cursorD = 5
  cursorR = 0
  ##############
  holidayWeekDays = [5] ## 5 means Friday (0 means Sunday)
  maxCache = 5
  weekSyn = True
  def _rtl(self):
    if self.layoutDirection()==qc.Qt.RightToLeft:
      return 1
    else:## elif d==qc.Qt.LeftToRight:
      return 0
  def _rtlSgn(self):
    if self.layoutDirection()==qc.Qt.RightToLeft:
      return 1
    else:## elif d==qc.Qt.LeftToRight:
      return -1
  ########################################################################
  def weekNumber(self, year, month, day):## week number in year
    first = core.getWeekDay(year, 1, 1) - core.firstWeekDay - 1
    return (core.datesDiff(year, 1, 1, year, month, day) + first%7) / 7 + 1
  def getWeekDayName(self, i):
    if self.weekSyn:
      return core.weekDayNameAb[(i+core.firstWeekDay)%7]
    else:
      return core.weekDayName[(i+core.firstWeekDay)%7]
  ########################################################################
  def buildStatus(self, year, month, addCache=True):
    #print 'Building cache (%s, %s)'%(year, month)
    s = MonthStatus()#s = []
    s.year = year
    s.month = month
    pyear = year
    pmonth = month -1
    if pmonth <= 0 :
      pmonth =12
      pyear -=1
    prevMonthLen = core.getMonthLen(pyear, pmonth, self.mode)
    currentMonthLen = core.getMonthLen(year, month, self.mode)
    s.monthLen = currentMonthLen
    #####################
    s.weekNum = [self.weekNumber(year, month, 1+7*i) for i in xrange(6)]
    offset = core.getWeekDay(year, month, 1)
    if offset==0:
      ###### Which Method ????????????????????
      #day = prevMonthLen - 6 ; s.weekNum = [self.weekNumber(year, month, 1+7*i)-1 for i in xrange(6)]
      day = 1
    else:
      day = prevMonthLen - offset + 1
    s.monthStartOffset = offset
    ######################
    for i in xrange(6):
      s.append([])
      for j in xrange(7):
        c = Cell()
        c.pos = (j, i)
        s[i].append(c)
        c.jd = core.to_jd(year, month, day, self.mode)
        if i<2 and day>15:
          c.gray = -1
          c.date = (pyear, pmonth, day)
          #c.ym = (pyear, pmonth)
        elif i>=4 and day<20:
          c.gray = 1
          nyear = year
          nmonth = month +1
          if nmonth > 12 :
            nmonth =1
            nyear += 1
          c.date = (nyear, nmonth, day)
        else:
          c.gray = 0
          c.date = (year, month, day)
        cyear, cmonth, cday = c.date
        if c.gray==0:
          wd = (core.firstWeekDay + j) % 7 ##??????????
          if wd in self.holidayWeekDays:
            c.holiday = True
        day+=1
        if i>3 and day>currentMonthLen:
          day =1
          sday=1
        if i<2 and day>prevMonthLen:
          day =1
    if addCache:
      ## Clean Cache
      n = len(self.months)
      #print 'Cache size: %s'%n
      if n >= self.maxCache:
        keys = self.months.keys()
        keys.sort()
        if keys[n/2] < (year, month):
          rm = keys[0]
          if rm==self.today[:2]:
            rm = keys[1]
        else:
          rm = keys[-1]
          if rm==self.today[:2]:
            rm = keys[-2]
        #if rm != (year, month):
        #print 'Removing cache (%s, %s)'%(rm[0], rm[1])
        self.months.pop(rm)
    try:#### for memory emhancement
      del self.months[(year, month)]
    except:
      pass
    self.months[(year, month)] = s
    return s
  def computeCurrentMonth(self, overwrite=False):
    if overwrite:
      status = self.buildStatus(self.year, self.month)
    else:
      try:
        status = self.months[(self.year, self.month)]
      except KeyError:
        status = self.buildStatus(self.year, self.month)
    sx, sy = divmod(status.monthStartOffset + self.day - 1, 7)
    self.cell = status[sx][sy]
    assert self.cell.date == (self.year, self.month, self.day)
    return status
  ########################################################################
  def __init__(self, parent=None, mode=None):
    qt.QWidget.__init__(self, parent)
    #super(self.__class__, self).__init__(parent)## if no class will be derived from this widget
    self.months = {}
    if mode is None:
        mode = core.primaryMode
    self.mode = mode
    y, m, d = core.getSysDate()
    self.year = y
    self.month = m
    self.day = d
    self.today = (y, m, d)
    self.computeCurrentMonth()
    ###########
    self.labelBox = qt.QWidget()
    self.cal = qt.QWidget()
    labelBoxL = qt.QHBoxLayout()
    labelBoxL.setContentsMargins(1, 1, 1, 1) ## left, top, right, bottom
    #####
    self.prevYearButton = qt.QPushButton('-')
    self.prevYearButton.setToolTip(_('Previous Year'))
    labelBoxL.addWidget(self.prevYearButton)
    #####
    self.yearLabel = qt.QLabel(qloc.toString(y))
    labelBoxL.addWidget(self.yearLabel)
    #####
    self.nextYearButton = qt.QPushButton('+')
    self.nextYearButton.setToolTip(_('Next Year'))
    labelBoxL.addWidget(self.nextYearButton)
    #####
    labelBoxL.addSpacing(30)
    #####
    self.prevMonthButton = qt.QPushButton('-')
    self.prevMonthButton.setToolTip(_('Previous Month'))
    labelBoxL.addWidget(self.prevMonthButton)
    #####
    self.monthLabel = qt.QLabel(core.getMonthName(self.mode, m, y))
    labelBoxL.addWidget(self.monthLabel)
    #####
    self.nextMonthButton = qt.QPushButton('+')
    self.nextMonthButton.setToolTip(_('Next Month'))
    labelBoxL.addWidget(self.nextMonthButton)
    #####
    self.labelBox.setLayout(labelBoxL)
    #####
    vbox = qt.QVBoxLayout()
    vbox.setContentsMargins(0, 0, 0, 0) ## left, top, right, bottom
    self.labelBox.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed))
    ## (Fixed,Fixed) or (Preferred,Fixed)
    vbox.addWidget(self.labelBox)
    vbox.addWidget(self.cal)
    self.setLayout(vbox)
    #####
    self.prevYearButton.connect(self.prevYearButton, qc.SIGNAL('clicked()'), self._prevYearClicked)
    self.nextYearButton.connect(self.nextYearButton, qc.SIGNAL('clicked()'), self._nextYearClicked)
    self.prevMonthButton.connect(self.prevMonthButton, qc.SIGNAL('clicked()'), self._prevMonthClicked)
    self.nextMonthButton.connect(self.nextMonthButton, qc.SIGNAL('clicked()'), self._nextMonthClicked)
    #####
    self.resize(self.calW, self.calH)
    self.cal.paintEvent = self._calPaintEvent
    self.cal.mousePressEvent = self.calMousePressEvent
    self.cal.keyPressEvent = self.keyPressEvent
  def _prevYearClicked(self):
    self.year -= 1
    self.yearLabel.setText(qloc.toString(self.year))
    self.cal.repaint()
  def _nextYearClicked(self):
    self.year += 1
    self.cal.repaint()
  def _prevMonthClicked(self):
    self.month -= 1
    if self.month<1:
      self.month += 12
      self.year -= 1
    self.cal.repaint()
  def _nextMonthClicked(self):
    self.month += 1
    if self.month>12:
      self.month -= 12
      self.year += 1
    self.cal.repaint()
  def _calPaintEvent(self, event):
    status = self.computeCurrentMonth()
    self.yearLabel.setText(qloc.toString(self.year))
    self.monthLabel.setText(core.getMonthName(self.mode, self.month, self.year))
    w = self.cal.width()
    h = self.cal.height()
    self.calW = w
    self.calH = h
    rtl = self._rtl()
    if rtl:
      self.cx = [ (w-self.leftMargin)*(13.0-2*i)/14.0\
                  for i in xrange(7) ] ## centers x
    else:
      self.cx = [self.leftMargin + (w-self.leftMargin)*(1.0+2*i)/14.0\
                 for i in xrange(7) ] ## centers x
    self.cy = [self.topMargin + (h-self.topMargin)*(1.0+2*i)/12.0\
               for i in xrange(6) ] ## centers y
    self.dx = (w-self.leftMargin)/7.0 ## delta x
    self.dy = (h-self.topMargin)/6.0 ## delta y
    self.gx = [x + self._rtlSgn()*self.dx/2.0 for x in self.cx] ## grid x
    self.gy = [y - self.dy/2.0 for y in self.cy] ## grid y
    #######
    painter = qt.QPainter()
    painter.begin(self.cal)
    painter.setPen(self.bgColor)
    painter.setBrush(self.bgColor)
    painter.drawRect(0, 0, w, h)
    painter.setPen(self.normDayColor)
    painter.setBrush(self.normDayColor)#???
    for x in self.gx:
      painter.drawLine(x, 0, x, h)
    for y in self.gy:
      painter.drawLine(0, y, w, y)
    #######
    sx, sy = self.cell.pos
    if self.cursorBgColor!=None:
      painter.setBrush(self.cursorBgColor)
      painter.setPen(qt.QPen(qt.QBrush(self.cursorBgColor), 0, qc.Qt.SolidLine, qc.Qt.RoundCap))
      painter.drawRoundedRect(self.gx[sx]-rtl*self.dx, self.gy[sy],
        self.dx, self.dy, self.cursorR, self.cursorR)
    ###
    if self.cursorInColor!=None:
      painter.setBrush(self.cursorInColor)
      painter.setPen(qt.QPen(qt.QBrush(self.cursorInColor), 0, qc.Qt.SolidLine, qc.Qt.RoundCap))
      painter.drawRoundedRect(self.gx[sx]-rtl*self.dx+self.cursorD/2.0, self.gy[sy]+self.cursorD/2.0,
        self.dx-self.cursorD, self.dy-self.cursorD, self.cursorR, self.cursorR)
    #######
    painter.setPen(self.borderTextColor)
    for i in range(7):
      painter.drawText(qc.QRectF(self.gx[i]-rtl*self.dx, 0, self.dx, self.topMargin),
        qc.Qt.AlignCenter, self.getWeekDayName(i))
    for j in range(6):
      painter.drawText(qc.QRectF(self.gx[0]-(1-rtl)*self.leftMargin,
        self.gy[j], self.leftMargin, self.dy),
        qc.Qt.AlignCenter, qloc.toString(status.weekNum[j]))
    #######
    for i in range(7):
      for j in range(6):
        cell = status[j][i]
        if cell.gray:
          painter.setPen(self.inactiveDayColor)
        elif cell.holiday:
          painter.setPen(self.holidayColor)
        else:
          painter.setPen(self.normDayColor)
        painter.drawText(qc.QRectF(self.gx[i]-rtl*self.dx, self.gy[j], self.dx, self.dy),
          qc.Qt.AlignCenter, qloc.toString(cell.date[2]))
    #######
    painter.end()
  def _findCol(self, x):
    for i in xrange(7):
      if abs(x-self.cx[i]) <= self.dx/2.0:
        return i
    return -1
  def _findRow(self, y):
    for i in xrange(6):
      if abs(y-self.cy[i]) <= self.dy/2.0:
        return i
    return -1
  def calMousePressEvent(self, event):
    x= event.x()
    y = event.y()
    ## b = event.button
    ## qc.Qt.LeftButton, qc.Qt.RightButton, qc.Qt.MidButton
    ## file:///usr/share/doc/python-qt4-doc/html/qt.html#MouseButton-enum
    self.pointer = (x, y)
    col = self._findCol(x)
    row = self._findRow(y)
    if row>=0 and col>=0:
      status = self.computeCurrentMonth()
      self.day = status[row][col].date[2]
      if row==0 and self.day>15:
        self.month -= 1
        if self.month <= 0 :
          self.month = 12
          self.year -= 1
        gray = -1
        ##row = 5
      elif row>3 and self.day<15:
        self.month += 1
        if self.month > 12 :
          self.month = 1
          self.year += 1
        gray = 1
        ##row = 0
      else:
        gray = 0
      #self.emit(qc.SIGNAL('dayChange(int, int, int)'), self.year, self.month, self.day)
      self.emit(qc.SIGNAL('dayChange'))
      self.cal.repaint()
  def keyPressEvent(self, event):## Arrow keys dosent work!!???????????
    #print event.key(), event.text()
    pass
  def getDate(self):
    '''
    get date of day that is selected in the SimpleCal widget
    @return: a tuple of (year, month, day)
    '''
    return (self.year, self.month, self.day)
  def setDate(self, year, month, day):
    '''
    select day with given date to the SimpleCal widget
    @param year:
    @param month:
    @param day:
    @return: None
    '''
    self.year = year
    self.month = month
    self.day = day
    self.cal.repaint()
  def selectToday(self):
    'select today in the SimpleCal widget'
    self.setDate(*core.getSysDate())

def dayChanged(*args):
  print('dayChanged', args)


if __name__=='__main__':
  app = qt.QApplication(sys.argv)
  app.setLayoutDirection(qc.Qt.RightToLeft)
  w = SimpleCal()
  #w.connect(w, qc.SIGNAL('dayChange(int, int, int)'), dayChanged)
  w.connect(w, qc.SIGNAL('dayChange'), dayChanged)
  w.show()
  sys.exit(app.exec_())


