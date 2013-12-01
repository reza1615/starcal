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

import sys
from os.path import dirname

from PyQt4 import QtGui as qt
from PyQt4 import QtCore as qc
from scal2.ui_qt.app import app

from scal2.utils import toUnicode
from scal2.locale_man import tr as _
from pray_times_backend import timeNames, methodsList

from scal2.ui_qt.mywidgets import VBox, HBox
from scal2.ui_qt.mywidgets.about_dialog import AboutDialog

dataDir = dirname(__file__)
earthR = 6370

autoLocale = True

class LocationDialog(qt.QDialog):
    def __init__(self, maxResults=200):
        #qt.QWidget.__init__(self, None, qc.Qt.Tool)## FIXME
        qt.QDialog.__init__(self, None, qc.Qt.Tool)## FIXME
        self.maxResults = maxResults
        self.vbox = qt.QVBoxLayout()
        self.vbox.setMargin(0)
        self.setLayout(self.vbox)
        ###############
        hbox = HBox()
        hbox.addWidget(qt.QLabel(_('Search Cities:')))
        entry = qt.QLineEdit()
        hbox.addWidget(entry)
        entry.changeEvent = self.entryChanged
        self.vbox.addWidget(hbox)
        ######################
        treev = qt.QTreeWidget()
        treev.setColumnCount(2)
        treev.setHeaderLabels([_('Index'), _('City'),])
        treev.hideColumn(0)
        #treev.set_headers_clickable(False)
        #treev.set_headers_visible(False)
        self.vbox.addWidget(treev)
        self.treev = treev
        treev.selectionChanged = self.treevSelectionChanged
        #treev.set_search_column(1)
        #########
        lines = file(dataDir+'/locations.txt').read().split('\n')
        cityData = []
        country = ''
        for l in lines:
            p = l.split('\t')
            if len(p)<2:
                #print(p)
                continue
            if p[0]=='':
                if p[1]=='':
                    city, lat, lng = p[2:5]
                    #if country=='Iran':
                    #    print(city)
                    if len(p)>4:
                        cityData.append((
                            country + '/' + city,
                            _(country) + '/' + _(city),
                            float(lat),
                            float(lng)
                        ))
                    else:
                        print(country, p)
                else:
                    country = p[1]

        self.cityData = cityData
        self.updateList()
        ###########
        gbox = qt.QGroupBox(_('Edit Manually'))
        gboxLay = qt.QVBoxLayout()
        gboxLay.setMargin(0)## FIXME
        gbox.setLayout(gboxLay)
        gbox.setCheckable(True)
        self.connect(gbox, qc.SIGNAL('toggled (bool)'), self.editCheckbToggled)
        self.gboxEdit = gbox
        vbox = VBox()
        #group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        #####
        hbox = HBox()
        label = qt.QLabel(_('Name:'))
        hbox.addWidget(label)
        #group.add_widget(label)
        #label.set_alignment(0, 0.5)
        entry = qt.QLineEdit()
        hbox.addWidget(entry)
        vbox.addWidget(hbox)
        self.entry_edit_name = entry
        ####
        hbox = HBox()
        label = qt.QLabel(_('Latitude:'))
        hbox.addWidget(label)
        #group.add_widget(label)
        #label.set_alignment(0, 0.5)
        ####
        spin = qt.QDoubleSpinBox()
        spin.setSingleStep(1)
        spin.setRange(-180, 180)
        spin.setDecimals(3)
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        hbox.addWidget(spin)
        vbox.addWidget(hbox)
        self.spin_lat = spin
        ####
        hbox = HBox()
        label = qt.QLabel(_('Longitude:'))
        hbox.addWidget(label)
        #group.add_widget(label)
        spin = qt.QDoubleSpinBox()
        spin.setSingleStep(1)
        spin.setRange(-180, 180)
        spin.setDecimals(3)
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        hbox.addWidget(spin)
        vbox.addWidget(hbox)
        self.spin_lng = spin
        ####
        hbox = HBox()
        self.lowerLabel = qt.QLabel('')
        # self.lowerLabel.setSizePolicy Expandig ## FIXME
        hbox.addWidget(self.lowerLabel)
        #self.lowerLabel.set_alignment(0, 0.5)
        button = qt.QPushButton(_('Calculate Nearest City'))
        self.connect(button, qc.SIGNAL('clicked ()'), self.calcClicked)
        hbox.addWidget(button)
        vbox.addWidget(hbox)
        ####
        vbox.setEnabled(False)
        gboxLay.addWidget(vbox)
        self.vbox_edit = vbox
        self.vbox.addWidget(gbox)
        #######
        bbox = qt.QDialogButtonBox(qc.Qt.Horizontal)
        cancelB = bbox.addButton(qt.QDialogButtonBox.Cancel)
        okB = bbox.addButton(qt.QDialogButtonBox.Ok)
        if autoLocale:
            cancelB.setText(_('_Cancel'))
            #cancelB.setIcon(qt.QIcon('cancel.png'))
            okB.setText(_('_OK'))
            #okB.setIcon(qt.QIcon('ok.png'))
            #okB.grab_default()#?????????
            #okB.grab_focus()#?????????
        ## ???????????????
        self.connect(bbox, qc.SIGNAL('rejected()'), lambda: self.reject())
        self.connect(bbox, qc.SIGNAL('accepted()'), lambda: self.accept())
        #self.connect(cancelB, qc.SIGNAL('clicked()'), self.reject)
        #self.connect(okB, qc.SIGNAL('clicked()'), self.accept)
        '''
        cancelB = self.add_button(gtk.STOCK_CANCEL, self.EXIT_CANCEL)
        okB = self.add_button(gtk.STOCK_OK, self.EXIT_OK)
        #if autoLocale:
        cancelB.setText(_('_Cancel'))
        cancelB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL, gtk.ICON_SIZE_BUTTON))
        okB.setText(_('_OK'))
        okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK, gtk.ICON_SIZE_BUTTON))
        '''
        self.vbox.addWidget(bbox)
        #######
        #self.vbox.show()
    def calcClicked(self):
        lat = self.spin_lat.value()
        lng = self.spin_lng.value()
        md = earthR*2*pi
        city = ''
        for (name, lname, lat2, lng2) in self.cityData:
            d = earthDistance(lat, lng, lat2, lng2)
            assert d>=0
            if d<md:
                md = d
                city = lname
        self.lowerLabel.setText(_('%s kilometers from %s')%(md, city))
    def treevSelectionChanged(self, treev, selected, deselected):
        try:
            i = selected.first().top()
        except:
            return
        j = int(self.topLevelItem(i).text(0))
        s = int(self.topLevelItem(i).text(1))
        self.entry_edit_name.setText(s)
        self.spin_lat.setValue(self.cityData[j][2])
        self.spin_lng.setValue(self.cityData[j][3])
        self.lowerLabel.setText(_('%s kilometers from %s')%(0.0, s))
        qt.QTreeWidget.selectionChanged(treev)
    def editCheckbToggled(self, active):
        self.vbox_edit.setEnabled(active)
        if not active:
            try:
                i = self.selectedIndexes()[0].row()
            except:
                lname = ''
                lat = 0
                lng = 0
            else:
                j = int(self.topLevelItem(i).text(0))
                name, lname, lat, lng = self.cityData[j]
            self.entry_edit_name.setText(lname)
            self.spin_lat.setValue(lat)
            self.spin_lng.setValue(lng)
    def updateList(self, s=''):
        s = s.lower()
        t = self.treev
        t.clear()
        d = self.cityData
        n = len(d)
        if s=='':
            for i in range(n):
                t.addTopLevelItem(qt.QTreeWidgetItem([unicode(i), d[i][0].decode('utf8')]))
        else:## here check also translations
            mr = self.maxResults
            r = 0
            for i in range(n):
                if s in (d[i][0]+'\n'+d[i][1]).lower():
                    t.append((i, d[i][1]))
                    r += 1
                    if r>=mr:
                        break
    def entryChanged(self, entry):
        print('entryChanged')
        self.updateList(entry.getText())
        qt.QLineEdit.changeEvent(entry)
    def run(self):
        ex = self.exec_()
        if ex == qt.QDialog.Accepted:
            if self.gboxEdit.isChecked() or self.selectedIndexes():
                return (self.entry_edit_name.getText(), self.spin_lat.value(), self.spin_lng.value())
        return None



class LocationButton(qt.QPushButton):
    def __init__(self, locName, lat, lng):
        qt.QPushButton.__init__(self, toUnicode(locName))
        self.setLocation(locName, lat, lng)
        self.dialog = LocationDialog()
        ####
        self.connect(self, qc.SIGNAL('clicked ()'), self.onClicked)
    def setLocation(self, locName, lat, lng):
        self.locName = locName
        self.lat = lat
        self.lng = lng
    def onClicked(self):
        res = self.dialog.run()
        if res:
            self.locName, self.lat, self.lng = res
            self.setText(toUnicode(self.locName))




class TextPlugUI:
    def makeWidget(self):
        self.confDialog = qt.QDialog()
        self.confDialog.setWindowTitle(_('Pray Times') + ' - ' + _('Configuration'))
        self.confDialog.vbox = qt.QVBoxLayout()
        self.confDialog.vbox.setMargin(0)
        self.confDialog.setLayout(self.confDialog.vbox)
        #group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        ###
        hbox = HBox()
        label = qt.QLabel(_('Location'))
        #group.add_widget(label)
        #label.set_alignment(0, 0.5)
        hbox.addWidget(label)
        self.locButton = LocationButton(self.locName, self.ptObj.lat, self.ptObj.lng)
        hbox.addWidget(self.locButton)
        self.confDialog.vbox.addWidget(hbox)
        ###
        hbox = HBox()
        label = qt.QLabel(_('Calculation Method'))
        #group.add_widget(label)
        #label.set_alignment(0, 0.5)
        hbox.addWidget(label)
        self.methodCombo = qt.QComboBox()
        for methodObj in methodsList:
            self.methodCombo.addItem(_(methodObj.desc))
        hbox.addWidget(self.methodCombo)
        self.confDialog.vbox.addWidget(hbox)
        #######
        treev = qt.QTreeWidget()
        treev.setColumnCount(3)
        treev.setHeaderLabels([_('Enable'), _('Description'), _('Name')])
        treev.hideColumn(2)
        ###
        self.shownTimesTreewidget = treev
        for name in timeNames:
            item = qt.QTreeWidgetItem(['', _(name.capitalize()), name])
            item.setCheckState(0, True)
            treev.addTopLevelItem(item)
        gbox = qt.QGroupBox(_('Shown Times'))
        gboxLay = qt.QVBoxLayout()
        gboxLay.setMargin(0)## FIXME
        gbox.setLayout(gboxLay)
        gboxLay.addWidget(treev)
        self.confDialog.vbox.addWidget(gbox)
        ######
        hbox = HBox()
        hbox.addWidget(qt.QLabel(_('Imsak')))
        spin = qt.QSpinBox()
        spin.setSingleStep(1)
        spin.setRange(0, 99)
        spin.setLayoutDirection(qc.Qt.LeftToRight)
        self.imsakSpin = spin
        hbox.addWidget(spin)
        hbox.addWidget(qt.QLabel(' '+_('minutes before fajr')))
        self.confDialog.vbox.addWidget(hbox)
        ######
        self.updateConfWidget()
        #######
        bbox = qt.QDialogButtonBox(qc.Qt.Horizontal)
        cancelB = bbox.addButton(qt.QDialogButtonBox.Cancel)
        okB = bbox.addButton(qt.QDialogButtonBox.Ok)
        if autoLocale:
            cancelB.setText(_('_Cancel'))
            #cancelB.setIcon(qt.QIcon('cancel.png'))
            okB.setText(_('_OK'))
            #okB.setIcon(qt.QIcon('ok.png'))
        self.confDialog.vbox.addWidget(bbox)
        bbox.connect(bbox, qc.SIGNAL('rejected()'), self.confDialogCancel)
        bbox.connect(bbox, qc.SIGNAL('accepted()'), self.confDialogOk)
        ##############
        '''
        submenu = gtk.Menu()
        submenu.add(gtk.MenuItem('Item 1'))
        submenu.add(gtk.MenuItem('Item 2'))
        #self.submenu = submenu
        self.menuitem = gtk.MenuItem('Owghat')
        self.menuitem.set_submenu(submenu)
        self.menuitem.show_all()
        '''
        self.dialog = None
    def updateConfWidget(self):
        self.locButton.setLocation(self.locName, self.ptObj.lat, self.ptObj.lng)
        self.methodCombo.setCurrentIndex(methodsList.index(self.ptObj.method))
        ###
        treev = self.shownTimesTreewidget
        for i in range(treev.topLevelItemCount()):
            #row[0] = (row[2] in self.shownTimeNames)
            item = treev.topLevelItem(i)
            item.setCheckState(0, qc.Qt.Checked if item.text(2) in self.shownTimeNames else qc.Qt.Unchecked)
        ###
        self.imsakSpin.setValue(self.imsak)
    def updateConfVars(self):
        self.locName = self.locButton.locName
        self.ptObj.lat = self.locButton.lat
        self.ptObj.lng = self.locButton.lng
        self.ptObj.method = methodsList[self.methodCombo.currentIndex()]
        self.shownTimeNames = []
        treev = self.shownTimesTreewidget
        for i in range(treev.topLevelItemCount()):
            item = treev.topLevelItem(i)
            if item.checkState(0)==qc.Qt.Checked:
                self.shownTimeNames.append(str(item.text(2)))
        self.imsak = int(self.imsakSpin.value())
        self.ptObj.imsak = '%d min'%self.imsak
    def confDialogCancel(self):
        self.confDialog.hide()
        self.updateConfWidget()
    def confDialogOk(self):
        #print('confDialogOk')
        self.confDialog.hide()
        #self.confDialog.accept()
        self.updateConfVars()
        self.saveConfig()
    def set_dialog(self, dialog):
        self.dialog = dialog
    def open_configure(self):
        self.confDialog.exec_()
    def open_about(self):
        about = AboutDialog()
        about.set_name(self.name) ## or set_program_name
        #about.set_version(VERSION)
        about.set_title(_('About')+' '+self.name) ## must call after set_name and set_version !
        about.set_authors([
            _('Hamid Zarrabi-Zadeh <zarrabi@scs.carleton.ca>'),
            _('Saeed Rasooli <saeed.gnu@gmail.com>')
        ])
        about.connect(bbox, qc.SIGNAL('rejected()'), lambda: about.reject())
        about.connect(bbox, qc.SIGNAL('accepted()'), lambda: about.accept())
        #about.set_comments(_(''))
        #about.connect('delete-event', lambda w, e: about.destroy())
        #about.connect('response', lambda w: about.hide())
        #about.set_skip_taskbar_hint(True)
        #buttonbox = about.vbox.get_children()[1]
        ##buttonbox.set_homogeneous(False)
        ##buttonbox.set_layout(qt.QPushButtonBOX_SPREAD)
        #buttons = buttonbox.get_children()## List of buttons of about dialogs
        #buttons[1].setText(_('C_redits'))
        #buttons[2].setText(_('_Close'))
        #buttons[2].set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE,gtk.ICON_SIZE_BUTTON))
        about.exec_()
        about.destroy()









