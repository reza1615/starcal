# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
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

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc

from scal2.locale_man import tr as _
from scal2.locale_man import rtl

from scal2 import core
from scal2.core import myRaise

from scal2 import ui

from scal2.ui_qt.mywidgets import HBox, VBox
from scal2.ui_qt.mywidgets.expander import Expander
from scal2.ui_qt import preferences
from scal2.ui_qt.preferences import qpixDir

class CustomizableWidgetWrapper:
    def __init__(self, widget, name, desc, items=None, optionsWidget=None, enable=True):
        self.widget = widget ## it maybe a QWidget or a QAction
        self._name = name
        self.desc = desc
        if not items:
            items = []
        self.items = items
        self.optionsWidget = optionsWidget
        self.enable = enable
    updateVars = lambda self: None
    #updateWidgets = lambda self: None ## FIXME
    confStr = lambda self: ''
    def moveItemUp(self, i):
        if not self.layout:
            return
        self.removeWidget(self.items[i].widget)
        self.insertWidget(i-1, self.items[i].widget)## QBoxLayout.insertWidget
        self.items.insert(i-1, self.items.pop(i))
    onDateChange = lambda self: None

class MainWinItem(CustomizableWidgetWrapper):
    def __init__(self, *args, **kwargs):
        CustomizableWidgetWrapper.__init__(self, self, *args, **kwargs)## widget is self
        self.myKeys = []
    onConfigChange = lambda self: None


class CustomizeDialog(qt.QWidget):## QDialog
    def __init__(self, items=[], mainWin=None):
        qt.QDialog.__init__(self)
        self.setWindowTitle(_('Customize'))
        self.vbox = qt.QVBoxLayout()
        self.vbox.setMargin(0)
        self.setLayout(self.vbox)## FIXME
        self.optionBox = qt.QStackedLayout()
        self.optionBox.setMargin(0)
        #self.optionBox.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
        self.nullWidget = qt.QLabel('')
        self.optionBox.addWidget(self.nullWidget)
        #if rtl:
        #    self.setLayoutDirection(qt.QBoxLayout.RightToLeft)
        ###
        self.items = items
        self.mainWin = mainWin
        ###
        self.tree = qt.QTreeWidget(self)
        #self.tree.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
        self.tree.setHeaderHidden(True)
        self.tree.setItemsExpandable(True)
        self.tree.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.tree.setColumnCount(2)
        self.connect(self.tree, qc.SIGNAL('itemChanged (QTreeWidgetItem *,int)'), self.itemChanged)
        for item in items:
            qItem = qt.QTreeWidgetItem(['', item.desc])
            qItem.setCheckState(0, qc.Qt.Checked if item.enable else qc.Qt.Unchecked)
            if item.optionsWidget:
                self.optionBox.addWidget(item.optionsWidget)
                #item.optionsWidget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
            for child in item.items:
                child.qItem = qt.QTreeWidgetItem(['', child.desc])
                child.qItem.setCheckState(0, qc.Qt.Checked if child.enable else qc.Qt.Unchecked)
                qItem.addChild(child.qItem)
                if child.optionsWidget:
                    self.optionBox.addWidget(child.optionsWidget)
            self.tree.addTopLevelItem(qItem)
            item.qItem = qItem
        #####
        hbox = qt.QHBoxLayout()
        hbox.setMargin(0)
        vbox_l = qt.QVBoxLayout()
        vbox_l.setMargin(0)
        vbox_l.addWidget(self.tree)
        hbox.addLayout(vbox_l)
        #####
        toolbar = qt.QToolBar(self)
        toolbar.setOrientation(qc.Qt.Vertical)
        ###
        action = qt.QAction(qt.QIcon(qpixDir+'/go-up.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.upClicked)
        action.setToolTip(_('Move up'))
        toolbar.addAction(action)
        ###
        action = qt.QAction(qt.QIcon(qpixDir+'/go-down.png'), '', self)
        action.connect(action, qc.SIGNAL('triggered()'), self.downClicked)
        action.setToolTip(_('Move down'))
        toolbar.addAction(action)
        ###
        hbox.addWidget(toolbar)
        self.vbox.addLayout(hbox)
        self.vbox_l = vbox_l
        ########
        self.widget = VBox()
        for item in items:
            try:
                self.widget.addWidget(item.widget)
            except TypeError:
                print '\nERROR: the widget for item %s has wrong type %s'%(item._name, type(item.widget))
        self.widget.setVisible(True)
        for item in items:
            if item.enable:
                for chItem in item.items:
                    if not chItem.enable:
                        chItem.widget.setVisible(False)
            else:
                item.widget.setVisible(False)
        ########
        self.tree.selectionChanged = self.treevCursorChanged
        ###
        self.vbox.addLayout(self.optionBox)
        ########
        bbox = qt.QDialogButtonBox(self)
        closeB = bbox.addButton(qt.QDialogButtonBox.Close)
        if ui.autoLocale:
            closeB.setText(_('_Close'))
        ## ???????????????
        self.connect(closeB, qc.SIGNAL('clicked()'), self.closeEvent)
        self.vbox.addWidget(bbox)
    def itemChanged(self, qItem, column_index):## enableCellToggled
        index, parentIndex = self.getSelectedIndex()
        item = self.getItemByIndex(index, parentIndex)
        item.enable = (qItem.checkState(0)==qc.Qt.Checked)
        item.widget.setVisible(item.enable)
        if item.enable:
            item.onDateChange()
            try:
                item.widget.repaint()
            except:
                pass
        elif self.mainWin:
            self.mainWin.setMinHeightLater()
    def getItemByIndex(self, index, parentIndex=-1):
        if parentIndex==-1:
            return self.items[index]
        else:
            return self.items[parentIndex].items[index]
    def getSelectedIndex(self):
        qIndexes = self.tree.selectedIndexes()
        if not qIndexes:
            return (-1, -1)
        qIndex = qIndexes[0]
        return (qIndex.row(), qIndex.parent().row())
    def treevCursorChanged(self, selected, deselected):
        index, parentIndex = self.getSelectedIndex()
        if index==-1:
            return
        #print 'treevCursorChanged', index, parentIndex
        item = self.getItemByIndex(index, parentIndex)
        if item.optionsWidget:
            self.optionBox.setCurrentWidget(item.optionsWidget)
            pass
        else:
            self.optionBox.setCurrentWidget(self.nullWidget)
    def upClicked(self):
        index, parentIndex = self.getSelectedIndex()
        if index==-1:
            return
        #print 'upClicked', index, parentIndex
        #item = self.getItemByIndex(index, parentIndex)
        if index<=0:
            qt.QApplication.beep()
            return
        if parentIndex==-1:
            self.moveItemUp(index)
            qItem = self.tree.takeTopLevelItem(index)
            self.tree.insertTopLevelItem(index-1, qItem)
            self.tree.setCurrentItem(qItem)
        else:
            root = self.items[parentIndex]
            root.moveItemUp(index)
            qRootItem = self.tree.topLevelItem(parentIndex)
            qItem = qRootItem.takeChild(index)
            qRootItem.insertChild(index-1, qItem)
            self.tree.setCurrentItem(qItem)
    def downClicked(self):
        index, parentIndex = self.getSelectedIndex()
        if index==-1:
            return
        #print 'upClicked', index, parentIndex
        #item = self.getItemByIndex(index, parentIndex)
        if parentIndex==-1:
            if index>=len(self.items)-1:
                qt.QApplication.beep()
                return
            self.moveItemUp(index+1)
            qItem = self.tree.takeTopLevelItem(index+1)
            self.tree.insertTopLevelItem(index, qItem)
            self.tree.setCurrentItem(self.tree.topLevelItem(index+1))
        else:
            root = self.items[parentIndex]
            if index>=len(root.items)-1:
                qt.QApplication.beep()
                return
            root.moveItemUp(index+1)
            qRootItem = self.tree.topLevelItem(parentIndex)
            qItem = qRootItem.takeChild(index+1)
            qRootItem.insertChild(index, qItem)
            self.tree.setCurrentItem(qRootItem.child(index+1))
    def moveItemUp(self, i):
        self.widget.removeWidget(self.items[i].widget)
        self.widget.insertWidget(i-1, self.items[i].widget)## QBoxLayout.insertWidget
        self.items.insert(i-1, self.items.pop(i))
    #def confStr(self):## FIXME
    def closeEvent(self, event=None):
        text = ''
        mainWinItems = []
        for item in self.items:
            item.updateVars()
            text += item.confStr()
            mainWinItems.append((item._name, item.enable))
        text += 'ui.mainWinItems=%r\n'%mainWinItems
        open(preferences.customizeConfPath, 'w').write(text) # FIXME
        self.hide()
        if event:
            event.ignore()



