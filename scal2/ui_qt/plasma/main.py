#!/usr/bin/env python2
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

## /usr/share/kde4/apps/plasma/plasmoids


import sys, os
from os.path import dirname, join
from math import ceil
from time import localtime
from time import time as now

from time import strftime ## FIXME replcae with my own format_time

rootDir = '/usr/share/starcal2'
if not os.path.isdir(rootDir):
    raise OSError('starcal2 is not currently installed!')
sys.argv = [__file__]
sys.path.insert(0, rootDir)


from scal2.ui_qt.starcal2 import * ## before import tr as _

from scal2.locale_man import rtl
from scal2.locale_man import tr as _
#from scal2.locale_man import loadTranslator
#_ = loadTranslator(True)## FIXME

from scal2 import core

from scal2.ui_qt.preferences import qpixDir
from scal2.ui_qt import preferences


from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

import PyKDE4
import PyKDE4.plasma
import PyKDE4.plasmascript



"""
def removeXml(st):
    n = len(st)
    i = 0
    xml = False
    st2 = ''
    for c in st:
        if xml:
            if c=='>':
                xml = False
        else:
            if c=='<':
                xml = True
            else:
                st2 += c
    return st2
"""

def removePangoMarkup(text):
    import pango
    return pango.parse_markup(text)[1]


class PClockLabel(PyKDE4.plasma.Plasma.Label):
    def __init__(self, parent=None):
        '''format is a string that used in strftime()
        for example format can be "<b>%T</b>"
        local is bool. if True, use Local time, and if False, use GMT time
        selectable is bool that passes to GtkLabel'''
        PyKDE4.plasma.Plasma.Label.__init__(self, parent)
        #self.setTextFormat(qc.Qt.PlainText)#??????????
        ##self.set_direction(gtk.TEXT_DIR_LTR)##???????????
        self.updateFormat()
        self.running = False
        ##self.connect('button-press-event', self.button_press)
        self.timer = qc.QTimer(self) ## argument not necessary
        self.start()#???
    def start(self):
        self.running = True
        self.update()
    def update(self):
        if self.running:
            self.timer.singleShot(int(1000*(1-now()%1)), self.update)
            try:
                self.setText(strftime(self.format).decode('utf-8'))
            except:
                pass
    def stop(self):
        self.running = False
    def updateFormat(self):
        self.format = removePangoMarkup(preferences.clockFormat)


class StarCalApplet(MainWin):
    def __init__(self, papplet):
        self.papplet = papplet
        self.tbutton = papplet.tbutton
        self.name = core.APP_DESC ## self.papplet.package().metadata().name()
        MainWin.__init__(self, trayMode=1)
        ######
        self.timer = qc.QTimer(self.tbutton) ## argument not necessary
        qc.QObject.connect(self.timer, qc.SIGNAL('timeout()'), self.trayUpdate)
        self.timer.start(self.timeout)
        ######
        self.trayUpdate() ## ??????? Needed?
    def closeEvent(self, event):
        print('--------------- StarCalApplet.closeEvent')
        self.tbutton.setChecked(False)
        MainWin.closeEvent(self, event)
    def trayInit(self):
        self.tbutton.setCheckable(True)
        #qc.QObject.connect(self.tbutton, qc.SIGNAL('pressed()'), self.appletButtonPress)
        #qc.QObject.connect(self.tbutton, qc.SIGNAL('toggled()'), self.trayClicked) ## NOT WORKS
        #qc.QObject.connect(self.tbutton, qc.SIGNAL('clicked()'), self.trayClicked)
        self.tbutton.connect(self.tbutton, qc.SIGNAL("clicked()"), self.trayClicked)
        ## ????? Create right click menu
        #####
        self.clockTr = PClockLabel()
        ##??????? qc.Qt.RichText couse to the click on label didnt toggle the button
        #####
        self.painter = qt.QPainter()
        self.pmap = qt.QPixmap()
        self.icon = PyKDE4.plasma.Plasma.Label()
        self.iconT = qt.QLabel()
        #####
        hbox = qt.QGraphicsLinearLayout(qc.Qt.Horizontal, self.tbutton)
        hbox.setContentsMargins(3, 3, 4, 3) ## left, top, right, bottom
        hbox.addItem(self.icon)
        #hbox.addStretch(1)
        hbox.addItem(self.clockTr)
        #hbox.setItemSpacing(0, 0)
        #hbox.setAlignment(self.icon, qc.Qt.Alignment(qc.Qt.AlignHCenter))
        self.tbutton.setLayout(hbox)
        print('name=%s'%self.name)
        #self.connect(self, qc.SIGNAL('hoverMoveEvent'), self.hoverMoveEvent)
        self.tooltipMgr = PyKDE4.plasma.Plasma.ToolTipManager.self()
        self.tooltipMgr.registerWidget(self.papplet.applet)
        self.tooltipContent = PyKDE4.plasma.Plasma.ToolTipContent(self.name, '')
    def trayClicked(self):
        #print('trayClicked', self.tbutton.isChecked())
        #self.emit('main-show')
        #while gtk.events_pending():
        #    gtk.main_iteration_do(False)
        if self.tbutton.isChecked():
            #print(self.papplet.applet.contentsRect().topLeft()##??????????????????)
            #if ui.winX==0 and ui.winY==0:##??????????????????
            #ui.winX = self.papplet.x()
            #ui.winY = self.papplet.y()
            self.move(ui.winX, ui.winY)
            ## every calling of .hide() and .present(), makes
            ## window not on top (forgets being on top)
            #act = self.actionAbove.isChecked()
            #self.set_keep_above(act)
            #if self.checkSticky.isChecked():
            #    self.stick()
            #self.deiconify()
            self.show()## raise_() does not work
        else:
            p = self.pos()
            ui.winX = p.x()
            ui.winY = p.y()
            self.hide()
    def appletButtonPress(self, *args):
        print('appletButtonPress', args)
        ## ????? Check if button==3 open the menu
    def updateTrayClock(self):
        clockTr0 = ui.showDigClockTr
        ui.showDigClockTr = self.checkClockTr.get_active()
        if ui.showDigClockTr:
            if not clockTr0:
                ##self.clockTr = PClockLabel()
                ##self.trayHbox.pack_start(self.clockTr, 0, 0)
                self.clockTr.show()
            else:
                self.clockTr.format = preferences.clockFormat
        else:
            if clockTr0:
                ##self.clockTr.destroy()
                self.clockTr.hide()
    def trayUpdate(self, gdate=None, checkDate=True):## FIXME
        if gdate==None:
            gdate = localtime()[:3]
        if self.lastGDate!=gdate or not checkDate:
            jd = core.modules[core.DATE_GREG].to_jd(*gdate)
            if core.primaryMode==core.DATE_GREG:
                ddate = gdate
            else:
                ddate = core.modules[core.primaryMode].jd_to(jd)
            self.lastGDate = gdate
            ui.todayCell = ui.cellCache.getTodayCell()
            imPath = ui.trayImageHoli if ui.todayCell.holiday else ui.trayImage
            self.pmap.load(imPath)
            try:
                self.painter.end()
            except:
                pass
            self.painter.begin(self.pmap)
            w = self.pmap.width()
            h = self.pmap.height()
            self.painter.drawText(qc.QPoint(0, h-2), _(ddate[2]))
            self.iconT.setPixmap(self.pmap)
            self.icon.setWidget(self.iconT)
            #self.icon.setGeometry(qc.QRectF(0, 0, w, h))
            #self.iconT.setGeometry(qc.QRect(0, 0, w, h))
            self.iconT.setFixedWidth(w)
            #self.iconT.setFixedHeight(h)
            ## position of left lower corner of text ^^
            ## trayTextColor, ui.trayFont, ui.fontCustomEnable ??????
            ####################
            wd = core.getWeekDay(*ddate)
            tt = core.getWeekDayN(wd)
            #if ui.pluginsTextTray:##?????????
            #    sep = _(',')+' '
            #else:
            sep = u'<br>'
            for item in ui.shownCals:
                if item['enable']:
                    mode = item['mode']
                    y, m, d = ui.todayCell.dates[mode]
                    tt += u'%s%s %s %s'%(sep, _(d), core.getMonthName(mode, m), _(y))
            if ui.pluginsTextTray:
                text = ui.todayCell.pluginsText
                if text!='':
                    tt += u'%s%s'%(sep, text.replace(u'\t', sep)) #????????????
            if rtl:## tags: div, p, body
                tt = u'<p dir="rtl">%s</p>'%tt
            #else:
            #    tt = '<p dir="ltr">%s</p>'%tt
            self.tooltipContent.setMainText('') ## self.name
            self.tooltipContent.setSubText(tt)
            self.tooltipMgr.setContent(self.papplet.applet, self.tooltipContent)
        return True
    def onConfigChange(self):## FIXME
        MainWin.onConfigChange(self)
        self.clockTr.updateFormat()






class StarCalPlasmaApplet(PyKDE4.plasmascript.Applet):
    def __init__(self, parent, arg=None):
        PyKDE4.plasmascript.Applet.__init__(self, parent)
        self.setApplet(PyKDE4.plasma.Plasma.Applet(parent, []))
    def init(self):
        self.tbutton = PyKDE4.plasma.Plasma.PushButton(self.applet)
        self.tbutton.setCheckable(True)
        self.tbutton.setText('')
        self.layout = qt.QGraphicsLinearLayout(qc.Qt.Horizontal, self.applet)
        self.layout.addItem(self.tbutton)
        self.sapplet = StarCalApplet(self)
        self.setHasConfigurationInterface(True)
        self.setLayout(self.layout)
        self.setAspectRatioMode(0)
        ## 0: free size
        ## 1: square (ratio=1)
        ## 2: fixed ratio (of initial size)
        #print('ui.traySize', ui.traySize)
        self.resize(300, ui.traySize+50) ## how to calculate/estimate needed width
    def showConfigurationInterface(self):
        self.sapplet.prefShow()



def CreateApplet(parent):
        return StarCalPlasmaApplet(parent)


