# -*- coding: utf-8 -*-
# 
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License,    or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Or on Debian systems, from /usr/share/common-licenses/GPL

import os, sys, shlex, time
from os.path import join, dirname

from scal2 import core
from scal2.core import pixDir, convert, numLocale, myRaise

from scal2.locale_man import tr as _
from scal2.locale_man import rtl

from scal2 import event_man
#from scal2.event_man import dateEncode, timeEncode, dateDecode, timeDecode
from scal2 import ui

from gobject import timeout_add_seconds
import gtk
from gtk import gdk


from scal2.ui_gtk.utils import imageFromFile, pixbufFromFile, rectangleContainsPoint, showError,\
                               labelStockMenuItem, labelImageMenuItem, confirm, toolButtonFromStock, set_tooltip
from scal2.ui_gtk.color_utils import gdkColorToRgb
from scal2.ui_gtk.drawing import newOutlineSquarePixbuf
#from scal2.ui_gtk.mywidgets.multi_spin_box import DateBox, TimeBox
from scal2.ui_gtk.export import ExportToIcsDialog

from scal2.ui_gtk.event.occurrence_view import *
from scal2.ui_gtk.event.common import IconSelectButton, EventEditorDialog, GroupEditorDialog

#print 'Testing translator', __file__, _('About')


class TrashEditorDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self)
        self.set_title(_('Edit Trash'))
        #self.connect('delete-event', lambda obj, e: self.destroy())
        #self.resize(800, 600)
        ###
        cancelB = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        okB = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        if ui.autoLocale:
            cancelB.set_label(_('_Cancel'))
            cancelB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL,gtk.ICON_SIZE_BUTTON))
            okB.set_label(_('_OK'))
            okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
        self.connect('response', lambda w, e: self.hide())
        #######
        self.trash = ui.eventTrash
        ##
        sizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        #######
        hbox = gtk.HBox()
        label = gtk.Label(_('Title'))
        label.set_alignment(0, 0.5)
        hbox.pack_start(label, 0, 0)
        sizeGroup.add_widget(label)
        self.titleEntry = gtk.Entry()
        hbox.pack_start(self.titleEntry, 1, 1)
        self.vbox.pack_start(hbox, 0, 0)
        ####
        hbox = gtk.HBox()
        label = gtk.Label(_('Icon'))
        label.set_alignment(0, 0.5)
        hbox.pack_start(label, 0, 0)
        sizeGroup.add_widget(label)
        self.iconSelect = IconSelectButton()
        hbox.pack_start(self.iconSelect, 0, 0)
        hbox.pack_start(gtk.Label(''), 1, 1)
        self.vbox.pack_start(hbox, 0, 0)
        ####
        self.vbox.show_all()
        self.updateWidget()
    def run(self):
        if gtk.Dialog.run(self)==gtk.RESPONSE_OK:
            self.updateVars()
        self.destroy()
    def updateWidget(self):
        self.titleEntry.set_text(self.trash.title)
        self.iconSelect.set_filename(self.trash.icon)
    def updateVars(self):
        self.trash.title = self.titleEntry.get_text()
        self.trash.icon = self.iconSelect.filename
        self.trash.saveConfig()



class EventManagerDialog(gtk.Dialog):## FIXME
    def checkEventToAdd(self, group, event):
        if not group.checkEventToAdd(event):
            showError(_('Group type "%s" can not contain event type "%s"')%(group.desc, event.desc), self)
            raise RuntimeError('Invalid event type for this group')
    def onResponse(self, win, event):
        self.hide()
        if self.mainWin:
            self.mainWin.onConfigChange()
        timeout_add_seconds(0, event_man.restartDaemon)## FIXME
    def onConfigChange(self):
        if not self.isLoaded:
            return
        for gid, eid, eventIndex in ui.trashedEvents:
            groupIndex = ui.eventGroups.index(gid)
            event = ui.eventTrash.getEvent(eid)
            self.trees.remove(self.trees.get_iter((groupIndex, eventIndex)))
            self.trees.insert(
                self.trashIter,
                0,
                self.getEventRow(event),
            )
        ###
        for gid, eid in ui.changedEvents:
            groupIndex = ui.eventGroups.index(gid)
            group = ui.eventGroups[gid]
            eventIndex = group.index(eid)
            event = group.getEvent(eid)
            eventPath = (groupIndex, eventIndex)
            eventIter = self.trees.get_iter(eventPath)
            for i, value in enumerate(self.getEventRow(event)):
                self.trees.set_value(eventIter, i, value)
        ###
        ui.changedEvents = []
        for gid in ui.changedGroups:
            groupIndex = ui.eventGroups.index(gid)
            group = ui.eventGroups[gid]
            groupIter = self.trees.get_iter((groupIndex,))
            for i, value in enumerate(self.getGroupRow(group)):
                self.trees.set_value(groupIter, i, value)
        ui.changedGroups = []
    def onShow(self, widget):
        self.onConfigChange()
    def __init__(self, mainWin=None):
        gtk.Dialog.__init__(self)
        self.mainWin = mainWin
        self.isLoaded = False
        self.set_title(_('Event Manager'))
        self.resize(600, 300)
        self.connect('delete-event', self.onDeleteEvent)
        ##
        okB = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        if ui.autoLocale:
            okB.set_label(_('_OK'))
            okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
        #self.connect('response', lambda w, e: self.hide())
        self.connect('response', self.onResponse)
        self.connect('show', self.onShow)
        #######
        treeBox = gtk.HBox()
        #####
        self.treev = gtk.TreeView()
        #self.treev.set_headers_visible(False)## FIXME
        #self.treev.get_selection().set_mode(gtk.SELECTION_MULTIPLE)## FIXME
        #self.treev.set_rubber_banding(gtk.SELECTION_MULTIPLE)## FIXME
        self.treev.connect('realize', self.onTreeviewRealize)
        self.treev.connect('cursor-changed', self.treeviewCursorChanged)## FIXME
        self.treev.connect('button-press-event', self.treeviewButtonPress)
        self.treev.connect('row-activated', self.onRowActivated)
        self.treev.connect('key-press-event', self.onKeyPress)
        #####
        swin = gtk.ScrolledWindow()
        swin.add(self.treev)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        treeBox.pack_start(swin, 1, 1)
        ###
        toolbar = gtk.Toolbar()
        toolbar.set_orientation(gtk.ORIENTATION_VERTICAL)
        size = gtk.ICON_SIZE_SMALL_TOOLBAR
        ###
        tb = toolButtonFromStock(gtk.STOCK_GO_UP, size)
        set_tooltip(tb, _('Move up'))
        tb.connect('clicked', self.moveUpByButton)
        toolbar.insert(tb, -1)
        ###
        tb = toolButtonFromStock(gtk.STOCK_GO_DOWN, size)
        set_tooltip(tb, _('Move down'))
        tb.connect('clicked', self.moveDownByButton)
        toolbar.insert(tb, -1)
        ###
        tb = toolButtonFromStock(gtk.STOCK_COPY, size)
        set_tooltip(tb, _('Duplicate'))
        tb.connect('clicked', self.duplicateButtonClicked)
        toolbar.insert(tb, -1)
        ###
        treeBox.pack_start(toolbar, 0, 0)
        #####
        self.vbox.pack_start(treeBox)
        #######
        self.trees = gtk.TreeStore(int, gdk.Pixbuf, str, str)
        ## event: eid,  event_icon,   event_summary, event_description
        ## group: gid,  group_pixbuf, group_title,   ?description
        ## trash: -1,        trash_icon,   _('Trash'),    ''
        self.treev.set_model(self.trees)
        ###
        col = gtk.TreeViewColumn()
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell)
        col.add_attribute(cell, 'pixbuf', 1)
        self.treev.append_column(col)
        ###
        col = gtk.TreeViewColumn(_('Summary'), gtk.CellRendererText(), text=2)
        col.set_resizable(True)
        self.treev.append_column(col)
        ###
        col = gtk.TreeViewColumn(_('Description'), gtk.CellRendererText(), text=3)
        self.treev.append_column(col)
        ###
        #self.treev.set_search_column(2)## or 3
        ###
        #self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        #self.clipboard = gtk.clipboard_get()
        self.toPasteEvent = None ## (path, bool move)
        #####
        self.vbox.show_all()
        #self.reloadEvents()## FIXME
    def canPasteToGroup(self, group):
        if self.toPasteEvent is None:
            return False
        ## check event type here? FIXME
        return True
    def genRightClickMenu(self, path):
        ## how about multi-selection? FIXME
        ## and Select _All menu item
        #cur = self.treev.get_cursor()
        #if not cur:
        #    return None
        #(path, col) = cur
        obj_list = self.getObjsByPath(path)
        #print len(obj_list)
        menu = gtk.Menu()
        if len(obj_list)==1:
            group = obj_list[0]
            if group.name == 'trash':
                #print 'right click on trash', group.title
                menu.add(labelStockMenuItem('Edit', gtk.STOCK_EDIT, self.editTrash))
                menu.add(labelStockMenuItem('Empty Trash', gtk.STOCK_CLEAR, self.emptyTrash))
            else:
                #print 'right click on group', group.title
                menu.add(labelStockMenuItem('Edit', gtk.STOCK_EDIT, self.editGroup, path, group))
                eventTypes = group.acceptsEventTypes
                if eventTypes is None:
                    eventTypes = event_man.eventsClassNameList
                for eventType in eventTypes:
                    #if eventType == 'custom':## FIXME
                    #    desc = _('Event')
                    #else:
                    desc = event_man.eventsClassDict[eventType].desc
                    menu.add(labelStockMenuItem(
                        _('Add ') + desc,
                        gtk.STOCK_ADD,
                        self.addEventToGroupFromMenu,
                        path,
                        group,
                        eventType,
                        _('Add') + ' ' + desc,
                    ))
                pasteItem = labelStockMenuItem('Paste Event', gtk.STOCK_PASTE, self.pasteEventIntoGroup, path)
                pasteItem.set_sensitive(self.canPasteToGroup(group))
                menu.add(pasteItem)
                ##
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('Add New Group', gtk.STOCK_NEW, self.addGroupAfterGroup, path))
                menu.add(labelStockMenuItem('Duplicate', gtk.STOCK_COPY, self.duplicateGroupFromMenu, path))
                menu.add(labelStockMenuItem('Duplicate with All Events', gtk.STOCK_COPY, self.duplicateGroupWithEventsFromMenu, path))
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('Delete Group', gtk.STOCK_DELETE, self.deleteGroup, path))
                ##
                menu.add(labelStockMenuItem('Move Up', gtk.STOCK_GO_UP, self.moveUpFromMenu, path))
                menu.add(labelStockMenuItem('Move Down', gtk.STOCK_GO_DOWN, self.moveDownFromMenu, path))
                ##
                menu.add(labelImageMenuItem('Export to iCalendar', 'ical-32.png', self.exportGroupToIcsFromMenu, group))
                ###
                for (actionName, actionFuncName) in group.actions:
                    menu.add(labelStockMenuItem(_(actionName), None, self.groupActionClicked, group, actionFuncName))
        elif len(obj_list)==2:
            (group, event) = obj_list
            #print 'right click on event', event.summary
            if group.name != 'trash':
                menu.add(labelStockMenuItem('Edit', gtk.STOCK_EDIT, self.editEventFromMenu, path))
                menu.add(gtk.SeparatorMenuItem())
            menu.add(labelStockMenuItem('Cut', gtk.STOCK_CUT, self.cutEvent, path))
            menu.add(labelStockMenuItem('Copy', gtk.STOCK_COPY, self.copyEvent, path))
            ##
            if group.name == 'trash':
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('Delete', gtk.STOCK_DELETE, self.deleteEventFromTrash, path))
            else:
                pasteItem = labelStockMenuItem('Paste', gtk.STOCK_PASTE, self.pasteEventAfterEvent, path)
                pasteItem.set_sensitive(self.canPasteToGroup(group))
                menu.add(pasteItem)
                ##
                menu.add(gtk.SeparatorMenuItem())
                #menu.add(labelImageMenuItem(_('Move to Trash'), ui.eventTrash.icon, self.moveEventToTrash, path))
                menu.add(labelImageMenuItem(_('Move to %s')%ui.eventTrash.title, ui.eventTrash.icon, self.moveEventToTrash, path))
        else:
            return
        menu.show_all()
        return menu
    def openRightClickMenu(self, path, etime=None):
        menu = self.genRightClickMenu(path)
        if not menu:
            return
        if etime is None:
            etime = gtk.get_current_event_time()
        menu.popup(None, None, None, 3, etime)
    def onTreeviewRealize(self, event):
        self.reloadEvents()## FIXME
        self.isLoaded = True
    def onRowActivated(self, treev, path, col):
        if len(path)==1:
            if self.treev.row_expanded(path):
                self.treev.collapse_row(path)
            else:
                self.treev.expand_row(path, False)
        elif len(path)==2:
            self.editEventByPath(path)
    def onKeyPress(self, treev, g_event):
        #from scal2.time_utils import getCurrentTime, getGtkTimeFromEpoch
        #print g_event.time-getGtkTimeFromEpoch(time.time())## FIXME
        #print getCurrentTime()-gdk.CURRENT_TIME/1000.0
        ## gdk.CURRENT_TIME == 0## FIXME
        ## g_event.time == gtk.get_current_event_time() ## OK
        k = g_event.keyval
        if k==65383:# Simulate right click (key beside Right-Ctrl)
            cur = self.treev.get_cursor()
            if not cur:
                return
            (path, col) = cur
            menu = self.genRightClickMenu(path)
            if not menu:
                return
            rect = self.treev.get_cell_area(path, self.treev.get_column(1))
            x = rect.x
            if rtl:
                x -= 100
            else:
                x += 50
            (dx, dy) = self.treev.translate_coordinates(self, x, rect.y + rect.height)
            (wx, wy) = self.window.get_origin()
            menu.popup(None, None, lambda m: (wx+dx, wy+dy+20, True), 3, g_event.time)
        else:
            return False
        return True
    getRowBgColor = lambda self: gdkColorToRgb(self.treev.style.base[gtk.STATE_NORMAL])## bg color of non-selected rows
    getEventRow = lambda self, event: (
        event.eid,
        pixbufFromFile(event.icon),
        event.summary,
        event.description,
    )
    getGroupRow = lambda self, group, rowBgColor: (
        group.gid,
        newOutlineSquarePixbuf(
            group.color,
            20,
            0 if group.enable else 15,
            rowBgColor,
        ),
        group.title,
        '',
    )
    def reloadEvents(self):
        self.trees.clear()
        rowBgColor = self.getRowBgColor()
        for group in ui.eventGroups:
            groupIter = self.trees.append(None, self.getGroupRow(group, rowBgColor))
            for event in group:
                self.trees.append(groupIter, self.getEventRow(event))
        self.trashIter = self.trees.append(None, (
            -1,
            pixbufFromFile(ui.eventTrash.icon),
            ui.eventTrash.title,
            '',
        ))
        for event in ui.eventTrash:
            self.trees.append(self.trashIter, self.getEventRow(event))
        self.treeviewCursorChanged()
    def onDeleteEvent(self, obj, event):
        self.hide()
        return True
    def getObjsByPath(self, path):
        obj_list = []
        for i in range(len(path)):
            it = self.trees.get_iter(path[:i+1])
            obj_id = self.trees.get_value(it, 0)
            if i==0:
                if obj_id==-1:
                    obj_list.append(ui.eventTrash)
                else:
                    obj_list.append(ui.eventGroups[obj_id])
            else:
                obj_list.append(obj_list[i-1].getEvent(obj_id))
        return obj_list
    def treeviewCursorChanged(self, treev=None):
        cur = self.treev.get_cursor()
        if not cur:
            return
        (path, col) = cur
        ## update eventInfoBox
        return True
    def treeviewButtonPress(self, treev, g_event):
        pos_t = treev.get_path_at_pos(int(g_event.x), int(g_event.y))
        if not pos_t:
            return
        (path, col, xRel, yRel) = pos_t
        if not path:
            return
        if not col:
            return
        rect = treev.get_cell_area(path, col)
        if not rectangleContainsPoint(rect, g_event.x, g_event.y):
            return
        if g_event.button == 1:
            obj_list = self.getObjsByPath(path)
            node_iter = self.trees.get_iter(path)
            if len(obj_list) == 1:## group, not event
                group = obj_list[0]
                if group.name != 'trash':
                    cell = col.get_cell_renderers()[0]
                    try:
                        cell.get_property('pixbuf')
                    except:
                        pass
                    else:
                        group.enable = not group.enable
                        group.saveConfig()
                        self.trees.set_value(
                            node_iter,
                            1,
                            newOutlineSquarePixbuf(
                                group.color,
                                20,
                                0 if group.enable else 15,
                                self.getRowBgColor(),
                            ),
                        )
        elif g_event.button == 3:
            self.openRightClickMenu(path, g_event.time)
    def addGroupAfterGroup(self, menu, path):
        (index,) = path
        group = GroupEditorDialog().run()
        if group is None:
            return
        group.saveConfig()
        ui.eventGroups.insert(index+1, group)
        ui.eventGroups.saveConfig()
        afterGroupIter = self.trees.get_iter(path)
        self.trees.insert_after(
            #self.trees.get_iter_root(),## parent
            self.trees.iter_parent(afterGroupIter),
            afterGroupIter,## sibling
            self.getGroupRow(group, self.getRowBgColor()), ## row
        )
    def duplicateGroup(self, path):
        (index,) = path
        (group,) = self.getObjsByPath(path)
        newGroup = group.copy()
        ui.duplicateGroupTitle(newGroup)
        newGroup.saveConfig()
        ui.eventGroups.insert(index+1, newGroup)
        ui.eventGroups.saveConfig()
        self.trees.insert(
            None,
            index+1,
            self.getGroupRow(newGroup, self.getRowBgColor()),
        )
    def duplicateGroupWithEvents(self, path):
        (index,) = path
        (group,) = self.getObjsByPath(path)
        newGroup = group.deepCopy()
        ui.duplicateGroupTitle(newGroup)
        newGroup.saveConfig()
        ui.eventGroups.insert(index+1, newGroup)
        ui.eventGroups.saveConfig()
        newGroupIter = self.trees.insert(
            None,
            index+1,
            self.getGroupRow(newGroup, self.getRowBgColor()),
        )
        for event in newGroup:
            self.trees.append(newGroupIter, self.getEventRow(event))
    duplicateGroupFromMenu = lambda self, menu, path: self.duplicateGroup(path[0])
    duplicateGroupWithEventsFromMenu = lambda self, menu, path: self.duplicateGroupWithEvents(path)
    def duplicateButtonClicked(self, button):
        cur = self.treev.get_cursor()
        if not cur:
            return
        (path, col) = cur
        if len(path)==1:
            self.duplicateGroup(path)
        elif len(path)==2:## FIXME
            self.toPasteEvent = (path, False)
            self.pasteEventAfterEvent(None, path)
    def editGroup(self, menu, path, group):
        group = GroupEditorDialog(group).run()
        if group is None:
            return
        groupIter = self.trees.get_iter(path)
        for i, value in enumerate(self.getGroupRow(group, self.getRowBgColor())):
            self.trees.set_value(groupIter, i, value)
    def deleteGroup(self, menu, path):
        (index,) = path
        (group,) = self.getObjsByPath(path)
        if not confirm(_('Press OK if you are sure to delete group "%s"')%group.title):
            return
        ui.deleteEventGroup(group)
        self.trees.remove(self.trees.get_iter(path))
        self.reloadEvents()## FIXME
    def addEventToGroupFromMenu(self, menu, path, group, eventType, title):
        event = group.createEvent(eventType)
        event = EventEditorDialog(
            event,
            eventTypeChangable=(eventType=='custom'),## or True FIXME
            title=title,
            parent=self,
        ).run()
        if event is None:
            return
        group.append(event)
        group.saveConfig()
        self.trees.append(
            self.trees.get_iter(path),## parent
            self.getEventRow(event), ## row
        )
    def editEventByPath(self, path):
        (group, event) = self.getObjsByPath(path)
        event = EventEditorDialog(
            event,
            title=_('Edit ')+event.desc,
            parent=self,
        ).run()
        if event is None:
            return
        event.saveConfig()
        eventIter = self.trees.get_iter(path)
        for i, value in enumerate(self.getEventRow(event)):
            self.trees.set_value(eventIter, i, value)
    editEventFromMenu = lambda self, menu, path: self.editEventByPath(path)
    def moveEventToTrash(self, menu, path):
        (group, event) = self.getObjsByPath(path)
        ui.moveEventToTrash(group, event)
        self.trees.remove(self.trees.get_iter(path))
        self.trees.insert(
            self.trashIter,
            0,
            self.getEventRow(event),
        )
    def deleteEventFromTrash(self, menu, path):
        (trash, event) = self.getObjsByPath(path)
        trash.deleteEvent(event.eid)## trash == ui.eventTrash
        trash.saveConfig()
        self.trees.remove(self.trees.get_iter(path))
    def emptyTrash(self, menu):
        ui.eventTrash.empty()
        while True:
            childIter = self.trees.iter_children(self.trashIter)
            if childIter is None:
                break
            self.trees.remove(childIter)
    def editTrash(self, menu):
        TrashEditorDialog().run()
        self.trees.set_value(
            self.trashIter,
            1,
            pixbufFromFile(ui.eventTrash.icon),
        )
        self.trees.set_value(
            self.trashIter,
            2,
            ui.eventTrash.title,
        )
    def moveUp(self, path):
        if len(path)==1:
            if path[0]==0:
                return
            srcIter = self.trees.get_iter(path)
            if self.trees.get_value(srcIter, 0)==-1:
                return
            tarIter = self.trees.get_iter((path[0]-1))
            self.trees.move_before(srcIter, tarIter)
            ui.eventGroups.moveUp(path[0])
            ui.eventGroups.saveConfig()
        elif len(path)==2:
            (parentObj, event) = self.getObjsByPath(path)
            parentLen = len(parentObj)
            srcIter = self.trees.get_iter(path)
            (parentIndex, eventIndex) = path
            #print eventIndex, parentLen
            if eventIndex > 0:
                tarIter = self.trees.get_iter((parentIndex, eventIndex-1))
                self.trees.move_before(srcIter, tarIter)## or use self.trees.swap FIXME
                parentObj.moveUp(eventIndex)
                parentObj.saveConfig()
            else:
                ## move event to end of previous group
                #if parentObj.name == 'trash':
                #    return
                if parentIndex < 1:
                    return
                newParentIter = self.trees.get_iter((parentIndex - 1))
                newParentId = self.trees.get_value(newParentIter, 0)
                if newParentId==-1:## could not be!
                    return
                newGroup = ui.eventGroups[newParentId]
                self.checkEventToAdd(newGroup, event)
                self.trees.remove(srcIter)
                eventNewPath = self.trees.get_path(self.trees.append(
                    newParentIter,## parent
                    self.getEventRow(event), ## row
                ))
                self.treev.expand_to_path(eventNewPath)
                self.treev.set_cursor(eventNewPath)
                ###
                parentObj.excludeEvent(event.eid)
                parentObj.saveConfig()
                newGroup.append(event)
                newGroup.saveConfig()
    def moveDown(self, path):
        if len(path)==1:
            srcIter = self.trees.get_iter(path)
            if self.trees.get_value(srcIter, 0)==-1:
                return
            tarIter = self.trees.get_iter((path[0]+1))
            if self.trees.get_value(tarIter, 0)==-1:
                return
            self.trees.move_after(srcIter, tarIter)## or use self.trees.swap FIXME
            ui.eventGroups.moveDown(path[0])
            ui.eventGroups.saveConfig()
        elif len(path)==2:
            (parentObj, event) = self.getObjsByPath(path)
            parentLen = len(parentObj)
            srcIter = self.trees.get_iter(path)
            (parentIndex, eventIndex) = path
            #print eventIndex, parentLen
            if eventIndex < parentLen-1:
                tarIter = self.trees.get_iter((parentIndex, eventIndex+1))
                self.trees.move_after(srcIter, tarIter)
                parentObj.moveDown(eventIndex)
                parentObj.saveConfig()
            else:
                ## move event to top of next group
                if parentObj.name == 'trash':
                    return
                newParentIter = self.trees.get_iter((parentIndex + 1))
                newParentId = self.trees.get_value(newParentIter, 0)
                if newParentId==-1:
                    return
                newGroup = ui.eventGroups[newParentId]
                self.checkEventToAdd(newGroup, event)
                self.trees.remove(srcIter)
                eventNewPath = self.trees.get_path(self.trees.insert(
                    newParentIter,## parent
                    0,## position
                    self.getEventRow(event), ## row
                ))
                self.treev.expand_to_path(eventNewPath)
                self.treev.set_cursor(eventNewPath)
                ###
                parentObj.excludeEvent(event.eid)
                parentObj.saveConfig()
                newGroup.insert(0, event)
                newGroup.saveConfig()
    moveUpFromMenu = lambda self, menu, path: self.moveUp(path)
    moveDownFromMenu = lambda self, menu, path: self.moveDown(path)
    def moveUpByButton(self, button):
        cur = self.treev.get_cursor()
        if not cur:
            return
        self.moveUp(cur[0])
    def moveDownByButton(self, button):
        cur = self.treev.get_cursor()
        if not cur:
            return
        self.moveDown(cur[0])
    def exportGroupToIcsFromMenu(self, menu, group):
        ExportToIcsDialog(group.exportToIcs, group.title).run()
    def groupActionClicked(self, menu, group, actionFuncName):
        getattr(group, actionFuncName)()
    def cutEvent(self, menu, path):
        self.toPasteEvent = (path, True)
    def copyEvent(self, menu, path):
        self.toPasteEvent = (path, False)
    def pasteEventAfterEvent(self, menu, tarPath):## tarPath is a 2-lengthed tuple
        if not self.toPasteEvent:
            return
        (srcPath, move) = self.toPasteEvent
        (srcGroup, srcEvent) = self.getObjsByPath(srcPath)
        (tarGroup, tarEvent) = self.getObjsByPath(tarPath)
        self.checkEventToAdd(tarGroup, srcEvent)
        tarGroupIter = self.trees.get_iter(tarPath[:1])
        tarEventIter = self.trees.get_iter(tarPath)
        # tarEvent is not used
        ###
        if move:
            srcGroup.excludeEvent(srcEvent.eid)
            srcGroup.saveConfig()
            tarGroup.insert(tarPath[1], srcEvent)
            tarGroup.saveConfig()
            self.trees.remove(self.trees.get_iter(srcPath))
            newEvent = srcEvent
        else:
            newEvent = srcEvent.copy()
            newEvent.saveConfig()
            tarGroup.insert(tarPath[1], newEvent)
            tarGroup.saveConfig()
        newEventPath = self.trees.get_path(self.trees.insert_after(
            tarGroupIter,## parent
            tarEventIter,## sibling
            self.getEventRow(newEvent), ## row
        ))
        self.treev.set_cursor(newEventPath)
        self.toPasteEvent = None
    def pasteEventIntoGroup(self, menu, tarPath):## tarPath is a 1-lengthed tuple
        if not self.toPasteEvent:
            return
        (srcPath, move) = self.toPasteEvent
        (srcGroup, srcEvent) = self.getObjsByPath(srcPath)
        (tarGroup,) = self.getObjsByPath(tarPath)
        self.checkEventToAdd(tarGroup, srcEvent)
        tarGroupIter = self.trees.get_iter(tarPath)
        ###
        if move:
            srcGroup.excludeEvent(srcEvent.eid)
            srcGroup.saveConfig()
            tarGroup.append(srcEvent)
            tarGroup.saveConfig()
            tarGroupCount = self.trees.iter_n_children(tarGroupIter)
            self.trees.remove(self.trees.get_iter(srcPath))
            newEvent = srcEvent
        else:
            newEvent = srcEvent.copy()
            newEvent.saveConfig()
            tarGroup.append(newEvent)
            tarGroup.saveConfig()
        self.trees.append(
            tarGroupIter,## parent
            self.getEventRow(newEvent), ## row
        )
        self.toPasteEvent = None
    #def selectAllEventInGroup(self, menu):## FIXME
    #    pass
    #def selectAllEventInTrash(self, menu):## FIXME
    #    pass





def makeWidget(obj):## obj is an instance of Event or EventRule or EventNotifier
    if hasattr(obj, 'WidgetClass'):
        widget = obj.WidgetClass(obj)
        try:
            widget.show_all()
        except AttributeError:
            widget.show()
        widget.updateWidget()## FIXME
        return widget
    else:
        return None

##############################################################################





##############################################################################

if rtl:
    gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)


modPrefix = 'scal2.ui_gtk.event.'

for cls in event_man.eventsClassList:
    try:
        module = __import__(modPrefix + cls.name, fromlist=['EventWidget'])
        cls.WidgetClass = module.EventWidget
    except:
        myRaise()

for cls in event_man.eventRulesClassList:
    try:
        module = __import__(modPrefix + 'rules.' + cls.name, fromlist=['RuleWidget'])
    except:
        myRaise()
        continue
    try:
        cls.WidgetClass = module.RuleWidget
    except AttributeError:
        print 'no class RuleWidget defined in module "%s"'%cls.name

for cls in event_man.eventNotifiersClassList:
    try:
        module = __import__(modPrefix + 'notifiers.' + cls.name, fromlist=['NotifierWidget', 'notify'])
        cls.WidgetClass = module.NotifierWidget
        cls.notify = module.notify
    except:
        myRaise()

for cls in event_man.eventGroupsClassList:
    try:
        module = __import__(modPrefix + 'groups.' + cls.name, fromlist=['GroupWidget'])
    except:
        myRaise()
        continue
    try:
        cls.WidgetClass = module.GroupWidget
    except AttributeError:
        print 'no class GroupWidget defined in module "%s"'%cls.name


event_man.Event.makeWidget = makeWidget
event_man.EventRule.makeWidget = makeWidget
event_man.EventNotifier.makeWidget = makeWidget
event_man.EventGroup.makeWidget = makeWidget

ui.eventGroups.loadConfig()
ui.eventTrash.loadConfig()

def testCustomEventEditor():
    from pprint import pprint, pformat
    dialog = gtk.Dialog()
    #dialog.vbox.pack_start(IconSelectButton('/usr/share/starcal2/pixmaps/starcal2.png'))
    event = event_man.Event(1)
    event.loadConfig()
    widget = event.makeWidget()
    dialog.vbox.pack_start(widget)
    dialog.vbox.show_all()
    dialog.add_button('OK', 0)
    def on_response(d, e):
        widget.updateVars()
        widget.event.saveConfig()
        pprint(widget.event.getData())
    dialog.connect('response', on_response)
    #dialog.run()
    dialog.present()
    gtk.main()

if __name__=='__main__':
    testCustomEventEditor()

