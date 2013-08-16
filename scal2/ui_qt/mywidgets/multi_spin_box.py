# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com>
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
from time import localtime
from time import time as now

from math import ceil
iceil = lambda f: int(ceil(f))


from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

qc.QLocale.setDefault(qc.QLocale(qc.QLocale.Persian, qc.QLocale.Iran))
qloc = qc.QLocale()
qloc.setNumberOptions(qc.QLocale.OmitGroupSeparator)
##print 'language', qloc.language() ## QLocale.Persian==89

def myRaise():
    i = sys.exc_info()
    try:
        print('line %s: %s: %s'%(i[2].tb_lineno, i[0].__name__, i[1]))
    except:
        print i


class MultiSpinBox(qt.QAbstractSpinBox):
    '''
    A widget that presents an SpinBox with mutiple integer values that will managed smarty
    signals: "firstMax", "firstMin"
    '''
    def __init__(self, mins, maxs, fields, sep, nums=None, arrowSelect=True):##forceSelect=False
        qt.QAbstractSpinBox.__init__(self)
        #super(MultiSpinBox, self).__init__()
        #self.window_up = None
        #self.window_down = None
        n = len(mins)
        if len(sep) == n-1:
            sep = sep + ('',)
        elif len(sep)!=n:
            raise ValueError('bad sep list')
        if len(maxs)!=n:
            raise ValueError('bad maxs list')
        if len(fields)!=n:
            raise ValueError('bad fields list')
        self.sep = sep
        self.size = n
        self.mins = mins
        self.maxs = maxs
        self.fields = fields
        self.arrowSelect = arrowSelect
        #self.forceSelect = forceSelect
        self.editable = True
        self.zero = unichr(qloc.zeroDigit().unicode()) ## unicode(qloc.toString(0))
        #############################
        self.entry = self.lineEdit() ## QLineEdit ~= GtkEntry !!
        self.entry.setLayoutDirection(qc.Qt.LeftToRight)
        #############################
        self.sepIndex = []
        pos = 0
        for i in range(self.size):
            pos += fields[i]
            self.sepIndex.append(pos)
            pos += len(sep[i])
        self.widthChars = pos ## width of entry(lineedit) in chars
        ## self.set_width_chars(pos) #???????## GTK
        metrics=self.entry.fontMetrics() ## like metrics=qt.QFontMetrics(self.entry.font())
        #print 'metrics', metrics.maxWidth(), metrics.charWidth(self.zero, 0)
        self.widthPix = metrics.charWidth(self.zero, 0) * pos + 25 ## ???????????
        ## self.widthPix = metrics.maxWidth()*pos
        self.setMinimumWidth(self.widthPix)
        ############################
        #if forceSelect:#??????????
        #    self.connect('move-cursor', self._entryMoveCursor)
        #self.connect('event', showEvent)
        self.connect(self, qc.SIGNAL('editingFinished()'), self._entryActivate)
        #############
        reg = ''
        for i in range(n):
            reg += '\\d{0,%d}'%fields[i]
            try:
                reg += sep[i]
            except IndexError:
                pass
        self.entry.setValidator(qt.QRegExpValidator(qc.QRegExp(reg), self.entry))
    def keyPressEvent(self, event):
        if not self.editable:
            return
        key = event.key()
        if key==qc.Qt.Key_Left:
            if self.arrowSelect:
                self.entryValidate()
                pos = self.entry.cursorPosition()
                part = self.size-1
                for i in range(self.size):
                    if pos <= self.sepIndex[i]:
                        part = i
                        break
                if part>0:
                    part -=1
                if part==0:
                    start = 0
                    leng = self.sepIndex[0]
                else:
                    start = self.sepIndex[part-1] + len(self.sep[part-1])
                    leng = self.sepIndex[part] - start
                self.entry.setSelection(start, leng)
                self.entry.setFocus()
        elif key==qc.Qt.Key_Right:
            if self.arrowSelect:
                self.entryValidate()
                pos = self.entry.cursorPosition()
                part = self.size-1
                for i in range(self.size):
                    if pos <= self.sepIndex[i]:
                        part = i
                        break
                if part < self.size-1:
                    part += 1
                start = self.sepIndex[part-1] + len(self.sep[part-1])
                leng = self.sepIndex[part] - start
                self.entry.setSelection(start, leng)
                self.entry.setFocus()
        else:
            qt.QAbstractSpinBox.keyPressEvent(self, event) ## OR QWidget.keyPressEvent ???????
        #event.accept()##????????
    def _entryActivate(self):
        self.entryValidate()
        return True
    def stepEnabled(self):
        return qt.QAbstractSpinBox.StepUpEnabled | qt.QAbstractSpinBox.StepDownEnabled
    def stepBy(self, step):
        if self.editable:
            self._entryPlus(step)
    def _entryPlus(self, plus=1, part=None):
        self.entryValidate()
        pos = self.entry.cursorPosition()
        if part==None:
            part = self.size-1
            for i in range(self.size):
                if pos <= self.sepIndex[i]:
                    part = i
                    break
        #print part, self.nums
        new = self.nums[part] + plus
        if new > self.maxs[part]:#or self.maxs[part]==None:
            new = self.mins[part]
            if part==0:
                self.emit(qc.SIGNAL('firstMax'))##?????????????????
            else:
                self._entryPlus(1, part-1)
        elif new < self.mins[part]:
            new = self.maxs[part]
            if part==0:
                self.emit(qc.SIGNAL('firstMin'))
            else:
                self._entryPlus(-1, part-1)
        self.nums[part] = new
        self.entry.setText(self._ints2str(self.nums))
        self.entry.setFocus()##????????????????
        if self.arrowSelect:
                if part==0:
                    start = 0
                    leng = self.sepIndex[0]
                else:
                    start = self.sepIndex[part-1] + len(self.sep[part-1])
                    leng = self.sepIndex[part] - start
                self.entry.setSelection(start, leng)
        else:
            self.entry.setCursorPosition(pos)
        return True
    def entryValidate(self):
        n = self.size
        pos = self.entry.cursorPosition()
        text = unicode(self.entry.text())
        nums = []
        nfound = [] ## not found seperator
        p = 0
        for i in range(n):
            if i==n-1 and self.sep[i]=='':
                if nfound==[]:
                    nums.append(text[p:])
                else:
                    nums.append('')
                break
            p2 = text.find(self.sep[i], p)
            if p2==-1:
                    nums.append('')
                    nfound.append([i, p])
                    continue
            if nfound==[]:
                nums.append(text[p:p2].strip())
            else:
                [j, np] = nfound[0]
                nums[j] = text[p:p2].strip()
                nfound = []
                nums.append('')
            p = p2 + len(self.sep[i])
        if p2==-1:
            [j, p] = nfound[0]
            nums[j] = text[p:]
        if len(nums)>n:
            nums = nums[:n]
        else:
            while len(nums)<n:
                nums.append('')
        for i in range(n):
            if nums[i]=='':
                num = self.mins[i]
            else:
                try:
                    num = self._str2int(nums[i])
                except ValueError:
                    try:
                        num = int(nums[i])
                    except:
                        num = self.mins[i]
                if num > self.maxs[i]:#or self.maxs[part]==None:
                    num = self.maxs[i]
                #elif num==0:
                #    num = self.mins[i]
            nums[i] = num
        ntext = self._ints2str(nums)
        if ntext!=text:
            self.entry.setText(ntext)
            self.entry.setCursorPosition(pos)
        self.nums = nums
        return ntext
    def getNums(self):
        self.entryValidate()
        return self.nums
    def setNums(self, nums=(0,0,0)):
        if len(nums)!=self.size:
            raise ValueError('argument nums has length %s instaed of %s'%(len(nums), self.size))
        pos = self.entry.cursorPosition()
        self.nums = list(nums)
        self.entry.setText(self._ints2str(nums))
        self.entry.setCursorPosition(pos)
    def setEditable(self, editable):
        self.setReadOnly(not editable) ## self OR self.entry
        self.editable = editable
    def isEditable(self):
        return self.editable
    def _ints2str(self, ints):
        text = u''
        for i in range(self.size):
            uni = u''
            try:
                n = ints[i]
            except:
                n = self.mins[i]
            uni = unicode(qloc.toString(n))
            uni = (self.fields[i]-len(uni)) * self.zero + uni
            text += (uni+self.sep[i])
        return text
    def _str2int(self, st):
        return qloc.toInt(st.decode('utf-8'))[0]
    #def _move_cursor(self, obj, step, count, extend_selection):
        ## forceSelect
        #print'_entry_move_cursor', count, extend_selection

class DateBox(MultiSpinBox):
    def __init__(self, date=None, **kwargs):
        if date==None:
            date = localtime()[:3]
        MultiSpinBox.__init__(self, mins=(0,1,1), maxs=(9999,12,31), fields=(4,2,2), sep=(u'/', u'/'), nums=date, **kwargs)
        self.getDate = self.getNums
    setDate = lambda self, y, m, d: self.setNums((y, m, d))


class YearMonthBox(MultiSpinBox):
    def __init__(self, date=None, **kwargs):
        if date==None:
            date = localtime()[:2]
        MultiSpinBox.__init__(self, mins=(0,1), maxs=(9999,12), fields=(4,2), sep=(u'/',), nums=date, **kwargs)
        self.getYM = self.getNums
    setYM = lambda self, y, m: self.setNums((y, m))

class TimeBox(MultiSpinBox):
    def __init__(self, hms=None, **kwargs):
        if hms==None:
            hms = localtime()[3:6]
        MultiSpinBox.__init__(self, mins=(0,0,0), maxs=(23,59,59), fields=(2,2,2), sep=(u':', u':'), nums=hms, **kwargs)
        self.getTime = self.getNums
    setTime = lambda self, h, m=0, s=0: self.setNums((h, m, s))
    def getSeconds(self):
        h, m, s = self.getTime()
        return h*3600 + m*60 + s
    def setSeconds(self, seconds):
        day, s = divmod(seconds, 86400) ## do what with "day" ?????
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        self.setTime(h, m, s)
        ##return day

class DateTimeBox(MultiSpinBox):
    def __init__(self, dateTime=None, **kwargs):
        if dateTime==None:
            dateTime = localtime()[:6]
        MultiSpinBox.__init__(self, mins=(0,1,1,0,0,0), maxs=(9999,12,31,23,59,59),\
            fields=(4,2,2,2,2,2), sep=(u'/', u'/',u'     ',u':',u':',' seconds'), nums=dateTime, **kwargs)
        self.getDateTime = self.getNums
        self.setDateTime = self.setNums

class TimerBox(TimeBox):
    def __init__(self, **kwargs):
        TimeBox.__init__(self, **kwargs)
        #self.timer = False
        #self.clock = False
        self.delay = 1.0 # timer delay
        self.tPlus = -1 # timer plus (step)
        self.elapse = 0
        self.qtimer = qc.QTimer(self)
    def timerStart(self):
        self.clock = False
        self.timer = True
        #self.delay = 1.0 # timer delay
        #self.tPlus = -1 # timer plus (step)
        #self.elapse = 0
        #########
        self.tOff = now()*self.tPlus - self.getSeconds()
        self.setEditable(False)
        self._timerUpdate()
    def timerStop(self):
        self.timer = False
        self.setEditable(True)
    def _timerUpdate(self):
        if not self.timer:
            return
        sec = int(now()*self.tPlus - self.tOff)
        self.setSeconds(sec)
        if self.tPlus*(sec-self.elapse) >= 0:
            self.emit(qc.SIGNAL('time-elapse'))
            self.timerStop()
        else:
            self.qtimer.singleShot(iceil(self.delay*1000), self._timerUpdate)
    def clockStart(self):
        self.timer = False
        self.clock = True
        self.setEditable(False)
        self._clockUpdate()
    def clockStop(self):
        self.clock = False
        self.setEditable(True)
    def _clockUpdate(self):
        if self.clock:
            self.qtimer.singleShot(iceil(1000*(1-now()%1)), self._clockUpdate)
            self.setTime(*localtime()[3:6])

class ExtTimerBox(qt.QWidget):## FIXME
    def __init__(self, **kwargs):
        pass


def timerExample():
    app = qt.QApplication(sys.argv)
    timerbox = TimerBox()
    timerbox.setSeconds(100)
    timerbox.timerStart()
    timerbox.show()
    sys.exit(app.exec_())


def clockExample():
    app = qt.QApplication(sys.argv)
    timerbox = TimerBox()
    timerbox.clockStart()
    timerbox.show()
    sys.exit(app.exec_())

def dateBoxExample():
    app = qt.QApplication(sys.argv)
    dateb = DateBox()
    dateb.setDate(*localtime()[:3])
    dateb.show()
    sys.exit(app.exec_())


if __name__=='__main__':
    timerExample()
    #clockExample()
    #dateBoxExample()


