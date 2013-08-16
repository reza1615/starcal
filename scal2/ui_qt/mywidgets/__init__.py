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

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc



class VBox(qt.QWidget):
    vertical = True
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed)
        cls = qt.QVBoxLayout if self.vertical else qt.QHBoxLayout
        layout = cls()
        layout.setSpacing(0)
        layout.setMargin(0)
        self.setLayout(layout)
        for attr in ('addWidget', 'insertWidget', 'removeWidget', 'addLayout', 'addStretch', 'setDirection'):
            setattr(self, attr, getattr(layout, attr))

class HBox(VBox):
    vertical = False




if __name__=='__main__':
    import sys
    app = qt.QApplication(sys.argv)
    exp = Expander('expander')
    #exp.addWidget(qt.QLabel('Hello World'))
    #exp.addWidget(qt.QLineEdit())
    exp.addWidget(qt.QLabel('Hello\nPython'))
    #exp.show()
    win = qt.QWidget()
    vbox = qt.QVBoxLayout()
    vbox.addWidget(exp)
    #vbox.addStretch()
    win.setLayout(vbox)
    win.show()
    sys.exit(app.exec_())

