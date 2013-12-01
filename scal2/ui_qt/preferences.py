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


import sys, os
from os.path import dirname, join, isabs

from scal2.locale_man import tr as _
from scal2.locale_man import langDict
from scal2.utils import toUnicode

from scal2 import core
from scal2.core import convert, myRaise, rootDir, pixDir, confDir, sysConfDir

from scal2.format_time import compileTmFormat

from scal2 import ui

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

from scal2.ui_qt.font_utils import *
from scal2.ui_qt.drawing import *
from scal2.ui_qt import qt_ud as ud
#from scal2.ui_qt.monthcal import calcTextWidth
from scal2.ui_qt.mywidgets import HBox, VBox
from scal2.ui_qt.mywidgets.expander import Expander



qpixDir = join(rootDir, 'pixmaps_qt')

QVar = qc.QVariant





def newFixedLabel(text):
    label = qt.QLabel(text)
    label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Minimum)
    #label.setFixedWidth(calcTextWidth(text, label))
    return label



############################################################

## stock image of "Next" and "Previous" buttons(year/month)
## STOCK_GO_BACK, STOCK_GO_FORWARD, STOCK_GO_DOWN, STOCK_GO_UP, STOCK_ZOOM_OUT, STOCK_ZOOM_IN
#prevStock = STOCK_GO_BACK ### ???????????????
#nextStock = STOCK_GO_FORWARD ### ??????????????

############################################################


dateFormat = '%Y/%m/%d'
clockFormat = '%X' ## '%T' or '%X' (local) or '<b>%T</b>' (bold) or '%m:%d' (no seconds)

dateFormatBin = compileTmFormat(dateFormat)
clockFormatBin = compileTmFormat(clockFormat)

adjustTimeCmd = ''

############################################################

class ToolbarItem:
    def __init__(self, name, iconName, method, tooltip='', text=''):
        self.name = name
        self.icon = qt.QIcon(join(qpixDir, iconName+'.png'))
        self.method = method
        if not tooltip:
            tooltip = name.capitalize()
        self.tooltip = _(tooltip)
        if not text:
            text = tooltip
        self.text = _(text)
    def makeAction(self, parent):
        action = qt.QAction(self.icon, self.text, parent)
        action.connect(action, qc.SIGNAL('triggered()'), getattr(parent, self.method))
        action.setToolTip(self.tooltip)
        return action

toolbarItemsData = (
    ToolbarItem('today', 'go-home', 'goToday', 'Select Today'),
    ToolbarItem('date', 'date', 'selectDateShow', 'Select Date...', 'Date...'),
    ToolbarItem('customize', 'edit', 'customizeShow'),
    ToolbarItem('preferences', 'preferences', 'prefShow'),
    ToolbarItem('export', 'convert', 'exportClicked',  _('Export to %s')%'HTML'),
    ToolbarItem('about', 'about', 'aboutShow', _('About ')+core.APP_DESC),
    ToolbarItem('quit', 'quit', 'quit',)
)

toolbarItemsDataDict = dict([(item.name, item) for item in toolbarItemsData])

otherActionsData = (
    ToolbarItem('copy_time', 'copy', 'copyTime', 'Copy Time', 'Copy _Time'),
    ToolbarItem('copy_date', 'copy', 'copyDate', 'Copy Date', 'Copy _Date'),
    ToolbarItem('copy_date_today', 'copy', 'copyDateToday', 'Copy Date', 'Copy _Date'),
    ToolbarItem('adjust', 'preferences', 'adjustTime', 'Adjust System Time', 'Ad_just System Time'),
    ToolbarItem('export_tray', 'convert',  'exportClickedTray',  _('Export to %s')%'HTML'),
)


############################################################

sysConfPath = join(sysConfDir, 'ui-qt.conf')
if os.path.isfile(sysConfPath):
    try:
        exec(file(sysConfPath).read())
    except:
        myRaise(__file__)

confPath = join(confDir, 'ui-qt.conf')
if os.path.isfile(confPath):
    try:
        exec(file(confPath).read())
    except:
        myRaise(__file__)

customizeConfPath = join(confDir, 'ui-customize.conf')
if os.path.isfile(customizeConfPath):
    try:
        exec(open(customizeConfPath).read())
    except:
        myRaise(__file__)


#if adjustTimeCmd=='':## FIXME
for cmd in ('kdesudo', 'kdesu', 'gksudo', 'gksu', 'gnomesu'):
    if os.path.isfile('/usr/bin/%s'%cmd):
        adjustTimeCmd = [
            cmd,
            join(rootDir, 'run'),
            'scal2/ui_gtk/adjust_dtime.py', ## implement in qt FIXME
        ]
        break


## r, g, b in range(256)


rgbToQColor = lambda r, g, b, a=255: qt.QColor(r, g, b, a)
qColorToRgb = lambda qc: (qc.red(), qc.green(), qc.blue(), qc.alpha())


#def image_from_file(path):
#    im = gtk.Image()
#    im.set_from_file(path)
#    return im



##################################################
def qColorDecode(qc):
    a = qc.alpha()
    if a==255:
        return (qc.red(), qc.green(), qc.blue())
    else:
        return (qc.red(), qc.green(), qc.blue(), a)

def newColorPixmap(qcolor, width, height):
    pmap = qt.QPixmap(width, height)
    painter = qt.QPainter()
    painter.begin(pmap)
    painter.setBrush(qcolor)
    painter.setPen(qcolor)
    painter.drawRect(0, 0, width, height)
    painter.end()
    return pmap


def qColorFromHtml(s):
    if len(s)==7:
        return qt.QColor(eval('0x'+s[1:3]),
                                         eval('0x'+s[3:5]),
                                         eval('0x'+s[5:]))
    elif len(s)==9:
        return qt.QColor(eval('0x'+s[1:3]),
                                         eval('0x'+s[3:5]),
                                         eval('0x'+s[5:9]),
                                         eval('0x'+s[7:]))
    else:
        raise ValueError

def qColorToHtml(qc):
    a = qc.alpha()
    if a==255:
        return '#%.2x%.2x%.2x'%(qc.red(), qc.green(), qc.blue())
    else:
        return '#%.2x%.2x%.2x%.2x'%(qc.red(), qc.green(), qc.blue(), a)



class ColorButton(qt.QPushButton):
    def __init__(self, useAlpha=False, width=50, height=30, borderWidth=6, parent=None):
        qt.QPushButton.__init__(self, parent)
        self.useAlpha = useAlpha
        self.borderWidth = borderWidth
        self.setFixedSize(width, height)
        self.setQColor(qt.QColor(0, 0, 0))
        self.connect(self, qc.SIGNAL('clicked()') , self.onClick)
        ######
        self.setAcceptDrops(True)
        self.px = -1
        self.py = -1
    def setQColor(self, qcolor):
        if not qcolor.isValid():
            return
        self.qcolor = qcolor
        w = self.width() - 2*self.borderWidth
        h = self.height() - 2*self.borderWidth
        self.pmap = newColorPixmap(qcolor, w, h)
        self.setIcon(qt.QIcon(self.pmap))
        self.setIconSize(qc.QSize(w, h))
        if self.useAlpha:
            self.setToolTip('(%d, %d, %d, %d)'%(qcolor.red(), qcolor.green(),
                                                                                    qcolor.blue(), qcolor.alpha()))
        else:
            self.setToolTip('(%d, %d, %d)'%(qcolor.red(), qcolor.green(), qcolor.blue()))
    def onClick(self):
        if self.useAlpha:
            n, ok = qt.QColorDialog.getRgba(self.qcolor.rgba(), self)
            if ok:
                c = qt.QColor()
                c.setRgba(n)
                self.setQColor(c)
        else:
            qcolor = qt.QColorDialog.getColor(self.qcolor, self)
            if qcolor.isValid():
                self.setQColor(qcolor)
    """def resizeEvent(self, event):
        size = event.size()
        if self.useFixedSize==None:
            w = size.width() - 12
            h = size.height() - 12
        else:
            w, h = self.useFixedSize
        self.pmap = newColorPixmap(self.qcolor, w, h)
        self.setIcon(qt.QIcon(self.pmap))
        self.setIconSize(qc.QSize(w, h))#"""
    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasColor() or mime.hasText():
            event.accept()
        else:
            event.ignore()
    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasColor() or mime.hasText():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat('application/x-color'):
            self.setQColor(qColorFromHtml(str(mime.data('application/x-color'))))
            event.accept()
        if mime.hasFormat('text/plain'):
            text = str(mime.text())
            try:
                self.setQColor(qColorFromHtml(text))
            except:
                print('droped invalid text "%s"'%text)
                event.ignore()
            else:
                event.accept()
        else:
            event.ignore()
    def mouseMoveEvent(self, event):
        if not (event.buttons() & qc.Qt.LeftButton):
            return
        x = event.x()
        y = event.y()
        d = max(abs(x-self.px), abs(y-self.py))
        if d<10:
            qt.QPushButton.mouseMoveEvent(self, event)
        else:
            self.startDrag()
    def mousePressEvent(self, event):
        self.px = event.x()
        self.py = event.y()
        qt.QPushButton.mousePressEvent(self, event)
    def startDrag(self):
        mime = qc.QMimeData()
        s = qColorToHtml(self.qcolor)
        mime.setData('application/x-color', s)
        mime.setData('text/plain', s) ## html (#RRGGBB) or in format (r, g, b) ????
        drag = qt.QDrag(self)
        drag.setMimeData(mime)
        drag.setHotSpot(qc.QPoint(self.px, self.py))
        drag.setPixmap(self.pmap)
        drag.start(qc.Qt.CopyAction)
    setColor = lambda self, color: self.setQColor(qt.QColor(*color))
    getColor = lambda self: qColorDecode(self.qcolor)
##########################################


class FontButton(qt.QPushButton):
    def __init__(self, parent=None):
        qt.QPushButton.__init__(self, 'None', parent)
        self.connect(self, qc.SIGNAL('clicked()'), self.onClick)
        self.setFont(qfontEncode(ui.fontDefault))
    def onClick(self):
        if self.qfont==None:
            res = qt.QFontDialog.getFont(self)
        else:
            res = qt.QFontDialog.getFont(self.qfont, self)
        if res[1]:
            self.setFont(res[0])
    def setFont(self, qfont):
        self.qfont = qfont
        self.setText(qfontToStr(qfont)) ## ??????????????
    def getFont(self):
        return self.qfont
### ????????????????????? no Bold option
### Strikeout and Underline options will not save!!



## (VAR_NAME, bool, CHECKBUTTON_TEXT)                   ## CheckButton
## (VAR_NAME, list, LABEL_TEXT, (ITEM1, ITEM2, ...))    ## ComboBox
## (VAR_NAME, int,  LABEL_TEXT, MIN, MAX)               ## SpinButton
## (VAR_NAME, float,LABEL_TEXT, MIN, MAX, DIGITS)       ## SpinButton
class ModuleOptionItem():
    def __init__(self, module, opt):
        t = opt[1]
        self.opt = opt ## needed??
        self.module = module
        self.type = t
        self.var_name = opt[0]
        hboxw = qt.QWidget()
        hbox = qt.QHBoxLayout(hboxw)
        if t==bool:
            w = qt.QCheckBox(_(opt[2]))
            #w.setTristate(False) ## Needed?
            self.get_value = lambda: w.checkState()==qc.Qt.Checked
            self.set_value = lambda v: w.setCheckState(qc.Qt.Checked if v else qc.Qt.Unchecked)
        elif t==list:
            hbox.addWidget(newFixedLabel(_(opt[2])))
            w = qt.QComboBox() ### or RadioButton
            for s in opt[3]:
                w.addItem(_(s))
            self.get_value = w.currentIndex
            self.set_value = w.setCurrentIndex
        elif t==int:
            hbox.addWidget(newFixedLabel(_(opt[2])))
            w = qt.QSpinBox()
            w.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            w.setRange(opt[3], opt[4])
            w.setSingleStep(1) ## ??????????
            w.setLayoutDirection(qc.Qt.LeftToRight)
            self.get_value = w.value
            self.set_value = w.setValue
        elif t==float:
            hbox.addWidget(newFixedLabel(_(opt[2])))
            w = qt.QDoubleSpinBox()
            w.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            w.setRange(opt[3], opt[4])
            w.setDecimals(opt[5])
            w.setSingleStep(1) ## ??????????
            w.setLayoutDirection(qc.Qt.LeftToRight)
            self.get_value = w.value
            self.set_value = w.setValue
        else:
            raise RuntimeError('bad option type "%s"'%t)
        hbox.addWidget(w)
        hbox.addStretch() ## ???????????????
        hboxw.setLayout(hbox)
        self.widget = hboxw
        self.widget.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        ####
        self.updateVar = lambda: setattr(self.module, self.var_name, self.get_value())
        self.updateWidget = lambda: self.set_value(getattr(self.module, self.var_name))


class PrefItem():
    ## self.__init__, self.module, self.varName, self.widget
    ## self.varName an string containing the name of variable
    ## set self.module=None if varName is name of a global variable in this module
    def get(self):
        raise NotImplementedError
    def set(self, value):
        raise NotImplementedError
    #updateVar = lambda self: setattr(self.module, self.varName, self.get())
    def updateVar(self):
        if self.module==None:
            if self.varName=='':
                print('PrefItem.updateVar: this PrefItem instance has no reference variable to write to!')
            else:
                exec('global %s;%s=%r'%(self.varName, self.varName, self.get()))
        else:
            setattr(self.module, self.varName, self.get())
    #updateWidget = lambda self: self.set(getattr(self.module, self.varName))
    def updateWidget(self):
        if self.module==None:
            if self.varName=='':
                print('PrefItem.updateWidget: this PrefItem instance has no reference variable to read from!')
            else:
                self.set(eval(self.varName))
        else:
            self.set(getattr(self.module, self.varName))
    ## confStr(): gets the value from variable (not from GUI) and returns a string to save to file
    ##                        the string will has a NEWLINE at the END
    def confStr(self):
        if self.module==None:
            if self.varName=='':
                return ''
            else:
                return '%s=%r\n'%(self.varName, eval(self.varName))
        else:
            return '%s=%r\n'%(self.varName, getattr(self.module, self.varName))


class ComboTextPrefItem(PrefItem):
    def __init__(self, module, varName, items=[]):## items is a list of strings
        self.module = module
        self.varName = varName
        w = qt.QComboBox()
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        for s in items:
            w.addItem(s)
        self.get = w.currentIndex
        self.set = w.setCurrentIndex
    #def set(self, value):
    #    print('ComboTextPrefItem.set', value)
    #    self.widget.setCurrentIndex(int(value))

class ComboEntryTextPrefItem(PrefItem):
    def __init__(self, module, varName, items=[]):## items is a list of strings
        self.module = module
        self.varName = varName
        w = qt.QComboBox()
        w.setEditable(True)
        w.setLayoutDirection(qc.Qt.LeftToRight)
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        for s in items:
            w.addItem(s)
        lineEdit = w.lineEdit()
        self.get = lambda: unicode(lineEdit.text())
        self.set = lineEdit.setText

class ComboImageTextPrefItem(PrefItem):
    def __init__(self, module, varName, items=[]):## items is a list of pairs (imagePath, text)
        self.module = module
        self.varName = varName
        ###
        combo = qt.QComboBox()
        self.widget = combo
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        for (imPath, label) in items:
            self.append(imPath, label)
        self.get = combo.currentIndex
        self.set = combo.setCurrentIndex
    def append(self, imPath, label):
        if imPath=='':
            self.widget.addItem(label)
        else:
            if not isabs(imPath):
                imPath = join(pixDir, imPath)
            self.widget.addItem(qt.QIcon(imPath), label)

class LangPrefItem(PrefItem):
    def __init__(self):
        self.module = core
        self.varName = 'lang'
        ###
        combo = qt.QComboBox()
        ###
        self.widget = combo
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.append(join(pixDir, 'computer.png'), _('System Setting'))
        for (key, data) in langDict.items():
            self.append(data.flag, data.name)
    def append(self, imPath, label):
        if imPath=='':
            self.widget.addItem(label)
        else:
            if not isabs(imPath):
                imPath = join(pixDir, imPath)
            self.widget.addItem(qt.QIcon(imPath), label)
    def get(self):
        i = self.widget.currentIndex()
        if i==0:
            return ''
        else:
            return langDict.keyList[i-1]
    def set(self, value):
        assert isinstance(value, str)
        if value=='':
            self.widget.setCurrentIndex(0)
        else:
            try:
                i = langDict.keyList.index(value)
            except ValueError:
                print('language %s in not in list!'%value)
                self.widget.setCurrentIndex(0)
            else:
                self.widget.setCurrentIndex(i+1)
    #def updateVar(self):
    #    lang =




class FontPrefItem(PrefItem):##????????????
    def __init__(self, module, varName):
        self.module = module
        self.varName = varName
        w = FontButton()
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.get = lambda: qfontDecode(w.qfont)
        self.set = lambda font: w.setFont(qfontEncode(font))


class CheckPrefItem(PrefItem):
    def __init__(self, module, varName, label='', tooltip=None):
        self.module = module
        self.varName = varName
        w = qt.QCheckBox(label)
        w.setCheckable(True)
        if tooltip!=None:
            try:
                w.setToolTip(tooltip)
            except:
                print('tooltip', repr(tooltip), type(tooltip))
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.get = lambda: w.checkState()==qc.Qt.Checked
        self.set = lambda v: w.setCheckState(qc.Qt.Checked if v else qc.Qt.Unchecked)



class CheckStartupPrefItem(PrefItem):### cbStartCommon
    def __init__(self):
        self.module = None
        self.varName = ''
        w = qt.QCheckBox(_('Run on session startup'))
        w.setCheckable(True)
        w.setToolTip('Run on startup of Gnome, KDE, Xfce, LXDE, ...\nFile: %s'%ui.comDesk)
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.get = lambda: w.checkState()==qc.Qt.Checked
        self.set = lambda v: w.setCheckState(qc.Qt.Checked if v else qc.Qt.Unchecked)
    def updateVar(self):
        if self.get():
            if not ui.addStartup():
                self.set(False)
        else:
            try:
                ui.removeStartup()
            except:
                pass
    def updateWidget(self):
        self.set(ui.checkStartup())


## http://qt.nokia.com/products/appdev/add-on-products/catalog/4/Widgets/qtcolorpicker/
class ColorPrefItem(PrefItem):
    def __init__(self, module, varName, useAlpha=False):
        self.module = module
        self.varName = varName
        w = ColorButton(useAlpha)
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        self.set = w.setColor
        self.get = w.getColor


class SpinPrefItem(PrefItem):
    def __init__(self, module, varName, min_=-99, max_=99, digits=1, inc1=1, inc2=10):
        self.module = module
        self.varName = varName
        if digits==0:
            w = qt.QSpinBox()
        else:
            w = qt.QDoubleSpinBox()
            w.setDecimals(digits)
        w.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        w.setRange(min_, max_)
        w.setSingleStep(1) ## ??????????
        w.setLayoutDirection(qc.Qt.LeftToRight)
        self.widget = w
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.get = w.value
        self.set = w.setValue



class RadioListPrefItem(PrefItem):
    def __init__(self, vertical, module, varName, texts, label=None):
        self.num = len(texts)
        assert self.num>0
        self.module = module
        self.varName = varName
        if vertical:
            widget = VBox()
        else:
            widget = HBox()
        self.widget = widget
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.radios = [qt.QRadioButton(_(s), widget) for s in texts]
        first = self.radios[0]
        if label!=None:
            widget.addWidget(newFixedLabel(label))
            #widget.addStretch()
        widget.addWidget(first)
        for r in self.radios[1:]:
            #widget.addStretch()
            widget.addWidget(r)
        #widget.addStretch()
    def get(self):
        for i in range(self.num):
            if self.radios[i].isChecked():
                return i
    def set(self, index):
        self.radios[index].setChecked(True)

class RadioHListPrefItem(RadioListPrefItem):
    def __init__(self, *args, **kwargs):
        RadioListPrefItem.__init__(self, False, *args, **kwargs)

class RadioVListPrefItem(RadioListPrefItem):
    def __init__(self, *args, **kwargs):
        RadioListPrefItem.__init__(self, True, *args, **kwargs)


class ListPrefItem(PrefItem):
    def __init__(self, vertical, module, varName, items=[]):
        self.module = module
        self.varName = varName
        if vertical:
            widget = VBox()
        else:
            widget = HBox()
        for item in items:
            assert isinstance(item, PrefItem)
            widget.addWidget(item.widget)
        self.num = len(items)
        self.items = items
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
    get = lambda self: tuple([item.get() for item in self.items])
    def set(self, valueL):
        assert len(valueL)==self.num
        for i in range(self.num):
            self.items[i].set(valueL[i])
    def append(self, item):
        assert isinstance(item, PrefItem)
        self.widget.addWidget(item.widget)
        self.items.append(item)


class HListPrefItem(ListPrefItem):
    def __init__(self, *args, **kwargs):
        ListPrefItem.__init__(self, False, *args, **kwargs)

class VListPrefItem(ListPrefItem):
    def __init__(self, *args, **kwargs):
        ListPrefItem.__init__(self, True, *args, **kwargs)

class CalPropPrefItem(PrefItem):
    def __init__(self, module, varName):
        self.module = module
        self.varName = varName
        self.widget = qt.QWidget()
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        lay = qt.QGridLayout()
        self.checkb = []
        self.combo = []
        self.spinX = []
        self.spinY = []
        self.fontb = []
        self.colorb = []
        ######
        n = len(getattr(self.module, self.varName))
        self.num = n
        for i in range(n):
            checkb = qt.QCheckBox('', self.widget)
            checkb.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            checkb.setToolTip(_('Enable/Disable'))
            self.checkb.append(checkb)
            lay.addWidget(checkb, i, 0)
            ####
            combo = qt.QComboBox()
            for m in core.modules:
                combo.addItem(_(m.desc))
            self.combo.append(combo)
            lay.addWidget(combo, i, 1)
            ###
            lay.addItem(qt.QSpacerItem(0, 0, qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed), i, 2)
            label = qt.QLabel(_('position'))
            label.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
            lay.addWidget(label, i, 3)
            ###
            spin = qt.QDoubleSpinBox()
            spin.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            spin.setRange(-99, 99)
            spin.setDecimals(1)
            spin.setSingleStep(1) ## ??????????
            spin.setLayoutDirection(qc.Qt.LeftToRight)
            self.spinX.append(spin)
            lay.addWidget(spin, i, 4)
            ###
            spin = qt.QDoubleSpinBox()
            spin.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
            spin.setRange(-99, 99)
            spin.setDecimals(1)
            spin.setSingleStep(1) ## ??????????
            spin.setLayoutDirection(qc.Qt.LeftToRight)
            self.spinY.append(spin)
            lay.addWidget(spin, i, 5)
            ###
            lay.addItem(qt.QSpacerItem(0, 0, qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed), i, 6)
            fontb = FontButton()
            self.fontb.append(fontb)
            lay.addWidget(fontb, i, 7)
            ####
            colorb = ColorButton()
            self.colorb.append(colorb)
            lay.addWidget(colorb, i, 8)
        #########
        self.widget.setLayout(lay)
    def get(self):
        result = []
        for i in range(self.num):
            result.append({
                'enable':self.checkb[i].checkState()==qc.Qt.Checked,
                'mode'  :self.combo[i].currentIndex(),
                'x'     :self.spinX[i].value(),
                'y'     :self.spinY[i].value(),
                'font'  :qfontDecode(self.fontb[i].getFont()),
                'color' :self.colorb[i].getColor()
            })
        return result
    def set(self, data):
        assert len(data)==self.num ## ?????????????
        for i in range(self.num):
            item = data[i]
            self.checkb[i].setCheckState(qc.Qt.Checked if item['enable'] else qc.Qt.Unchecked)
            self.combo[i].setCurrentIndex(item['mode'])
            self.spinX[i].setValue(item['x'])
            self.spinY[i].setValue(item['y'])
            self.fontb[i].setFont(qfontEncode(item['font']))
            self.colorb[i].setColor(item['color'])


class WeekDayCheckListPrefItem(PrefItem):### use synopsis (Sun, Mon, ...) ????????????
    def __init__(self, module, varName, vertical=False, homo=True, abbreviateNames=True):
        self.module = module
        self.varName = varName
        widget = qt.QWidget()
        if vertical:
            widget = VBox()
        else:
            widget = HBox()
        ## lay.set_homogeneous(homo) ##????????????
        ls = []
        nameList = core.weekDayNameAb if abbreviateNames else core.weekDayName
        for item in nameList:
            button = qt.QPushButton(item, widget)
            button.setCheckable(True)
            ls.append(button)
        s = core.firstWeekDay
        for i in range(7):
            widget.addWidget(ls[(s+i)%7])
        self.cbList = ls
        self.widget = widget
        self.widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        self.start = s
    def setStart(self, s):
        widget = self.widget
        ls = self.cbList
        for w in ls:
            widget.removeWidget(w)
        for j in range(7):
            widget.addWidget(ls[(s+j)%7])
        self.start = s
    def get(self):
        value = []
        cbl = self.cbList
        for j in range(7):
            if cbl[j].isChecked():
                value.append(j)
        return tuple(value)
    def set(self, value):
        cbl = self.cbList
        for cb in cbl:
            cb.setChecked(False)
        for j in value:
            cbl[j].setChecked(True)



class PluginTreeview(qt.QTreeWidget):
    def __init__(self):
        qt.QTreeWidget.__init__(self)
        self.setColumnCount(4)
        self.setHeaderLabels([_('Index'), _('Enable'), _('Show Date'), _('Description')])
        self.hideColumn(0)
        self.resizeColumnToContents(1)
        #self.resizeColumnToContents(2)
        self.connect(self, qc.SIGNAL('activated(const QModelIndex&)'), self.rowActivate)
        ## Drag & Drop ????????????????
        self.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        #self.setDropIndicatorShown(True)
        ###########################################
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        vboxPlug = qt.QVBoxLayout()
        vboxPlug.setMargin(0)
        vboxPlug.addWidget(self)
        hbox.addLayout(vboxPlug)
        ###
        buttonHBox = qt.QHBoxLayout() ## or QDialogButtonBox ?????????
        buttonHBox.setMargin(0)
        ###
        button = qt.QPushButton(self.style().standardIcon(qt.QStyle.SP_DialogHelpButton), _('_About Plugin'), self)
        button.setEnabled(False)
        self.connect(button, qc.SIGNAL('clicked()'), self.about)
        self.plugButtonAbout = button
        buttonHBox.addWidget(button)
        buttonHBox.addStretch()
        ###
        button = qt.QPushButton(qt.QIcon(pixDir+'preferences-other.png'), _('C_onfigure Plugin'), self)
        button.setEnabled(False)
        self.connect(button, qc.SIGNAL('clicked()'), self.conf)
        self.plugButtonConf = button
        buttonHBox.addWidget(button)
        buttonHBox.addStretch()
        ###
        vboxPlug.addLayout(buttonHBox)
        ###
        toolbar = qt.QToolBar(self)
        toolbar.setOrientation(qc.Qt.Vertical)
        action = qt.QAction(qt.QIcon(qpixDir+'/go-top.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.top)
        action.setToolTip(_('Move to top'))
        toolbar.addAction(action)
        ###################
        action = qt.QAction(qt.QIcon(qpixDir+'/go-up.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.up)
        action.setToolTip(_('Move up'))
        toolbar.addAction(action)
        ###################
        action = qt.QAction(qt.QIcon(qpixDir+'/go-down.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.down)
        action.setToolTip(_('Move down'))
        toolbar.addAction(action)
        ###################
        action = qt.QAction(qt.QIcon(qpixDir+'/go-bottom.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.bottom)
        action.setToolTip(_('Move to bottom'))
        toolbar.addAction(action)
        ###################
        action = qt.QAction(qt.QIcon(qpixDir+'/list-add.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.add)
        action.setToolTip(_('Add'))
        toolbar.addAction(action)
        self.actionAdd = action
        ###################
        action = qt.QAction(qt.QIcon(qpixDir+'/delete.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.delete)
        action.setToolTip(_('Delete'))
        toolbar.addAction(action)
        #if len(self.plugAddItems)==0:
        #    action.setEnabled(False)
        ###########
        hbox.addWidget(toolbar)
        self.hboxAll = hbox
        ###########################################
        dialog = qt.QDialog(self)
        dialog.setWindowTitle(_('Add Plugin'))
        buttonBox = qt.QDialogButtonBox(
            qt.QDialogButtonBox.Cancel | qt.QDialogButtonBox.Ok,
            qc.Qt.Horizontal,
            dialog
        )
        self.connect(dialog, qc.SIGNAL('rejected()'), self.addDialogClose)
        self.connect(dialog, qc.SIGNAL('accepted()'), self.addDialogOK)
        self.connect(buttonBox, qc.SIGNAL('rejected()'), self.addDialogClose)
        self.connect(buttonBox, qc.SIGNAL('accepted()'), self.addDialogOK)
        '''
        if ui.autoLocale:
            okB.setText(_('_OK'))
            #okB.setIcon(qt.QIcon('ok.png'))
            canB.setText(_('_Cancel'))
            #canB.setIcon(qt.QIcon('cancel.png'))
        '''
        treev = qt.QTreeWidget()
        treev.setColumnCount(1)
        treev.setHeaderLabels([_('Description')])
        self.connect(treev, qc.SIGNAL('activated(const QModelIndex&)'), self.addTreevActivate)
        ####
        vboxAddPlug = qt.QVBoxLayout()
        vboxAddPlug.setMargin(0)
        vboxAddPlug.addWidget(treev)
        vboxAddPlug.addWidget(buttonBox)
        dialog.setLayout(vboxAddPlug)
        self.plugAddDialog = dialog
        self.plugAddTreev = treev
    def selectionChanged(self, selected, deselected):
        try:
            i = selected.first().top()
        except:
            return
        j = int(self.topLevelItem(i).text(0))
        plug = core.allPlugList[j]
        self.plugButtonAbout.setEnabled(plug.about!=None)
        self.plugButtonConf.setEnabled(plug.has_config)
    def about(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        j = int(self.topLevelItem(i).text(0))
        plug = core.allPlugList[j]
        if plug.about==None:
            return
        text = toUnicode(plug.about) + u'\n' + _('Credits') + u':\n\t' + toUnicode('\n\t'.join(plug.authors))
        qt.QMessageBox.about(self, _('About Plugin'), text)
        """## ??????????????????????????
        about = gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_name('')
        #about.set_name(plug.desc) ## or set_program_name
        #about.set_title(_('About ')+plug.desc) ## must call after set_name and set_version !
        about.set_title(_('About Plugin'))
        about.set_authors(plug.authors)
        about.set_comments(plug.about)
        #about.set_license(core.licenseText)
        #about.set_wrap_license(True)
        about.connect('delete-event', lambda w, e: w.destroy())
        about.connect('response', lambda w, e: w.destroy())
        #about.set_resizable(True)
        #about.vbox.show_all()## OR about.vbox.show_all() ; about.run()
        about.present()"""
    def conf(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        j = int(self.topLevelItem(i).text(0))
        plug = core.allPlugList[j]
        if not plug.has_config:
            return
        plug.open_configure()
    def rowActivate(self, index):
        #print('rowActivate', index.row(), index.column())
        if index.column()==3:## Description Colums
            self.about() #??????
    def add(self):
        ## ???????????????????????????
        ## Reize window to show all texts
        #r, x, y, w, h = self.plugAddTreev.get_column(0).cell_get_size()
        #print(r[2], r[3], x, y, w, h)
        #self.plugAddDialog.resize(w+30, 75 + 30*len(self.plugAddModel))
        ###############
        self.plugAddDialog.exec_()
        #self.plugAddDialog.present()
        #self.plugAddDialog.show()
    def addDialogClose(self):
        self.plugAddDialog.hide()
        return True
    def top(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        n = self.columnCount()
        if i<0 or i>=self.topLevelItemCount():
            qt.QApplication.beep()
            return
        j = int(self.topLevelItem(i).text(0))
        item = self.takeTopLevelItem(i)
        self.insertTopLevelItem(0, item)
        self.setCurrentItem(item, 0)
    def bottom(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        if i<0 or i>=self.topLevelItemCount()-1:
            gdk.beep()
            return
        item = self.takeTopLevelItem(i)
        self.addTopLevelItem(item)
        self.setCurrentItem(item, 0)
    def up(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        if i<=0 or i>=self.topLevelItemCount():
            qt.QApplication.beep()
            return
        item = self.takeTopLevelItem(i)
        self.insertTopLevelItem(i-1, item)
        self.setCurrentItem(item, 0)
    def down(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        if i<0 or i>=self.topLevelItemCount()-1:
            qt.QApplication.beep()
            return
        item = self.takeTopLevelItem(i)
        self.insertTopLevelItem(i+1, item)
        self.setCurrentItem(item, 0)
    def delete(self):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        n = self.topLevelItemCount()
        if i<0 or i>=n:
            qt.QApplication.beep()
            return
        j = int(self.topLevelItem(i).text(0))
        if n<2:
            self.clear() ## Segmentation fault !!!!!!!!!!!
        else:
            #self.removeItemWidget(self.topLevelItem(i), 0)
            self.takeTopLevelItem(i)
        self.plugAddItems.append(j)
        desc = core.allPlugList[j].desc
        self.plugAddTreev.addTopLevelItem(qt.QTreeWidgetItem([toUnicode(desc)]))
        self.actionAdd.setEnabled(True)
        if n>1:
            self.setCurrentItem(self.topLevelItem(min(n-2, i)), 0)
    def addDialogOK(self):
        treevAdd = self.plugAddTreev
        try:
            i = treevAdd.selectedIndexes()[0].row()
        except:
            qt.QApplication.beep()
            return
        j = self.plugAddItems[i]
        selected = self.selectedIndexes()
        if len(selected)==0:##???????????????
            pos = self.topLevelItemCount()
        else:
            pos = selected[0].row() + 1
        item = qt.QTreeWidgetItem([
            str(pos),
            '',
            '',
            toUnicode(core.allPlugList[j].desc)
        ])
        item.setCheckState(1, qc.Qt.Checked)
        item.setCheckState(2, qc.Qt.Unchecked)
        self.insertTopLevelItem(pos, item)
        treevAdd.takeTopLevelItem(i)
        self.plugAddItems.pop(i)
        self.plugAddDialog.hide()
        self.setCurrentItem(item, 0)
    addTreevActivate = lambda self, index: self.addDialogOK()
    def updateGui(self):
        self.clear()
        #self.setColumnCount(4)
        #self.hideColumn(0)
        for i in core.plugIndex:#????????
            plug = core.allPlugList[i]
            item = qt.QTreeWidgetItem([str(i), '', '', toUnicode(plug.desc)])
            item.setCheckState(1, qc.Qt.Checked if plug.enable else qc.Qt.Unchecked)
            item.setCheckState(2, qc.Qt.Checked if plug.show_date else qc.Qt.Unchecked)
            self.addTopLevelItem(item)
        n1 = len(core.plugIndex)
        n2 = len(core.allPlugList)
        #assert n1 <= n2
        if n1>n2:
            core.plugIndex = core.plugIndex[:n2]
        self.plugAddItems = []
        treev = self.plugAddTreev
        treev.clear()
        if n1 < n2:
            for i in range(n2):
                """
                if i not in core.plugIndex:
                """
                try:
                    core.plugIndex.index(i)
                except ValueError:
                    self.plugAddItems.append(i)
                    treev.addTopLevelItem(qt.QTreeWidgetItem([toUnicode(core.allPlugList[i].desc)]))
                    self.actionAdd.setEnabled(True)
    def startDrag(self, dropActions):
        try:
            i = self.selectedIndexes()[0].row()
        except:
            return
        #item = self.currentItem()
        mime = qc.QMimeData()
        mime.setText(str(i))
        drag = qt.QDrag(self)
        drag.setMimeData(mime)
        #drag.setHotSpot(qc.QPoint(-12, -12))
        #drag.setPixmap(self.style().standardPixmap(qt.QStyle.SP_DialogHelpButton))
        drag.exec_(dropActions)
    def dragEnterEvent(self, event):
        event.accept()
    def dragMoveEvent (self, event):
        event.accept()
    def dropEvent(self, event):
        text = str(event.mimeData().text())
        try:
            i = int(text)
        except:
            event.ignore()
            return
        n = self.topLevelItemCount()
        if not 0 <= i < n:
            event.ignore()
            return
        event.accept()
        targetItem = self.itemAt(event.pos())
        j = self.indexOfTopLevelItem(targetItem)
        if j==-1:
            j = n-1
            targetItem = self.topLevelItem(j)
        sourceItem = self.takeTopLevelItem(i)
        self.insertTopLevelItem(j, sourceItem)
        self.setCurrentItem(self.topLevelItem(j), 0)






class NothingObject(object):
    def __init__(self, defaultValue=None):
        object.__init__(self)
        #object.__setattr__(self, 'defaultValue', defaultValue)
    def __getattribute__(self, attr):
        if attr in ('__call__', '__setattr__'):
            return object.__getattribute__(self, attr)
        print('NothingObject.__getattribute__(%r)'%attr)
        #return object.__getattribute__(self, 'defaultValue')
        return object.__getattribute__(self, 'foo_callable')
    def __setattr__(self, attr, value):
        print('NothingObject.__setattr__(%r, %r)'%(attr, value))
    def __call__(self, *args, **kwargs):
        print('NothingObject.__call__')
    def foo_callable(self, *args, **kwargs):
        pass

class PrefDialog(qt.QWidget):
    def __init__(self, mainWin=None):
        if mainWin==None:
            self.mainWin = mainWin = NothingObject()
            trayMode = 0
        else:
            self.mainWin = mainWin
            trayMode = mainWin.trayMode
        qt.QWidget.__init__(self, None, qc.Qt.Tool)
        self.setWindowTitle(_('Preferences'))
        ## qc.Qt.Tool    ====>    No taskbar hint
        ## qc.Qt.X11BypassWindowManagerHint    ==> Popup(no control for window manager)
        bbox = qt.QDialogButtonBox(self)
        cancelB = bbox.addButton(qt.QDialogButtonBox.Cancel)
        applyB = bbox.addButton(qt.QDialogButtonBox.Apply)
        okB = bbox.addButton(qt.QDialogButtonBox.Ok)
        if ui.autoLocale:
            cancelB.setText(_('_Cancel'))
            #cancelB.setIcon(qt.QIcon('cancel.png'))
            applyB.setText(_('_Apply'))
            #applyB.setIcon(qt.QIcon('apply.png'))
            okB.setText(_('_OK'))
            #okB.setIcon(qt.QIcon('ok.png'))
            #okB.grab_default()#?????????
            #okB.grab_focus()#?????????
        ## ???????????????
        self.connect(cancelB, qc.SIGNAL('clicked()'), self.cancel)
        self.connect(applyB, qc.SIGNAL('clicked()'), self.apply)
        self.connect(okB, qc.SIGNAL('clicked()'), self.ok)
        okB.setToolTip(_('Apply and Close'))
        ##############################################
        self.localePrefItems = []
        self.corePrefItems = []
        self.uiPrefItems = []
        self.herePrefItems = [] ## ??????????
        ##############################################
        notebook = qt.QTabWidget()
        self.notebook = notebook
        ################################ Tab 1 ############################################
        vbox = qt.QVBoxLayout()
        vbox.setMargin(0)
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('Language')))
        itemLang = LangPrefItem()
        self.localePrefItems.append(itemLang)
        ###
        hbox.addWidget(itemLang.widget)
        if core.langSh=='en':
            hbox.addStretch()
        else:
            label = qt.QLabel('Language')
            label.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
            hbox.addWidget(label)
            #hbox.addStretch()
        vbox.addLayout(hbox)
        ##########################
        #exp = Expander(_('Shown Calendars'), 2, self)
        itemShownCals = CalPropPrefItem(ui, 'shownCals')
        self.uiPrefItems.append(itemShownCals)
        #exp.addWidget(itemShownCals.widget)
        #exp.setExpanded(True)
        #vbox.addWidget(exp)
        vbox.addWidget(itemShownCals.widget)
        ##########################
        if trayMode!=1:
            #hbox = qt.QHBoxLayout()
            #hbox.setMargin(0)
            item = CheckStartupPrefItem()
            self.uiPrefItems.append(item)
            #hbox.addWidget(item.widget)
            #vbox.addLayout(hb)
            vbox.addWidget(item.widget)
            ########################
            item = CheckPrefItem(ui, 'showMain', _('Show main window on start'))
            self.uiPrefItems.append(item)
            vbox.addWidget(item.widget)
        ##########################
        item = CheckPrefItem(ui, 'winTaskbar', _('Window in Taskbar'))
        self.uiPrefItems.append(item)
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        #####
        item = CheckPrefItem(ui, 'showWinController', _('Show Window Controllers'))
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        #####
        vbox.addLayout(hbox)
        ##########################
        """
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('Show Digital Clock:')))
        #hbox.addStretch()
        item = CheckPrefItem(ui, 'showDigClockTb', _('On Toolbar'))
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        """
        #hbox.addStretch()
        if trayMode==1:
            item = CheckPrefItem(ui, 'showDigClockTr', _('On Applet'), 'Panel Applet')
        else:
            item = CheckPrefItem(ui, 'showDigClockTr', _('On Tray'), 'Notification Area')
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        vbox.addLayout(hbox)
        ##########################
        widgetGen = qt.QWidget()
        widgetGen.setLayout(vbox)
        ################################ Tab 2 ################################################
        vbox = qt.QVBoxLayout()
        vbox.setMargin(0)
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        ########
        item = CheckPrefItem(ui, 'mcalGrid', _('Grid'))
        self.uiPrefItems.append(item)
        item.widget.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(item.widget)
        cbGrid = item.widget
        ########
        item = ColorPrefItem(ui, 'mcalGridColor', True)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        self.connect(cbGrid, qc.SIGNAL('clicked()'),
                                 lambda: item.widget.setEnabled(cbGrid.checkState()==qc.Qt.Checked))
        ########
        hbox.addStretch()
        item = CheckPrefItem(ui, 'fontCustomEnable', _('Application Font'), fontToStr(ui.fontDefault))
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        enableItem = item
        item = FontPrefItem(ui, 'fontCustom')
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        #self.connect(item.widget, qc.SIGNAL('clicked'), self.checkbFontClicked)
        self.connect(
            item.widget,
            qc.SIGNAL('clicked()'),
            lambda: item.widget.setEnabled(enableItem.get())
        )
        vbox.addLayout(hbox)
        ########################### Theme #####################
        item = CheckPrefItem(ui, 'bgUseDesk', _('Use Desktop Background'))
        self.uiPrefItems.append(item)
        vbox.addWidget(item.widget)
        #####################
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        label = qt.QLabel('<b>%s</b>: '%_('Colors'))
        label.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        hbox.addStretch()
        ###
        label = qt.QLabel(_('Background'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'bgColor', True)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        #self.colorbBg = item.widget ##??????
        ###
        label = qt.QLabel(_('Border'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'borderColor', True)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ###
        label = qt.QLabel(_('Cursor'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'cursorOutColor', False)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ###
        label = qt.QLabel(_('Cursor BG'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'cursorBgColor', True)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ###
        vbox.addLayout(hbox)
        ####################
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        label = qt.QLabel('<b>%s</b>: '%_('Font Colors'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        hbox.addStretch()
        ####
        label = qt.QLabel(_('Holiday'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'holidayColor', False)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ###
        label = qt.QLabel(_('Inactive Day'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'inactiveColor', True)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ####
        label = qt.QLabel(_('Border'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = ColorPrefItem(ui, 'borderTextColor', False)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ####
        vbox.addLayout(hbox)
        ###################
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        """
        hbox2 = qt.QHBoxLayout()
        hbox2.setMargin(0)
        self.checkYmArrows = qt.QCheckBox('')
        self.ymArrowHboxW = qt.QWidget()
        self.connect(self.checkYmArrows, qc.SIGNAL('clicked()'), self.checkYmArrowsClicked)
        #self.connect(self.checkYmArrows, qc.SIGNAL('clicked'),
        #    lambda obj: hbox2.setEnabled(self.checkYmArrows.get_active()))
        hbox.addWidget(self.checkYmArrows)
        hbox2.addWidget(qt.QLabel(_('Previous year/month button')))
        im1 = qt.QLabel()
        im1.connect(qc.SIGNAL('mousePressEvent()'), self.imageClicked1)
        hbox2.addWidget(im1)
        ##
        #hbox2.addStretch()
        hbox2.addWidget(qt.QLabel(_('Next')))
        im2 = qt.QLabel()
        im2.connect(qc.SIGNAL('mousePressEvent()'), self.imageClicked2)
        hbox2.addWidget(im2)
        ##
        menu = qt.QMenu()
        for stock in (STOCK_GO_UP,STOCK_GO_DOWN,STOCK_GO_BACK,STOCK_GO_FORWARD,\
                      STOCK_ZOOM_IN,STOCK_ZOOM_OUT,STOCK_ADD,STOCK_REMOVE):
                action = menu.addAction(QIcon('???'), '', self.imageSet)
                action.stock = stock
        for arrow in (ARROW_LEFT, ARROW_RIGHT, ARROW_UP, ARROW_DOWN):
                ##menu.add(self.newArrowMenuItem(arrow, self.imageSet, arrow))
                action = menu.addAction(QIcon('???'), '', self.imageSet)
                action.stock = arrow
        menu.show_all()
        self.menu_im = menu
        self.im1 = im1
        self.im2 = im2
        self.ev1 = ev1
        self.ev2 = ev2
        #hbox2.addStretch()
        self.ymArrowHboxW.setLayout(hbox2)
        hbox.addWidget(self.ymArrowHboxW)
        """
        #########
        label = qt.QLabel(_('Left Margin'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = SpinPrefItem(ui, 'mcalLeftMargin', 0, 99, 0, 1, 10)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        ####
        hbox.addStretch()
        label = qt.QLabel(_('Top'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = SpinPrefItem(ui, 'mcalTopMargin', 0, 99, 0, 1, 10)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ####
        vbox.addLayout(hbox)
        ################
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        label = qt.QLabel('<b>%s</b>:'%_('Cursor'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        hbox.addStretch()
        label = qt.QLabel(_('Diameter Factor'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        item = SpinPrefItem(ui, 'cursorDiaFactor', 0, 1, 2, 0.01, 0.1)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        ###
        hbox.addStretch()
        label = qt.QLabel(_('Rounding Factor'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        #hbox.addStretch()
        item = SpinPrefItem(ui, 'cursorRoundingFactor', 0, 1, 2, 0.01, 0.1)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        ###
        item = CheckPrefItem(ui, 'cursorFixed', _('Fixed Size'))
        self.uiPrefItems.append(item)
        self.connect(item.widget, qc.SIGNAL('stateChanged(int)'), self.cursorFixedClicked)
        #hbox.addStretch()
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        self.cursorFixedCheck = item.widget
        self.cursorFixedItems = []
        label = qt.QLabel(_('Width'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        self.cursorFixedItems.append(label)
        item = SpinPrefItem(ui, 'cursorW', 0, 99, 0, 1, 10)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        self.cursorFixedItems.append(item.widget)
        #hbox.addStretch()
        ####
        label = qt.QLabel(_('Height'))
        label.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        hbox.addWidget(label)
        self.cursorFixedItems.append(label)
        item = SpinPrefItem(ui, 'cursorH', 0, 99, 0, 1, 10)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        self.cursorFixedItems.append(item.widget)
        #hbox.addStretch()
        ####
        vbox.addLayout(hbox)
        #############
        item = RadioHListPrefItem(ui, 'dragIconCell',
            (_('Date String'), _('Cell Image')),
            _('Drag & Drop Icon'))
        self.uiPrefItems.append(item)
        item.radios[0].setToolTip('yyyy/mm/dd')
        item.set(0)
        vbox.addWidget(item.widget)
        ###################################
        widgetApp = qt.QWidget()
        widgetApp.setLayout(vbox)
        ################################ Tab 3 (Advanced) ##########################
        vbox = qt.QVBoxLayout()
        vbox.setMargin(0)
        #sgroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        ######
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('Date Format')))
        #sgroup.add_widget(label)
        #hbox.addStretch()
        item = ComboEntryTextPrefItem(None, 'dateFormat',
            ('%Y/%m/%d', '%Y-%m-%d', '%y/%m/%d', '%y-%m-%d',
            '%OY/%Om/%Od', '%OY-%Om-%Od', '%m/%d', '%m/%d/%Y'))
        self.herePrefItems.append(item)
        hbox.addWidget(item.widget)
        vbox.addLayout(hbox)
        ###
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        #hbox.addStretch()
        hbox.addWidget(newFixedLabel(_('Digital Clock Format')))
        #sgroup.add_widget(label)
        item = ComboEntryTextPrefItem(None, 'clockFormat',
            ('%T', '%X', '%Y/%m/%d - %T', '%OY/%Om/%Od - %X',
            '<i>%Y/%m/%d</i> - %T','<b>%T</b>', '<b>%X</b>', '%H:%M',
            '<b>%H:%M</b>','%OY/%Om/%Od,%X'
            '%OY/%Om/%Od,%X','%OH:%OM','<b>%OH:%OM</b>'))
        self.herePrefItems.append(item)
        hbox.addWidget(item.widget)
        vbox.addLayout(hbox)
        ######
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('Days maximum cache size')))
        #sgroup.add_widget(label)
        item = SpinPrefItem(ui, 'maxDayCacheSize', 0, 9999, 0, 1, 30)
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        hbox.addStretch()
        vbox.addLayout(hbox)
        vbox4 = vbox
        ########
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('First day of week')))
        label.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        ##item = ComboTextPrefItem( ##?????????
        self.comboFirstWD = qt.QComboBox()
        for item in core.weekDayName:
            self.comboFirstWD.addItem(item)
        self.comboFirstWD.addItem(_('Automatic'))
        self.connect(self.comboFirstWD, qc.SIGNAL('currentIndexChanged (int)'), self.comboFirstWDChanged)
        hbox.addWidget(self.comboFirstWD)
        hbox.addStretch()
        vbox.addLayout(hbox)
        #########
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('Holidays')+'    '))
        item = WeekDayCheckListPrefItem(core, 'holidayWeekDays')
        self.corePrefItems.append(item)
        self.holiWDItem = item ## Holiday Week Days Item
        hbox.addWidget(item.widget)
        vbox.addLayout(hbox)
        #########
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        hbox.addWidget(newFixedLabel(_('First week of year containts')))
        combo = qt.QComboBox()
        texts = []
        texts = [_('First %s of year')%name for name in core.weekDayName]+[_('First day of year')]
        texts[4] += ' (ISO 8601)' ##??????
        for text in texts:
            combo.addItem(text)
        #combo.addItem(_('Automatic'))## (as Locale)#?????????????????
        hbox.addWidget(combo)
        hbox.addStretch()
        vbox.addLayout(hbox)
        self.comboWeekYear = combo
        ##################################################
        ################################
        options = []
        for mod in core.modules:
            for opt in mod.options:
                optl = ModuleOptionItem(mod, opt)
                options.append(optl)
                vbox.addWidget(optl.widget)
        self.moduleOptions = options
        ##########################
        widgetAdv = qt.QWidget()
        widgetAdv.setLayout(vbox)
        ################################ Tab 4 (Plugins) ############################################
        #'''
        vbox = qt.QVBoxLayout()
        vbox.setMargin(0)
        vbox3 = vbox
        #####
        ##pluginsTextTray:
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        #hbox.addStretch()
        if trayMode==1:
            item = CheckPrefItem(ui, 'pluginsTextTray', _('Show in applet (for today)'))
        else:
            item = CheckPrefItem(ui, 'pluginsTextTray', _('Show in tray (for today)'))
        self.uiPrefItems.append(item)
        hbox.addWidget(item.widget)
        #hbox.addStretch()
        vbox.addLayout(hbox)
        #####
        self.plugTreev = PluginTreeview()
        vbox.addLayout(self.plugTreev.hboxAll)
        ####################
        widgetPlug = qt.QWidget()
        widgetPlug.setLayout(vbox)
        ############################################################################
        """
        lay = qt.QVBoxLayout()
        lay.setMargin(0)
        tab = qt.QWidget()
        im = qt.QLabel()
        im.setPixmap(qt.QPixmap('%s/preferences-other.png'%pixDir))
        lay.addWidget(im)
        lay.addWidget(qt.QLabel(_('_General')))
        tab.setLayout(lay)
        notebook.addTab(widgetGen, tab) ## tab could not a QWIdget!!
        """
        notebook.addTab(widgetGen, qt.QIcon('%s/preferences-other.png'%pixDir), _('_General'))
        notebook.addTab(widgetApp, qt.QIcon('%s/preferences-desktop-theme.png'%pixDir), _('A_ppearance'))
        notebook.addTab(widgetPlug, qt.QIcon('%s/preferences-plugin.png'%pixDir), _('_Plugins'))
        notebook.addTab(widgetAdv, qt.QIcon('%s/applications-system.png'%pixDir), _('A_dvanced'))
        ##########
        #notebook.addTab(widgetGen, _('_General'))
        #notebook.addTab(widgetApp, _('A_ppearance'))
        #notebook.addTab(widgetPlug, _('_Plugins'))
        #notebook.addTab(widgetAdv, _('A_dvanced'))
        ########################
        vboxAll = qt.QVBoxLayout()
        vboxAll.setMargin(0)
        vboxAll.addWidget(notebook)
        vboxAll.addWidget(bbox)
        self.setLayout(vboxAll)
        #notebook.set_tab_label_packing(vbox4, False, False, gtk.PACK_START)
        #notebook.set_property('homogeneous', True) #?????????
        #notebook.set_tab_reorderable(vbox1, True) #?????????
        #self.prefPages = (vbox1, vbox2, vbox3, vbox4)
        #for i in ui.prefPagesOrder:
        #    j = ui.prefPagesOrder[i]
        #    notebook.reorder_child(self.prefPages[i], j)
    def cursorFixedClicked(self, state=None):
        if state==None:
            state = self.cursorFixedCheck.checkState()
        enable = state==qc.Qt.Checked
        for w in self.cursorFixedItems:
            w.setEnabled(enable)
    def comboFirstWDChanged(self, index):
        f = index ## self.comboFirstWD.currentIndex() ## 0 means Sunday
        if f==7: ## auto
            try:
                f = core.getLocaleFirstWeekDay()
            except:
                pass
        ## core.firstWeekDay will be later = f
        self.holiWDItem.setStart(f)
    """
    checkYmArrowsClicked = lambda self, check: self.ymArrowHboxW.setEnabled(check.checkState()==qt.Qt.Checked)
    def stockMenuItem(self, stock, func, *args):
        item = gtk.MenuItem()
        item.add(gtk.image_new_from_stock(stock, gtk.ICON_SIZE_MENU))
        item.connect('activate', func, *args)
        return item
    def newArrowMenuItem(self, arrowType, func=None, *args):
        item = gtk.MenuItem()
        #ev = gtk.EventBox()
        #ev.connect('activate', func, *args)
        item.add(gtk.Arrow(arrowType, gtk.SHADOW_IN))
        if func!=None:
            item.connect('activate', func, *args)
        return item
    def imageClicked1(self, event):
        self.im_num = 1
        self.menu_im.popup(event.globalPos())
    def imageClicked2(self, event):
        self.im_num = 2
        self.menu_im.popup(event.globalPos())
    def imageSet(self, action):
        stock = action.stock
        if isinstance(stock, str):
            if self.im_num==1:
                self.ev1.remove(self.im1)
                self.im1.destroy()
                self.im1 = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_SMALL_TOOLBAR)
                self.im1.type = stock
                self.ev1.add(self.im1)
                self.im1.show()
            elif self.im_num==2:
                self.ev2.remove(self.im2)
                self.im2.destroy()
                self.im2 = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_SMALL_TOOLBAR)
                self.im2.type = stock
                self.ev2.add(self.im2)
                self.im2.show()
        elif isinstance(stock, gtk._gtk.ArrowType):
            if self.im_num==1:
                self.ev1.remove(self.im1)
                self.im1.destroy()
                self.im1 = gtk.Arrow(stock, gtk.SHADOW_IN)
                self.im1.type = stock
                self.ev1.add(self.im1)
                self.im1.show()
            elif self.im_num==2:
                self.ev2.remove(self.im2)
                self.im2.destroy()
                self.im2 = gtk.Arrow(stock, gtk.SHADOW_IN)
                self.im2.type = stock
                self.ev2.add(self.im2)
                self.im2.show()
        else:
            raise ValueError('bad stock or arrow type %s'%stock)"""
    def closeEvent(self, event):
        self.hide()
        event.ignore()
    def ok(self):
        self.hide()
        self.apply()
        if isinstance(self.mainWin, NothingObject):
            sys.exit(0)
    def cancel(self):
        self.hide()
        self.updatePrefGui()
        #if isinstance(self.mainWin, NothingObject):
        #    self.destroy()
        #    sys.exit(0)
    def apply(self, widget=None):
        #global prevStock, nextStock
        ############################################## Updating pref variables
        for opt in self.moduleOptions:
            opt.updateVar()
        for item in self.localePrefItems:
            item.updateVar()
        for item in self.corePrefItems:
            item.updateVar()
        for item in self.uiPrefItems:
            item.updateVar()
        for item in self.herePrefItems:
            try:
                item.updateVar()
            except:
                print(item.varName)
        ###### Plugin Manager
        index = []
        treev = self.plugTreev
        rows = treev.topLevelItemCount()
        for i in range(rows):
            item = treev.topLevelItem(i)
            j = int(item.text(0))
            index.append(j)
            plug = core.allPlugList[j]
            #try:
            plug.enable = (item.checkState(1) == qc.Qt.Checked)
            plug.show_date = (item.checkState(2) == qc.Qt.Checked)
            #except:
            #    core.myRaise(__file__)
            #    print(i, core.plugIndex)
        core.plugIndex = index
        ######
        first = self.comboFirstWD.currentIndex()
        if first==7:
            core.firstWeekDayAuto = True
            try:
                core.firstWeekDay = core.getLocaleFirstWeekDay()
            except:
                pass
        else:
            core.firstWeekDayAuto = False
            core.firstWeekDay = first
        ######
        mode = self.comboWeekYear.currentIndex()
        core.weekNumberMode = mode
        #if mode==8:
        #    core.weekNumberModeAuto = True
        #    core.weekNumberMode = core.getLocaleweekNumberMode()
        #else:
        #    core.weekNumberModeAuto = False
        #    core.weekNumberMode = mode
        ######
        """ui.showYmArrows = self.checkYmArrows.get_active()
        prevStock = self.im1.type ##?????????
        nextStock = self.im2.type ##?????????"""
        ######
        core.primaryMode = ui.shownCals[0]['mode']
        #################################################### Saving Preferences
        for mod in core.modules:
            mod.save()
        ##################### Saving locale config
        text = ''
        for item in self.localePrefItems:
            text += item.confStr()
        open(core.localeConfPath, 'w').write(text)
        ##################### Saving core config
        text = 'allPlugList=%s\n\nplugIndex=%r\n'%(core.getAllPlugListRepr(), core.plugIndex)
        for item in self.corePrefItems:
            text += item.confStr()
        for key in ('firstWeekDayAuto', 'firstWeekDay', 'weekNumberModeAuto', 'weekNumberMode'):
            value = eval('core.'+key)
            text += '%s=%r\n'%(key, value)
        file(core.confPath, 'w').write(text)
        ##################### Saving ui config
        text = ''
        for item in self.uiPrefItems:
            text += item.confStr()
        #text += 'showYmArrows=%r\n'%ui.showYmArrows
        #text += 'prefPagesOrder=%s'%repr(tuple(
        #    [self.notebook.page_num(page) for page in self.prefPages]))
        file(ui.confPath, 'w').write(text)
        ##################### Saving here config
        text = ''
        for item in self.herePrefItems:
            text += item.confStr()
        """for key in ('prevStock', 'nextStock'):
            value = eval(key)
            if isinstance(key, gtk._gtk.ArrowType):
                text += '%s=gtk.%s\n'%(key, value.value_name[4:])
            else:
                text += '%s=%r\n'%(key, value)"""
        text += 'adjustTimeCmd=%r\n'%adjustTimeCmd ##???????????
        file(confPath, 'w').write(text)
        ############################################# Updating Main GUI
        self.mainWin.onConfigChange()
        """
        if ui.bgUseDesk and ui.bgColor[3]==255:
            msg = gtk.MessageDialog(buttons=gtk.BUTTONS_OK_CANCEL, message_format=_(
            'If you want to have a transparent calendar (and see your desktop), change the opacity of calendar background color!'))
            if msg.run()==gtk.RESPONSE_OK:
                self.colorbBg.emit('clicked')
            msg.destroy()
        """
        if ui.checkNeedRestart():
            #if self.trayMode==1:
            #    pass ## FIXME
            #else:
            if qt.QMessageBox.question(
                self,
                _('Need Restart '+core.APP_DESC),
                _('Some preferences need for restart %s to apply.'%core.APP_DESC),
                _('_Restart'),
                _('_Cancel'),
                '',
                0,
                1,
            ) == 0:
                core.restart()
    def updatePrefGui(self):############### Updating Pref Gui (NOT MAIN GUI)
        for opt in self.moduleOptions:
            opt.updateWidget()
        for item in self.localePrefItems:
            item.updateWidget()
        for item in self.corePrefItems:
            item.updateWidget()
        for item in self.uiPrefItems:
            item.updateWidget()
        for item in self.herePrefItems:
            item.updateWidget()
        ###############################
        self.cursorFixedClicked()
        ###############################
        if core.firstWeekDayAuto:
            self.comboFirstWD.setCurrentIndex(7)
        else:
            self.comboFirstWD.setCurrentIndex(core.firstWeekDay)
        #######
        #if core.weekNumberModeAuto:
        #    self.comboWeekYear.setCurrentIndex(8)
        #else:
        self.comboWeekYear.setCurrentIndex(core.weekNumberMode)
        #self.checkShowToolbar.setCurrentIndex(ui.showToolbar)
        self.mainWin.overrideWindowFlags(qc.Qt.Tool)
        #######
        """
        self.checkYmArrows.setCurrentIndex(ui.showYmArrows)
        self.ymArrowHboxW.setEnabled(ui.showYmArrows)
        self.im_num = 1
        self.imageSet(None, prevStock)
        self.im_num = 2
        self.imageSet(None, nextStock)
        """
        ####### Plugin Manager
        self.plugTreev.updateGui()
    #def plugTreevExpose(self, widget, event):
        #self.plugDescCell.set_property('wrap-width', self.plugDescCol.get_width()+2)

if __name__=='__main__':
    from scal2.locale_man import rtl
    app = qt.QApplication(sys.argv)
    if rtl:
        app.setLayoutDirection(qc.Qt.RightToLeft)
    app.setWindowIcon(qt.QIcon(ui.logo))
    #########
    ## Theme / Style ## FIXME
    #app.setStyleSheet(...
    #########
    d = PrefDialog()
    d.updatePrefGui()
    #d.resize(600, 800)
    d.show()
    app.exec_()




