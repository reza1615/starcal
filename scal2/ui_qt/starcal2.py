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

import sys

if sys.version_info[0] != 2:
    print('Run this script with Python 2.x')
    sys.exit(1)

import os
from os.path import join, dirname, isfile, isdir
from time import localtime
from time import time as now

from subprocess import Popen

sys.path.insert(0, dirname(dirname(dirname(__file__))))
from scal2.path import *
from scal2.utils import myRaise, restartLow

if not isdir(confDir):
    try:
        __import__('scal2.ui_qt.import_config_1to2')
    except:
        myRaise()
    restartLow()

from scal2.utils import toUnicode
from scal2 import core

from scal2 import locale_man
from scal2.locale_man import rtl ## import scal2.locale_man after core
_ = locale_man.loadTranslator(True)## FIXME
#from scal2.locale_man import tr as _

from scal2.core import convert, getMonthName, getMonthLen

#core.showInfo()

from scal2 import ui
from scal2.ui import showYmArrows

from scal2.monthcal import getMonthStatus, getCurrentMonthStatus

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

from scal2.ui_qt.app import app
from scal2.ui_qt.utils import *
from scal2.ui_qt.mywidgets import HBox, VBox
from scal2.ui_qt.mywidgets.expander import Expander
from scal2.ui_qt.mywidgets.about_dialog import AboutDialog

import scal2.ui_qt.export
import scal2.ui_qt.selectdate
from scal2.ui_qt import preferences
from scal2.ui_qt.preferences import qpixDir
from scal2.ui_qt.customize import CustomizableWidgetWrapper, MainWinItem, CustomizeDialog
from scal2.ui_qt.monthcal import MonthCal, qfontEncode



#core.COMMAND = sys.argv[0] ## OR __file__ ## ????????
core.COMMAND = 'starcal2-qt'
ui.uiName = 'qt'

def liveConfChanged():
    tm = now()
    if tm-ui.lastLiveConfChangeTime > 0.5:
        timer = qc.QTimer()
        timer.connect(timer, qc.SIGNAL('timeout()'), ui.saveLiveConfLoop)
        timer.start(ui.saveLiveConfDelay*1000)
    ui.lastLiveConfChangeTime = tm


######
if rtl:
    app.setLayoutDirection(qc.Qt.RightToLeft)
######
app.setWindowIcon(qt.QIcon(ui.logo))


app.connect(app, qc.SIGNAL('aboutToQuit()'), ui.saveLiveConf) ## ??????



geo = qt.QApplication.desktop().screenGeometry()
screenW = geo.width()
screenH = geo.height()


qc.QTextCodec.setCodecForTr(qc.QTextCodec.codecForName("utf-8"))
qc.QTextCodec.setCodecForCStrings(qc.QTextCodec.codecForName("utf-8"))


################# function and class defenitions ###############################


class MonthLabel(qt.QLabel):
    def __init__(self, mode, active=0):
        assert 0<=active<12
        self.mode = mode
        self.module = core.modules[mode]
        s = getMonthName(mode, active+1)
        qt.QLabel.__init__(self, s)
        self.setAlignment(qc.Qt.AlignCenter)
        menu = qt.QMenu(self)
        actions = []
        for i in range(12):
            if ui.monthRMenuNum:
                text = '%s: %s'%(_(i+1, fillZero=2), getMonthName(mode, i+1))
            else:
                text = getMonthName(mode, i+1)
            action = menu.addAction(text)
            action.index = i
            actions.append(action)
        self.connect(menu, qc.SIGNAL('triggered (QAction *)'), self.itemActivate)
        self.menu = menu
        self.menuWidth = 0
        self.menuHeight = 200
        self.actions = actions
        self.active = active
        self.setActive(active)
    def setActive(self, active):
        ## (Performance) update menu here, or make menu entirly before popup ????????????????
        #assert 0<=active<12
        self.setText(getMonthName(self.mode, active+1))
        if not locale_man.langSh in ('', 'en'):
            self.setToolTip(core.modules[self.mode].getMonthName(active+1)) ## not translation
        self.active = active
        self.show()
    def changeMode(self, mode):
        self.mode = mode
        self.module = core.modules[mode]
        #if ui.boldYmLabel:
        #    self.setText('<b>%s</b>'%getMonthName(mode, self.active+1))
        #else:
        self.setText(getMonthName(mode, self.active+1))
    def itemActivate(self, action):
        if not hasattr(action, 'index'):
            return
        item = action.index
        self.setActive(item)
        self.emit(qc.SIGNAL('changed'), self, item)
    def mousePressEvent(self, event):
        #print('starcal_qt: mousePressEvent')
        button = event.button()
        #if button!=qc.Qt.RightButton:
        #    event.ignore()
        #    return
        x = event.globalX() - self.menuWidth/2 ## center
        y = event.globalY() - (self.active+0.5)*self.menuHeight/12
        self.menu.setActiveAction(self.actions[self.active])
        self.menu.popup(qc.QPoint(x, y))
        ui.updateFocusTime()
        event.accept()
    def onConfigChange(self):
        self.menuWidth = self.menu.sizeHint().width()
        self.menuHeight = self.menu.sizeHint().height()




class ArrowToolButton(qt.QToolButton):
    def __init__(self, arrowType, parent=None):
        qt.QToolButton.__init__(self, parent)
        self.setArrowType(arrowType)
    def event(self, ev):
        t = ev.type()
        if t==100:## exiting ## 100==qc.QEvent.StyleChange
            return True ## FIXME
        if t in (qc.QEvent.HoverEnter, qc.QEvent.GraphicsSceneHoverEnter):
            self.emit(qc.SIGNAL('mouseEnter'))
        elif t in (qc.QEvent.HoverLeave, qc.QEvent.GraphicsSceneHoverLeave):
            self.emit(qc.SIGNAL('mouseLeave'))
        return qt.QToolButton.event(self, ev)


class IntLabel(qt.QLabel):## label_id is the same calendar mode for a year label
    itemsNum = 9
    arrowHeight = 15
    def __init__(self, label_id):
        self.label_id = label_id
        active = 0
        qt.QLabel.__init__(self, _(active))
        self.setAlignment(qc.Qt.AlignCenter)
        self.menu = qt.QMenu(self)
        self.menuWidth = 0
        self.menuHeight = 200
        #self.connect(self.menu, qc.SIGNAL('aboutToShow()'), self.updateMenu)
        #self.menu.scroll = self.scroll
        self.menu.wheelEvent = self.menuWheelEvent
        ##########
        upArrow = ArrowToolButton(qc.Qt.UpArrow, self)
        upArrow.setFixedHeight(self.arrowHeight)
        self.connect(upArrow, qc.SIGNAL('mouseEnter'), self.upArrowSelect)
        self.connect(upArrow, qc.SIGNAL('mouseLeave'), self.upArrowDeselect)
        self.upAction = qt.QWidgetAction(self)
        self.upAction.setDefaultWidget(upArrow)
        ########
        downArrow = ArrowToolButton(qc.Qt.DownArrow, self)
        downArrow.setFixedHeight(self.arrowHeight)
        self.connect(downArrow, qc.SIGNAL('mouseEnter'), self.downArrowSelect)
        self.connect(downArrow, qc.SIGNAL('mouseLeave'), self.downArrowDeselect)
        self.downAction = qt.QWidgetAction(self)
        self.downAction.setDefaultWidget(downArrow)
        ##########
        self.start = 0
        self._remain = 0
        self.etime = 0
        self.step = 0
        #########
        actions = []
        self.menu.addAction(self.upAction)
        for i in range(self.itemsNum):
            action = qt.QAction('none', self)
            action.index = i
            self.menu.addAction(action)
            actions.append(action)
        self.menu.addAction(self.downAction)
        self.actions = actions
        self.connect(self.menu, qc.SIGNAL('triggered (QAction *)'), self.itemActivate)
        self.connect(self.menu, qc.SIGNAL('aboutToShow ()'), self.updateMenu)
        self.setActive(active)
        ##########
        #self.menu.connect('map', lambda obj: self.drag_highlight())
        #self.menu.connect('unmap', lambda obj: self.drag_unhighlight())
        #########
        #self.connect('enter-notify-event', self.highlight)
        #self.connect('leave-notify-event', self.unhighlight)
    def setActive(self, active):
        self.setText(_(active))
        self.active = active
    def updateMenu(self):
        for action in self.actions:
            action.setText(_(self.start + action.index))
    def itemActivate(self, action):
        if not hasattr(action, 'index'):
            return
        num = self.start + action.index
        self.setActive(num)
        self.emit(qc.SIGNAL('changed'), self, num)
    def mousePressEvent(self, event):
        #if event.button()==qc.Qt.RightButton:
        index = self.itemsNum/2
        start = self.active - index
        self.start = start
        for i in range(self.itemsNum):
            self.actions[i].setText(_(start+i))
            self.actions[i].num = start+i
        self.menu.setActiveAction(self.actions[index])
        x = event.globalX() - self.menuWidth/2
        y = event.globalY() - ((index+0.5)/self.itemsNum)*self.menuHeight
        event.accept()
        self.menu.popup(qc.QPoint(x, y))
        #else:
        #    event.ignore()
    def upArrowSelect(self):
        self._remain = -1
        qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.upArrowRemain)
    def downArrowSelect(self):
        self._remain = 1
        qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.downArrowRemain)
    def upArrowDeselect(self):
        self._remain = 0
    def downArrowDeselect(self):
        self._remain = 0
    def upArrowRemain(self):
        if self._remain != -1:
            return
        t = now()
        if t-self.etime<ui.labelMenuDelay-0.02:
            if self.step>1:
                self.step = 0
                return
            else:
                self.step += 1
                self.etime = t #??????????
                qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.upArrowRemain)
        else:
            self.start -= 1
            self.updateMenu()
            self.etime = t
            qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.upArrowRemain)
    def downArrowRemain(self):
        if self._remain != 1:
            return
        t = now()
        if t-self.etime<ui.labelMenuDelay-0.02:
            if self.step>1:
                self.step = 0
                return
            else:
                self.step += 1
                self.etime = t #??????????
                qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.downArrowRemain)
        else:
            self.start += 1
            self.updateMenu()
            self.etime = t
            qc.QTimer.singleShot(int(ui.labelMenuDelay*1000), self.downArrowRemain)
    def arrowRemain(self, plus):
        t = now()
        if self._remain!=plus:
            return False
        if t-self.etime<ui.labelMenuDelay-0.02:
            if self.step>1:
                self.step = 0
                return False
            else:
                self.step += 1
                self.etime = t #??????????
                return True
        else:
            self.start += plus
            self.updateMenu()
            self.etime = t
            return True
    def menuWheelEvent(self, event):
        if event.orientation()==qc.Qt.Vertical:
            if event.delta()>0:
                self.start -= 1
            else:
                self.start += 1
            self.updateMenu()
    def onConfigChange(self):
        self.menuWidth = self.menu.sizeHint().width()
        self.menuHeight = self.menu.sizeHint().height()


BUTTON_MIN     = 0
BUTTON_MAX     = 1
BUTTON_CLOSE   = 2
#BUTTON_STICK
#BUTOON_ABOVE
#BUTTON_BELOW
BUTTON_SEP     = 4
BUTTON_MENU    = 5 ## ???????????????????


class WinConButton(qt.QLabel):
    IMAGE_NAMES = (('button-min.png',   'button-min-focus.png'),
                   ('button-max.png',   'button-max-focus.png'),
                   ('button-close.png', 'button-close-focus.png'))
    IMAGE_INACTIVE = 'button-inactive.png'
    TOOLTIPS = (_('Minimize Window'), _('Maximize Window'), _('Close Window'))
    STATE_NORM     = 0
    STATE_FOCUS    = 1
    STATE_INACTIVE = 2
    def __init__(self, buttonType, win):
        qt.QLabel.__init__(self, win)
        self.setAlignment(qc.Qt.AlignTop)## does not work? FIXME
        self.win =    win
        self.type = buttonType
        self.pix = (
            qt.QPixmap('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[buttonType][0])),
            qt.QPixmap('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[buttonType][1])),
            qt.QPixmap('%s/wm/%s'%(pixDir, self.IMAGE_INACTIVE))
        )
        self.setToolTip(self.TOOLTIPS[buttonType])
        self.setState(self.STATE_NORM)
    setState = lambda self, state: self.setPixmap(self.pix[state])
    setNorm    = lambda self: self.setState(self.STATE_NORM)
    setFocus = lambda self: self.setState(self.STATE_FOCUS)
    setInactive = lambda self: self.setState(self.STATE_INACTIVE)
    def event(self, ev):
        t = ev.type()
        if t==qc.QEvent.Enter:
            self.setState(self.STATE_FOCUS)
            return True
        elif t==qc.QEvent.Leave:
            if self.win.isActiveWindow():
                self.setState(self.STATE_NORM)
            else:
                self.setState(self.STATE_INACTIVE)
            return True
        elif t==qc.QEvent.MouseButtonPress:
            self.setState(self.STATE_NORM)
            return True
        elif t==qc.QEvent.MouseButtonRelease:
            if ev.button()==qc.Qt.LeftButton:
                if 0 <= ev.x() < self.width() and 0 <= ev.y() < self.height():
                    if self.type==BUTTON_MIN:
                        #self.win.setWindowState(qc.Qt.WindowMinimized)## does not work!!
                        self.win.showMinimized()
                    elif self.type==BUTTON_MAX:
                        if self.win.windowState()==qc.Qt.WindowMaximized:
                            #self.win.setWindowState(qc.Qt.WindowNoState)##?????
                            self.win.showNormal()
                        else:
                            #self.win.setWindowState(qc.Qt.WindowMaximized)
                            self.win.showMaximized()
                    elif self.type==BUTTON_CLOSE:
                        self.win.close()
                return True
        return qt.QLabel.event(self, ev)


class WinConMenuButton(qt.QLabel):## FIXME
    def __init__(self, buttonType, win):
        qt.QLabel.__init__(self, win)
        self.win =    win
        self.type = BUTTON_MENU
        #############
        self.pixNorm = qt.QPixmap(ui.logo)
        self.pixInactive = qt.QPixmap('%s/starcal-inactive.png'%pixDir)
        #############
        menu = qt.QMenu(self) ## parent = self OR win ????????
        #minAction
        #maxAction
        #closeAction
        self.menu = menu
        self.setNorm()
    setNorm = lambda self: self.setPixmap(self.pixNorm)
    setInactive = lambda self: self.setPixmap(self.pixInactive)



class WinController(qt.QWidget):
    def __init__(self, win, reverse=False, buttonSize=23, spacing=0):
        self.buttons = []
        qt.QWidget.__init__(self, win)
        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        #self.setFixedHeight(buttonSize*2)
        self.setFixedHeight(30)
        ###########
        if ui.winTaskbar:
            buttonTypes = [BUTTON_SEP, BUTTON_MIN, BUTTON_MAX, BUTTON_CLOSE]
        else:
            buttonTypes = [BUTTON_SEP, BUTTON_CLOSE]
        if reverse:
            buttonTypes.reverse()
        self.buttonTypes = buttonTypes
        ###########
        hbox = qt.QHBoxLayout(self)
        hbox.setMargin(0)
        hbox.setSpacing(spacing)
        for typ in buttonTypes:
            if typ==BUTTON_SEP:
                hbox.addStretch()
            else:
                button = WinConButton(typ, win)
                button.setFixedSize(qc.QSize(buttonSize, buttonSize))
                self.buttons.append(button)
                hbox.addWidget(button)
        self.setLayout(hbox)
    def event(self, ev):
        if hasattr(self, 'buttons'):
            t = ev.type()
            if t==qc.QEvent.WindowActivate:
                for b in self.buttons:
                    b.setNorm()
            elif t==qc.QEvent.WindowDeactivate:
                for b in self.buttons:
                    b.setInactive()
        return qt.QWidget.event(self, ev)


class VSeparator(qt.QLabel):
    def __init__(self, parent=None):
        qt.QLabel.__init__(self, '|', parent)
        self.setAlignment(qc.Qt.AlignCenter)
        self.setEnabled(False)
        #self.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)## FIXME



class FClockLabel(qt.QLabel):
    def __init__(self, parent=None):
        '''format is a string that used in strftime(), it can contains markup that apears in GtkLabel
        for example format can be "<b>%T</b>"
        local is bool. if True, use Local time, and if False, use GMT time
        selectable is bool that passes to GtkLabel'''
        qt.QLabel.__init__(self, parent)
        self.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
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
            ##timeout_add(int(1000*(1-now()%1)), self.update)
            self.timer.singleShot(int(1000*(1-now()%1)), self.update)
            try:
                self.setText(strftime(self.format).decode('utf-8'))
            except:
                pass
    def stop(self):
        self.running = False
    def updateFormat(self):
        #self.format = removePangoMarkup(preferences.clockFormat)
        self.format = preferences.clockFormat


class CustomizableToolbar(qt.QToolBar, MainWinItem):
    styleList = ('Icon', 'Text', 'Text beside Icon', 'Text below Icon')
    setIconSize = lambda self, size: qt.QToolBar.setIconSize(self, qc.QSize(size, size))
    def __init__(self, mainWin):
        qt.QToolBar.__init__(self, mainWin)
        self.mainWin = mainWin
        #self.setContentsMargins(0, 0, 0, 0)## does not work FIXME
        #self.setIconSizeName(ui.toolbarIconSize)
        optionsWidget = VBox()
        ###
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(qt.QLabel(_('Style')))
        self.styleCombo = qt.QComboBox()
        for item in self.styleList:
            self.styleCombo.addItem(_(item))
        hbox.addWidget(self.styleCombo)
        self.connect(self.styleCombo, qc.SIGNAL('currentIndexChanged (int)'), self.styleComboChanged)
        styleNum = self.styleList.index(ui.toolbarStyle)
        self.styleCombo.setCurrentIndex(styleNum)
        self.setToolButtonStyle(styleNum)
        optionsWidget.addLayout(hbox)
        ###
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        self.iconSizeLabel = qt.QLabel(_('Icon Size'))
        hbox.addWidget(self.iconSizeLabel)
        self.iconSizeSpin = qt.QSpinBox()
        self.iconSizeSpin.setRange(2, 64)
        self.iconSizeSpin.setValue(ui.toolbarIconSizePixel)
        self.setIconSize(ui.toolbarIconSizePixel)
        hbox.addWidget(self.iconSizeSpin)
        self.connect(self.iconSizeSpin, qc.SIGNAL('valueChanged (int)'), self.iconSizeSpinChanged)
        optionsWidget.addLayout(hbox)
        #self.iconSizeHbox = hbox
        ###
        MainWinItem.__init__(self, 'toolbar', _('Toolbar'), optionsWidget=optionsWidget)
    def iconSizeSpinChanged(self, value):
        self.setIconSize(value)
    def styleComboChanged(self, index):
        self.iconSizeLabel.setEnabled(index!=1)
        self.iconSizeSpin.setEnabled(index!=1)
        self.setToolButtonStyle(index)
    def addButton(self, tbItem, enable):
        action = tbItem.makeAction(self.mainWin)
        qt.QToolBar.addAction(self, action)
        self.items.append(CustomizableWidgetWrapper(action, tbItem.name, tbItem.tooltip, enable=enable))
    def updateVars(self):
        ui.toolbarItems = [(child._name, child.enable) for child in self.items]
        ui.toolbarIconSizePixel = int(self.iconSizeSpin.value())
        ui.toolbarStyle = self.toolbarStyleList[self.styleCombo.currentIndex()]
    def confStr(self):
        text = ''
        for mod_attr in ('ui.toolbarItems', 'ui.toolbarIconSizePixel', 'ui.toolbarStyle'):
            text += '%s=%r\n'%(mod_attr, eval(mod_attr))
        return text
    def moveItemUp(self, i):## FIXME
        self.removeAction(self.items[i].widget)
        self.insertAction(self.items[i-1].widget, self.items[i].widget)
        self.items.insert(i-1, self.items.pop(i))

setFizedWidthSquare = lambda widget: widget.setFixedWidth(widget.minimumSizeHint().height())

prevTxt = '<'
nextTxt = '>'

class YearMonthLabelBox(HBox, MainWinItem): ## FIXME
    def __init__(self):
        HBox.__init__(self)
        MainWinItem.__init__(self, 'labelBox', _('Year & Month Labels'))
        self.wgroup = [[] for i in range(ui.shownCalsNum)]
        self.yearLabel = [None for i in range(ui.shownCalsNum)]
        self.monthLabel = [None for i in range(ui.shownCalsNum)]
        #############################
        def addNewArrow(text):
            arrow = qt.QPushButton(text)
            setFizedWidthSquare(arrow)
            arrow.setFocusPolicy(qc.Qt.NoFocus)
            self.addWidget(arrow)
            self.wgroup[0].append(arrow)
            return arrow
        if showYmArrows:
            self.arrowPY = addNewArrow(prevTxt)
        label = IntLabel(core.primaryMode)
        self.yearLabel[0] = label
        #label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        self.connect(label, qc.SIGNAL('changed'), self.yearLabelChange)
        self.addWidget(label)
        self.wgroup[0].append(label)
        if showYmArrows:
            self.arrowNY = addNewArrow(nextTxt)
            sep = VSeparator()
            self.addWidget(sep)
            #self.addStretch()
            self.wgroup[0].append(sep)
            self.arrowPM = addNewArrow(prevTxt)
        label = MonthLabel(core.primaryMode)
        self.monthLabel[0] = label
        self.connect(label, qc.SIGNAL('changed'), self.monthLabelChange)
        self.addWidget(label)
        self.wgroup[0].append(label)
        if showYmArrows:
            self.arrowNM = addNewArrow(nextTxt)
            #######
            #self.arrowsUpdate()
        #############################
        for i in range(1, ui.shownCalsNum):
            mode = ui.shownCals[i]['mode']
            sep = VSeparator()
            self.addWidget(sep)
            #self.addStretch()
            self.wgroup[i-1].append(sep)
            self.wgroup[i].append(sep) ##??????????
            #if i==1: self.vsep0 = sep
            ###############
            label = IntLabel(mode)
            self.yearLabel[i] = label
            label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            self.connect(label, qc.SIGNAL('changed'), self.yearLabelChange)
            self.addWidget(label)
            self.wgroup[i].append(label)
            ###############
            label = qt.QLabel('')
            label.setFixedWidth(5)
            self.addWidget(label)
            self.wgroup[i].append(label)
            ###############
            label = MonthLabel(mode)
            self.monthLabel[i] = label
            label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            self.connect(label, qc.SIGNAL('changed'), self.monthLabelChange)
            self.addWidget(label)
            self.wgroup[i].append(label)
        #############################
        if showYmArrows:
            py = self.arrowPY ## previous year
            ny = self.arrowNY ## next year
            pm = self.arrowPM ## previous month
            nm = self.arrowNM ## next month
            #########
            py.setAutoRepeat(True)
            py.setAutoRepeatDelay(300)
            py.setAutoRepeatInterval(150)
            #########
            ny.setAutoRepeat(True)
            ny.setAutoRepeatDelay(300)
            ny.setAutoRepeatInterval(150)
            #########
            pm.setAutoRepeat(True)
            pm.setAutoRepeatDelay(300)
            pm.setAutoRepeatInterval(150)
            #########
            nm.setAutoRepeat(True)
            nm.setAutoRepeatDelay(300)
            nm.setAutoRepeatInterval(150)
            #########
            self.connect(py, qc.SIGNAL('clicked()'), lambda: self.yearPlus(-1))
            self.connect(ny, qc.SIGNAL('clicked()'), lambda: self.yearPlus(1))
            self.connect(pm, qc.SIGNAL('clicked()'), lambda: self.monthPlus(-1))
            self.connect(nm, qc.SIGNAL('clicked()'), lambda: self.monthPlus(1))
            #############################
            py.setToolTip(_('Previous Year'))
            ny.setToolTip(_('Next Year'))
            pm.setToolTip(_('Previous Month'))
            nm.setToolTip(_('Next Month'))
    def monthPlus(self, plus=1):
        ui.monthPlus(plus)
        self.onDateChange()
        self.emit(qc.SIGNAL('date-change'), self)
    #def monthButtonPress(self, widget, plus, remain=True):
    #def monthButtonRemain(self, plus):
    def yearPlus(self, plus=1):
        ui.yearPlus(plus)
        self.onDateChange()
        self.emit(qc.SIGNAL('date-change'), self)
    #def yearButtonPress(self, widget, plus, remain=True):
    #def yearButtonRemain(self, plus):
    #def arrowRelease(self, widget):
    def yearLabelChange(self, ylabel, year):
        mode = ylabel.label_id
        p_year, p_month, p_day = ui.cell.dates[mode]
        ui.changeDate(*convert(year, p_month, p_day, mode, core.primaryMode))
        self.onDateChange()
        self.emit(qc.SIGNAL('date-change'), self)
    def monthLabelChange(self, mlabel, item):
        #print('monthLabelChange', item, mlabel.mode)
        p_year, p_month, p_day = ui.cell.dates[mlabel.mode]
        ui.changeDate(*convert(p_year, item+1, p_day, mlabel.mode, core.primaryMode))
        self.onDateChange()
        self.emit(qc.SIGNAL('date-change'), self)
    """
    def updateArrows(self):
        if showYmArrows:
            if isinstance(preferences.prevStock, str):
                self.arrowPY.set_image(gtk.image_new_from_stock(preferences.prevStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
                self.arrowPM.set_image(gtk.image_new_from_stock(preferences.prevStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
            elif isinstance(preferences.prevStock, gtk._gtk.ArrowType):
                if self.arrowPY.child!=None:
                    self.arrowPY.remove(self.arrowPY.child)
                arrow = gtk.Arrow(preferences.prevStock, gtk.SHADOW_IN)
                self.arrowPY.add(arrow)
                arrow.show()
                ######
                if self.arrowPM.child!=None:
                    self.arrowPM.remove(self.arrowPM.child)
                arrow = gtk.Arrow(preferences.prevStock, gtk.SHADOW_IN)
                self.arrowPM.add(arrow)
                arrow.show()
            #################
            if isinstance(preferences.nextStock, str):
                self.arrowNY.set_image(gtk.image_new_from_stock(preferences.nextStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
                self.arrowNM.set_image(gtk.image_new_from_stock(preferences.nextStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
            elif isinstance(preferences.nextStock, gtk._gtk.ArrowType):
                if self.arrowNY.child!=None:
                    self.arrowNY.remove(self.arrowNY.child)
                arrow = gtk.Arrow(preferences.nextStock, gtk.SHADOW_IN)
                self.arrowNY.add(arrow)
                arrow.show()
                ######
                if self.arrowNM.child!=None:
                    self.arrowNM.remove(self.arrowNM.child)
                arrow = gtk.Arrow(preferences.nextStock, gtk.SHADOW_IN)
                self.arrowNM.add(arrow)
                arrow.show()
    """
    def updateTextWidth(self):
        ############### update width of month labels
        #met = qt.QFontMetrics(qfontEncode(ui.getFont()))
        met = app.fontMetrics()
        ###
        monthWidth = []
        for module in core.modules:
            wm = 0
            for m in range(12):
                name = _(module.getMonthName(m))
                n = len(name)
                w = 0
                for i in range(n):
                    w += met.charWidth(name, i)
                if w > wm:
                    wm = w
            monthWidth.append(wm)
        for i in range(len(ui.shownCals)):
            mode = ui.shownCals[i]['mode']
            self.monthLabel[i].setFixedWidth(monthWidth[mode])
        ###
        yearWidth = int(4 * max([met.charWidth(_(i), 0) for i in range(10)]))
        for label in self.yearLabel:
            label.setFixedWidth(yearWidth)
    def onConfigChange(self):
        self.updateTextWidth()
        #self.updateArrows()
        #####################
        for i in range(len(self.monthLabel)):
            self.monthLabel[i].changeMode(ui.shownCals[i]['mode'])
            self.monthLabel[i].onConfigChange()
            self.yearLabel[i].onConfigChange()
        #####################
        for i in range(ui.shownCalsNum):
            if ui.shownCals[i]['enable']:
                showList(self.wgroup[i])
            else:
                hideList(self.wgroup[i])
        #if not ui.shownCals[0]['enable']:##???????
        #    self.vsep0.hide()
    def onDateChange(self):
        for (i, item) in enumerate(ui.shownCals):
            if item['enable']:
                y, m, d = ui.cell.dates[item['mode']]
                self.monthLabel[i].setActive(m-1)
                self.yearLabel[i].setActive(y)






class StatusBox(qt.QStatusBar, MainWinItem): ## FIXME
    def __init__(self):
        qt.QStatusBar.__init__(self)
        #self.setSizeGripEnabled(True)
        self.setLayoutDirection(qc.Qt.LeftToRight)
        MainWinItem.__init__(self, 'statusBar', _('Status Bar'))
    def onDateChange(self):## updateDateLabels
        n = ui.shownCalsNum
        text = ''
        shownCals = list(ui.shownCals[:])
        if rtl:
            shownCals.reverse()
        for item in shownCals:
            if item['enable']:
                mode = item['mode']
                text += (' ' + ui.cell.format(preferences.dateFormatBin, mode))
        met = app.fontMetrics()
        count = (self.width() - met.width(text))//(met.width(' ')*(n+1))
        text = text.replace(' ', ' '*count)
        self.showMessage(text)
        #print(self.width(), met.width(text))

"""
class PluginsTextBox(VBox, MainWinItem):
    def __init__(self, window=None, populatePopupFunc=None):
        VBox.__init__(self)
        self.enableExpander = ui.pluginsTextInsideExpander ## FIXME
        self.window = window
        #####
        self.textview = qt.QTextEdit()
        self.textview.setLineWrapMode(qt.QTextEdit.WidgetWidth)
        self.textview.setWordWrapMode(qt.QTextOption.WordWrap)
        self.textview.setReadOnly(True)
        self.textview.setCursorWidth(0) ## ?????????? set_cursor_visible(False)
        self.textview.setAlignment(qc.Qt.AlignHCenter)
        self.textview.setVerticalScrollBarPolicy(qc.Qt.ScrollBarAlwaysOff)
        self.textview.setHorizontalScrollBarPolicy(qc.Qt.ScrollBarAlwaysOff)
        #if populatePopupFunc:
        #    self.textview.connect('populate-popup', populatePopupFunc)## FIXME
        #####
        self.expander = Expander(parent=self, window=None, indent=5)
        def pluginsTextBoxExpanded(item):
            ui.pluginsTextIsExpanded = True
            ui.saveLiveConf()
        def pluginsTextBoxCollapsed(item):
            ui.pluginsTextIsExpanded = False
            ui.saveLiveConf()
            if self.window:
                self.get_window().setMinHeightLater()
        self.connect(self.expander, qc.SIGNAL('itemExpanded (QTreeWidgetItem *)'), pluginsTextBoxExpanded)
        self.connect(self.expander, qc.SIGNAL('itemCollapsed (QTreeWidgetItem *)'), pluginsTextBoxCollapsed)
        if self.enableExpander:
            self.expander.addWidget(self.textview)
            self.addWidget(self.expander)
            self.expander.setExpanded(ui.pluginsTextIsExpanded)
        else:
            self.addWidget(self.textview)
        #####
        self.show() ## FIXME
        #####
        optionsWidget = HBox()
        self.enableExpanderCheckb = qt.QCheckBox(_('Inside Expander'))
        self.enableExpanderCheckb.setCheckState(qc.Qt.Checked if self.enableExpander\
                                                else qc.Qt.Unchecked)
        self.connect(self.enableExpanderCheckb, qc.SIGNAL('stateChanged (int)'), self.enableExpanderCheckbStateChanged)
        self.setEnableExpander(self.enableExpander)
        optionsWidget.addWidget(self.enableExpanderCheckb)
        ####
        MainWinItem.__init__(self, 'pluginsText', _('Plugins Text'), optionsWidget=optionsWidget)
    def enableExpanderCheckbStateChanged(self, state):
        print('enableExpanderCheckbStateChanged')
        self.setEnableExpander(state == qc.Qt.Checked)
        #qt.QCheckBox.stateChanged(self.enableExpanderCheckb, state)
    getWidget = lambda self: self.expander if self.enableExpander else self.textview
    def minimumSizeHint(self):
        self.textview.document().setTextWidth(self.width())
        return self.textview.document().size().toSize()
    def fixHeight(self):
        self.textview.document().setTextWidth(self.width())
        h = self.textview.document().size().height()
        self.textview.setMaximumHeight(h)
        #self.textview.setMaximumHeight(h)## no need, and no different
    def setText(self, text):
        if text:
            #text = text.replace('\t', '\n') ## FIXME
            self.textview.setText(text)
            self.getWidget().show()
            #self.fixHeight()
        else:
            self.textview.setText('')## forethought
            self.getWidget().hide()
        if self.window:
            self.get_window().setMinHeightLater()
    def setEnableExpander(self, enable):
        #print('setEnableExpander', enable)
        if enable:
            if not self.enableExpander:
                self.removeWidget(self.textview)
                self.expander.addWidget(self.textview)
                self.addWidget(self.expander)
                #self.expander.setExpanded(False)
                #self.expander.setExpanded(True)
                self.expander.show()
        else:
            if self.enableExpander:
                self.expander.removeWidget()
                self.removeWidget(self.expander)
                self.addWidget(self.textview)
                self.textview.show()
        self.enableExpander = enable
    def updateVars(self):
        ui.pluginsTextInsideExpander = self.enableExpander
    def confStr(self):
        text = ''
        for mod_attr in ('ui.pluginsTextInsideExpander',):
            text += '%s=%r\n'%(mod_attr, eval(mod_attr))
        return text
"""


class PluginsTextBox(qt.QTextBrowser, MainWinItem):
    def __init__(self, populatePopupFunc=None):
        qt.QTextBrowser.__init__(self)
        self.setAlignment(qc.Qt.AlignCenter)
        self.setLineWrapMode(qt.QTextEdit.WidgetWidth)
        self.setWordWrapMode(qt.QTextOption.WordWrap)
        self.setReadOnly(True)
        self.setCursorWidth(0) ## ?????????? set_cursor_visible(False)
        self.setVerticalScrollBarPolicy(qc.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(qc.Qt.ScrollBarAlwaysOff)
        #if populatePopupFunc:
        #    self.connect('populate-popup', populatePopupFunc)## FIXME
        #####
        #self.show() ## FIXME
        MainWinItem.__init__(self, 'pluginsText', _('Plugins Text'))
    def fixHeight(self):
        self.document().setTextWidth(self.width())
        h = self.document().size().height() # + 5
        self.setMaximumHeight(h)
        #self.setMaximumHeight(h)## no need, and no different
    def setText(self, text):
        if text:
            text = '<center>%s</center>'%text.replace('\t', '&nbsp;'*4).replace('\n', '<br>')
            qt.QTextBrowser.setText(self, text)
            self.show()
            self.fixHeight()
        else:
            qt.QTextBrowser.setText(self, '')## forethought
            self.hide()
    def confStr(self):
        text = ''
        for mod_attr in ('ui.pluginsTextInsideExpander',):
            text += '%s=%r\n'%(mod_attr, eval(mod_attr))
        return text
    def onDateChange(self):
        self.setText(ui.cell.pluginsText)

class CustomDayWidget(HBox, MainWinItem):
    def __init__(self, populatePopupFunc=None):
        HBox.__init__(self)
        self.textview = qt.QTextBrowser()
        self.textview.setLineWrapMode(qt.QTextEdit.WidgetWidth)
        self.textview.setWordWrapMode(qt.QTextOption.WordWrap)
        self.textview.setReadOnly(True)
        self.textview.setCursorWidth(0) ## ?????????? set_cursor_visible(False)
        #self.textview.setAlignment(qc.Qt.AlignHCenter)## FIXME
        self.addWidget(self.textview)
        #if populatePopupFunc
        #  self.textview.connect('populate-popup', populatePopupFunc)## FIXME
        MainWinItem.__init__(self, 'customDayText', _('CustomDay Text'))
    def fixHeight(self):
        self.textview.document().setTextWidth(self.width())
        h = self.textview.document().size().height()
        self.textview.setMaximumHeight(h)
    def setData(self, data):## {'type': type, 'desc':desc}
        if data:
            cd = ui.cell.customday
            imgPath = '%s%s%s'%(ui.pixDir, os.sep, ui.customdayModes[data['type']][1])
            self.textview.setText('<IMG>%s</IMG> %s'%(imgPath, data['desc']))
            self.textview.show()
            self.fixHeight()
        else:
            self.textview.setText('')## forethought
            self.textview.hide()
    def onDateChange(self):
        self.setData(ui.cell.customday)



class MainWin(qt.QMainWindow):
    menuCellWidth = 145
    menuMainWidth = 145
    timeout = 1 ## second
    setMinHeight = lambda self: self.resize(ui.winWidth, 2)
    setMinHeightLater = lambda self: qc.QTimer.singleShot(100, self.setMinHeight)
    def setKeepAbove(self, above):
        if above:
            self.setWindowFlags(self.windowFlags() | qc.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~qc.Qt.WindowStaysOnTopHint)
    def getMyWindowFlags(self):
        if ui.winTaskbar:
            flags = qc.Qt.FramelessWindowHint
        else:
            flags = qc.Qt.FramelessWindowHint | qc.Qt.Tool
        if ui.winKeepAbove:
            flags = flags | qc.Qt.WindowStaysOnTopHint
        return flags
    def updateMyWindowFlags(self):
        self.setWindowFlags(self.getMyWindowFlags())
        self.show()
        #self.raise_()## does not work!
    def __init__(self, trayMode=2):
        qt.QMainWindow.__init__(self, None, self.getMyWindowFlags())
        self.setWindowIcon(qt.QIcon(ui.logo))
        self.setContentsMargins(0, 0, 0, 0)
        ##################
        ## trayMode:
            ## 0: none (simple window)
            ## 1: applet (gnome or plasma) ## ??????????
            ## 2: standard tray icon (QSystemTrayIcon)
        if trayMode>0 and not qt.QSystemTrayIcon.isSystemTrayAvailable():
            trayMode = 0
        self.trayMode = trayMode
        #self.customDay = scal2.ui_qt.customday.CustomDayDialog(self)
        ###########
        self.lastGDate = None
        #########
        self.setWindowTitle('%s %s'%(core.APP_DESC, core.VERSION))
        self.setWindowRole(core.APP_NAME)
        self.setMinHeight()
        #self.setBaseSize(ui.winWidth, ui.winHeight)
        self.move(ui.winX, ui.winY)
        #############################################################
        self.mcal = MonthCal(parent=self)
        self.connect(self.mcal, qc.SIGNAL('popup-menu-cell'), self.popupMenuCell)
        self.connect(self.mcal, qc.SIGNAL('popup-menu-main'), self.popupMenuMain)
        self.connect(self.mcal, qc.SIGNAL('2button-press'), ui.dayOpenEvolution)
        self.connect(self.mcal, qc.SIGNAL('pref-update-bg-color'), self.prefUpdateBgColor)
        ##################################################################
        ################## Making Actions ########################
        actionsDict = dict([(item.name, item.makeAction(self)) \
                            for item in preferences.toolbarItemsData + preferences.otherActionsData])
        ################## Building Toolbar ######################
        toolbar = CustomizableToolbar(self)
        #####################
        if not ui.toolbarItems:
            ui.toolbarItems = [(item.name, True) for item in preferences.toolbarItemsData]
        for (name, enable) in ui.toolbarItems:
            try:
                tbItem = preferences.toolbarItemsDataDict[name]
            except KeyError:
                myRaise()
            else:
                toolbar.addButton(tbItem, enable)
        self.toolbar = toolbar

        """
        hbox = qt.QHBoxLayout()
        #print('spacing', hbox.spacing())
        #print('margin', hbox.margin())
        hbox.addWidget(toolbar)
        hbox.addStretch()
        if ui.showDigClockTb:
            self.clock = FClockLabel(preferences.clockFormat)
            hbox.addWidget(self.clock)
        else:
            self.clock = None
        #self.clockTr = None
        self.toolbBox = hbox
        """
        #####################################################################################################
        self.vbox = VBox()
        #############################
        if ui.showWinController:
            self.buildWinCont()
        else:
            self.winCon = None
        ########
        self.setCentralWidget(self.vbox)
        ####################
        self.pluginsTextBox = PluginsTextBox()## self.populatePopup ## FIXME
        self.customDayWidget = CustomDayWidget()## self.populatePopup ## FIXME
        ####################
        defaultItems = [
            toolbar,
            YearMonthLabelBox(),
            self.mcal,
            StatusBox(),
            self.pluginsTextBox,
            self.customDayWidget
        ]
        defaultItemsDict = dict([(obj._name, obj) for obj in defaultItems])
        self.items = []
        self.customizeDialog = None
        for (name, enable) in ui.mainWinItems:
            try:
                item = defaultItemsDict[name]
            except:
                myRaise()
                continue
            item.enable = enable
            item.widget.resizeEvent = lambda event: self.childResizeEvent(item, event) ## FIXME
            self.connect(item, qc.SIGNAL('date-change'), self.onDateChange)
            item.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
            self.items.append(item)
        self.customizeDialog = CustomizeDialog(items=self.items, mainWin=self)
        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
        self.vbox.addWidget(self.customizeDialog.widget)
        nullWidget = qt.QWidget()
        nullWidget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
        self.vbox.addWidget(nullWidget)
        #self.customizeDialog.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
        #self.vbox.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
        self.vbox.show()
        ####################
        #self.setMinHeight()
        ############
        self.moving = False
        self.movingDef = (0, 0)
        ###########
        self.prefDialog = preferences.PrefDialog(self)
        self.export = scal2.ui_qt.export.ExportDialog(self)
        self.selectDateDialog = scal2.ui_qt.selectdate.SelectDateDialog()
        self.connect(self.selectDateDialog, qc.SIGNAL('response-date'), self.selectDateResponse)
        ############### Building About Dialog
        about = AboutDialog()
        about.set_name(core.APP_DESC) ## or set_program_name
        about.set_version(core.VERSION)
        about.set_title(_('About ')+core.APP_DESC) ## must call after set_name and set_version !
        about.set_authors([_(line) for line in open(join(rootDir, 'authors-dialog')).read().splitlines()])
        about.set_comments(core.aboutText)
        about.set_license(core.licenseText)
        about.set_wrap_license(True)
        about.set_website(core.homePage) ## A palin label (not link)
        about.set_logo(ui.logo)
        self.about = about
        #################### Building menu of right click on the tray icon
        trayActionNames = ('copy_time', 'copy_date_today', 'adjust', 'preferences', 'about')
        ### When menu will show above the pointer
        menu = qt.QMenu()
        for name in trayActionNames:
            menu.addAction(actionsDict[name])
        menu.addSeparator()
        menu.addAction(actionsDict['quit'])
        self.menuTray = self.menuTray1 = menu
        ### When menu will show below the pointer
        menu = qt.QMenu()
        menu.addAction(actionsDict['quit'])
        menu.addSeparator()
        for name in reversed(trayActionNames):
            menu.addAction(actionsDict[name])
        self.menuTray2 = menu
        ########################################### Building main menu
        menu = qt.QMenu()
        ###### ????????????????????
        #action = menu.addAction(_('Resize'), self.startResize)## mousePressEvent
        #action.setIcon(qt.QIcon('%s/resize.png'%pixDir))
        ######
        self.actionAbove = menu.addAction(_('_On Top'), self.keepAboveClicked)
        self.actionAbove.setCheckable(True)
        self.actionAbove.setChecked(ui.winKeepAbove)
        ######
        #self.actionSticky = menu.addAction(_('_Sticky'), self.stickyClicked)
        #self.actionSticky.setCheckable(True)
        #self.actionSticky.setChecked(ui.winSticky)
        #if ui.winSticky:
        #    self.stick()##??????????????????????????????
        #####
        for name in ('today', 'date', 'customize', 'preferences', 'add', 'export', 'about'):
            menu.addAction(actionsDict[name])
        if self.trayMode!=1:
            menu.addAction(actionsDict['quit'])
        self.menuMain = menu
        ############################################################
        composited = False
        #try:
        #    if self.is_composited():
        #        composited = True
        #except AttributeError:
        #    pass
        ###############
        self.trayInit()
        if self.trayMode!=1:
            timerTray = qc.QTimer()
            #timerTray.setInterval(self.timeout*1000)
            self.connect(timerTray, qc.SIGNAL('timeout()'), self.trayUpdate)
            timerTray.start(self.timeout*1000)
        ######### Building menu of right click on a day
        menu = qt.QMenu()
        #menu.addAction(actionsDict['add'])
        menu.addAction(actionsDict['copy_date'])
        menu.addSeparator()
        menu.addAction(actionsDict['today'])
        menu.addAction(actionsDict['date'])
        if isfile('/usr/bin/evolution'):##??????????????????
            menu.addAction(qt.QIcon('%s/evolution-18.png'%pixDir), _('In E_volution'), ui.dayOpenEvolution)
        #if isfile('/usr/bin/sunbird'):##??????????????????
        #    menu.addAction(qt.QIcon('%s/sunbird-18.png'%pixDir), _('In E_volution'), ui.dayOpenSunbird)
        menu.num = 1
        self.menuCell1 = menu
        self.menuCell = menu ## may be changed later frequently, here just initialized
        ########## Building menu of right click on a day (that has CustomDay)
        menu = qt.QMenu()
        #menu.addAction(actionsDict['edit'])
        menu.addAction(actionsDict['copy_date'])
        #menu.addSeparator()
        #menu.addAction(actionsDict['remove'])
        menu.addSeparator()
        menu.addAction(actionsDict['today'])
        menu.addAction(actionsDict['date'])
        if isfile('/usr/bin/evolution'):##??????????????????
            menu.addAction(qt.QIcon('%s/evolution-18.png'%pixDir), _('In E_volution'), ui.dayOpenEvolution)
        #if isfile('/usr/bin/sunbird'):##??????????????????
        #    menu.addAction(qt.QIcon('%s/sunbird-18.png'%pixDir), _('In E_volution'), ui.dayOpenSunbird)
        menu.num = 2
        self.menuCell2 = menu
        ######################
        self.prefDialog.updatePrefGui()
        self.clipboard = qt.QApplication.clipboard()
        #########################################
        for plug in core.allPlugList:
            if plug.external and hasattr(plug, 'set_dialog'):
                plug.set_dialog(self)
        ########################### END OF MainWin.__init__
    #def mainWinStateEvent(self, obj, event):
        #print(dir(event))
        #print(event.new_window_state)
        #self.event = event
    selectDateShow = lambda self: self.selectDateDialog.show()
    def selectDateResponse(self, y, m, d):
        ui.changeDate(y, m, d)
        self.onDateChange()
    def keyPressEvent(self, event):
        k = event.key()
        #print(now(), 'MainWin.keyPressEvent', k, hex(k))
        ## file:///usr/share/doc/python-qt4-doc/html/qt.html#Key-enum
        ## file:///usr/share/doc/python-qt4-doc/html/qkeyevent.html
        if k==qc.Qt.Key_Escape:
            self.escPressed()
        elif k==qc.Qt.Key_F1:
            self.aboutShow()
        elif k in (qc.Qt.Key_Insert,qc.Qt.Key_Plus):# Insert or plus
            self.showCustomDay(month=ui.cell.month, day=ui.cell.day)
        elif k == qc.Qt.Key_Q:
            self.quit()
        #if Alt+F7: FIXME
        #    self.startManualMoving()
        else:
            for item in self.items:
                if item.enable and k in item.myKeys:
                    item.keyPressEvent(event)
        ## event.ignore() ## I dont want the event. Propagate to the parent widget.
        event.accept() ## I want the event. Do not propagate to the parent widget.
    def buildWinCont(self):
        try:
            self.winCon.destroy()
        except:
            pass
        self.winCon = WinController(self, reverse=True)
        #self.winCon.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.vbox.insertWidget(0, self.winCon)
        self.winCon.show()
    def destroyWinCont(self):
        self.winCon.destroy()
        self.winCon = None
    def childResizeEvent(self, child, event):
        child.widget.__class__.resizeEvent(child.widget, event)
        self.setMinHeightLater()
        event.accept()
    def resizeEvent(self, event):
        ## event.size() == self.size()
        size = event.size()
        ww = size.width()
        needRepaint = ui.bgUseDesk and max(abs(ui.winWidth-ww), abs(ui.winHeight-size.height())) > 1## or use event.ollSize
        ui.winWidth = ww
        if needRepaint:
            self.mcal.repaint()
        event.accept()
    def moveEvent(self, event):
        pos = event.pos()
        wx = pos.x()
        wy = pos.y()
        needRepaint = ui.bgUseDesk and max(abs(ui.winX-wx), abs(ui.winY-wy)) > 1## or use event.oldPos
        ui.winX = wx
        ui.winY = wy
        if needRepaint:
            self.mcal.repaint()
        event.accept()
    def startManualMoving(self, event):
        self.movingDef = event.pos()
        self.moving = True
        self.setCursor(qc.Qt.SizeAllCursor)
    def endManualMoving(self):
        self.moving = False
        self.setCursor(qc.Qt.ArrowCursor)
    def mousePressEvent(self, event):
        b = event.button()
        if b==qc.Qt.RightButton:
            self.menuMain.popup(event.globalPos())
            ui.updateFocusTime()
            #self.endManualMoving()
            event.accept()
        elif b==qc.Qt.LeftButton:
            if self.moving:
                self.endManualMoving()
            else:
                self.startManualMoving(event)
            event.accept()
    def mouseMoveEvent(self, event):
        if self.moving:
            self.move(event.globalPos() - self.movingDef)
    def mouseReleaseEvent(self, event):
        self.endManualMoving()
    """
    def startResize(self, widget, event):
        self.menuMain.hide()
        x, y, mask = rootWindow.get_pointer()
        self.begin_resize_drag(gdk.WINDOW_EDGE_SOUTH_EAST, event.button, x, y, event.time)
        return True
    """
    def changeDate(self, year, month, day):
        ui.changeDate(year, month, day)
        self.onDateChange()
    goToday = lambda self, widget=None: self.changeDate(*core.getSysDate())
    def onDateChange(self, sender=None):
        #print('MainWin.onDateChange, sender is %s instance'%sender.__class__.__name__)
        for item in self.items:
            if item.enable and item is not sender:
                #try:
                    item.onDateChange()
                #except AttributeError:
                #    print('item %s does not have onDateChange'%item._name)
        #for j in range(len(core.plugIndex)):##????????????????????
        #    try:
        #        core.allPlugList[core.plugIndex[j]].date_change(*date)
        #    except AttributeError:
        #        pass
        #self.setMinHeight()## FIXME
        if ui.cell.customday!=None:#if Cell has CustomDay
            self.menuCell = self.menuCell2
            self.menuCellWidth = self.menuCell2Width
        else:
            self.menuCell = self.menuCell1
            self.menuCellWidth = self.menuCell1Width
        for j in range(len(core.plugIndex)):
            try:
                core.allPlugList[core.plugIndex[j]].date_change_after(*date)
            except AttributeError:
                pass
    def popupMenuCell(self, x, y):
        p = self.mcal.mapToGlobal(qc.QPoint(x, y))
        x = p.x()
        y = p.y()
        if rtl:
            x -= self.menuCellWidth
        self.menuCell.popup(qc.QPoint(x, y))
        ui.updateFocusTime()
    def popupMenuMain(self, x, y):
        p = self.mcal.mapToGlobal(qc.QPoint(x, y))
        x = p.x()
        y = p.y()
        if rtl:
            x -= self.menuMainWidth
        self.menuMain.popup(qc.QPoint(x, y))
        ui.updateFocusTime()
    def prefUpdateBgColor(self, cal):
        self.prefDialog.colorbBg.set_color(ui.bgColor)
    def keepAboveClicked(self):
        ui.winKeepAbove = self.actionAbove.isChecked()
        self.updateMyWindowFlags()
        liveConfChanged()
    """
    def stickyClicked(self, check):
        if check.get_active():
            self.stick()
            ui.winSticky = True
        else:
            self.unstick()
            ui.winSticky = False
    """
    def updateMenuSize(self):
        ## To calc/update menus size
        self.menuCell1Width = self.menuCell1.sizeHint().width()
        self.menuCell2Width = self.menuCell2.sizeHint().width()
        self.menuMainWidth = self.menuMain.sizeHint().width()
        ###
        t1size = self.menuTray1.sizeHint()
        self.menuTray1Width = t1size.width()
        self.menuTray1Height = t1size.height()
        ###
        t2size = self.menuTray2.sizeHint()
        self.menuTray2Width = t2size.width()
        self.menuTray2Height = t2size.height()
    def copyDate(self, obj=None, event=None):
        self.clipboard.setText(ui.cell.format(preferences.dateFormatBin, core.primaryMode))
    def copyDateToday(self, obj=None, event=None):
        self.clipboard.setText(ui.todayCell.format(preferences.dateFormatBin, core.primaryMode))
    def copyTime(self, obj=None, event=None):
        self.clipboard.setText(ui.todayCell.format(preferences.clockFormatBin, core.primaryMode, localtime()[3:6]))
    """
    def updateToolbarClock(self):
        if ui.showDigClockTb:
            if self.clock==None:
                self.clock = FClockLabel(preferences.clockFormat)
                self.toolbBox.addWidget(self.clock)
                self.clock.show()
            else:
                self.clock.format = preferences.clockFormat
        else:
            if self.clock!=None:
                self.clock.destroy()
                self.clock = None

    def updateTrayClock(self):
        if self.trayMode!=3:
            return
        if ui.showDigClockTr:
            if self.clockTr==None:
                if self.trayMode==3:
                    self.clockTr = FClockLabel(preferences.clockFormat)
                    try:
                        self.trayHbox.pack_start(self.clockTr, 0, 0)
                    except AttributeError:
                        self.clockTr.destroy()
                        self.clockTr = None
                    else:
                        self.clockTr.show()
            else:
                self.clockTr.format = preferences.clockFormat
        else:
            if self.clockTr!=None:
                self.clockTr.destroy()
                self.clockTr = None
    """
    aboutShow = lambda self, obj=None, data=None: self.about.show()## or run() #?????????
    prefShow = lambda self, obj=None, data=None: self.prefDialog.show()
    customizeShow = lambda self, obj=None, data=None: self.customizeDialog.show()
    def showCustomDay(self, obj=None, data=None, month=None, day=None):## FIXME
        if month==None:
            month = ui.cell.month
        if day==None:
            day = ui.cell.day
        self.customDay.set_month_day(month, day)
        self.customDay.entryComment.set_text('')
        self.customDay.entryComment.grab_focus()
        self.customDay.show()
    def trayInit(self):
        if self.trayMode==2:
            self.sysTray = qt.QSystemTrayIcon(self)
            self.connect(self.sysTray, \
                qc.SIGNAL('activated (QSystemTrayIcon::ActivationReason)'), self.trayClicked)
        else:
            self.sysTray = None
    def trayPopup(self):
        if self.sysTray == None:
            return
        r = self.sysTray.geometry()
        x = r.x()
        y = r.y()
        w = r.width()
        h = r.height()
        if y+h > screenH - 100:## taskbar is at the bottom screen
            menu = self.menuTray2
            menuW = self.menuTray2Width
            menuH = self.menuTray2Height
        else:## taskbar is at the top of screen
            menu = self.menuTray1
            menuW = self.menuTray1Width
            menuH = self.menuTray1Height
        eps = 15
        if y < eps:# top
            mx = x+w-menuW if rtl else x
            my = y+h
        elif y+h > screenH-eps:# buttom
            mx = x+w-menuW if rtl else x
            my = y-menuH
        elif x < eps:# left
            mx = x+w
            my = y
        elif x+w > screenW-eps:## right
            mx = x-menuW
            my = y
        else:
            #print('trayPopup: x=%s, x+w=%s, screenW=%s    y=%s, y+h=%s, screenH=%s'%(x, x+w, screenW, y, y+h, screenH))
            mx = x
            my = y
        menu.popup(qc.QPoint(mx, my))
        ui.updateFocusTime()
    def trayUpdate(self, gdate=None, checkDate=True):
        if self.trayMode<2:
            return
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
            pixmap = qt.QPixmap(ui.trayImageHoli if ui.todayCell.holiday else ui.trayImage)
            painter = qt.QPainter(pixmap)
            if ui.trayFont!=None:
                painter.setFont(qfontEncode(ui.trayFont))
            painter.setPen(qt.QColor(*ui.trayTextColor))
            #painter.drawText(x, y, w, h, qc.Qt.AlignCenter, text)
            w = pixmap.width()
            h = pixmap.height()
            s = ui.traySize
            if ui.trayY0==None:
                y = s/4+int((0.9*s-h)/2) +5
            else:
                y = ui.trayY0
            painter.drawText(0, y, w, h-y, qc.Qt.AlignCenter, _(ddate[2]))
            painter.end()
            self.sysTray.setIcon(qt.QIcon(pixmap))
            ######################################
            ##tt = core.getWeekDayN(core.getWeekDay(*ddate))
            tt = toUnicode(core.getWeekDayN(core.jwday(ui.todayCell.jd)))
            #if ui.pluginsTextTray:##?????????
            #    sep = _(',')+' '
            #else:
            sep = u'\n'
            for item in ui.shownCals:
                if item['enable']:
                    mode = item['mode']
                    module = core.modules[mode]
                    y, m, d = ui.todayCell.dates[mode]
                    tt += u'%s%s %s %s'%(sep, _(d), getMonthName(mode, m, y), _(y))
            if ui.pluginsTextTray:
                text = toUnicode(ui.todayCell.pluginsText.replace('\t', '\n'))
                if text:
                    tt += u'\n\n' + text #????????????
            tt = u'<div dir="rtl">%s</div>'%tt
            self.sysTray.setToolTip(tt)
            self.sysTray.setVisible(True)
        return True
    def trayClicked(self, reason):
        if reason==qt.QSystemTrayIcon.Context:
            self.trayPopup()
            return
        elif reason==qt.QSystemTrayIcon.MiddleClick:##???????????
            self.copyTime()
            return
        #print('trayClicked')
        if self.isVisible():
            p = self.pos()
            ui.winX = p.x()
            ui.winY = p.y()
            self.hide()
        else:
            self.move(ui.winX, ui.winY)
            #if self.actionSticky.get_active():
            #    self.stick()
            #self.deiconify()
            #self.raise_()
            self.show()## does not work!
    def closeEvent(self, event):
        #print('--------------- MainWin.closeEvent')
        p = self.pos()
        ui.winX = p.x()
        ui.winY = p.y()
        if self.trayMode==0:
            self.quit()
        elif self.trayMode==1:
            self.hide()
        elif self.trayMode==2:
            if self.sysTray.isVisible():
                self.hide()
            else:
                self.quit() ## ??????????????????????????
    def escPressed(self):
        self.closeEvent(None)
    def quit(self, widget=None, event=None):
        ui.saveLiveConf()
        qc.QCoreApplication.quit()
    def adjustTime(self, widget=None, event=None):
        Popen(preferences.adjustTimeCmd)
    exportClicked = lambda self: self.export.showDialog(ui.cell.year, ui.cell.month)
    def exportClickedTray(self, widget=None, event=None):
        y, m = core.getSysDate()[:2]
        self.export.showDialog(y, m)
    def onConfigChange(self):
        ## apply ui.winTaskbar ## need to restart ro be applie? FIXME
        app.setFont(qfontEncode(ui.getFont()))
        self.updateMenuSize()
        #self.updateToolbarClock()## FIXME
        #self.updateTrayClock()
        if ui.showWinController:
            if self.winCon==None:
                self.buildWinCont()
        else:
            if self.winCon!=None:
                self.destroyWinCont()
        ui.cellCache.clear()
        for item in self.items:
            item.onConfigChange()
        self.trayUpdate(checkDate=False)
        #if self.sysTray:
        #    self.sysTray.show()
        self.onDateChange()
    updateConfigLater = lambda self: qc.QTimer.singleShot(100, self.onConfigChange)
    def show(self, update_flags=False):
        if update_flags:
            self.setWindowFlags(self.getMyWindowFlags())
        self.updateConfigLater()
        qt.QWidget.show(self)


################# end of function and class defenitions ########################


## gtk.link_button_set_uri_hook(core.openUrl) FIXME ?????????????

## Maybe this file be imported from plasma applet file
def main():
    '''
    try:
        import psyco
    except ImportError:
        print('Warning: module "psyco" not found. It could speed up execution.')
        psyco_found=False
    else:
        psyco.full()
        print('Using module "psyco" to speed up execution.')
        psyco_found=True'''
    ui.init()
    trayMode=2
    if len(sys.argv)>1:
        if sys.argv[1]=='--no-tray': ## to tray icon
            mainWin = MainWin(trayMode=0)
            show = True
        else:
            mainWin = MainWin(trayMode=2)
            if sys.argv[1]=='--hide':
                show = False
            elif sys.argv[1]=='--show':
                show = True
            elif sys.argv[1]=='--no-tray-check':
                show = ui.showMain
            #elif sys.argv[1]=='--html':#????????????
            #    mainWin.exportHtml('calendar.html') ## exportHtml(path, months, title)
            #    sys.exit(0)
            else:
                show = ui.showMain or not mainWin.sysTray
    else:
        mainWin = MainWin(trayMode=2)
        show = ui.showMain or not mainWin.sysTray
    #if show:
    #    mainWin.show()
    mainWin.show() ## main.raise_() ## ~= gtk.Window.show(self)
    if not show:
        #mainWin.hide()## FIXME
        qc.QTimer.singleShot(100, mainWin.hide)
    ##rootWindow.set_cursor(gdk.Cursor(gdk.LEFT_PTR))#???????????
    return app.exec_()


## if __name__ == '__main__':
sys.exit(main())

