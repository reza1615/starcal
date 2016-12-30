# -*- coding: utf-8 -*-
#
# Copyright (C) Saeed Rasooli <saeed.gnu@gmail.com>
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


import json, os
from os.path import join, split, isdir, isfile, dirname, splitext
from os import listdir
import math
from time import time as now

import natz

from scal3.lib import OrderedDict

from .path import *

from scal3.lockfile import checkAndSaveJsonLockFile
from scal3.utils import printError, ifloor, iceil, findNearestIndex, myRaise, myRaiseTback
from scal3.utils import toStr
from scal3.os_utils import makeDir
from scal3.interval_utils import *
from scal3.time_utils import *
from scal3.date_utils import *
from scal3.json_utils import jsonToData


from scal3.s_object import *

from scal3.cal_types import calTypes, jd_to, to_jd, convert, DATE_GREG, getSysDate
from scal3 import ics
from scal3.locale_man import tr as _
from scal3.locale_man import getMonthName, textNumEncode
from scal3 import core
from scal3.core import log, getAbsWeekNumberFromJd, jwday, jd_to_primary



dayLen = 24*3600

icsMinStartYear = 1970
icsMaxEndYear = 2050

eventsDir = join(confDir, 'event', 'events')
groupsDir = join(confDir, 'event', 'groups')
accountsDir = join(confDir, 'event', 'accounts')

##########################

lockPath = join(confDir, 'event', 'lock.json')
readOnly = checkAndSaveJsonLockFile(lockPath)
if readOnly:
	print('Event lock file %s exists, EVENT DATA IS READ-ONLY'%lockPath)

##########################

makeDir(eventsDir)
makeDir(groupsDir)
makeDir(accountsDir)

###################################################

class JsonEventObj(JsonSObj):
	def save(self):
		if readOnly:
			print('events are read-only, ignored file %s'%self.file)
			return
		JsonSObj.save(self)


class BsonHistEventObj(BsonHistObj):
	def save(self, *args):
		if readOnly:
			print('events are read-only, ignored file %s'%self.file)
			return
		return BsonHistObj.save(self, *args)




class InfoWrapper(JsonEventObj):
	file = join(confDir, 'event', 'info.json')
	skipLoadNoFile = True
	params = (
		'version',
		'last_run',
	)
	paramsOrder = (
		'version',
		'last_run',
	)
	def __init__(self):
		self.version = ''
		self.last_run = 0
	def update(self):
		self.version = core.VERSION
		self.last_run = int(now())
	def updateAndSave(self):
		self.update()
		self.save()

info = InfoWrapper.load()

###################################################

class LastIdsWrapper(JsonEventObj):
	skipLoadNoFile = True
	file = join(confDir, 'event', 'last_ids.json')
	params = (
		'event',
		'group',
		'account',
	)
	paramsOrder = (
		'event',
		'group',
		'account',
	)
	def __init__(self):
		self.event = 0
		self.group = 0
		self.account = 0


lastIds = LastIdsWrapper.load()

###########################################################################

class ClassGroup(list):
	def __init__(self, tname):
		list.__init__(self)
		self.tname = tname
		self.names = []
		self.byName = {}
		self.byDesc = {}
		self.main = None
	def register(self, cls):
		assert cls.name != ''
		cls.tname = self.tname
		self.append(cls)
		self.names.append(cls.name)
		self.byName[cls.name] = cls
		self.byDesc[cls.desc] = cls
		return cls
	def setMain(self, cls):
		self.main = cls
		return cls

class classes:
	rule = ClassGroup('rule')
	notifier = ClassGroup('notifier')
	event = ClassGroup('event')
	group = ClassGroup('group')
	account = ClassGroup('account')

defaultEventTypeIndex = 0 ## FIXME
defaultGroupTypeIndex = 0 ## FIXME

__plugin_api_get__ = [
	'classes', 'defaultEventTypeIndex', 'defaultGroupTypeIndex',
	'EventRule', 'EventNotifier', 'Event', 'EventGroup', 'Account',
]


###########################################################################

def getEventUID(event):
	import socket
	event_st = core.compressLongInt(hash(str(event.getData())))
	time_st = core.getCompactTime()
	host = socket.gethostname()
	return event_st + '_' + time_st + '@' + host

class BadEventFile(Exception):## FIXME
	pass


class Occurrence(SObj):
	def __init__(self):
		self.event = None
	def intersection(self):
		raise NotImplementedError
	getDaysJdList = lambda self: [] ## make generator FIXME
	getTimeRangeList = lambda self: [] ## make generator FIXME
	def getFloatJdRangeList(self):
		ls = []
		for ep0, ep1 in self.getTimeRangeList():
			ls.append((getFloatJdFromEpoch(ep0), getFloatJdFromEpoch(ep1)))
		return ls
	def getStartJd(self):
		raise NotImplementedError
	def getEndJd(self):
		raise NotImplementedError
	#__iter__ = lambda self: iter(self.getTimeRangeList())

class JdSetOccurrence(Occurrence):
	name = 'jdSet'
	def __init__(self, jdSet=None):
		Occurrence.__init__(self)
		if not jdSet:
			jdSet = []
		self.jdSet = set(jdSet)
	__repr__ = lambda self: 'JdSetOccurrence(%r)'%list(self.jdSet)
	__bool__ = lambda self: bool(self.jdSet)
	__len__ = lambda self: len(self.jdSet)
	getStartJd = lambda self: min(self.jdSet)
	getEndJd = lambda self: max(self.jdSet)+1
	def intersection(self, occur):
		if isinstance(occur, JdSetOccurrence):
			return JdSetOccurrence(self.jdSet.intersection(occur.jdSet))
		elif isinstance(occur, TimeRangeListOccurrence):
			return TimeRangeListOccurrence(
				intersectionOfTwoIntervalList(
					self.getTimeRangeList(),
					occur.getTimeRangeList(),
				)
			)
		elif isinstance(occur, TimeListOccurrence):
			return occur.intersection(self)
		else:
			raise TypeError
	getDaysJdList = lambda self: sorted(self.jdSet)
	getTimeRangeList = lambda self: [
		(
			getEpochFromJd(jd),
			getEpochFromJd(jd+1),
		) for jd in self.jdSet
	]
	def calcJdRanges(self):
		jdList = sorted(self.jdSet) ## jdList is sorted
		if not jdList:
			return []
		startJd = jdList[0]
		endJd = startJd + 1
		jdRanges = []
		for jd in jdList[1:]:
			if jd == endJd:
				endJd += 1
			else:
			   jdRanges.append((startJd, endJd))
			   startJd = jd
			   endJd = startJd + 1
		jdRanges.append((startJd, endJd))
		return jdRanges


class TimeRangeListOccurrence(Occurrence):
	name = 'timeRange'
	def __init__(self, rangeList=None):
		Occurrence.__init__(self)
		if not rangeList:
			rangeList = []
		self.rangeList = rangeList
	__repr__ = lambda self: 'TimeRangeListOccurrence(%r)'%self.rangeList
	__bool__ = lambda self: bool(self.rangeList)
	__len__ = lambda self: len(self.rangeList)
	#__getitem__ = lambda i: self.rangeList.__getitem__(i)## FIXME
	getStartJd = lambda self: getJdFromEpoch(min([r[0] for r in self.rangeList]))
	getEndJd = lambda self: getJdFromEpoch(max([r[1] for r in self.rangeList]))
	def intersection(self, occur):
		if isinstance(occur, (JdSetOccurrence, TimeRangeListOccurrence)):
			return TimeRangeListOccurrence(
				intersectionOfTwoIntervalList(
					self.getTimeRangeList(),
					occur.getTimeRangeList(),
				)
			)
		elif isinstance(occur, TimeListOccurrence):
			return occur.intersection(self)
		else:
			raise TypeError('bad type %s (%r)'%(occur.__class__.__name__, occur))
	def getDaysJdList(self):
		jds = set()
		for startEpoch, endEpoch in self.rangeList:
			for jd in getJdListFromEpochRange(startEpoch, endEpoch):
				jds.add(jd)
		return sorted(jds)
	getTimeRangeList = lambda self: self.rangeList
	@staticmethod
	def newFromStartEnd(startEpoch, endEpoch):
		if startEpoch > endEpoch:
			return TimeRangeListOccurrence([])
		else:
			return TimeRangeListOccurrence([(startEpoch, endEpoch)])



class TimeListOccurrence(Occurrence):
	name = 'repeativeTime'
	def __init__(self, *args):
		Occurrence.__init__(self)
		if len(args)==0:
			self.startEpoch = 0
			self.endEpoch = 0
			self.stepSeconds = -1
			self.epochList = set()
		if len(args)==1:
			self.epochList = set(args[0])
		elif len(args)==3:
			self.setRange(*args)
		else:
			raise ValueError
	__repr__ = lambda self: 'TimeListOccurrence(%r)'%self.epochList
	#__bool__ = lambda self: self.startEpoch == self.endEpoch
	__bool__ = lambda self: bool(self.epochList)
	getStartJd = lambda self: getJdFromEpoch(min(self.epochList))
	getEndJd = lambda self: getJdFromEpoch(max(self.epochList)+1)
	def setRange(self, startEpoch, endEpoch, stepSeconds):
		try:
			from numpy.core.multiarray import arange
		except ImportError:
			from scal3.utils import arange
		######
		self.startEpoch = startEpoch
		self.endEpoch = endEpoch
		self.stepSeconds = stepSeconds
		self.epochList = set(arange(startEpoch, endEpoch, stepSeconds))
	def intersection(self, occur):
		if isinstance(occur, (JdSetOccurrence, TimeRangeListOccurrence)):
			epochBetween = []
			for epoch in self.epochList:
				for startEpoch, endEpoch in occur.getTimeRangeList():
					if startEpoch <= epoch < endEpoch:
						epochBetween.append(epoch)
						break
			return TimeListOccurrence(epochBetween)
		elif isinstance(occur, TimeListOccurrence):
			return TimeListOccurrence(
				self.epochList.intersection(occur.epochList)
			)
		else:
			raise TypeError
	def getDaysJdList(self):## improve performance ## FIXME
		jds = set()
		for epoch in self.epochList:
			jds.add(getJdFromEpoch(epoch))
		return sorted(jds)
	getTimeRangeList = lambda self:\
		[
			(
				epoch,
				epoch,
			)
			for epoch in self.epochList
		]## or end=None ## FIXME



## Should not be registered, or instantiate directly
@classes.rule.setMain
class EventRule(SObj):
	name = ''
	desc = ''
	provide = ()
	need = ()
	conflict = ()
	sgroup = -1
	expand = False
	params = ()
	__bool__ = lambda self: True
	def __init__(self, parent):## parent can be an event or group
		self.parent = parent
	getMode = lambda self: self.parent.mode
	changeMode = lambda self, mode: True
	def calcOccurrence(self, startJd, endJd, event):
		raise NotImplementedError
	getInfo = lambda self: self.desc + ': %s'%self
	getEpochFromJd = lambda self, jd: getEpochFromJd(jd, tz=self.parent.getTimeZoneObj())

class AllDayEventRule(EventRule):
	jdMatches = lambda self, jd: True
	def calcOccurrence(self, startJd, endJd, event):## improve performance ## FIXME
		jds = set()
		for jd in range(startJd, endJd):
			if self.jdMatches(jd):
				jds.add(jd)## benchmark FIXME
		return JdSetOccurrence(jds)

## Should not be registered, or instantiate directly
class MultiValueAllDayEventRule(AllDayEventRule):
	conflict = (
		'date',
	)
	#params = ('values',)
	expand = True ## FIXME
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.values = []
	getData = lambda self: self.values
	def setData(self, data):
		if not isinstance(data, (tuple, list)):
			data = [data]
		self.values = data
	formatValue = lambda self, v: _(v)
	__str__ = lambda self: textNumEncode(numRangesEncode(self.values))
	def hasValue(self, value):
		for item in self.values:
			if isinstance(item, (tuple, list)):
				if item[0] <= value <= item[1]:
					return True
			elif item == value:
				return True
		return False
	def getValuesPlain(self):
		ls = []
		for item in self.values:
			if isinstance(item, (tuple, list)):
				ls += list(range(item[0], item[1]+1))
			else:
				ls.append(item)
		return ls
	def setValuesPlain(self, values):
		self.values = simplifyNumList(values)
	changeMode = lambda self, mode: False

@classes.rule.register
class YearEventRule(MultiValueAllDayEventRule):
	name = 'year'
	desc = _('Year')
	def __init__(self, parent):
		MultiValueAllDayEventRule.__init__(self, parent)
		self.values = [getSysDate(self.getMode())[0]]
	jdMatches = lambda self, jd: self.hasValue(jd_to(jd, self.getMode())[0])
	def newModeValues(self, newMode):
		curMode = self.getMode()
		yearConv = lambda year: convert(year, 7, 1, curMode, newMode)[0]
		values2 = []
		for item in self.values:
			if isinstance(item, (tuple, list)):
				values2.append((
					yearConv(item[0]),
					yearConv(item[1]),
				))
			else:
				values2.append(yearConv(item))
		return values
	def changeMode(self, mode):## FIXME
		self.values = self.newModeValues(mode)
		return True

@classes.rule.register
class MonthEventRule(MultiValueAllDayEventRule):
	name = 'month'
	desc = _('Month')
	conflict = (
		'date',
		'weekMonth',
	)

	def __init__(self, parent):
		MultiValueAllDayEventRule.__init__(self, parent)
		self.values = [1]
	jdMatches = lambda self, jd: self.hasValue(jd_to(jd, self.getMode())[1])
	## overwrite __str__? FIXME


@classes.rule.register
class DayOfMonthEventRule(MultiValueAllDayEventRule):
	name = 'day'
	desc = _('Day of Month')
	def __init__(self, parent):
		MultiValueAllDayEventRule.__init__(self, parent)
		self.values = [1]
	jdMatches = lambda self, jd: self.hasValue(jd_to(jd, self.getMode())[2])


@classes.rule.register
class WeekNumberModeEventRule(EventRule):
	name = 'weekNumMode'
	desc = _('Week Number')
	need = (
		'start',## FIXME
	)
	conflict = (
		'date',
		'weekMonth',
	)
	params = (
		'weekNumMode',
	)
	EVERY_WEEK, ODD_WEEKS, EVEN_WEEKS = list(range(3)) ## remove EVERY_WEEK? FIXME
	weekNumModeNames = ('any', 'odd', 'even')
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.weekNumMode = self.EVERY_WEEK
	getData = lambda self: self.weekNumModeNames[self.weekNumMode]
	def setData(self, modeName):
		if not modeName in self.weekNumModeNames:
			raise BadEventFile('bad rule weekNumMode=%r, the value for weekNumMode must be one of %r'\
				%(modeName, self.weekNumModeNames))
		self.weekNumMode = self.weekNumModeNames.index(modeName)
	def calcOccurrence(self, startJd, endJd, event):## improve performance ## FIXME
		startAbsWeekNum = getAbsWeekNumberFromJd(event.getStartJd()) - 1 ## 1st week ## FIXME
		if self.weekNumMode==self.EVERY_WEEK:
			return JdSetOccurrence(list(range(startJd, endJd)))
		elif self.weekNumMode==self.ODD_WEEKS:
			jds = set()
			for jd in range(startJd, endJd):
				if (getAbsWeekNumberFromJd(jd)-startAbsWeekNum)%2 == 1:
					jds.add(jd)
			return JdSetOccurrence(jds)
		elif self.weekNumMode==self.EVEN_WEEKS:
			jds = set()
			for jd in range(startJd, endJd):
				if (getAbsWeekNumberFromJd(jd)-startAbsWeekNum)%2 == 0:
					jds.add(jd)
			return JdSetOccurrence(jds)
	def getInfo(self):
		if self.weekNumMode == self.EVERY_WEEK:
			return ''
		elif self.weekNumMode == self.ODD_WEEKS:
			return _('Odd Weeks')
		elif self.weekNumMode == self.EVEN_WEEKS:
			return _('Even Weeks')

@classes.rule.register
class WeekDayEventRule(AllDayEventRule):
	name = 'weekDay'
	desc = _('Day of Week')
	conflict = (
		'date',
		'weekMonth',
	)
	params = (
		'weekDayList',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.weekDayList = list(range(7)) ## or [] ## FIXME
	getData = lambda self: self.weekDayList
	def setData(self, data):
		if isinstance(data, int):
			self.weekDayList = [data]
		elif isinstance(data, (tuple, list)):
			self.weekDayList = data
		else:
			raise BadEventFile('bad rule weekDayList=%s, value for weekDayList must be a list of integers (0 for sunday)'%data)
	jdMatches = lambda self, jd: jwday(jd) in self.weekDayList
	def getInfo(self):
		if self.weekDayList == list(range(7)):
			return ''
		sep = _(',') + ' '
		sep2 = ' ' + _('or') + ' '
		return _('Day of Week') + ': ' + \
			   sep.join([core.weekDayName[wd] for wd in self.weekDayList[:-1]]) + \
			   sep2 + core.weekDayName[self.weekDayList[-1]]


@classes.rule.register
class WeekMonthEventRule(EventRule):
	name = 'weekMonth'
	desc = _('Week-Month')
	conflict = (
		'date',
		'month',
		'ex_month',
		'weekNumMode'
		'weekday',
		'cycleDays',
		'cycleWeeks',
		'cycleLen',
	)
	params = (
		'month',## 0..12 ## 0 means every month
		'wmIndex',## 0..4
		'weekDay',## 0..6
	)
	'''
	paramsValidators = {
		'month': lambda m: 0 <= m <= 12,
		'wmIndex': lambda m: 0 <= m <= 4,
		'weekDay': lambda m: 0 <= m <= 6,
	}
	'''
	wmIndexNames = (
		_('First'),## 0
		_('Second'),## 1
		_('Third'),## 2
		_('Fourth'),## 3
		_('Last'),## 4
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.month = 1
		self.wmIndex = 4
		self.weekDay = core.firstWeekDay
	#def setJd(self, jd):## usefull? FIXME
	#	self.month, self.wmIndex, self.weekDay = core.getMonthWeekNth(jd, self.getMode())
	#def getJd(self):
	def calcOccurrence(self, startJd, endJd, event):
		mode = self.getMode()
		startYear, startMonth, startDay = jd_to(startJd, mode)
		endYear, endMonth, endDay = jd_to(endJd, mode)
		jds = set()
		monthList = list(range(1, 13)) if self.month==0 else [self.month]
		for year in range(startYear, endYear):
			for month in monthList:
				jd = to_jd(year, month, 7*self.wmIndex+1, mode)
				jd += (self.weekDay-jwday(jd))%7
				if self.wmIndex == 4:## Last (Fouth or Fifth)
					if jd_to(jd, mode)[1] != month:
						jd -= 7
				if startJd <= jd < endJd:
					jds.add(jd)
		return JdSetOccurrence(jds)



@classes.rule.register
class DateEventRule(EventRule):
	name = 'date'
	desc = _('Date')
	need = ()
	conflict = (
		'year', 'month', 'day', 'weekNumMode', 'weekDay'
		'start', 'end', 'cycleDays', 'duration', 'cycleLen'
	)## all rules except for dayTime and dayTimeRange (and possibly hourList, minuteList, secondList)
	## also conflict with 'holiday' ## FIXME
	__str__ = lambda self: dateEncode(self.date)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.date = getSysDate(self.getMode())
	getData = lambda self: str(self)
	def setData(self, data):
		self.date = dateDecode(data)
	def getJd(self):
		year, month, day = self.date
		return to_jd(year, month, day, self.getMode())
	getEpoch = lambda self: self.getEpochFromJd(self.getJd())
	def setJd(self, jd):
		self.date = jd_to(jd, self.getMode())
	def calcOccurrence(self, startJd, endJd, event):
		myJd = self.getJd()
		if startJd <= myJd < endJd:
			return JdSetOccurrence([myJd])
		else:
			return JdSetOccurrence()
	def changeMode(self, mode):
		self.date = jd_to(self.getJd(), mode)
		return True

class DateAndTimeEventRule(DateEventRule):
	sgroup = 1
	params = (
		'date',
		'time',
	)
	def __init__(self, parent):
		DateEventRule.__init__(self, parent)
		self.time = localtime()[3:6]
	getEpoch = lambda self: self.parent.getEpochFromJhms(
		self.getJd(),
		self.time[0],
		self.time[1],
		self.time[2],
	)
	def setEpoch(self, epoch):
		jd, h, m, s = self.parent.getJhmsFromEpoch(epoch)
		self.setJd(jd)
		self.time = (h, m, s)
	def setJdExact(self, jd):
		self.setJd(jd)
		self.time = (0, 0, 0)
	def setDate(self, date):
		self.date = date
		self.time = (0, 0, 0)
	getDate = lambda self, mode: convert(self.date[0], self.date[1], self.date[2], self.getMode(), mode)
	getData = lambda self: {
		'date': dateEncode(self.date),
		'time': timeEncode(self.time),
	}
	def setData(self, arg):
		if isinstance(arg, dict):
			self.date = dateDecode(arg['date'])
			if 'time' in arg:
				self.time = timeDecode(arg['time'])
		elif isinstance(arg, str):
			self.date = dateDecode(arg)
		else:
			raise BadEventFile('bad rule %s=%r'%(self.name, arg))
	getInfo = lambda self: self.desc + ': ' + dateEncode(self.date) + _(',') + ' ' + _('Time') + ': ' + timeEncode(self.time)



@classes.rule.register
class DayTimeEventRule(EventRule):## Moment Event
	name = 'dayTime'
	desc = _('Time in Day')
	provide = (
		'time',
	)
	conflict = (
		'dayTimeRange',
		'cycleLen',
	)
	params = (
		'dayTime',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.dayTime = localtime()[3:6]
	getData = lambda self: timeEncode(self.dayTime)
	def setData(self, data):
		self.dayTime = timeDecode(data)
	def calcOccurrence(self, startJd, endJd, event):
		mySec = getSecondsFromHms(*self.dayTime)
		return TimeListOccurrence(## FIXME
			self.getEpochFromJd(startJd) + mySec,
			self.getEpochFromJd(endJd) + mySec + 1,
			dayLen,
		)
	getInfo = lambda self: _('Time in Day') + ': ' + timeEncode(self.dayTime)

@classes.rule.register
class DayTimeRangeEventRule(EventRule):
	name = 'dayTimeRange'
	desc = _('Day Time Range')
	conflict = (
		'dayTime',
		'cycleLen',
	)
	params = (
		'dayTimeStart',
		'dayTimeEnd',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.dayTimeStart = (0, 0, 0)
		self.dayTimeEnd = (24, 0, 0)
	def setRange(self, start, end):
		self.dayTimeStart = tuple(start)
		self.dayTimeEnd = tuple(end)
	getHourRange = lambda self: (
		timeToFloatHour(*self.dayTimeStart),
		timeToFloatHour(*self.dayTimeEnd),
	)
	getSecondsRange = lambda self: (
		getSecondsFromHms(*self.dayTimeStart),
		getSecondsFromHms(*self.dayTimeEnd),
	)
	getData = lambda self: (timeEncode(self.dayTimeStart), timeEncode(self.dayTimeEnd))
	setData = lambda self, data: self.setRange(timeDecode(data[0]), timeDecode(data[1]))
	def calcOccurrence(self, startJd, endJd, event):
		daySecStart = getSecondsFromHms(*self.dayTimeStart)
		daySecEnd = getSecondsFromHms(*self.dayTimeEnd)
		if daySecEnd <= daySecStart:
			daySecEnd = daySecStart
		tmList = []
		for jd in range(startJd, endJd):
			epoch = self.getEpochFromJd(jd)
			tmList.append((epoch+daySecStart, epoch+daySecEnd))
		return TimeRangeListOccurrence(tmList)


@classes.rule.register
class StartEventRule(DateAndTimeEventRule):
	name = 'start'
	desc = _('Start')
	conflict = (
		'date',
	)
	def calcOccurrence(self, startJd, endJd, event):
		return TimeRangeListOccurrence.newFromStartEnd(
			max(self.getEpochFromJd(startJd), self.getEpoch()),
			self.getEpochFromJd(endJd),
		)


@classes.rule.register
class EndEventRule(DateAndTimeEventRule):
	name = 'end'
	desc = _('End')
	conflict = (
		'date',
		'duration',
	)
	def calcOccurrence(self, startJd, endJd, event):
		return TimeRangeListOccurrence.newFromStartEnd(
			self.getEpochFromJd(startJd),
			min(self.getEpochFromJd(endJd), self.getEpoch()),
		)


@classes.rule.register
class DurationEventRule(EventRule):
	name = 'duration'
	desc = _('Duration')
	need = (
		'start',
	)
	conflict = (
		'date',
		'end',
	)
	params = (
		'value',
		'unit',
	)
	sgroup = 1
	units = (1, 60, 3600, dayLen, 7*dayLen)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.value = 0
		self.unit = 1 ## seconds
	getSeconds = lambda self: self.value * self.unit
	def setSeconds(self, s):
		for unit in reversed(self.units):
			if s%unit == 0:
				self.value, self.unit = int(s//unit), unit
				return
		self.unit, self.value = int(s), 1
	def setData(self, data):
		try:
			self.value, self.unit = durationDecode(data)
		except Exception as e:
			log.error('Error while loading event rule "%s": %s'%(self.name, e))
	getData = lambda self: durationEncode(self.value, self.unit)
	def calcOccurrence(self, startJd, endJd, event):
		myStartEpoch = self.parent['start'].getEpoch()
		startEpoch = max(
			myStartEpoch,
			self.getEpochFromJd(startJd),
		)
		endEpoch = min(
			myStartEpoch + self.getSeconds(),
			self.getEpochFromJd(endJd),
		)
		return TimeRangeListOccurrence.newFromStartEnd(
			startEpoch,
			endEpoch,
		)



def cycleDaysCalcOccurrence(days, startJd, endJd, event):
	eStartJd = event.getStartJd()
	if startJd <= eStartJd:
		startJd = eStartJd
	else:
		startJd = eStartJd + ((startJd - eStartJd - 1) // days + 1) * days
	return JdSetOccurrence(list(range(
		startJd,
		endJd,
		days,
	)))

@classes.rule.register
class CycleDaysEventRule(EventRule):
	name = 'cycleDays'
	desc = _('Cycle (Days)')
	need = (
		'start',
	)
	conflict = (
		'date',
		'cycleWeeks',
		'cycleLen',
		'weekMonth',
	)
	params = (
		'days',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.days = 7
	getData = lambda self: self.days
	def setData(self, days):
		self.days = days
	calcOccurrence = lambda self, startJd, endJd, event: cycleDaysCalcOccurrence(self.days, startJd, endJd, event)
	getInfo = lambda self: _('Repeat: Every %s Days')%_(self.days)

@classes.rule.register
class CycleWeeksEventRule(EventRule):
	name = 'cycleWeeks'
	desc = _('Cycle (Weeks)')
	need = (
		'start',
	)
	conflict = (
		'date',
		'cycleDays',
		'cycleLen',
		'weekMonth',
	)
	params = (
		'weeks',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.weeks = 1
	getData = lambda self: self.weeks
	def setData(self, weeks):
		self.weeks = weeks
	calcOccurrence = lambda self, startJd, endJd, event: cycleDaysCalcOccurrence(self.weeks*7, startJd, endJd, event)
	getInfo = lambda self: _('Repeat: Every %s Weeks')%_(self.weeks)


@classes.rule.register
class CycleLenEventRule(EventRule):
	name = 'cycleLen' ## or 'cycle' FIXME
	desc = _('Cycle (Days & Time)')
	provide = (
		'time',
	)
	need = (
		'start',
	)
	conflict = (
		'date',
		'dayTime',
		'dayTimeRange',
		'cycleDays',
		'cycleWeeks',
		'weekMonth',
	)
	params = (
		'days',
		'extraTime',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.days = 7
		self.extraTime = (0, 0, 0)
	getData = lambda self: {
		'days': self.days,
		'extraTime': timeEncode(self.extraTime),
	}
	def setData(self, arg):
		self.days = arg['days']
		self.extraTime = timeDecode(arg['extraTime'])
	def calcOccurrence(self, startJd, endJd, event):
		startEpoch = self.getEpochFromJd(startJd)
		eventStartEpoch = event.getStartEpoch()
		##
		cycleSec = self.days*dayLen + getSecondsFromHms(*self.extraTime)
		##
		if startEpoch <= eventStartEpoch:
			startEpoch = eventStartEpoch
		else:
			startEpoch = eventStartEpoch + ((startEpoch - eventStartEpoch - 1) // cycleSec + 1) * cycleSec
		##
		return TimeListOccurrence(
			startEpoch,
			self.getEpochFromJd(endJd),
			cycleSec,
		)
	getInfo = lambda self: _('Repeat: Every %s Days and %s')%(_(self.days), timeEncode(self.extraTime))

@classes.rule.register
class ExYearEventRule(YearEventRule):
	name = 'ex_year'
	desc = '[%s] %s'%(_('Exception'), _('Year'))
	jdMatches = lambda self, jd: not YearEventRule.jdMatches(self, jd)

@classes.rule.register
class ExMonthEventRule(MonthEventRule):
	name = 'ex_month'
	desc = '[%s] %s'%(_('Exception'), _('Month'))
	conflict = (
		'date',
		'month',
		'weekMonth',
	)
	jdMatches = lambda self, jd: not MonthEventRule.jdMatches(self, jd)

@classes.rule.register
class ExDayOfMonthEventRule(DayOfMonthEventRule):
	name = 'ex_day'
	desc = '[%s] %s'%(_('Exception'), _('Day of Month'))
	jdMatches = lambda self, jd: not DayOfMonthEventRule.jdMatches(self, jd)

@classes.rule.register
class ExDatesEventRule(EventRule):
	name = 'ex_dates'
	desc = '[%s] %s'%(_('Exception'), _('Date'))
	#conflict = ('date',)## FIXME
	params = (
		'dates',
	)
	def __init__(self, parent):
		EventRule.__init__(self, parent)
		self.setDates([])
	def setDates(self, dates):
		self.dates = dates
		self.jdList = [to_jd(y, m, d, self.getMode()) for y, m, d in dates]
	def calcOccurrence(self, startJd, endJd, event):## improve performance ## FIXME
		return JdSetOccurrence(
			set(range(startJd, endJd)).difference(self.jdList)
		)
	def getData(self):
		datesConf = []
		for date in self.dates:
			datesConf.append(dateEncode(date))
		return datesConf
	def setData(self, datesConf):
		dates = []
		if isinstance(datesConf, str):
			for date in datesConf.split(','):
				dates.append(dateDecode(date.strip()))
		else:
			for date in datesConf:
				if isinstance(date, str):
					date = dateDecode(date)
				elif isinstance(date, (tuple, list)):
					checkDate(date)
				dates.append(date)
		self.setDates(dates)
	def changeMode(self, mode):
		dates = []
		for jd in self.jdList:
			dates.append(jd_to(jd, mode))
		self.dates = dates

#@classes.rule.register
#class HolidayEventRule(EventRule):## FIXME
#	name = 'holiday'
#	desc = _('Holiday')
#	conflict = ('date',)


#@classes.rule.register
#class ShowInMCalEventRule(EventRule):## FIXME
#	name = 'show_cal'
#	desc = _('Show in Calendar')

#@classes.rule.register
#class SunTimeRule(EventRule):## FIXME
## ... minutes before Sun Rise      eval('sunRise-x')
## ... minutes after Sun Rise       eval('sunRise+x')
## ... minutes before Sun Set       eval('sunSet-x')
## ... minutes after Sun Set        eval('sunSet+x')

###########################################################################
###########################################################################

## Should not be registered, or instantiate directly
@classes.notifier.setMain
class EventNotifier(SObj):
	name = ''
	desc = ''
	params = ()
	def __init__(self, event):
		self.event = event
	getMode = lambda self: self.event.mode
	def notify(self, finishFunc):
		pass

@classes.notifier.register
class AlarmNotifier(EventNotifier):
	name = 'alarm'
	desc = _('Alarm')
	params = (
		'alarmSound',
		'playerCmd',
	)
	def __init__(self, event):
		EventNotifier.__init__(self, event)
		self.alarmSound = '' ## FIXME
		self.playerCmd = 'mplayer'

@classes.notifier.register
class FloatingMsgNotifier(EventNotifier):
	name = 'floatingMsg'
	desc = _('Floating Message')
	params = (
		'fillWidth',
		'speed',
		'bgColor',
		'textColor',
	)
	def __init__(self, event):
		EventNotifier.__init__(self, event)
		###
		self.fillWidth = False
		self.speed = 100
		self.bgColor = (255, 255, 0)
		self.textColor = (0, 0, 0)

@classes.notifier.register
class WindowMsgNotifier(EventNotifier):
	name = 'windowMsg'
	desc = _('Message Window')## FIXME
	params = (
		'extraMessage',
	)
	def __init__(self, event):
		EventNotifier.__init__(self, event)
		self.extraMessage = ''
		## window icon ## FIXME

#@classes.notifier.register## FIXME
class CommandNotifier(EventNotifier):
	name = 'command'
	desc = _('Run a Command')
	params = (
		'command',
		'pyEval',
	)
	def __init__(self, event):
		EventNotifier.__init__(self, event)
		self.command = ''
		self.pyEval = False

###########################################################################
###########################################################################

class RuleContainer:
	requiredRules = ()
	supportedRules = None
	params = (
		'timeZoneEnable',
		'timeZone',
	)
	paramsOrder = (
		'timeZoneEnable',
		'timeZone',
	)
	def __init__(self):
		self.timeZoneEnable = False
		self.timeZone = ''
		###
		self.clearRules()
		self.rulesHash = None
	def clearRules(self):
		self.rulesOd = OrderedDict()
	getRule = lambda self, key: self.rulesOd.__getitem__(key)
	setRule = lambda self, key, value: self.rulesOd.__setitem__(key, value)
	getRulesData = lambda self: [(rule.name, rule.getData()) for rule in self.rulesOd.values()]
	getRulesHash = lambda self: hash(str(
		(
			self.getTimeZoneStr(),
			sorted(self.getRulesData()),
		)
	))
	getRuleNames = lambda self: self.rulesOd.keys()
	addRule = lambda self, rule: self.rulesOd.__setitem__(rule.name, rule)
	def addNewRule(self, ruleType):
		rule = classes.rule.byName[ruleType](self)
		self.addRule(rule)
		return rule
	def getAddRule(self, ruleType):
		try:
			return self.getRule(ruleType)
		except KeyError:
			return self.addNewRule(ruleType)
	removeRule = lambda self, rule: self.rulesOd.__delitem__(rule.name)
	__delitem__ = lambda self, key: self.rulesOd.__delitem__(key)
	__getitem__ = lambda self, key: self.getRule(key)
	__setitem__ = lambda self, key, value: self.setRule(key, value)
	__iter__ = lambda self: iter(self.rulesOd.values())
	def setRulesData(self, rulesData):
		self.clearRules()
		for ruleName, ruleData in rulesData:
			rule = classes.rule.byName[ruleName](self)
			rule.setData(ruleData)
			self.addRule(rule)
	def addRequirements(self):
		for name in self.requiredRules:
			if not name in self.rulesOd:
				self.addNewRule(name)
	def checkAndAddRule(self, rule):
		ok, msg = self.checkRulesDependencies(newRule=rule)
		if ok:
			self.addRule(rule)
		return (ok, msg)
	def removeSomeRuleTypes(self, *rmTypes):
		for ruleType in rmTypes:
			try:
				del self.rulesOd[ruleType]
			except KeyError:
				pass
	def checkAndRemoveRule(self, rule):
		ok, msg = self.checkRulesDependencies(disabledRule=rule)
		if ok:
			self.removeRule(rule)
		return (ok, msg)
	def checkRulesDependencies(self, newRule=None, disabledRule=None, autoCheck=True):
		rulesOd = self.rulesOd.copy()
		if newRule:
			rulesOd[newRule.name] = newRule
		if disabledRule:
			#try:
			del rulesOd[disabledRule.name]
			#except:
			#	pass
		provideList = []
		for ruleName, rule in rulesOd.items():
			provideList.append(ruleName)
			provideList += rule.provide
		for rule in rulesOd.values():
			for conflictName in rule.conflict:
				if conflictName in provideList:
					return (False, '%s "%s" %s "%s"'%(
						_('Conflict between'),
						_(rule.desc),
						_('and'),
						_(rulesOd[conflictName].desc),
					))
			for needName in rule.need:
				if not needName in provideList:
					## find which rule(s) provide(s) needName ## FIXME
					return (False, '"%s" %s "%s"'%(
						_(rule.desc),
						_('needs'),
						_(needName), #_(rulesOd[needName].desc)
					))
		return (True, '')
	def copyRulesFrom(self, other):
		for ruleType, rule in other.rulesOd.items():
			if ruleType in self.supportedRules:
				self.getAddRule(ruleType).copyFrom(rule)
	def copySomeRuleTypesFrom(self, other, *ruleTypes):
		for ruleType in ruleTypes:
			if not ruleType in self.supportedRules:
				print('copySomeRuleTypesFrom: unsupported rule %s for container %r'%(ruleType, self))
				continue
			try:
				rule = other.rulesOd[ruleType]
			except KeyError:
				pass
			else:
				self.getAddRule(ruleType).copyFrom(rule)
	def getTimeZoneObj(self):
		if self.timeZoneEnable and self.timeZone:
			try:
				return natz.timezone(self.timeZone)
			except:
				myRaise()
		return core.localTz
	getTimeZoneStr = lambda self: str(self.getTimeZoneObj())
	getEpochFromJd = lambda self, jd: getEpochFromJd(jd, tz=self.getTimeZoneObj())
	getJdFromEpoch = lambda self, jd: getJdFromEpoch(jd, tz=self.getTimeZoneObj())
	getJhmsFromEpoch = lambda self, epoch: getJhmsFromEpoch(epoch, tz=self.getTimeZoneObj())
	getEpochFromJhms = lambda self, jd, h, m , s: getEpochFromJhms(jd, h, m , s, tz=self.getTimeZoneObj())


def fixIconInData(data):
	icon = data['icon']
	iconDir, iconName = split(icon)
	if iconDir == join(pixDir, 'event'):
		icon = iconName
	data['icon'] = icon

def fixIconInObj(self):
	icon = self.icon
	if icon and not '/' in icon:
		icon = join(pixDir, 'event', icon)
	self.icon = icon

###########################################################################
###########################################################################

## Should not be registered, or instantiate directly
@classes.event.setMain
class Event(BsonHistEventObj, RuleContainer):
	name = 'custom'## or 'event' or '' FIXME
	desc = _('Custom Event')
	iconName = ''
	#requiredNotifiers = ()## needed? FIXME
	readOnly = False
	isAllDay = False
	isSingleOccur = False
	basicParams = (
		#'modified',
		'remoteIds',
		'notifiers',## FIXME
	)
	params = RuleContainer.params + (
		'icon',
		'summary',
		'description',
	)
	paramsOrder = RuleContainer.paramsOrder + (
		'type',
		'calType',
		'summary',
		'description',
		'rules',
		'notifiers',
		'notifyBefore',
		'remoteIds',
		'modified',
	)
	@classmethod
	def getFile(cls, _id):
		return join(eventsDir, '%s.json'%_id)
	@classmethod
	def getSubclass(cls, _type):
		return classes.event.byName[_type]
	@classmethod
	def getDefaultIcon(cls):
		return join(pixDir, 'event', cls.iconName+'.png') if cls.iconName else ''
	__bool__ = lambda self: bool(self.rulesOd) ## FIXME
	__repr__ = lambda self: '%s(id=%s)'%(self.__class__.__name__, self.id)
	__str__ = lambda self: '%s(id=%s, summary=%s)'%(
		self.__class__.__name__,
		self.id,
		self.summary,
	)
	def __init__(self, _id=None, parent=None):
		if _id is None:
			self.id = None
		else:
			self.setId(_id)
		self.parent = parent
		try:
			self.mode = parent.mode
		except:
			self.mode = calTypes.primary
		self.icon = self.__class__.getDefaultIcon()
		self.summary = self.desc ## + ' (' + _(self.id) + ')' ## FIXME
		self.description = ''
		self.files = []
		######
		RuleContainer.__init__(self)
		self.timeZoneEnable = not self.isAllDay
		self.notifiers = []
		self.notifyBefore = (0, 1) ## (value, unit) like DurationEventRule
		## self.snoozeTime = (5, 60) ## (value, unit) like DurationEventRule ## FIXME
		self.addRequirements()
		self.setDefaults()
		if parent is not None:
			self.setDefaultsFromGroup(parent)
		######
		self.modified = now()## FIXME
		self.remoteIds = None## (accountId, groupId, eventId)
		## remote groupId and eventId both can be integer or string or unicode (depending on remote account type)
	def getShownDescription(self):
		if not self.description:
			return ''
		try:
			showFull = self.parent.showFullEventDesc
		except:
			showFull = False
		if showFull:
			return self.description
		else:
			return self.description.split('\n')[0]
	def afterModify(self):
		if self.id is None:
			self.setId()
		self.modified = now()## FIXME
		#self.parent.eventsModified = self.modified
		###
		if self.parent and self.id in self.parent.idList:
			rulesHash = self.getRulesHash()
			## what is self.notifyBefore is changed? BUG FIXME
			if rulesHash != self.rulesHash:
				self.parent.updateOccurrenceEvent(self)
				self.rulesHash = rulesHash
		else:## None or enbale=False
			self.rulesHash = ''
	getNotifyBeforeSec = lambda self: self.notifyBefore[0] * self.notifyBefore[1]
	getNotifyBeforeMin = lambda self: int(self.getNotifyBeforeSec()/60)
	def setDefaults(self):
		'''
			sets default values that depends on event type
			not common parameters, like those are set in __init__
			DON'T call this method from parent event class
		'''
		pass
	def setDefaultsFromGroup(self, group):
		'''
			Call this method from parent event class
		'''
		self.timeZone = group.getTimeZoneStr()
		if group.icon:## and not self.icon FIXME
			self.icon = group.icon
	def getInfo(self):
		lines = []
		rulesDict = self.rulesOd.copy()
		for rule in rulesDict.values():
			lines.append(rule.getInfo())
		return '\n'.join(lines)
	#def addRequirements(self):
	#	RuleContainer.addRequirements(self)
	#	notifierNames = (notifier.name for notifier in self.notifiers)
	#	for name in self.requiredNotifiers:
	#		if not name in notifierNames:
	#			self.notifiers.append(classes.notifier.byName[name](self))
	def loadFiles(self):
		self.files = []
		#if isdir(self.filesDir):
		#	for fname in listdir(self.filesDir):
		#		if isfile(join(self.filesDir, fname)) and not fname.endswith('~'):## FIXME
		#			self.files.append(fname)
	#getUrlForFile = lambda self, fname: 'file:' + os.sep*2 + self.filesDir + os.sep + fname
	def getFilesUrls(self):
		data = []
		baseUrl = self.getUrlForFile('')
		for fname in self.files:
			data.append((
				baseUrl + fname,
				_('File') + ': ' + fname,
			))
		return data
	getSummary = lambda self: self.summary
	getDescription = lambda self: self.description
	def getTextParts(self, showDesc=True):
		summary = self.getSummary()
		##
		if self.timeZoneEnable and self.timeZone:
			try:
				natz.timezone(self.timeZone)
			except natz.exceptions.UnknownTimeZoneError:
				invalidTZ = _('Invalid Time Zone: %s') % self.timeZone
				summary = '(%s) '%invalidTZ + summary
		####
		description = self.getDescription()
		if showDesc and description:
			try:
				sep = self.parent.eventTextSep
			except:
				sep = core.eventTextSep
			return (summary, sep, description)
		else:
			return (summary,)
	getText = lambda self, showDesc=True: ''.join(self.getTextParts(showDesc))
	def setId(self, _id=None):
		if _id is None or _id<0:
			_id = lastIds.event + 1 ## FIXME
			lastIds.event = _id
		elif _id > lastIds.event:
			lastIds.event = _id
		self.id = _id
		self.file = self.getFile(self.id)
		#self.filesDir = join(self.dir, 'files')
		self.loadFiles()
	def invalidate(self):
		## make sure it can't be written to file again, it's about to be deleted
		self.id = None
		self.file = ''
	def save(self):
		if self.id is None:
			self.setId()
		#makeDir(self.dir)
		BsonHistEventObj.save(self)
	def copyFrom(self, other, exact=False):## FIXME
		BsonHistEventObj.copyFrom(self, other)
		self.mode = other.mode
		self.notifyBefore = other.notifyBefore[:]
		#self.files = other.files[:]
		self.notifiers = other.notifiers[:]## FIXME
		self.copyRulesFrom(other)
		self.addRequirements()
		####
		## copy dates between different rule types in different event types
		jd = other.getJd()
		if jd is not None:
			if exact:
				self.setJdExact(jd)
			else:
				self.setJd(jd)
	def getData(self):
		data = BsonHistEventObj.getData(self)
		data.update({
			'type': self.name,
			'calType': calTypes.names[self.mode],
			'rules': self.getRulesData(),
			'notifiers': self.getNotifiersData(),
			'notifyBefore': durationEncode(*self.notifyBefore),
		})
		fixIconInData(data)
		return data
	def setData(self, data):
		BsonHistEventObj.setData(self, data)
		if self.remoteIds:
			self.remoteIds = tuple(self.remoteIds)
		if 'id' in data:
			self.setId(data['id'])
		if 'calType' in data:
			calType = data['calType']
			try:
				self.mode = calTypes.names.index(calType)
			except ValueError:
				raise ValueError('Invalid calType: %r'%calType)
		self.clearRules()
		if 'rules' in data:
			self.setRulesData(data['rules'])
		self.notifiers = []
		if 'notifiers' in data:
			for notifierName, notifierData in data['notifiers']:
				notifier = classes.notifier.byName[notifierName](self)
				notifier.setData(notifierData)
				self.notifiers.append(notifier)
		if 'notifyBefore' in data:
			self.notifyBefore = durationDecode(data['notifyBefore'])
		fixIconInObj(self)
	#def load(self):## skipRules arg for use in ui_gtk/event/notify.py ## FIXME
	getNotifiersData = lambda self: [(notifier.name, notifier.getData()) for notifier in self.notifiers]
	getNotifiersDict = lambda self: dict(self.getNotifiersData())
	def calcOccurrence(self, startJd, endJd):## float jd ## cache Occurrences ## FIXME
		rules = list(self.rulesOd.values())
		if not rules:
			return JdSetOccurrence()
		occur = rules[0].calcOccurrence(startJd, endJd, self)
		for rule in rules[1:]:
			try:
				startJd = occur.getStartJd()
			except:
				pass
			try:
				endJd = occur.getEndJd()
			except:
				pass
			occur = occur.intersection(rule.calcOccurrence(startJd, endJd, self))
		occur.event = self
		return occur ## FIXME
	calcOccurrenceAll = lambda self: self.calcOccurrence(self.parent.startJd, self.parent.endJd)
	#def calcFirstOccurrenceAfterJd(self, startJd):## too much tricky! FIXME
	def notify(self, finishFunc):
		self.n = len(self.notifiers)
		def notifierFinishFunc():
			self.n -= 1
			if self.n<=0:
				try:
					finishFunc()
				except:
					pass
		for notifier in self.notifiers:
			notifier.notify(notifierFinishFunc)
	def getIcsData(self, prettyDateTime=False):## FIXME
		return None
	def setIcsData(self, data):
		'''
		if 'T' in data['DTSTART']:
			return False
		if 'T' in data['DTEND']:
			return False
		startJd = ics.getJdByIcsDate(data['DTSTART'])
		endJd = ics.getJdByIcsDate(data['DTEND'])
		if 'RRULE' in data:
			rrule = dict(ics.splitIcsValue(data['RRULE']))
			if rrule['FREQ'] == 'YEARLY':
				y0, m0, d0 = jd_to(startJd, self.mode)
				y1, m1, d1 = jd_to(endJd, self.mode)
				if y0 != y1:## FIXME
					return False
				yr = self.getAddRule('year')
				interval = int(rrule.get('INTERVAL', 1))

			elif rrule['FREQ'] == 'MONTHLY':
				pass
			elif rrule['FREQ'] == 'WEEKLY':
				pass
		'''
		return False
	def changeMode(self, mode):
		backupRulesOd = self.rulesOd.copy()## is it deep copy? FIXME
		if mode != self.mode:
			for rule in self.rulesOd.values():
				if not rule.changeMode(mode):
					self.rulesOd = backupRulesOd
					return False
			self.mode = mode
		return True
	def getStartJd(self):## FIXME
		try:
			return self['start'].getJd()
		except KeyError:
			pass
		try:
			return self['date'].getJd()
		except KeyError:
			pass
		return self.parent.startJd
	def getEndJd(self):## FIXME
		try:
			return self['end'].getJd()
		except KeyError:
			pass
		try:
			return self['date'].getJd()
		except KeyError:
			pass
		return self.parent.endJd
	def getStartEpoch(self):## FIXME
		try:
			return self['start'].getEpoch()
		except KeyError:
			pass
		try:
			return self['date'].getEpoch()
		except KeyError:
			pass
		return getEpochFromJd(self.parent.startJd)
	def getEndEpoch(self):## FIXME
		try:
			return self['end'].getEpoch()
		except KeyError:
			pass
		try:
			return self['date'].getEpoch()
		except KeyError:
			pass
		return self.getEpochFromJd(self.parent.endJd)
	getJd = lambda self: self.getStartJd()
	setJd = lambda self, jd: None
	setJdExact = lambda self, jd: self.setJd(jd)

class SingleStartEndEvent(Event):
	isSingleOccur = True
	setStartEpoch = lambda self, epoch: self.getAddRule('start').setEpoch(epoch)
	setEndEpoch = lambda self, epoch: self.getAddRule('end').setEpoch(epoch)
	setJd = lambda self, jd: self.getAddRule('start').setJd(jd)
	def setJdExact(self, jd):
		self.getAddRule('start').setJdExact(jd)
		self.getAddRule('end').setJdExact(jd+1)
	getIcsData = lambda self, prettyDateTime=False: [
		('DTSTART', ics.getIcsTimeByEpoch(self.getStartEpoch(), prettyDateTime)),
		('DTEND', ics.getIcsTimeByEpoch(self.getEndEpoch(), prettyDateTime)),
		('TRANSP', 'OPAQUE'),
		('CATEGORIES', self.name),## FIXME
	]
	def calcOccurrence(self, startJd, endJd):
		return TimeRangeListOccurrence.newFromStartEnd(
			max(self.getEpochFromJd(startJd), self.getStartEpoch()),
			min(self.getEpochFromJd(endJd), self.getEndEpoch()),
		)



@classes.event.register
class TaskEvent(SingleStartEndEvent):
	## overwrites getEndEpoch from Event
	## overwrites setEndEpoch from SingleStartEndEvent
	## overwrites setJdExact from SingleStartEndEvent
	## Methods neccessery for modifying event by hand in timeline:
	##   getStartEpoch, getEndEpoch, modifyStart, modifyEnd, modifyPos
	name = 'task'
	desc = _('Task')
	iconName = 'task'
	requiredRules = (
		'start',
	)
	supportedRules = (
		'start',
		'end',
		'duration',
	)
	isAllDay = False
	def setDefaults(self):
		self.setStart(
			getSysDate(self.mode),
			tuple(localtime()[3:6]),
		)
		self.setEnd('duration', 1, 3600)
	def setDefaultsFromGroup(self, group):
		Event.setDefaultsFromGroup(self, group)
		if group.name == 'taskList':
			value, unit = group.defaultDuration
			self.setEnd('duration', value, unit)
	def setStart(self, date, dayTime):
		start = self['start']
		start.date = date
		start.time = dayTime
	def setEnd(self, endType, *values):
		self.removeSomeRuleTypes('end', 'duration')
		if endType=='date':
			rule = EndEventRule(self)
			rule.date, rule.time = values
		elif endType=='epoch':
			rule = EndEventRule(self)
			rule.setEpoch(values[0])
		elif endType=='duration':
			rule = DurationEventRule(self)
			rule.value, rule.unit = values
		else:
			raise ValueError('invalid endType=%r'%endType)
		self.addRule(rule)
	def getStart(self):
		start = self['start']
		return (start.date, start.time)
	def getEnd(self):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			return ('date', (end.date, end.time))
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			return ('duration', (duration.value, duration.unit))
		raise ValueError('no end date neither duration specified for task')
	def getEndEpoch(self):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			return end.getEpoch()
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			return self['start'].getEpoch() + duration.getSeconds()
		raise ValueError('no end date neither duration specified for task')
	def setEndEpoch(self, epoch):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			end.setEpoch(epoch)
			return
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			duration.setSeconds(epoch-self['start'].getEpoch())
			return
		raise ValueError('no end date neither duration specified for task')
	def modifyPos(self, newStartEpoch):
		start = self['start']
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			end.setEpoch(end.getEpoch() + newStartEpoch - start.getEpoch())
		start.setEpoch(newStartEpoch)
	def modifyStart(self, newStartEpoch):
		start = self['start']
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			duration.value -= float(newStartEpoch - start.getEpoch()) / duration.unit
		start.setEpoch(newStartEpoch)
	def modifyEnd(self, newEndEpoch):
		try:
			end = self['end']
		except KeyError:
			duration = self['duration']
			duration.value = float(newEndEpoch - self.getStartEpoch()) / duration.unit
		else:
			end.setEpoch(newEndEpoch)
	def setJdExact(self, jd):
		self.getAddRule('start').setJdExact(jd)
		self.setEnd('duration', 24, 3600)
	def copyFrom(self, other, *a, **kw):
		Event.copyFrom(self, other, *a, **kw)
		myStart = self['start']
		##
		if other.name == self.name:
			endType, values = other.getEnd()
			self.setEnd(endType, *values)
		else:
			if other.name == 'dailyNote':
				myStart.time = (0, 0, 0)
				self.setEnd('duration', 24, 3600)
			elif other.name == 'allDayTask':
				self.removeSomeRuleTypes('end', 'duration')
				self.copySomeRuleTypesFrom(other, 'start', 'end', 'duration')
			else:
				try:
					myStart.time = other['dayTime'].dayTime
				except KeyError:
					pass
	def setIcsData(self, data):
		self.setStartEpoch(ics.getEpochByIcsTime(data['DTSTART']))
		self.setEndEpoch(ics.getEpochByIcsTime(data['DTEND']))## FIXME
		return True


@classes.event.register
class AllDayTaskEvent(SingleStartEndEvent):## overwrites getEndEpoch from SingleStartEndEvent
	name = 'allDayTask'
	desc = _('All-Day Task')
	iconName = 'task'
	requiredRules = (
		'start',
	)
	supportedRules = (
		'start',
		'end',
		'duration',
	)
	isAllDay = True
	def setJd(self, jd):
		self.getAddRule('start').setJdExact(jd)
	def setStartDate(self, date):
		self.getAddRule('start').setDate(date)
	def setJdExact(self, jd):
		self.setJd(jd)
		self.setEnd('duration', 1)
	def setDefaults(self):
		jd = core.getCurrentJd()
		self.setJd(jd)
		self.setEnd('duration', 1)
	#def setDefaultsFromGroup(self, group):## FIXME
	#	Event.setDefaultsFromGroup(self, group)
	#	if group.name == 'taskList':
	#		value, unit = group.defaultAllDayDuration
	#		if value > 0:
	#			self.setEnd('duration', value)
	def setEnd(self, endType, value):
		self.removeSomeRuleTypes('end', 'duration')
		if endType=='date':
			rule = EndEventRule(self)
			rule.setDate(value)
		elif endType=='jd':
			rule = EndEventRule(self)
			rule.setJd(value)
		elif endType=='epoch':
			rule = EndEventRule(self)
			rule.setJd(self.getJdFromEpoch(values[0]))
		elif endType=='duration':
			rule = DurationEventRule(self)
			rule.value = value
			rule.unit = dayLen
		else:
			raise ValueError('invalid endType=%r'%endType)
		self.addRule(rule)
	def getEnd(self):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			return ('date', end.date)
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			return ('duration', duration.value)
		raise ValueError('no end date neither duration specified for task')
	def getEndJd(self):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			return end.getJd()
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			return self['start'].getJd() + duration.getSeconds()//dayLen
		raise ValueError('no end date neither duration specified for task')
	getEndEpoch = lambda self: self.getEpochFromJd(self.getEndJd())
	#def setEndJd(self, jd):
	#	self.getAddRule('end').setJdExact(jd)
	def setEndJd(self, jd):
		try:
			end = self['end']
		except KeyError:
			pass
		else:
			end.setJd(jd)
			return
		try:
			duration = self['duration']
		except KeyError:
			pass
		else:
			duration.setSeconds(dayLen*(jd-self['start'].getJd()))
			return
		raise ValueError('no end date neither duration specified for task')
	getIcsData = lambda self, prettyDateTime=False: [
		('DTSTART', ics.getIcsDateByJd(self.getJd(), prettyDateTime)),
		('DTEND', ics.getIcsDateByJd(self.getEndJd(), prettyDateTime)),
		('TRANSP', 'OPAQUE'),
		('CATEGORIES', self.name),## FIXME
	]
	def setIcsData(self, data):
		self.setJd(ics.getJdByIcsDate(data['DTSTART']))
		self.setEndJd(ics.getJdByIcsDate(data['DTEND']))## FIXME
		return True
	def copyFrom(self, other):
		SingleStartEndEvent.copyFrom(self, other)
		if other.name == self.name:
			self.setEnd(*other.getEnd())


@classes.event.register
class DailyNoteEvent(Event):
	name = 'dailyNote'
	desc = _('Daily Note')
	isSingleOccur = True
	iconName = 'note'
	requiredRules = (
		'date',
	)
	supportedRules = (
		'date',
	)
	isAllDay = True
	getDate = lambda self: self['date'].date
	def setDate(self, year, month, day):
		self['date'].date = (year, month, day)
	getJd = lambda self: self['date'].getJd()
	setJd = lambda self, jd: self['date'].setJd(jd)
	def setDefaults(self):
		self.setDate(*getSysDate(self.mode))
	def calcOccurrence(self, startJd, endJd):## float jd
		jd = self.getJd()
		return JdSetOccurrence([jd] if startJd <= jd < endJd else [])
	def getIcsData(self, prettyDateTime=False):
		jd = self.getJd()
		return [
			('DTSTART', ics.getIcsDateByJd(jd, prettyDateTime)),
			('DTEND', ics.getIcsDateByJd(jd+1, prettyDateTime)),
			('TRANSP', 'TRANSPARENT'),
			('CATEGORIES', self.name),## FIXME
		]
	def setIcsData(self, data):
		self.setJd(ics.getJdByIcsDate(data['DTSTART']))
		return True

@classes.event.register
class YearlyEvent(Event):
	name = 'yearly'
	desc = _('Yearly Event')
	iconName = 'birthday'
	requiredRules = (
		'month',
		'day',
	)
	supportedRules = requiredRules + ('start',)
	paramsOrder = Event.paramsOrder + ('startYear', 'month', 'day')
	isAllDay = True
	getMonth = lambda self: self['month'].values[0]
	setMonth = lambda self, month: self.getAddRule('month').setData(month)
	getDay = lambda self: self['day'].values[0]
	setDay = lambda self, day: self.getAddRule('day').setData(day)
	def setDefaults(self):
		y, m, d = getSysDate(self.mode)
		self.setMonth(m)
		self.setDay(d)
	def getJd(self):## used only for copyFrom
		try:
			startRule = self['start']
		except:
			y = getSysDate(self.mode)[0]
		else:
			y = startRule.getDate(self.mode)[0]
		m = self.getMonth()
		d = self.getDay()
		return to_jd(y, m, d, self.mode)
	def setJd(self, jd):## used only for copyFrom
		y, m, d = jd_to(jd, self.mode)
		self.setMonth(m)
		self.setDay(d)
		self.getAddRule('start').date = (y, 1, 1)
	def calcOccurrence(self, startJd, endJd):## float jd
		mode = self.mode
		month = self.getMonth()
		day = self.getDay()
		try:
			startRule = self['start']
		except:
			pass
		else:
			startJd = max(startJd, startRule.getJd())
		startYear = jd_to(ifloor(startJd), mode)[0]
		endYear = jd_to(iceil(endJd), mode)[0]
		jds = set()
		for year in (startYear, endYear+1):
			jd = to_jd(year, month, day, mode)
			if startJd <= jd < endJd:
				jds.add(jd)
		for year in range(startYear+1, endYear):
			jds.add(to_jd(year, month, day, mode))
		return JdSetOccurrence(jds)
	def getData(self):
		data = Event.getData(self)
		try:
			data['startYear'] = int(self['start'].date[0])
		except KeyError:
			pass
		data['month'] = self.getMonth()
		data['day'] = self.getDay()
		del data['rules']
		return data
	def setData(self, data):
		Event.setData(self, data)
		try:
			startYear = int(data['startYear'])
		except KeyError:
			pass
		except Exception as e:
			print(str(e))
		else:
			self.getAddRule('start').date = (startYear, 1, 1)
		try:
			month = data['month']
		except KeyError:
			pass
		else:
			self.setMonth(month)
		try:
			day = data['day']
		except KeyError:
			pass
		else:
			self.setDay(day)
	def getSuggestedStartYear(self):
		try:
			startJd = self.parent.startJd
		except:
			startJd = core.getCurrentJd()
		return jd_to(startJd, self.mode)[0]
	def getSummary(self):
		summary = Event.getSummary(self)
		try:
			showDate = self.parent.showDate
		except AttributeError:
			showDate = True
		if showDate:
			newParts = [
				_(self.getDay()),
				getMonthName(self.mode, self.getMonth()),
			]
			try:
				startRule = self['start']
			except KeyError:
				pass
			else:
				newParts.append(_(startRule.date[0]))
			summary = ' '.join(newParts) + ': ' + summary
		return summary
	def getIcsData(self, prettyDateTime=False):
		if self.mode != DATE_GREG:
			return None
		month = self.getMonth()
		day = self.getDay()
		startYear = icsMinStartYear
		try:
			startRule = self['start']
		except:
			try:
				startYear = jd_to(self.parent.startJd, DATE_GREG)[0]
			except AttributeError:
				pass
		else:
			startYear = startRule.getDate(DATE_GREG)[0]
		jd = to_jd(
			startYear,
			month,
			day,
			DATE_GREG,
		)
		return [
			('DTSTART', ics.getIcsDateByJd(jd, prettyDateTime)),
			('DTEND', ics.getIcsDateByJd(jd+1, prettyDateTime)),
			('RRULE', 'FREQ=YEARLY;BYMONTH=%d;BYMONTHDAY=%d'%(month, day)),
			('TRANSP', 'TRANSPARENT'),
			('CATEGORIES', self.name),## FIXME
		]
	def setIcsData(self, data):
		rrule = dict(ics.splitIcsValue(data['RRULE']))
		try:
			month = int(rrule['BYMONTH'])## multiple values are not supported
		except:
			return False
		try:
			day = int(rrule['BYMONTHDAY'])## multiple values are not supported
		except:
			return False
		self.setMonth(month)
		self.setDay(day)
		self.mode = DATE_GREG
		return True


@classes.event.register
class MonthlyEvent(Event):
	name = 'monthly'
	desc = _('Monthly Event')
	iconName = ''
	requiredRules = (
		'start',
		'end',
		'day',
		'dayTimeRange',
	)
	supportedRules = requiredRules
	isAllDay = False
	def setJd(self, jd):
		year, month, day = jd_to(jd, self.mode)
		self['start'].setDate((year, month, 1))
		self['end'].setDate((year+1, month, 1))
		self.setDay(day)
	def setDefaults(self):
		self.setJd(core.getCurrentJd())
	def getDay(self):
		try:
			return self['day'].values[0]
		except IndexError:
			return 1
	def setDay(self, day):
		self['day'].values = [day]


@classes.event.register
class WeeklyEvent(Event):
	name = 'weekly'
	desc = _('Weekly Event')
	iconName = ''
	requiredRules = (
		'start',
		'end',
		'cycleWeeks',
		'dayTimeRange',
	)
	supportedRules = requiredRules
	isAllDay = False
	def setDefaults(self):
		currentJd = core.getCurrentJd()
		self['start'].setJd(currentJd)
		self['end'].setJd(currentJd+8)

#@classes.event.register
#class UniversityCourseOwner(Event):## FIXME

@classes.event.register
class UniversityClassEvent(Event):
	name = 'universityClass'
	desc = _('Class')
	iconName = 'university'
	requiredRules  = (
		'weekNumMode',
		'weekDay',
		'dayTimeRange',
	)
	supportedRules = (
		'weekNumMode',
		'weekDay',
		'dayTimeRange',
	)
	params = Event.params + (
		'courseId',
	)
	isAllDay = False
	def __init__(self, _id=None, parent=None):
		## assert group is not None ## FIXME
		Event.__init__(self, _id, parent)
		self.courseId = None ## FIXME
	def setDefaultsFromGroup(self, group):
		Event.setDefaultsFromGroup(self, group)
		if group.name=='universityTerm':
			try:
				tm0, tm1 = group.classTimeBounds[:2]
			except:
				myRaise()
			else:
				self['dayTimeRange'].setRange(
					tm0 + (0,),
					tm1 + (0,),
				)
	getCourseName = lambda self: self.parent.getCourseNameById(self.courseId)
	getWeekDayName = lambda self: core.weekDayName[self['weekDay'].weekDayList[0]]
	def updateSummary(self):
		self.summary = _('%s Class')%self.getCourseName() + ' (' + self.getWeekDayName() + ')'
	def setJd(self, jd):
		self['weekDay'].weekDayList = [jwday(jd)]
		## set weekNumMode from absWeekNumber FIXME
	def getIcsData(self, prettyDateTime=False):
		startJd = self['start'].getJd()
		endJd = self['end'].getJd()
		occur = event.calcOccurrence(startJd, endJd)
		tRangeList = occur.getTimeRangeList()
		if not tRangeList:
			return
		return [
			('DTSTART', ics.getIcsTimeByEpoch(
				tRangeList[0][0],
				prettyDateTime,
			)),
			('DTEND', ics.getIcsTimeByEpoch(
				tRangeList[0][1],
				prettyDateTime,
			)),
			('RRULE', 'FREQ=WEEKLY;UNTIL=%s;INTERVAL=%s;BYDAY=%s'%(
				ics.getIcsDateByJd(endJd, prettyDateTime),
				1 if event['weekNumMode'].getData()=='any' else 2,
				ics.encodeIcsWeekDayList(event['weekDay'].weekDayList),
			)),
			('TRANSP', 'OPAQUE'),
			('CATEGORIES', self.name),## FIXME
		]

@classes.event.register
class UniversityExamEvent(DailyNoteEvent):
	name = 'universityExam'
	desc = _('Exam')
	iconName = 'university'
	requiredRules  = (
		'date',
		'dayTimeRange',
	)
	supportedRules = (
		'date',
		'dayTimeRange',
	)
	params = DailyNoteEvent.params + (
		'courseId',
	)
	isAllDay = False
	def __init__(self, _id=None, parent=None):
		## assert group is not None ## FIXME
		DailyNoteEvent.__init__(self, _id, parent)
		self.courseId = None ## FIXME
	def setDefaults(self):
		self['dayTimeRange'].setRange((9, 0), (11, 0))## FIXME
	def setDefaultsFromGroup(self, group):
		DailyNoteEvent.setDefaultsFromGroup(self, group)
		if group.name=='universityTerm':
			self.setJd(group.endJd)## FIXME
	getCourseName = lambda self: self.parent.getCourseNameById(self.courseId)
	def updateSummary(self):
		self.summary = _('%s Exam')%self.getCourseName()
	def calcOccurrence(self, startJd, endJd):
		jd = self.getJd()
		if startJd <= jd < endJd:
			epoch = self.getEpochFromJd(jd)
			startSec, endSec = self['dayTimeRange'].getSecondsRange()
			return TimeRangeListOccurrence(
				[
					(
						epoch + startSec,
						epoch + endSec,
					)
				]
			)
		else:
			return TimeRangeListOccurrence()
	def getIcsData(self, prettyDateTime=False):
		dayStart = self['date'].getEpoch()
		startSec, endSec = self['dayTimeRange'].getSecondsRange()
		return [
			('DTSTART', ics.getIcsTimeByEpoch(
				dayStart + startSec,
				prettyDateTime,
			)),
			('DTEND', ics.getIcsTimeByEpoch(
				dayStart + endSec,
				prettyDateTime
			)),
			('TRANSP', 'OPAQUE'),
		]





@classes.event.register
class LifeTimeEvent(SingleStartEndEvent):
	name = 'lifeTime'
	desc = _('Life Time Event')
	requiredRules  = (
		'start',
		'end',
	)
	supportedRules = (
		'start',
		'end',
	)
	isAllDay = True
	#def setDefaults(self):
	#	self['start'].date = ...
	def setJd(self, jd):
		self.getAddRule('start').setJdExact(jd)
	def addRule(self, rule):
		if rule.name in ('start', 'end'):
			rule.time = (0, 0, 0)
		SingleStartEndEvent.addRule(self, rule)
	def modifyPos(self, newStartEpoch):
		start = self['start']
		end = self['end']
		newStartJd = round(getFloatJdFromEpoch(newStartEpoch))
		end.setJdExact(end.getJd() + newStartJd - start.getJd())
		start.setJdExact(newStartJd)
	def modifyStart(self, newEpoch):
		self['start'].setEpoch(roundEpochToDay(newEpoch))
	def modifyEnd(self, newEpoch):
		self['end'].setEpoch(roundEpochToDay(newEpoch))







@classes.event.register
class LargeScaleEvent(Event):## or MegaEvent? FIXME
	name = 'largeScale'
	desc = _('Large Scale Event')
	isSingleOccur = True
	_myParams = (
		'scale',
		'start',
		'end',
		'endRel',
	)
	params = Event.params + _myParams
	paramsOrder = Event.paramsOrder + _myParams
	__bool__ = lambda self: True
	isAllDay = True
	def __init__(self, _id=None, parent=None):
		self.scale = 1 ## 1, 1000, 1000**2, 1000**3
		self.start = 0
		self.end = 1
		self.endRel = True
		Event.__init__(self, _id, parent)
	def setData(self, data):
		Event.setData(self, data)
		if 'duration' in data:
			data['end'] = data['duration']
			data['endRel'] = True
	getRulesHash = lambda self: hash(str((
		self.getTimeZoneStr(),
		'largeScale',
		self.scale,
		self.start,
		self.end,
		self.endRel,
	)))## FIXME hash(tpl) ot hash(str(tpl))
	getEnd = lambda self: self.start + self.end if self.endRel else self.end
	def setDefaultsFromGroup(self, group):
		Event.setDefaultsFromGroup(self, group)
		if group.name == 'largeScale':
			self.scale = group.scale
			self.start = group.getStartValue()
	getJd = lambda self: to_jd(self.start*self.scale, 1, 1, self.mode)
	def setJd(self, jd):
		self.start = jd_to(jd, self.mode)[0]//self.scale
	def calcOccurrence(self, startJd, endJd):
		myStartJd = iceil(to_jd(
			int(self.scale*self.start),
			1,
			1,
			self.mode,
		))
		myEndJd = ifloor(to_jd(
			int(self.scale*self.getEnd()),
			1,
			1,
			self.mode,
		))
		return TimeRangeListOccurrence.newFromStartEnd(
			max(
				self.getEpochFromJd(myStartJd),
				self.getEpochFromJd(startJd),
			),
			min(
				self.getEpochFromJd(myEndJd),
				self.getEpochFromJd(endJd),
			)
		)
	#def getIcsData(self, prettyDateTime=False):
	#	pass



@classes.event.register
class CustomEvent(Event):
	name = 'custom'
	desc = _('Custom Event')
	isAllDay = False


###########################################################################
###########################################################################


class EventContainer(BsonHistEventObj):
	name = ''
	desc = ''
	basicParams = (
		'idList',## FIXME
	)
	#BsonHistEventObj.params == ()
	params = (
		'timeZoneEnable',
		'timeZone',
		'icon',
		'title',
		'showFullEventDesc',
		'idList',
		'modified',
	)
	def __getitem__(self, key):
		if isinstance(key, int):## eventId
			return self.getEvent(key)
		else:
			raise TypeError('invalid key type %r give to EventContainer.__getitem__'%key)
	def getTimeZoneStr(self):
		if self.timeZoneEnable and self.timeZone:
			return self.timeZone
		return ''
	byIndex = lambda self, index: self.getEvent(self.idList[index])
	__str__ = lambda self: '%s(title=%s)'%(self.__class__.__name__, self.title)
	def __init__(self, title='Untitled'):
		self.parent = None
		self.timeZoneEnable = False
		self.timeZone = ''
		self.mode = calTypes.primary
		self.idList = []
		self.title = title
		self.icon = ''
		self.showFullEventDesc = False
		######
		self.modified = now()
		#self.eventsModified = self.modified
	def afterModify(self):
		self.modified = now()
	def getEvent(self, eid):
		if not eid in self.idList:
			raise ValueError('%s does not contain %s'%(self, eid))
		eventFile = Event.getFile(eid)
		if not isfile(eventFile):
			self.idList.remove(eid)
			self.save()## FIXME
			raise FileNotFoundError(
				'error while loading event file %r: file not found (container: %r)'%(eventFile, self)
			)
		data = jsonToData(open(eventFile).read())
		data['id'] = eid ## FIXME
		updateBasicDataFromBson(data, eventFile, 'event')
		event = classes.event.byName[data['type']](eid)
		event.setData(data)
		return event
	def __iter__(self):
		for eid in self.idList:
			try:
				event = self.getEvent(eid)
			except Exception as e:
				myRaise(e)
			else:
				yield event
	__len__ = lambda self: len(self.idList)
	def preAdd(self, event):
		if event.id in self.idList:
			raise ValueError('%s already contains %s'%(self, event))
		if event.parent not in (None, self):
			raise ValueError('%s already has a parent=%s, trying to add to %s'%(event, event.parent, self))
	def postAdd(self, event):
		event.parent = self ## needed? FIXME
	def insert(self, index, event):
		self.preAdd(event)
		self.idList.insert(index, event.id)
		self.postAdd(event)
	def append(self, event):
		self.preAdd(event)
		self.idList.append(event.id)
		self.postAdd(event)
	index = lambda self, eid: self.idList.index(eid)
	moveUp = lambda self, index: self.idList.insert(index-1, self.idList.pop(index))
	moveDown = lambda self, index: self.idList.insert(index+1, self.idList.pop(index))
	def remove(self, event):## call when moving to trash
		'''
			excludes event from this container (group or trash), not delete event data completely
			and returns the index of (previously contained) event
		'''
		index = self.idList.index(event.id)
		self.idList.remove(event.id)
		event.parent = None
		return index
	def copyFrom(self, other):
		BsonHistEventObj.copyFrom(self, other)
		self.mode = other.mode
	def getData(self):
		data = BsonHistEventObj.getData(self)
		data['calType'] = calTypes.names[self.mode]
		fixIconInData(data)
		return data
	def setData(self, data):
		BsonHistEventObj.setData(self, data)
		if 'calType' in data:
			calType = data['calType']
			try:
				self.mode = calTypes.names.index(calType)
			except ValueError:
				raise ValueError('Invalid calType: %r'%calType)
		###
		fixIconInObj(self)


@classes.group.register
@classes.group.setMain
class EventGroup(EventContainer):
	name = 'group'
	desc = _('Event Group')
	acceptsEventTypes = (
		'yearly',
		'dailyNote',
		'task',
		'allDayTask',
		'weekly',
		'monthly',
		'lifeTime',
		'largeScale',
		'custom',
	)
	canConvertTo = ()
	actions = []## [('Export to ICS', 'exportToIcs')]
	eventActions = [] ## FIXME
	sortBys = (
		## name, description, is_type_dependent
		('mode', _('Calendar Type'), False),
		('summary', _('Summary'), False),
		('description', _('Description'), False),
		('icon', _('Icon'), False),
	)
	sortByDefault = 'summary'
	basicParams = EventContainer.basicParams + (
		#'enable',## FIXME
		#'remoteIds', user edits the value ## FIXME
		'remoteSyncData',
		#'eventIdByRemoteIds',
		'deletedRemoteEvents',
	)
	params = EventContainer.params + (
		#'enable',
		'showInDCal',
		'showInWCal',
		'showInMCal',
		'showInStatusIcon',
		'showInTimeLine',
		'color',
		'eventCacheSize',
		'eventTextSep',
		'startJd',
		'endJd',
		'remoteIds',
		'remoteSyncData',
		#'eventIdByRemoteIds',
		'deletedRemoteEvents',
		## 'defaultEventType'
	)
	paramsOrder = (
		'enable',
		'type',
		'title',
		'calType',
		'timeZoneEnable',
		'timeZone',
		'showInDCal',
		'showInWCal',
		'showInMCal',
		'showInStatusIcon',
		'showInTimeLine',
		'showFullEventDesc',
		'color',
		'icon',
		'eventCacheSize',
		'eventTextSep',
		'startJd',
		'endJd',
		'remoteIds',
		'remoteSyncData',
		#'eventIdByRemoteIds',
		'deletedRemoteEvents',
		'idList',
	)
	@classmethod
	def getFile(cls, _id):
		return join(groupsDir, '%d.json'%_id)
	@classmethod
	def getSubclass(cls, _type):
		return classes.group.byName[_type]
	showInCal = lambda self: self.showInDCal or self.showInWCal or self.showInMCal
	def getSortBys(self):
		l = list(self.sortBys)
		if self.enable:
			l.append(('time_last', _('Last Occurrence Time'), False))
			l.append(('time_first', _('First Occurrence Time'), False))
			return 'time_last', l
		else:
			return self.sortByDefault, l
	def getSortByValue(self, event, attr):
		if attr in ('time_last', 'time_first'):
			if event.isSingleOccur:
				epoch = event.getStartEpoch()
				if epoch is not None:
					return epoch
			if self.enable:
				method = self.occur.getLastOfEvent if 'time_last' else self.occur.getFirstOfEvent
				last = method(event.id)
				if last:
					return last[0]
				else:
					print('no time_last returned for event %s'%event.id)
					return None
		return getattr(event, attr, None)
	def sort(self, attr='summary', reverse=False):
		isTypeDep = True
		for name, desc, dep in self.getSortBys()[1]:
			if name == attr:
				isTypeDep = dep
				break
		if isTypeDep:
			event_key = lambda event: (event.name, self.getSortByValue(event, attr))
		else:
			event_key = lambda event: self.getSortByValue(event, attr)
		self.idList = sorted(
			self.idList,
			key=lambda eid: event_key(self.getEvent(eid)),
			reverse=reverse,
		)
	def __getitem__(self, key):
		#if isinstance(key, basestring):## ruleName
		#	return self.getRule(key)
		if isinstance(key, int):## eventId
			return self.getEvent(key)
		else:
			raise TypeError('invalid key %r given to EventGroup.__getitem__'%key)
	def __setitem__(self, key, value):
		#if isinstance(key, basestring):## ruleName
		#	return self.setRule(key, value)
		if isinstance(key, int):## eventId
			raise TypeError('can not assign event to group')## FIXME
		else:
			raise TypeError('invalid key %r give to EventGroup.__setitem__'%key)
	def __delitem__(self, key):
		if isinstance(key, int):## eventId
			self.remove(self.getEvent(key))
		else:
			raise TypeError('invalid key %r give to EventGroup.__delitem__'%key)
	checkEventToAdd = lambda self, event: event.name in self.acceptsEventTypes
	__repr__ = lambda self: '%s(_id=%s)'%(self.__class__.__name__, self.id)
	__str__ = lambda self: '%s(_id=%s, title=%s)'%(
		self.__class__.__name__,
		self.id,
		self.title,
	)
	def __init__(self, _id=None):
		EventContainer.__init__(self, title=self.desc)
		if _id is None:
			self.id = None
		else:
			self.setId(_id)
		self.enable = True
		self.showInDCal = True
		self.showInWCal = True
		self.showInMCal = True
		self.showInStatusIcon = False
		self.showInTimeLine = True
		self.color = (0, 0, 0) ## FIXME
		#self.defaultNotifyBefore = (10, 60) ## FIXME
		if len(self.acceptsEventTypes)==1:
			self.defaultEventType = self.acceptsEventTypes[0]
			icon = classes.event.byName[self.acceptsEventTypes[0]].getDefaultIcon()
			if icon:
				self.icon = icon
		else:
			self.defaultEventType = 'custom'
		self.eventCacheSize = 0
		self.eventTextSep = core.eventTextSep
		###
		self.eventCache = {} ## from eid to event object
		###
		year, month, day = getSysDate(self.mode)
		self.startJd = to_jd(year-10, 1, 1, self.mode)
		self.endJd = to_jd(year+5, 1, 1, self.mode)
		##
		self.initOccurrence()
		###
		self.setDefaults()
		###########
		self.clearRemoteAttrs()
	def setRandomColor(self):
		import random
		from scal3.color_utils import hslToRgb
		self.color = hslToRgb(random.uniform(0, 360), 1, 0.5)## FIXME
	def clearRemoteAttrs(self):
		self.remoteIds = None## (accountId, groupId)
		## remote groupId can be an integer or string or unicode (depending on remote account type)
		self.remoteSyncData = {}
		#self.eventIdByRemoteIds = {}
		self.deletedRemoteEvents = {}
	def save(self):
		if self.id is None:
			self.setId()
		EventContainer.save(self)
	def afterSync(self):
		self.remoteSyncData[self.remoteIds] = now()
	def getLastSync(self):
		if self.remoteIds:
			try:
				return self.remoteSyncData[self.remoteIds]
			except KeyError:
				pass
	def setDefaults(self):
		'''
			sets default values that depends on group type
			not common parameters, like those are set in __init__
		'''
	__bool__ = lambda self: self.enable ## FIXME
	def setId(self, _id=None):
		if _id is None or _id<0:
			_id = lastIds.group + 1 ## FIXME
			lastIds.group = _id
		elif _id > lastIds.group:
			lastIds.group = _id
		self.id = _id
		self.file = self.getFile(self.id)
	def setTitle(self, title):
		self.title = title
	def setColor(self, color):
		self.color = color
	def getData(self):
		data = EventContainer.getData(self)
		data['type'] = self.name
		for attr in (
			'remoteSyncData',
			#'eventIdByRemoteIds',
			'deletedRemoteEvents',
		):
			if isinstance(data[attr], dict):
				data[attr] = sorted(data[attr].items())
		return data
	def setData(self, data):
		if 'showInCal' in data:## for compatibility
			data['showInDCal'] = data['showInWCal'] = data['showInMCal'] = data['showInCal']
			del data['showInCal']
		EventContainer.setData(self, data)
		if isinstance(self.remoteIds, list):
			self.remoteIds = tuple(self.remoteIds)
		for attr in (
			'remoteSyncData',
			#'eventIdByRemoteIds',
			'deletedRemoteEvents',
		):
			value = getattr(self, attr)
			if isinstance(value, list):
				valueDict = {}
				for item in value:
					if len(item) != 2:
						continue
					if not isinstance(item[0], (tuple, list)):
						continue
					valueDict[tuple(item[0])] = item[1]
				setattr(self, attr, valueDict)
		if 'id' in data:
			self.setId(data['id'])
		self.startJd = int(self.startJd)
		self.endJd = int(self.endJd)
		####
		#if 'defaultEventType' in data:
		#	self.defaultEventType = data['defaultEventType']
		#	if not self.defaultEventType in classes.event.names:
		#		raise ValueError('Invalid defaultEventType: %r'%self.defaultEventType)
	################# Event objects should be accessed from outside only within one of these 3 methods
	def getEvent(self, eid):
		if not eid in self.idList:
			raise ValueError('%s does not contain %s'%(self, eid))
		if eid in self.eventCache:
			return self.eventCache[eid]
		event = EventContainer.getEvent(self, eid)
		event.parent = self
		event.rulesHash = event.getRulesHash()
		if self.enable and len(self.eventCache) < self.eventCacheSize:
			self.eventCache[eid] = event
		return event
	def createEvent(self, eventType):
		#if not eventType in self.acceptsEventTypes:## FIXME
		#	raise ValueError('Event type "%s" not supported in group "%s"'%(eventType, self.name))
		event = classes.event.byName[eventType](parent=self)## FIXME
		return event
	def copyEventWithType(self, event, eventType):## FIXME
		newEvent = self.createEvent(eventType)
		###
		newEvent.changeMode(event.mode)
		newEvent.copyFrom(event)
		###
		newEvent.setId(event.id)
		event.invalidate()
		###
		return newEvent
	###############################################
	def remove(self, event):## call when moving to trash
		index = EventContainer.remove(self, event)
		try:
			del self.eventCache[event.id]
		except:
			pass
		if event.remoteIds:
			self.deletedRemoteEvents[event.id] = (now(),) + event.remoteIds
		#try:
		#	del self.eventIdByRemoteIds[event.remoteIds]
		#except:
		#	pass
		self.occurCount -= self.occur.delete(event.id)
		return index
	def removeAll(self):## clearEvents or excludeAll or removeAll FIXME
		for event in self.eventCache.values():
			event.parent = None ## needed? FIXME
		###
		self.idList = []
		self.eventCache = {}
		self.occur.clear()
		self.occurCount = 0
	def postAdd(self, event):
		EventContainer.postAdd(self, event)
		if len(self.eventCache) < self.eventCacheSize:
			self.eventCache[event.id] = event
		#if event.remoteIds:
		#	self.eventIdByRemoteIds[event.remoteIds] = event.id
		## need to update self.occur?
		## its done in event.afterModify() right? not when moving event from another group
		if self.enable:
			self.updateOccurrenceEvent(event)
	def updateCache(self, event):
		if event.id in self.eventCache:
			self.eventCache[event.id] = event
		event.afterModify()
	def copy(self):
		newGroup = SObj.copy(self)
		newGroup.removeAll()
		return newGroup
	def copyFrom(self, other):
		EventContainer.copyFrom(self, other)
		self.enable = other.enable
	def copyAs(self, newGroupType):
		newGroup = classes.group.byName[newGroupType]()
		newGroup.copyFrom(self)
		newGroup.removeAll()
		return newGroup
	def deepCopy(self):
		newGroup = self.copy()
		for event in self:
			newEvent = event.copy()
			newEvent.save()
			newGroup.append(newEvent)
		return newGroup
	def deepConvertTo(self, newGroupType):
		newGroup = self.copyAs(newGroupType)
		newEventType = newGroup.acceptsEventTypes[0]
		newGroup.enable = False ## to prevent per-event node update
		for event in self:
			newEvent = newGroup.createEvent(newEventType)
			newEvent.changeMode(event.mode)## FIXME needed?
			newEvent.copyFrom(event, True)
			newEvent.setId(event.id)
			newEvent.save()
			newGroup.append(newEvent)
		newGroup.enable = self.enable
		self.removeAll()## events with the same id's, can not be contained by two groups
		return newGroup
	def calcOccurrenceAll(self):
		startJd = self.startJd
		endJd = self.endJd
		for event in self:
			occur = event.calcOccurrence(startJd, endJd)
			if occur:
				yield event, occur
	def afterModify(self):## FIXME
		EventContainer.afterModify(self)
		self.initOccurrence()
		####
		if self.enable:
			self.updateOccurrence()
		else:
			self.eventCache = {}
	def updateOccurrenceEvent(self, event):
		if core.debugMode:
			print('updateOccurrenceEvent', self.id, self.title, event.id)
		eid = event.id
		self.occurCount -= self.occur.delete(eid)
		for t0, t1 in event.calcOccurrenceAll().getTimeRangeList():
			self.addOccur(t0, t1, eid)
	def initOccurrence(self):
		from scal3.event_search_tree import EventSearchTree
		#from scal3.time_line_tree import TimeLineTree
		#self.occur = TimeLineTree(offset=self.getEpochFromJd(self.endJd))
		self.occur = EventSearchTree()
		#self.occurLoaded = False
		self.occurCount = 0
	def clear(self):
	   self.occur.clear()
	   self.occurCount = 0
	def addOccur(self, t0, t1, eid):
		self.occur.add(t0, t1, eid)
		self.occurCount += 1
	def updateOccurrenceLog(self, stm0):
		if core.debugMode:
			print('updateOccurrence, id=%s, title=%s, count=%s, time=%s'%(
				self.id,
				self.title,
				self.occurCount,
				now()-stm0,
			))
	def updateOccurrence(self):
		stm0 = now()
		self.clear()
		for event, occur in self.calcOccurrenceAll():
			for t0, t1 in occur.getTimeRangeList():
				self.addOccur(t0, t1, event.id)
		#self.occurLoaded = True
		if core.debugMode:
			print('time = %d ms'%((now()-stm0)*1000))
			#print('updateOccurrence, id=%s, title=%s, count=%s, time=%s'%(
			#	self.id,
			#	self.title,
			#	self.occurCount,
			#	now()-stm0,
			#))
		#print('%s %d %.1f'%(self.id, 1000*(now()-stm0), self.occur.calcAvgDepth()))
	def exportToIcsFp(self, fp):
		currentTimeStamp = ics.getIcsTimeByEpoch(now())
		for event in self:
			print('exportToIcsFp', event.id)
			icsData = event.getIcsData()
			###
			commonText = 'BEGIN:VEVENT\n'
			commonText += 'CREATED:%s\n'%currentTimeStamp
			commonText += 'DTSTAMP:%s\n'%currentTimeStamp ## FIXME
			commonText += 'LAST-MODIFIED:%s\n'%currentTimeStamp
			commonText += 'SUMMARY:%s\n'%event.getText()
			commonText += 'DESCRIPTION:\n'
			#commonText += 'CATEGORIES:%s\n'%self.title## FIXME
			commonText += 'CATEGORIES:%s\n'%event.name## FIXME
			commonText += 'LOCATION:\n'
			commonText += 'SEQUENCE:0\n'
			commonText += 'STATUS:CONFIRMED\n'
			commonText += 'UID:%s\n'%getEventUID(event)
			###
			if icsData is None:
				occur = event.calcOccurrenceAll()
				if occur:
					if isinstance(occur, JdSetOccurrence):
						for sectionStartJd, sectionEndJd in occur.calcJdRanges():
						#for sectionStartJd in occur.getDaysJdList():
							#sectionEndJd = sectionStartJd + 1
							vevent = commonText
							vevent += 'DTSTART;VALUE=DATE:%.4d%.2d%.2d\n'%jd_to(sectionStartJd, DATE_GREG)
							vevent += 'DTEND;VALUE=DATE:%.4d%.2d%.2d\n'%jd_to(sectionEndJd, DATE_GREG)
							vevent += 'TRANSP:TRANSPARENT\n' ## http://www.kanzaki.com/docs/ical/transp.html
							vevent += 'END:VEVENT\n'
							fp.write(vevent)
					elif isinstance(occur, (TimeRangeListOccurrence, TimeListOccurrence)):
						for startEpoch, endEpoch in occur.getTimeRangeList():
							vevent = commonText
							vevent += 'DTSTART:%s\n'%ics.getIcsTimeByEpoch(startEpoch)
							if endEpoch is not None and endEpoch-startEpoch > 1:
								vevent += 'DTEND:%s\n'%ics.getIcsTimeByEpoch(int(endEpoch))## why its float? FIXME
							vevent += 'TRANSP:OPAQUE\n' ## FIXME ## http://www.kanzaki.com/docs/ical/transp.html
							vevent += 'END:VEVENT\n'
							fp.write(vevent)
					else:
						raise RuntimeError
			else:
				vevent = commonText
				for key, value in icsData:
					vevent += '%s:%s\n'%(key, value)
				vevent += 'END:VEVENT\n'
				fp.write(vevent)
	importExportExclude = (
		'remoteIds',
		'remoteSyncData',
		#'eventIdByRemoteIds',
		'deletedRemoteEvents',
	)
	def exportData(self):
		data = self.getData()
		for attr in self.importExportExclude:
			del data[attr]
		data = makeOrderedData(data, self.paramsOrder)
		data['events'] = []
		for eventId in self.idList:
			eventData = EventContainer.getEvent(self, eventId).getDataOrdered()
			data['events'].append(eventData)
			try:
				del eventData['remoteIds'] ## FIXME
			except KeyError:
				pass
			if not eventData['notifiers']:
				del eventData['notifiers']
				del eventData['notifyBefore']
		del data['idList']
		return data
	def importData(self, data):
		self.setData(data)
		self.clearRemoteAttrs()
		for eventData in data['events']:
			event = self.createEvent(eventData['type'])
			event.setData(eventData)
			event.save()
			self.append(event)
		self.save()
	simpleFilters = {
		'text': lambda event, text: not text or text in event.getText(),
		'text_lower': lambda event, text: not text or text in event.getText().lower(),
		'modified_from': lambda event, epoch: event.modified >= epoch,
		'type': lambda event, _type: event.name == _type,
	}
	def search(self, conds):
		conds = dict(conds)  # take a copy, we may modify it
		if 'time_from' in conds or 'time_to' in conds:
			try:
				time_from = conds['time_from']
			except KeyError:
				time_from = getEpochFromJd(self.startJd)
			else:
				del conds['time_from']
			try:
				time_to = conds['time_to']
			except KeyError:
				time_to = getEpochFromJd(self.endJd)
			else:
				del conds['time_to']
			idList = set()
			for epoch0, epoch1, eid, odt in self.occur.search(time_from, time_to):
				idList.add(eid)
			idList = sorted(idList)
		else:
			idList = self.idList
		#####
		data = []
		for eid in idList:
			try:
				event = self[eid]
			except:
				continue
			for key, value in conds.items():
				func = self.simpleFilters[key]
				if not func(event, value):
					break
			else:
				data.append({
					'id': eid,
					'icon': event.icon,
					'summary': event.summary,
					'description': event.getShownDescription(),
				})
		#####
		return data



@classes.group.register
class TaskList(EventGroup):
	name = 'taskList'
	desc = _('Task List')
	acceptsEventTypes = (
		'task',
		'allDayTask',
	)
	#actions = EventGroup.actions + []
	sortBys = EventGroup.sortBys + (
		('start', _('Start'), True),
		('end', _('End'), True),
	)
	sortByDefault = 'start'
	def getSortByValue(self, event, attr):
		if event.name in self.acceptsEventTypes:
			if attr=='start':
				return event.getStartEpoch()
			elif attr=='end':
				return event.getEndEpoch()
		return EventGroup.getSortByValue(self, event, attr)
	def __init__(self, _id=None):
		EventGroup.__init__(self, _id)
		self.defaultDuration = (0, 1) ## (value, unit)
		## if defaultDuration[0] is set to zero, the checkbox for task's end, will be unchecked for new tasks
	def copyFrom(self, other):
		EventGroup.copyFrom(self, other)
		if other.name == self.name:
			self.defaultDuration = other.defaultDuration[:]
	def getData(self):
		data = EventGroup.getData(self)
		data['defaultDuration'] = durationEncode(*self.defaultDuration)
		return data
	def setData(self, data):
		EventGroup.setData(self, data)
		if 'defaultDuration' in data:
			self.defaultDuration = durationDecode(data['defaultDuration'])

@classes.group.register
class NoteBook(EventGroup):
	name = 'noteBook'
	desc = _('Note Book')
	acceptsEventTypes = (
		'dailyNote',
	)
	canConvertTo = (
		'yearly',
		'taskList',
	)
	#actions = EventGroup.actions + []
	sortBys = EventGroup.sortBys + (
		('date', _('Date'), True),
	)
	sortByDefault = 'date'
	def getSortByValue(self, event, attr):
		if event.name in self.acceptsEventTypes:
			if attr=='date':
				return event.getJd()
		return EventGroup.getSortByValue(self, event, attr)


@classes.group.register
class YearlyGroup(EventGroup):
	name = 'yearly'
	desc = _('Yearly Events Group')
	acceptsEventTypes = (
		'yearly',
	)
	canConvertTo = (
		'noteBook',
	)
	params = EventGroup.params + (
		'showDate',
	)
	def __init__(self, _id=None):
		EventGroup.__init__(self, _id)
		self.showDate = True

@classes.group.register
class UniversityTerm(EventGroup):
	name = 'universityTerm'
	desc = _('University Term')
	acceptsEventTypes = (
		'universityClass',
		'universityExam',
	)
	actions = EventGroup.actions + [
		('View Weekly Schedule', 'viewWeeklySchedule'),
	]
	sortBys = EventGroup.sortBys + (
		('course', _('Course'), True),
		('time', _('Time'), True),
	)
	sortByDefault = 'time'
	params = EventGroup.params + (
		'courses',
	)
	paramsOrder = EventGroup.paramsOrder + (
		'classTimeBounds',
		'classesEndDate',
		'courses',
	)
	noCourseError = _('Edit University Term and define some Courses before you add a Class/Exam')
	def getSortByValue(self, event, attr):
		if event.name in self.acceptsEventTypes:
			if attr=='course':
				return event.courseId
			elif attr=='time':
				if event.name == 'universityClass':
					wd = event['weekDay'].weekDayList[0]
					return (wd - core.firstWeekDay)%7, event['dayTimeRange'].getHourRange()
				elif event.name == 'universityExam':
					return event['date'].getJd(), event['dayTimeRange'].getHourRange()
		return EventGroup.getSortByValue(self, event, attr)
	def __init__(self, _id=None):
		EventGroup.__init__(self, _id)
		self.classesEndDate = getSysDate(self.mode)## FIXME
		self.setCourses([]) ## list of (courseId, courseName, courseUnits)
		self.classTimeBounds = [
			(8, 0),
			(10, 0),
			(12, 0),
			(14, 0),
			(16, 0),
			(18, 0),
		] ## FIXME
	def getClassBoundsFormatted(self):
		count = len(self.classTimeBounds)
		if count < 2:
			return
		titles = []
		tmfactors = []
		firstTm = timeToFloatHour(*self.classTimeBounds[0])
		lastTm = timeToFloatHour(*self.classTimeBounds[-1])
		deltaTm = lastTm - firstTm
		for i in range(count-1):
			tm0, tm1 = self.classTimeBounds[i:i+2]
			titles.append(
				textNumEncode(simpleTimeEncode(tm0)) + ' ' + _('to') + ' ' + textNumEncode(simpleTimeEncode(tm1))
			)
		for tm1 in self.classTimeBounds:
			tmfactors.append((timeToFloatHour(*tm1)-firstTm)/deltaTm)
		return (titles, tmfactors)
	def getWeeklyScheduleData(self, currentWeekOnly=False):
		boundsCount = len(self.classTimeBounds)
		boundsHour = [h + m/60.0 for h,m in self.classTimeBounds]
		data = [
			[
				[] for i in range(boundsCount-1)
			] for weekDay in range(7)
		]
		## data[weekDay][intervalIndex] = {'name': 'Course Name', 'weekNumMode': 'odd'}
		###
		if currentWeekOnly:
			currentJd = core.getCurrentJd()
			if (
				getAbsWeekNumberFromJd(currentJd) - \
				getAbsWeekNumberFromJd(self.startJd)
			) % 2 == 1:
				currentWeekNumMode = 'odd'
			else:
				currentWeekNumMode = 'even'
			#print('currentWeekNumMode = %r'%currentWeekNumMode)
		else:
			currentWeekNumMode = ''
		###
		for event in self:
			if event.name != 'universityClass':
				continue
			weekNumMode = event['weekNumMode'].getData()
			if currentWeekNumMode:
				if weekNumMode not in ('any', currentWeekNumMode):
					continue
				weekNumMode = ''
			else:
				if weekNumMode=='any':
					weekNumMode = ''
			###
			weekDay = event['weekDay'].weekDayList[0]
			h0, h1 = event['dayTimeRange'].getHourRange()
			startIndex = findNearestIndex(boundsHour, h0)
			endIndex = findNearestIndex(boundsHour, h1)
			###
			classData = {
				'name': self.getCourseNameById(event.courseId),
				'weekNumMode': weekNumMode,
			}
			for i in range(startIndex, endIndex):
				data[weekDay][i].append(classData)

		return data
	def setCourses(self, courses):
		self.courses = courses
		#self.lastCourseId = max([1]+[course[0] for course in self.courses])
		#print('setCourses: lastCourseId=%s'%self.lastCourseId)
	#getCourseNamesDictById = lambda self: dict([c[:2] for c in self.courses])
	def getCourseNameById(self, courseId):
		for course in self.courses:
			if course[0] == courseId:
				return course[1]
		return _('Deleted Course')
	def setDefaults(self):
		calType = calTypes.names[self.mode]
		## FIXME
		## odd term or even term?
		jd = core.getCurrentJd()
		year, month, day = jd_to(jd, self.mode)
		md = (month, day)
		if calType=='jalali':
			## 0/07/01 to 0/11/01
			## 0/11/15 to 1/03/20
			if (1, 1) <= md < (4, 1):
				self.startJd = to_jd(year-1, 11, 15, self.mode)
				self.classesEndDate = (year, 3, 20)
				self.endJd = to_jd(year, 4, 10, self.mode)
			elif (4, 1) <= md < (10, 1):
				self.startJd = to_jd(year, 7, 1, self.mode)
				self.classesEndDate = (year, 11, 1)
				self.endJd = to_jd(year, 11, 1, self.mode)
			else:## md >= (10, 1)
				self.startJd = to_jd(year, 11, 15, self.mode)
				self.classesEndDate = (year+1, 3, 1)
				self.endJd = to_jd(year+1, 3, 20, self.mode)
		#elif calType=='gregorian':
		#	pass
	#def getNewCourseID(self):
	#	self.lastCourseId += 1
	#	print('getNewCourseID: lastCourseId=%s'%self.lastCourseId)
	#	return self.lastCourseId
	def copyFrom(self, other):
		EventGroup.copyFrom(self, other)
		if other.name == self.name:
			self.classesEndDate = other.classesEndDate[:]
			self.classTimeBounds = other.classTimeBounds[:]
	def getData(self):
		data = EventGroup.getData(self)
		data.update({
			'classTimeBounds': [hmEncode(hm) for hm in self.classTimeBounds],
			'classesEndDate': dateEncode(self.classesEndDate),
		})
		return data
	def setData(self, data):
		EventGroup.setData(self, data)
		#self.setCourses(data['courses'])
		if 'classesEndDate' in data:
			self.classesEndDate = dateDecode(data['classesEndDate'])
		if 'classTimeBounds' in data:
			self.classTimeBounds = sorted([hmDecode(hm) for hm in data['classTimeBounds']])
	def afterModify(self):
		EventGroup.afterModify(self)
		for event in self:
			try:
				event.updateSummary()
			except AttributeError:
				pass
			else:
				event.save()

@classes.group.register
class LifeTimeGroup(EventGroup):
	name = 'lifeTime'
	desc = _('Life Time Events Group')
	acceptsEventTypes = (
		'lifeTime',
	)
	sortBys = EventGroup.sortBys + (
		('start', _('Start'), True),
	)
	params = EventGroup.params + (
		'showSeperatedYmdInputs',
	)
	def getSortByValue(self, event, attr):
		if event.name in self.acceptsEventTypes:
			if attr=='start':
				return event.getStartJd()
			elif attr=='end':
				return event.getEndJd()
		return EventGroup.getSortByValue(self, event, attr)
	def __init__(self, _id=None):
		self.showSeperatedYmdInputs = False
		EventGroup.__init__(self, _id)
	def setDefaults(self):
		## only in time line ## or in init? FIXME
		self.showInDCal = False
		self.showInWCal = False
		self.showInMCal = False
		self.showInStatusIcon = False


@classes.group.register
class LargeScaleGroup(EventGroup):
	name = 'largeScale'
	desc = _('Large Scale Events Group')
	acceptsEventTypes = (
		'largeScale',
	)
	sortBys = EventGroup.sortBys + (
		('start', _('Start'), True),
		('end', _('End'), True),
	)
	sortByDefault = 'start'
	def getSortByValue(self, event, attr):
		if event.name in self.acceptsEventTypes:
			if attr=='start':
				return event.start * event.scale
			elif attr=='end':
				return event.getEnd() * event.scale
		return EventGroup.getSortByValue(self, event, attr)
	def __init__(self, _id=None):
		self.scale = 1 ## 1, 1000, 1000**2, 1000**3
		EventGroup.__init__(self, _id)
	def setDefaults(self):
		self.startJd = 0
		self.endJd = self.startJd + self.scale * 9999
		## only in time line ## or in init? FIXME
		self.showInDCal = False
		self.showInWCal = False
		self.showInMCal = False
		self.showInStatusIcon = False
	def copyFrom(self, other):
		EventGroup.copyFrom(self, other)
		if other.name == self.name:
			self.scale = other.scale
	def getData(self):
		data = EventGroup.getData(self)
		data['scale'] = self.scale
		return data
	def setData(self, data):
		EventGroup.setData(self, data)
		try:
			self.scale = data['scale']
		except KeyError:
			pass
	getStartValue = lambda self: jd_to(self.startJd, self.mode)[0]//self.scale
	getEndValue = lambda self: jd_to(self.endJd, self.mode)[0]//self.scale
	def setStartValue(self, start):
		self.startJd = int(to_jd(start*self.scale, 1, 1, self.mode))
	def setEndValue(self, end):
		self.endJd = int(to_jd(end*self.scale, 1, 1, self.mode))


###########################################################################
###########################################################################

class VcsEpochBaseEvent(Event):
	readOnly = True
	params = Event.params + (
		'epoch',
	)
	@classmethod
	def load(cls):## FIXME
		pass
	__bool__ = lambda self: True
	def save(self):
		pass
	def afterModify(self):
		pass
	getInfo = lambda self: self.getText()## FIXME
	def calcOccurrence(self, startJd, endJd):
		epoch = self.epoch
		if epoch is not None:
			if self.getEpochFromJd(startJd) <= epoch < self.getEpochFromJd(endJd):
				if not self.parent.showSeconds:
					print('-------- showSeconds = False')
					epoch -= (epoch % 60)
				return TimeListOccurrence(epoch)
		return TimeListOccurrence()

#@classes.event.register ## FIXME
class VcsCommitEvent(VcsEpochBaseEvent):
	name = 'vcs'
	desc = _('VCS Commit')
	params = VcsEpochBaseEvent.params + (
		'author',
		'shortHash',
	)
	def __init__(self, parent, _id):
		Event.__init__(self, parent=parent)
		self.id = _id ## commit full hash
		###
		self.epoch = None
		self.author = ''
		self.shortHash = ''
	__repr__ = lambda self: '%r.getEvent(%r)'%(self.parent, self.id)



class VcsTagEvent(VcsEpochBaseEvent):
	name = 'vcsTag'
	desc = _('VCS Tag')
	params = VcsEpochBaseEvent.params + (
	)
	def __init__(self, parent, _id):
		Event.__init__(self, parent=parent)
		self.id = _id ## tag name
		self.epoch = None
		self.author = ''



class VcsBaseEventGroup(EventGroup):
	acceptsEventTypes = ()
	myParams = (
		'vcsType',
		'vcsDir',
	)
	def __init__(self, _id=None):
		self.vcsType = 'git'
		self.vcsDir = ''
		#self.branch = 'master'
		EventGroup.__init__(self, _id)
	__str__ = lambda self: '%s(_id=%s, title=%s, vcsType=%s, vcsDir=%s)'%(
		self.__class__.__name__,
		self.id,
		self.title,
		self.vcsType,
		self.vcsDir,
	)
	def setDefaults(self):
		self.eventTextSep = '\n'
		self.showInTimeLine = False
	getRulesHash = lambda self: hash(str((
		self.name,
		self.vcsType,
		self.vcsDir,
	)))## FIXME
	def __getitem__(self, key):
		if key in classes.rule.names:
			return EventGroup.__getitem__(self, key)
		else:## len(commit_id)==40 for git
			return self.getEvent(key)
	def getVcsModule(self):
		name = toStr(self.vcsType)
		#if not isinstance(name, str):
		#	raise TypeError('getVcsModule(%r): bad type %s'%(name, type(name)))
		try:
			mod = __import__('scal3.vcs_modules', fromlist=[name])
		except ImportError:
			myRaise()
			return
		return getattr(mod, name)
	def updateVcsModuleObj(self):
		mod = self.getVcsModule()
		mod.clearObj(self)
		if self.enable and self.vcsDir:
			try:
				mod.prepareObj(self)
			except:
				myRaise()
	def afterModify(self):
		self.updateVcsModuleObj()
		EventGroup.afterModify(self)
	def setData(self, data):
		EventGroup.setData(self, data)
		self.updateVcsModuleObj()



class VcsEpochBaseEventGroup(VcsBaseEventGroup):
	myParams = VcsBaseEventGroup.myParams + (
		'showSeconds',
	)
	canConvertTo = VcsBaseEventGroup.canConvertTo + (
		'taskList',
	)
	def __init__(self, _id=None):
		self.showSeconds = True
		self.vcsIds = []
		VcsBaseEventGroup.__init__(self, _id)
	def clear(self):
		EventGroup.clear(self)
		self.vcsIds = []
	def addOccur(self, t0, t1, eid):
		EventGroup.addOccur(self, t0, t1, eid)
		self.vcsIds.append(eid)
	getRulesHash = lambda self: hash(str((
		self.name,
		self.vcsType,
		self.vcsDir,
		self.showSeconds,
	)))
	def deepConvertTo(self, newGroupType):
		newGroup = self.copyAs(newGroupType)
		if newGroupType == 'taskList':
			newEventType = 'task'
			newGroup.enable = False ## to prevent per-event node update
			for vcsId in self.vcsIds:
				event = self.getEvent(vcsId)
				newEvent = newGroup.createEvent(newEventType)
				newEvent.changeMode(event.mode)## FIXME needed?
				newEvent.copyFrom(event, True)
				newEvent.setStartEpoch(event.epoch)
				newEvent.setEnd('duration', 0, 1)
				newEvent.save()
				newGroup.append(newEvent)
			newGroup.enable = self.enable
		return newGroup



@classes.group.register
class VcsCommitEventGroup(VcsEpochBaseEventGroup):
	name = 'vcs'
	desc = _('VCS Repository (Commits)')
	myParams = VcsEpochBaseEventGroup.myParams + (
		'showAuthor',
		'showShortHash',
		'showStat',
	)
	params = EventGroup.params + myParams
	paramsOrder = EventGroup.paramsOrder + myParams
	def __init__(self, _id=None):
		VcsEpochBaseEventGroup.__init__(self, _id)
		self.showAuthor = True
		self.showShortHash = True
		self.showStat = True
	def updateOccurrence(self):
		stm0 = now()
		self.clear()
		if not self.vcsDir:
			return
		mod = self.getVcsModule()
		try:
			commitsData = mod.getCommitList(self, startJd=self.startJd, endJd=self.endJd)
		except:
			printError('Error while fetching commit list of %s repository in %s'%(
				self.vcsType,
				self.vcsDir,
			))
			myRaise()
			return
		for epoch, commit_id in commitsData:
			if not self.showSeconds:
				epoch -= (epoch % 60)
			self.addOccur(epoch, epoch, commit_id)
		###
		self.updateOccurrenceLog(stm0)
	def updateEventDesc(self, event):
		mod = self.getVcsModule()
		lines = []
		if event.description:
			lines.append(event.description)
		if self.showStat:
			statLine = mod.getCommitShortStatLine(self, event.id)
			if statLine:
				lines.append(statLine)## translation FIXME
		if self.showAuthor and event.author:
			lines.append(_('Author')+': '+event.author)
		if self.showShortHash and event.shortHash:
			lines.append(_('Hash')+': '+event.shortHash)
		event.description = '\n'.join(lines)
	def getEvent(self, commit_id):## cache commit data FIXME
		mod = self.getVcsModule()
		data = mod.getCommitInfo(self, commit_id)
		if not data:
			raise ValueError('No commit with id=%r'%commit_id)
		data['summary'] = self.title +': ' + data['summary']
		data['icon'] = self.icon
		event = VcsCommitEvent(self, commit_id)
		event.setData(data)
		self.updateEventDesc(event)
		return event





@classes.group.register
class VcsTagEventGroup(VcsEpochBaseEventGroup):
	name = 'vcsTag'
	desc = _('VCS Repository (Tags)')
	myParams = VcsEpochBaseEventGroup.myParams + (
		'showStat',
	)
	params = EventGroup.params + myParams
	paramsOrder = EventGroup.paramsOrder + myParams
	def __init__(self, _id=None):
		VcsEpochBaseEventGroup.__init__(self, _id)
		self.showStat = True
	def updateOccurrence(self):
		stm0 = now()
		self.clear()
		if not self.vcsDir:
			return
		mod = self.getVcsModule()
		try:
			tagsData = mod.getTagList(self, self.startJd, self.endJd)## TOO SLOW
		except:
			printError('Error while fetching tag list of %s repository in %s'%(
				self.vcsType,
				self.vcsDir,
			))
			myRaise()
			return
		#self.updateOccurrenceLog(stm0)
		for epoch, tag in tagsData:
			if not self.showSeconds:
				epoch -= (epoch % 60)
			self.addOccur(epoch, epoch, tag)
		###
		self.updateOccurrenceLog(stm0)
	def updateEventDesc(self, event):
		mod = self.getVcsModule()
		tag = event.id
		lines = []
		if self.showStat:
			tagIndex = self.vcsIds.index(tag)
			if tagIndex > 0:
				prevTag = self.vcsIds[tagIndex-1]
			else:
				prevTag = None
			statLine = mod.getTagShortStatLine(self, prevTag, tag)
			if statLine:
				lines.append(statLine)## translation FIXME
		event.description = '\n'.join(lines)
	def getEvent(self, tag):## cache commit data FIXME
		if not tag in self.vcsIds:
			raise ValueError('No tag %r'%tag)
		data = {}
		data['summary'] = self.title + ' ' + tag ## FIXME
		data['icon'] = self.icon
		event = VcsTagEvent(self, tag)
		event.setData(data)
		self.updateEventDesc(event)
		return event



class VcsDailyStatEvent(Event):
	name = 'vcsDailyStat'
	desc = _('VCS Daily Stat')
	readOnly = True
	isAllDay = True
	params = Event.params + (
		'jd',
	)
	__bool__ = lambda self: True
	def __init__(self, parent, jd):
		Event.__init__(self, parent=parent)
		self.id = jd ## ID is Julian Day
	def save(self):
		pass
	@classmethod
	def load(cls):## FIXME
		pass
	def afterModify(self):
		pass
	getInfo = lambda self: self.getText()## FIXME
	def calcOccurrence(self, startJd, endJd):
		jd = self.jd
		if jd is not None:
			if startJd <= jd < endJd:
				JdSetOccurrence(jd)
		return JdSetOccurrence()


@classes.group.register
class VcsDailyStatEventGroup(VcsBaseEventGroup):
	name = 'vcsDailyStat'
	desc = _('VCS Repository (Daily Stat)')
	myParams = VcsBaseEventGroup.myParams + (
	)
	params = EventGroup.params + myParams
	paramsOrder = EventGroup.paramsOrder + myParams
	def __init__(self, _id=None):
		VcsBaseEventGroup.__init__(self, _id)
		self.statByJd = {}
	def clear(self):
		VcsBaseEventGroup.clear(self)
		self.statByJd = {} ## a dict of (commintsCount, lastCommitId)s
	def updateOccurrence(self):
		stm0 = now()
		self.clear()
		if not self.vcsDir:
			return
		mod = self.getVcsModule()
		####
		try:
			utc = natz.timezone('UTC')
			self.vcsMinJd = getJdFromEpoch(mod.getFirstCommitEpoch(self), tz=utc)
			self.vcsMaxJd = getJdFromEpoch(mod.getLastCommitEpoch(self), tz=utc) + 1
		except:
			myRaise()
			return
		###
		startJd = max(self.startJd, self.vcsMinJd)
		endJd = min(self.endJd, self.vcsMaxJd)
		###
		lastCommitId = mod.getLastCommitIdUntilJd(self, startJd)
		for jd in range(startJd, endJd):
			commits = mod.getCommitList(self, startJd=jd, endJd=jd+1)
			if not commits:
				continue
			lastCommitIdPrev, lastCommitId = lastCommitId, commits[0][1]
			if not lastCommitIdPrev:
				continue
			stat = mod.getShortStat(self, lastCommitIdPrev, lastCommitId)
			self.statByJd[jd] = (len(commits), stat)
			self.addOccur(
				getEpochFromJd(jd),
				getEpochFromJd(jd+1),
				jd,
			)
		###
		self.updateOccurrenceLog(stm0)
	def getEvent(self, jd):## cache commit data FIXME
		from scal3.vcs_modules import encodeShortStat
		try:
			commitsCount, stat = self.statByJd[jd]
		except KeyError:
			raise ValueError('No commit for jd %s'%jd)
		mod = self.getVcsModule()
		event = VcsDailyStatEvent(self, jd)
		###
		event.icon = self.icon
		##
		statLine = encodeShortStat(*stat)
		event.summary = self.title + ': ' + _('%d commits')%commitsCount ## FIXME
		event.summary += ', ' + statLine
		#event.description = statLine
		## FIXME
		###
		return event


###########################################################################
###########################################################################

class JsonObjectsHolder(JsonEventObj):
	## keeps all objects in memory
	## Only use to keep groups and accounts, but not events
	skipLoadNoFile = True
	def __init__(self, _id=None):
		self.clear()
	def clear(self):
		self.byId = {}
		self.idList = []
	def __iter__(self):
		for _id in self.idList:
			yield self.byId[_id]
	__len__ = lambda self: len(self.idList)
	__bool__ = lambda self: bool(self.idList)
	index = lambda self, _id: self.idList.index(_id) ## or get object instead of obj_id? FIXME
	__getitem__ = lambda self, _id: self.byId.__getitem__(_id)
	byIndex = lambda self, index: self.byId[self.idList[index]]
	#byIndex = lambda
	__setitem__ = lambda self, _id, group: self.byId.__setitem__(_id, group)
	def insert(self, index, obj):
		assert not obj.id in self.idList
		self.byId[obj.id] = obj
		self.idList.insert(index, obj.id)
	def append(self, obj):
		assert not obj.id in self.idList
		self.byId[obj.id] = obj
		self.idList.append(obj.id)
	def delete(self, obj):
		assert obj.id in self.idList
		try:
			os.remove(obj.file)
		except:
			myRaise()
		try:
			del self.byId[obj.id]
		except:
			myRaise()
		try:
			self.idList.remove(obj.id)
		except:
			myRaise()
	pop = lambda self, index: self.byId.pop(self.idList.pop(index))
	moveUp = lambda self, index: self.idList.insert(index-1, self.idList.pop(index))
	moveDown = lambda self, index: self.idList.insert(index+1, self.idList.pop(index))
	def setData(self, data):
		self.clear()
		for sid in data:
			assert isinstance(sid, int) and sid != 0
			_id = sid
			_id = abs(sid)
			cls = getattr(classes, self.childName).main
			obj = cls.load(_id)
			obj.parent = self
			obj.enable = (sid > 0)
			self.idList.append(_id)
			self.byId[obj.id] = obj
	getData = lambda self: [_id if self.byId[_id] else -_id for _id in self.idList]



class EventGroupsHolder(JsonObjectsHolder):
	file = join(confDir, 'event', 'group_list.json')
	childName = 'group'
	def __init__(self, _id=None):
		JsonObjectsHolder.__init__(self)
		self.id = None
		self.parent = None
	def delete(self, obj):
		assert not obj.idList ## FIXME
		obj.parent = None
		JsonObjectsHolder.delete(self, obj)
	def setData(self, data):
		self.clear()
		if data:
			JsonObjectsHolder.setData(self, data)
			for obj in self:
				if obj.enable:
					obj.updateOccurrence()
		else:
			for name in (
				'noteBook',
				'taskList',
				'group',
			):
				cls = classes.group.byName[name]
				obj = cls()## FIXME
				obj.setRandomColor()
				obj.setTitle(cls.desc)
				obj.save()
				self.append(obj)
	def getEnableIds(self):
		ids = []
		for group in self:
			if group.enable:
				ids.append(group.id)
		return ids
	def moveToTrash(self, group, trash, addToFirst=True):
		if core.eventTrashLastTop:
			trash.idList = group.idList + trash.idList
		else:
			trash.idList += group.idList
		group.idList = []
		self.delete(group)
		self.save()
		trash.save()
	def convertGroupTo(self, group, newGroupType):
		groupIndex = self.index(group.id)
		newGroup = group.deepConvertTo(newGroupType)
		newGroup.setId(group.id)
		newGroup.afterModify()
		newGroup.save()
		self.byId[newGroup.id] = newGroup
		return newGroup
		## and then never use old `group` object
	def exportData(self, gidList):
		data = OrderedDict([
			('info', OrderedDict([
				('appName', core.APP_NAME),
				('version', core.VERSION),
			])),
			('groups', []),
		])
		for gid in gidList:
			data['groups'].append(self.byId[gid].exportData())
		return data
	def importData(self, data):
		newGroups = []
		for gdata in data['groups']:
			group = classes.group.byName[gdata['type']]()
			group.importData(gdata)
			self.append(group)
			newGroups.append(group)
		self.save()## FIXME
		return newGroups
	importJsonFile = lambda self, fpath: self.importData(jsonToData(open(fpath, 'rb').read()))
	def exportToIcs(self, fpath, gidList):
		fp = open(fpath, 'w')
		fp.write(ics.icsHeader)
		for gid in gidList:
			self[gid].exportToIcsFp(fp)
		fp.write('END:VCALENDAR\n')
		fp.close()
	def checkForOrphans(self):
		newGroup = EventGroup()
		newGroup.setTitle(_('Orphan Events'))
		newGroup.setColor((255, 255, 0))
		newGroup.enable = False
		for gid_fname in listdir(groupsDir):
			try:
				gid = int(splitext(gid_fname)[0])
			except ValueError:
				continue
			if not gid in self.idList:
				try:
					os.remove(join(groupsDir, gid_fname))
				except:
					myRaise()
		######
		myEventIds = []
		for group in self:
			myEventIds += group.idList
		myEventIds = set(myEventIds)
		##
		for fname in listdir(eventsDir):
			fname_nox, ext = splitext(fname)
			if ext != '.json':
				continue
			try:
				eid = int(fname_nox)
			except ValueError:
				continue
			if eid in myEventIds:
				continue
			newGroup.idList.append(eid)
		if newGroup.idList:
			newGroup.save()
			self.append(newGroup)
			self.save()
			return newGroup
		else:
			return


class EventAccountsHolder(JsonObjectsHolder):
	file = join(confDir, 'event', 'account_list.json')
	def loadClass(self, name):
		try:
			return classes.account.byName[name]
		except KeyError:## FIXME
			try:
				__import__('scal3.account.%s'%name)
			except ImportError:
				myRaiseTback()
			else:
				try:
					return classes.account.byName[name]
				except KeyError:## FIXME
					pass
		log.error('error while loading account: no account type "%s"'%name)
	def loadData(self, _id):
		objFile = join(accountsDir, '%s.json'%_id)
		if not isfile(objFile):
			log.error('error while loading account file %r: file not found'%objFile)## FIXME
			## FileNotFoundError
		data = jsonToData(open(objFile).read())
		updateBasicDataFromBson(data, objFile, 'account')
		#if data['id'] != _id:
		#	log.error('attribute "id" in json file does not match the file name: %s'%objFile)
		#del data['id']
		return data
	'''
	def load(self):
		#print('------------ EventAccountsHolder.load')
		self.clear()
		if isfile(self.file):
			for _id in jsonToData(open(self.file).read()):
				data = self.loadData(_id)
				if not data:
					continue
				name = data['type']
				if data['enable']:
					cls = self.loadClass(name)
					if cls is None:
						continue
					try:
						obj = cls(_id)
					except:
						myRaise()
						continue
					#data['id'] = _id ## FIXME
					obj.setData(data)
				else:
					obj = DummyAccount(
						name,
						_id,
						data['title'],
					)
				self.append(obj)
	'''
	def getLoadedObj(self, obj):
		_id = obj.id
		data = self.loadData(_id)
		name = data['type']
		cls = self.loadClass(name)
		if cls is None:
			return
		obj = cls(_id)
		data = self.loadData(_id)
		obj.setData(data)
		return obj
	def replaceDummyObj(self, obj):
		_id = obj.id
		index = self.idList.index(_id)
		obj = self.getLoadedObj(obj)
		self.byId[_id] = obj
		return obj



class EventTrash(EventContainer):
	name = 'trash'
	desc = _('Trash')
	file = join(confDir, 'event', 'trash.json')## FIXME
	skipLoadNoFile = True
	id = -1 ## FIXME
	def __init__(self):
		EventContainer.__init__(self, title=_('Trash'))
		self.icon = join(pixDir, 'trash.png')
		self.enable = False
	def delete(self, eid):
		from shutil import rmtree
		## different from EventContainer.remove
		## remove() only removes event from this group, but event file and data still available
		## and probably will be added to another event container
		## but after delete(), there is no event file, and not event data
		if not isinstance(eid, int):
			raise TypeError("delete takes event ID that is integer")
		assert eid in self.idList
		try:
			os.remove(Event.getFile(eid))
		except:
			myRaise()
		else:
			self.idList.remove(eid)
	def empty(self):
		from shutil import rmtree
		idList2 = self.idList[:]
		for eid in self.idList:
			try:
				os.remove(Event.getFile(eid))
			except:
				myRaise()
			idList2.remove(eid)
		self.idList = idList2
		self.save()


class DummyAccount:
	loaded = False
	enable = False
	params = ()
	paramsOrder = ()
	accountsDesc = {
		'google': _('Google'),
	}
	def __init__(self, _type, _id, title):
		self.name = _type
		self.desc = self.accountsDesc[_type]
		self.id = _id
		self.title = title
	def save():
		pass
	def load():
		pass
	def getLoadedObj(self):
		pass

## Should not be registered, or instantiate directly
@classes.account.setMain
class Account(BsonHistObj):
	loaded = True
	name = ''
	desc = ''
	basicParams = (## FIXME
		'enable',    
	)
	params = (
		'enable',
		'title',
		'remoteGroups',
	)
	paramsOrder = (
		'enable',
		'type',
		'title',
		'remoteGroups',
	)
	@classmethod
	def getFile(cls, _id):
		return join(accountsDir, '%d.json'%_id)
	@classmethod
	def getSubclass(cls, _type):
		return classes.account.byName[_type]
	def __init__(self, _id=None):
		if _id is None:
			self.id = None
		else:
			self.setId(_id)
		self.enable = True
		self.title = 'Account'
		self.remoteGroups = []## a list of dictionarise {'id':..., 'title':...}
		self.status = None## {'action': 'pull', 'done': 10, 'total': 20}
		## action values: 'fetchGroups', 'pull', 'push'
	def save(self):
		if self.id is None:
			self.setId()
		BsonHistObj.save(self)
	def setId(self, _id=None):
		if _id is None or _id<0:
			_id = lastIds.account + 1 ## FIXME
			lastIds.account = _id
		elif _id > lastIds.account:
			lastIds.account = _id
		self.id = _id
		self.file = self.getFile(self.id)
	def stop(self):
		self.status = None
	def fetchGroups(self):
		raise NotImplementedError
	def fetchAllEventsInGroup(self, remoteGroupId):
		raise NotImplementedError
	def sync(self, group, remoteGroupId):
		raise NotImplementedError
	def getData(self):
		data = BsonHistObj.getData(self)
		data['type'] = self.name
		return data


########################################################################

def getDayOccurrenceData(curJd, groups):
	data = []
	for groupIndex, group in enumerate(groups):
		if not group.enable:
			continue
		if not group.showInCal():
			continue
		#print('\nupdateData: checking event', event.summary)
		gid = group.id
		color = group.color
		for epoch0, epoch1, eid, odt in group.occur.search(getEpochFromJd(curJd), getEpochFromJd(curJd+1)):
			event = group[eid]
			###
			text = event.getTextParts()
			###
			timeStr = ''
			if epoch1-epoch0 < dayLen:
				jd0, h0, m0, s0 = getJhmsFromEpoch(epoch0)
				if jd0 < curJd:
					h0, m0, s0 = 0, 0, 0
				if epoch1 - epoch0 < 1:
					timeStr = timeEncode((h0, m0, s0), True)
				else:
					jd1, h1, m1, s1 = getJhmsFromEpoch(epoch1)
					if jd1 > curJd:
						h1, m1, s1 = 24, 0, 0
					timeStr = hmsRangeToStr(h0, m0, s0, h1, m1, s1)
			###
			try:
				eventIndex = group.index(eid)
			except ValueError:
				eventIndex = event.modified ## FIXME
			data.append((
				(epoch0, epoch1, groupIndex, eventIndex),## FIXME for sorting
				{
					'time': timeStr,
					'time_epoch': (epoch0, epoch1),
					'is_allday': epoch0 % dayLen == 0 and epoch1 % dayLen == 0,
					'text': text,
					'icon': event.icon,
					'color': color,
					'ids': (gid, eid),
					'show': (group.showInDCal, group.showInWCal, group.showInMCal),
					'showInStatusIcon': group.showInStatusIcon,
				}
			))
	data.sort()
	return [item[1] for item in data]


def getWeekOccurrenceData(curAbsWeekNumber, groups):
	startJd = core.getStartJdOfAbsWeekNumber(absWeekNumber)
	endJd = startJd + 7
	data = []
	for group in groups:
		if not group.enable:
			continue
		for event in group:
			if not event:
				continue
			occur = event.calcOccurrence(startJd, endJd)
			if not occur:
				continue
			text = event.getText()
			icon = event.icon
			ids = (group.id, event.id)
			if isinstance(occur, JdSetOccurrence):
				for jd in occur.getDaysJdList():
					wnum, weekDay = core.getWeekDateFromJd(jd)
					if wnum==curAbsWeekNumber:
						data.append({
							'weekDay':weekDay,
							'time':'',
							'text':text,
							'icon':icon,
							'ids': ids,
						})
			elif isinstance(occur, TimeRangeListOccurrence):
				for startEpoch, endEpoch in occur.getTimeRangeList():
					jd1, h1, min1, s1 = getJhmsFromEpoch(startEpoch)
					jd2, h2, min2, s2 = getJhmsFromEpoch(endEpoch)
					wnum, weekDay = core.getWeekDateFromJd(jd1)
					if wnum==curAbsWeekNumber:
						if jd1==jd2:
							data.append({
								'weekDay':weekDay,
								'time':hmsRangeToStr(h1, min1, s1, h2, min2, s2),
								'text':text,
								'icon':icon,
								'ids': ids,
							})
						else:## FIXME
							data.append({
								'weekDay':weekDay,
								'time':hmsRangeToStr(h1, min1, s1, 24, 0, 0),
								'text':text,
								'icon':icon,
								'ids': ids,
							})
							for jd in range(jd1+1, jd2):
								wnum, weekDay = core.getWeekDateFromJd(jd)
								if wnum==curAbsWeekNumber:
									data.append({
										'weekDay':weekDay,
										'time':'',
										'text':text,
										'icon':icon,
										'ids': ids,
									})
								else:
									break
							wnum, weekDay = core.getWeekDateFromJd(jd2)
							if wnum==curAbsWeekNumber:
								data.append({
									'weekDay':weekDay,
									'time':hmsRangeToStr(0, 0, 0, h2, min2, s2),
									'text':text,
									'icon':icon,
									'ids': ids,
								})
			elif isinstance(occur, TimeListOccurrence):
				for epoch in occur.epochList:
					jd, hour, minute, sec = getJhmsFromEpoch(epoch)
					wnum, weekDay = core.getWeekDateFromJd(jd)
					if wnum==curAbsWeekNumber:
						data.append({
							'weekDay':weekDay,
							'time':timeEncode((hour, minute, sec), True),
							'text':text,
							'icon':icon,
							'ids': ids,
						})
			else:
				raise TypeError
	return data


def getMonthOccurrenceData(curYear, curMonth, groups):
	startJd, endJd = core.getJdRangeForMonth(curYear, curMonth, calTypes.primary)
	data = []
	for group in groups:
		if not group.enable:
			continue
		for event in group:
			if not event:
				continue
			occur = event.calcOccurrence(startJd, endJd)
			if not occur:
				continue
			text = event.getText()
			icon = event.icon
			ids = (group.id, event.id)
			if isinstance(occur, JdSetOccurrence):
				for jd in occur.getDaysJdList():
					y, m, d = jd_to_primary(jd)
					if y==curYear and m==curMonth:
						data.append({
							'day':d,
							'time':'',
							'text':text,
							'icon':icon,
							'ids': ids,
						})
			elif isinstance(occur, TimeRangeListOccurrence):
				for startEpoch, endEpoch in occur.getTimeRangeList():
					jd1, h1, min1, s1 = getJhmsFromEpoch(startEpoch)
					jd2, h2, min2, s2 = getJhmsFromEpoch(endEpoch)
					y, m, d = jd_to_primary(jd1)
					if y==curYear and m==curMonth:
						if jd1==jd2:
							data.append({
								'day':d,
								'time':hmsRangeToStr(h1, min1, s1, h2, min2, s2),
								'text':text,
								'icon':icon,
								'ids': ids,
							})
						else:## FIXME
							data.append({
								'day':d,
								'time':hmsRangeToStr(h1, min1, s1, 24, 0, 0),
								'text':text,
								'icon':icon,
								'ids': ids,
							})
							for jd in range(jd1+1, jd2):
								y, m, d = jd_to_primary(jd)
								if y==curYear and m==curMonth:
									data.append({
										'day':d,
										'time':'',
										'text':text,
										'icon':icon,
										'ids': ids,
									})
								else:
									break
							y, m, d = jd_to_primary(jd2)
							if y==curYear and m==curMonth:
								data.append({
									'day':d,
									'time':hmsRangeToStr(0, 0, 0, h2, min2, s2),
									'text':text,
									'icon':icon,
									'ids': ids,
								})
			elif isinstance(occur, TimeListOccurrence):
				for epoch in occur.epochList:
					jd, hour, minute, sec = getJhmsFromEpoch(epoch)
					y, m, d = jd_to_primary(jd1)
					if y==curYear and m==curMonth:
						data.append({
							'day':d,
							'time':timeEncode((hour, minute, sec), True),
							'text':text,
							'icon':icon,
							'ids': ids,
						})
			else:
				raise TypeError
	return data





