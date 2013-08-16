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

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc


class Expander(qt.QTreeWidget):
    minHeight = 20
    def __init__(self, parent=None, title=None, window=None, indent=10):
        qt.QTreeWidget.__init__(self, parent)
        self.setAutoScroll(False)
        self.setHeaderHidden(True)
        self.setItemsExpandable(True)
        self.setSelectionMode(qt.QAbstractItemView.NoSelection)
        self.indent = indent
        self.setIndentation(indent)
        self.rootItem = qt.QTreeWidgetItem(qt.QTreeWidgetItem.UserType)
        self.addTopLevelItem(self.rootItem)
        self.setTitle(title)
        self.rootH = self.rowHeight(self.indexFromItem(self.rootItem))
        self.pressY = -1
        self.childWidget = None
        self.childItem = None
        self.setExpanded = self.rootItem.setExpanded
        self.isExpanded = self.rootItem.isExpanded
        ################
        if window:
            def resizeLater():
                window.resize(1, 1)

            def onExpanderChanged(item):
                self.setMinimumHeight(self.minimumSizeHint().height())
                qc.QTimer.singleShot(200, resizeLater)

            self.connect(self, qc.SIGNAL('itemCollapsed(QTreeWidgetItem *)'), onExpanderChanged)
            self.connect(self, qc.SIGNAL('itemExpanded(QTreeWidgetItem *)'), onExpanderChanged)
    def addWidget(self, widget):
        if self.childWidget!=None:
            print 'Only one widget could be added to Expander!'
            return
        widget.setParent(self)
        self.childItem = qt.QTreeWidgetItem(qt.QTreeWidgetItem.UserType)
        self.rootItem.addChild(self.childItem)
        self.setItemWidget(self.childItem, 0, widget)
        self.childWidget = widget
    def setTitle(self, title):
        if title:
            self.label = qt.QLabel(' '+title, self)
            self.setItemWidget(self.rootItem, 0, self.label)
        else:
            self.label = None
    def mousePressEvent(self, ev):
        ## expand when click on root item (like GtkExpander)
        #print 'press', ev.y()
        if ev.y() < self.rootH:
            self.pressY = ev.y()
        else:
            self.pressY = -1
            #if self.childWidget!=None:
            #    self.childWidget.mousePressEvent(ev) ## ??????????
            qt.QTreeWidget.mousePressEvent(self, ev)##??????
            #if self.childItem!=None:
            #    self.childItem.setSelected(False)
    def mouseReleaseEvent(self, ev):
        if self.pressY == -1:
            qt.QTreeWidget.mouseReleaseEvent(self, ev)
        else:
            if abs(self.pressY - ev.y()) < 10:
                self.rootItem.setExpanded(not self.rootItem.isExpanded())
            #else:
            #    qt.QTreeWidget.mouseReleaseEvent(self, ev)
    def calcTextWidth(self, text):
        n = len(text)
        met = self.fontMetrics()
        w = 0
        for i in range(n):
            w += met.charWidth(text, i)
        return w
    def minimumSizeHint(self):
        if self.label:
            s1 = self.label.minimumSizeHint()
            w1 = s1.width()
            h1 = s1.height() + 3
        else:
            w1 = 0
            h1 = self.minHeight
        if self.childWidget:
            s2 = self.childWidget.minimumSizeHint()
            w2 = s2.width()
            h2 = s2.height() + 30
        else:
            w2 = 0
            h2 = 0
        w = max(w1, w2) + self.indent*2 + 23
        if self.isExpanded():
            h = h1 + h2
        else:
            h = h1
        return qc.QSize(w, h)

