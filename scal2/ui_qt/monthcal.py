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

from time import time as now
import sys, os
from os.path import join, isfile

from scal2.locale_man import tr as _
from scal2.locale_man import rtl, rtlSgn

from scal2 import core
from scal2.core import myRaise, getMonthLen, pixDir

from scal2 import ui
from scal2.monthcal import getMonthStatus, getCurrentMonthStatus

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

from scal2.ui_qt.font_utils import *
from scal2.ui_qt.drawing import *
from scal2.ui_qt.mywidgets import HBox, VBox
from scal2.ui_qt.customize import MainWinItem



class MonthCal(qt.QWidget, MainWinItem):
    cx = [0, 0, 0, 0, 0, 0, 0]
    def heightSpinChanged(self, value):## FIXME
        h = int(value)
        self.setFixedHeight(h)
        ui.mcalHeight = h
    confStr = lambda self: 'ui.mcalHeight=%r\n'%ui.mcalHeight
    getDate = lambda self: (ui.cell.year, ui.cell.month, ui.cell.day)
    def setDate(self, date):
        ui.cell.year, ui.cell.month, ui.cell.day = date
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        #####################
        hbox = HBox()
        spin = qt.QSpinBox()
        spin.setRange(1, 999)
        spin.setSingleStep(1)
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        spin.setValue(ui.mcalHeight)
        self.connect(spin, qc.SIGNAL('valueChanged (int)'), self.heightSpinChanged)
        hbox.addWidget(qt.QLabel(_('Height')))
        hbox.addWidget(spin)
        MainWinItem.__init__(self, 'monthCal', _('Month Calendar'), optionsWidget=hbox)
        self.setFixedHeight(ui.mcalHeight)
        self.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        ######################
        ## self.supports_alpha = ## ??????????
        #self.kTime = 0
        ######################
        ## Define drag and drop
        ######################
        self.myKeys = (
            qc.Qt.Key_Up, qc.Qt.Key_Down, qc.Qt.Key_Right, qc.Qt.Key_Left, qc.Qt.Key_Space, qc.Qt.Key_Home, qc.Qt.Key_End,
            qc.Qt.Key_PageUp, qc.Qt.Key_PageDown, qc.Qt.Key_Menu, qc.Qt.Key_F10, qc.Qt.Key_M
        )
        ######################
        self.updateTextWidth()
    def paintEvent(self, event):
        self.updateTextWidth()
        self.calcCoord()
        w = self.width()
        h = self.height()
        #####
        painter = qt.QPainter()
        painter.begin(self)
        #####
        #painter.setPen(qt.QColor(*ui.bgColor))
        painter.setBrush(qt.QColor(*ui.bgColor))
        painter.drawRect(0, 0, w, h)
        #####
        status = getCurrentMonthStatus()
        #################################### Drawing Border
        if ui.mcalTopMargin>0:
            ##### Drawing border top background
            ##menuBgColor == borderColor ##???????????????
            painter.setBrush(qt.QColor(*ui.borderColor))
            painter.drawRect(0, 0, w, ui.mcalTopMargin)
            ######## Drawing weekDays names
            painter.setPen(qt.QColor(*ui.borderTextColor))
            dx = 0
            wdayAb = (self.wdaysWidth > w)
            for i in range(7):
                painter.drawText(self.cx[i]-self.dx/2.0, 0, self.dx, ui.mcalTopMargin,
                                 qc.Qt.AlignCenter, core.getWeekDayAuto(i, wdayAb))
            ######## Drawing "Menu" label
            painter.setPen(qt.QColor(*ui.menuTextColor))
            painter.drawText(
                w - ui.mcalLeftMargin if rtl else 0,
                0,
                ui.mcalLeftMargin,
                ui.mcalTopMargin,
                qc.Qt.AlignCenter,
                _('Menu')
            )
        if ui.mcalLeftMargin>0:
            ##### Drawing border left background
            painter.setBrush(qt.QColor(*ui.borderColor))
            if rtl:
                painter.drawRect(w-ui.mcalLeftMargin, ui.mcalTopMargin, ui.mcalLeftMargin, h-ui.mcalTopMargin)
            else:
                painter.drawRect(0, ui.mcalTopMargin, ui.mcalLeftMargin, h-ui.mcalTopMargin)
            ##### Drawing week numbers
            painter.setPen(qt.QColor(*ui.borderTextColor))
            for i in range(6):
                painter.drawText(
                    w - ui.mcalLeftMargin if rtl else 0,
                    self.cy[i]-self.dy/2.0,
                    ui.mcalLeftMargin,
                    self.dy,
                    qc.Qt.AlignCenter,
                    _(status.weekNum[i])
                )
        cursor = True ## FIXME
        quad = 90 ## 90*16
        selectedCellPos = ui.cell.monthPos
        for yPos in range(6):
            for xPos in range(7):
                c = status[yPos][xPos]
                x0 = self.cx[xPos]
                y0 = self.cy[yPos]
                cellInactive = (c.month != ui.cell.month)
                cellHasCursor = (cursor and (xPos, yPos) == selectedCellPos)
                if cellHasCursor:
                    ##### Drawing Cursor
                    d=ui.cursorD
                    if ui.cursorFixed:
                        cx0 = x0-ui.cursorW/2.0 - d
                        cy0 = y0-ui.cursorH/2.0 - d
                        cw = ui.cursorW + 2*d
                        ch = ui.cursorH + 2*d
                    else:
                        eps = 0.3 ## ????????????
                        cx0 = x0 - self.dx/2.0 + eps
                        cy0 = y0 - self.dy/2.0 + eps
                        cw = self.dx - 1 - 2*eps
                        ch = self.dy - 1 - 2*eps
                    painter.setBrush(qt.QColor(*ui.cursorBgColor))
                    if ui.cursorR==0:
                        painter.drawRect(cx0, cy0, cw, ch)
                    else:
                        ## if round_oval: ## ??????
                        ######### Circular Rounded
                        ro = min(ui.cursorR, cw/2, ch/2)
                        #a = min(cw, ch); ri = ro*(a-2*d)/a
                        ri = max(ro-d, 0)
                        ######### Outline:
                        path = qt.QPainterPath()
                        path.moveTo(cx0+ro, cy0)
                        path.lineTo(cx0+cw-ro, cy0)
                        path.arcTo(cx0+cw-2*ro, cy0, 2*ro, 2*ro, quad, -quad)## up right corner
                        path.lineTo(cx0+cw, cy0+ch-ro)
                        path.arcTo(cx0+cw-2*ro, cy0+ch-2*ro, 2*ro, 2*ro, 0, -quad)## down right corner
                        path.lineTo(cx0+ro, cy0+ch)
                        path.arcTo(cx0, cy0+ch-2*ro, 2*ro, 2*ro, -quad, -quad)## down left corner
                        path.lineTo(cx0, cy0+ro)
                        path.arcTo(cx0, cy0, 2*ro, 2*ro, -2*quad, -quad)## up left corner
                        ####
                        painter.drawPath(path)
                        ##if round_oval:##???????
                ##### end of Drawing Cursor
                '''
                if not cellInactive:
                    ## right buttom corner ?????????????????????
                    targetRect = QRectF()
                    pix = qt.QPixmap(join(pixDir, ui.customdayModes[c.customday['type']][1]))
                    painter.drawPixmap(self.cx[xPos]+self.dx/2.0-pix.width(),# right side
                                       self.cy[yPos]+self.dy/2.0-pix.height(),# buttom side
                                       self.customdayPixmaps[c.customday['type']])
                '''
                params = ui.mcalTypeParams[0]
                if params['enable']:
                    mode = core.primaryMode
                    num = _(c.dates[mode][2], mode)
                    qfont = qfontEncode(params['font'])
                    met = qt.QFontMetrics(qfont)
                    fontw = met.maxWidth() * len(num)
                    fonth = met.height()
                    painter.setFont(qfont)
                    if not cellInactive:
                        painter.setPen(qt.QColor(*ui.inactiveColor))
                    elif c.holiday:
                        painter.setPen(qt.QColor(*ui.holidayColor))
                    else:
                        painter.setPen(qt.QColor(*params['color']))
                    painter.drawText(
                        x0 - fontw/2.0 + params['x'],
                        y0 - fonth/2.0 + params['y'],
                        fontw,
                        fonth,
                        qc.Qt.AlignCenter,
                        num,
                    )
                if not cellInactive:
                    for mode, params in ui.getMcalMinorTypeParams()[1:]:
                        if params['enable']:
                            num = _(c.dates[mode][2], mode)
                            qfont = qfontEncode(params['font'])
                            met = qt.QFontMetrics(qfont)
                            fontw = met.maxWidth() * len(num)
                            fonth = met.height()
                            painter.setFont(qfont)
                            painter.setPen(qt.QColor(*params['color']))
                            painter.drawText(
                                x0 - fontw/2.0 + params['x'],
                                y0 - fonth/2.0 + params['y'],
                                fontw,
                                fonth,
                                qc.Qt.AlignCenter,
                                num,
                            )
                    if cellHasCursor:
                        ##### Drawing Cursor Outline
                        d = ui.cursorD
                        if ui.cursorFixed:
                            cx0 = x0 - ui.cursorW/2.0 - d
                            cy0 = y0 - ui.cursorH/2.0 - d
                            cw = ui.cursorW + 2*d
                            ch = ui.cursorH + 2* d
                        else:
                            eps = 0.3 ## ????????????
                            cx0 = x0-self.dx/2.0 + eps
                            cy0 = y0-self.dy/2.0 + eps
                            cw = self.dx - 1 - 2*eps
                            ch = self.dy - 1 - 2*eps
                        painter.setBrush(qt.QColor(*ui.cursorOutColor))
                        path = qt.QPainterPath()
                        if ui.cursorR==0:
                            path.moveTo(cx0, cy0)
                            path.lineTo(cx0+cw, cy0)
                            path.lineTo(cx0+cw, cy0+ch)
                            path.lineTo(cx0, cy0+ch)
                            path.lineTo(cx0, cy0)
                            #####
                            path.moveTo(cx0+d, cy0+d)
                            path.lineTo(cx0+d, cy0+ch-d)
                            path.lineTo(cx0+cw-d, cy0+ch-d)
                            path.lineTo(cx0+cw-d, cy0+d)
                            path.lineTo(cx0+d, cy0+d)
                        else:
                            ## if round_oval: #??????????
                            ######### Circular Rounded
                            ro = min(ui.cursorR, cw/2, ch/2)
                            #a = min(cw, ch); ri = ro*(a-2*d)/a
                            d = min(d, ro)
                            ri = ro-d
                            ######### Outline:
                            path.moveTo(cx0+ro, cy0)
                            path.lineTo(cx0+cw-ro, cy0)
                            path.arcTo(cx0+cw-2*ro, cy0, 2*ro, 2*ro, quad, -quad) ## up right corner
                            path.lineTo(cx0+cw, cy0+ch-ro)
                            path.arcTo(cx0+cw-2*ro, cy0+ch-2*ro, 2*ro, 2*ro, 0, -quad) ## down right corner
                            path.lineTo(cx0+ro, cy0+ch)
                            path.arcTo(cx0, cy0+ch-2*ro, 2*ro, 2*ro, -quad, -quad) ## down left corner
                            path.lineTo(cx0, cy0+ro)
                            path.arcTo(cx0, cy0, 2*ro, 2*ro, -2*quad, -quad) ## up left corner
                            #### Inline:
                            path.moveTo(cx0+ro, cy0+d) ## or line to?
                            path.arcTo(cx0+d, cy0+d, 2*ri, 2*ri, quad, quad) ## up left corner
                            path.lineTo(cx0+d, cy0+ch-ro)
                            path.arcTo(cx0+d, cy0+ch-ro-ri, 2*ri, 2*ri, 2*quad, quad) ## down left
                            path.lineTo(cx0+cw-ro, cy0+ch-d)
                            path.arcTo(cx0+cw-ro-ri, cy0+ch-ro-ri, 2*ri, 2*ri, 3*quad, quad) ## down right
                            path.lineTo(cx0+cw-d, cy0+ro)
                            path.arcTo(cx0+cw-ro-ri, cy0+d, 2*ri, 2*ri, 0, quad) ## up right
                            path.lineTo(cx0+ro, cy0+d)
                            ####
                            painter.drawPath(path)
                            ## if round_oval: ## ??????
                            ##### end of Drawing Cursor Outline


        ##### drawGrid
        if ui.mcalGrid:
            painter.setBrush(qt.QColor(*ui.mcalGridColor))
            for i in range(7):
                painter.drawRect(self.cx[i]+rtlSgn()*self.dx/2.0, 0, 1, h)
            for i in range(6):
                painter.drawRect(0, self.cy[i]-self.dy/2.0, w, 1)
    ## def dragDataGet
    ## def dragLeave
    ## def dragDataRec
    ## def dragBegin
    def updateTextWidth(self):
        ### update width of week days names to understand that should be
        ### synopsis or no
        qfont = qfontEncode(ui.getFont())
        wm = 0 ## max width
        for i in range(7):
            w = calcTextWidth(core.weekDayName[i], qfont)
            #print(w,)
            if w > wm:
                wm = w
        self.wdaysWidth = wm*7 + ui.mcalLeftMargin
        #print('max =', wm, '     wdaysWidth =', self.wdaysWidth)
    def calcCoord(self):## calculates coordidates (x and y of cells centers)
        w = self.width()
        h = self.height()
        if rtl:
            self.cx = [ (w-ui.mcalLeftMargin)*(13.0-2*i)/14.0 \
                                 for i in range(7) ] ## centers x
        else:
            self.cx = [ui.mcalLeftMargin \
                                 + (w-ui.mcalLeftMargin)*(1.0+2*i)/14.0 \
                                 for i in range(7) ] ## centers x
        self.cy = [ui.mcalTopMargin + (h-ui.mcalTopMargin)*(1.0+2*i)/12.0 \
                             for i in range(6) ] ## centers y
        self.dx = (w-ui.mcalLeftMargin)/7.0 ## delta x
        self.dy = (h-ui.mcalTopMargin)/6.0 ## delta y
    def monthPlus(self, p):
        ui.monthPlus(p)
        self.onDateChange()
    def keyPressEvent(self, event):
        k = event.key()
        print(now(), 'MonthCal.keyPressEvent', k, hex(k))
        if k==qc.Qt.Key_Up:
            self.jdPlus(-7)
        elif k==qc.Qt.Key_Down:
            self.jdPlus(7)
        elif k==qc.Qt.Key_Right:
            if rtl:
                self.jdPlus(-1)
            else:
                self.jdPlus(1)
        elif k==qc.Qt.Key_Left:
            if rtl:
                self.jdPlus(1)
            else:
                self.jdPlus(-1)
        elif k==qc.Qt.Key_Space or k==qc.Qt.Key_Home:
            self.goToday()
        elif k==qc.Qt.Key_End:
            self.changeDate(ui.cell.year, ui.cell.month, getMonthLen(ui.cell.year, ui.cell.month, core.primaryMode))
        elif k==qc.Qt.Key_End:
            self.changeDate(ui.cell.year, ui.cell.month, getMonthLen(ui.cell.year, ui.cell.month, core.primaryMode))
        elif k==qc.Qt.Key_PageUp:
            self.monthPlus(-1)
        elif k==qc.Qt.Key_PageDown:
            self.monthPlus(1)
        elif k==qc.Qt.Key_Menu:# Simulate right click (key beside Right-Ctrl)
            self.emit(qc.SIGNAL('popup-menu-cell'), *self.getCellPos())
        elif k in (qc.Qt.Key_F10, qc.Qt.Key_M):
            #print('keyPressEvent: menu', event.modifiers())
            if event.modifiers() & qc.Qt.ShiftModifier:
                ## Simulate right click (key beside Right-Ctrl)
                print('popup-menu-cell')
                self.emit(qc.SIGNAL('popup-menu-cell'), *self.getCellPos())
            else:
                print('popup-menu-main')
                self.emit(qc.SIGNAL('popup-menu-main'), *self.getMainMenuPos())
        else:
            event.ignore() ## I dont want the event. Propagate to the parent widget.
            #print(now(), 'MonthCal.keyPressEvent', hex(k))
            return
        event.accept() ## I want the event. Do not propagate to the parent widget.
    def mousePressEvent(self, event):
        #print('monthcal: mousePressEvent')
        x= event.x()
        y = event.y()
        b = event.button()
        #self.pointer = (x, y) ## needed? FIXME
        if b!=qc.Qt.MidButton:
            sx = -1
            sy = -1
            for i in range(7):
                if abs(x-self.cx[i]) <= self.dx/2.0:
                    sx = i
                    break
            for i in range(6):
                if abs(y-self.cy[i]) <= self.dy/2.0:
                    sy = i
                    break
            status = getCurrentMonthStatus()
            if sy==-1 or sx==-1:
                self.emit(qc.SIGNAL('popup-menu-main'), x, y)
                #self.menuMainWidth = self.menuMain.width()
            elif sy>=0 and sx>=0:
                cell = status[sy][sx]
                self.changeDate(*cell.dates[core.primaryMode])
                if event.type()==qc.QEvent.MouseButtonDblClick:
                    self.emit(qc.SIGNAL('2button-press')) ## Needed??
                if b==qc.Qt.RightButton and cell.month==ui.cell.month:## right click
                    #self.emit(qc.SIGNAL('popup-menu-cell'), *self.getCellPos())
                    self.emit(qc.SIGNAL('popup-menu-cell'), x, y)
        event.accept()## FIXME
    def wheelEvent(self, event):## scroll
        if event.orientation()==qc.Qt.Vertical:
            if event.delta()>0:
                self.jdPlus(-7)
            else:
                self.jdPlus(7)
    def jdPlus(self, plus):
        ui.jdPlus(plus)
        self.update()
        self.emit(qc.SIGNAL('date-change'), self)
    def changeDate(self, year, month, day, mode=None):
        ui.changeDate(year, month, day, mode)
        self.update()## equivalent of self.queue_draw() in GTK
        self.emit(qc.SIGNAL('date-change'), self)
    goToday = lambda self, widget=None: self.changeDate(*core.getSysDate())
    getCellPos = lambda self: (int(self.cx[ui.cell.monthPos[0]]),
                               int(self.cy[ui.cell.monthPos[1]] + self.dy/2.0))
    def getMainMenuPos(self):#???????????????????
        if rtl:
            return (int(self.width() - ui.mcalLeftMargin/2.0),
                    int(ui.mcalTopMargin/2.0))
        else:
            return (int(ui.mcalLeftMargin/2.0),
                    int(ui.mcalTopMargin/2.0))
    def onDateChange(self):
        self.update()## equivalent of self.queue_draw() in GTK
    def onConfigChange(self):
        self.shownCals = ui.shownCals
        self.updateTextWidth()


if __name__=='__main__':
    app = qt.QApplication(sys.argv)
    w = MonthCal()
    #w.resize(ui.winWidth, ui.mcalHeight)
    w.show()
    sys.exit(app.exec_())


