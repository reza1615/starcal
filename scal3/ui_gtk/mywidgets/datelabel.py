from scal3.utils import toStr
from scal3 import core
from scal3.locale_man import tr as _
from scal3 import ui

from scal3 import ui
from scal3.ui_gtk import *
from scal3.ui_gtk.utils import setClipboard

class DateLabel(gtk.Label):
	def __init__(self, text=None):
		gtk.Label.__init__(self, text)
		self.set_selectable(True)
		#self.set_cursor_visible(False)## FIXME
		self.set_can_focus(False)
		self.set_use_markup(True)
		self.connect('populate-popup', self.popupPopulate)
		####
		self.menu = gtk.Menu()
		##
		itemCopyAll = ImageMenuItem(_('Copy _All'))
		itemCopyAll.set_image(gtk.Image.new_from_stock(gtk.STOCK_COPY, gtk.IconSize.MENU))
		itemCopyAll.connect('activate', self.copyAll)
		self.menu.add(itemCopyAll)
		##
		itemCopy = ImageMenuItem(_('_Copy'))
		itemCopy.set_image(gtk.Image.new_from_stock(gtk.STOCK_COPY, gtk.IconSize.MENU))
		itemCopy.connect('activate', self.copy)
		self.itemCopy = itemCopy
		self.menu.add(itemCopy)
		##
		self.menu.show_all()
	def popupPopulate(self, label, menu):
		self.itemCopy.set_sensitive(self.get_property('cursor-position') > self.get_property('selection-bound'))## FIXME
		self.menu.popup(None, None, None, None, 3, 0)
		ui.updateFocusTime()
	def copy(self, item):
		start = self.get_property('selection-bound')
		end = self.get_property('cursor-position')
		setClipboard(toStr(self.get_text())[start:end])
	copyAll = lambda self, label: setClipboard(self.get_text())

