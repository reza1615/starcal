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

import sys, os
from math import floor, ceil

from scal3.lib import OrderedDict

try:
	from collections import Iterable
except ImportError:
	class Iterable:

		def __iter__(self):
			raise NotImplementedError

		@classmethod
		def __subclasshook__(cls, C):
			if cls is Iterable:
				if any('__iter__' in B.__dict__ for B in C.__mro__):
					return True
			return NotImplemented

try:
	from collections import Iterator
except ImportError:
	class Iterator(Iterable):

		def __next__(self):
			raise StopIteration

		__iter__ = lambda self: self

		@classmethod
		def __subclasshook__(cls, C):
			if cls is Iterator:
				if (any('__next__' in B.__dict__ for B in C.__mro__) and
					any('__iter__' in B.__dict__ for B in C.__mro__)):
					return True
			return NotImplemented




ifloor = lambda x: int(floor(x))
iceil = lambda x: int(ceil(x))

def arange(start, stop, step):
	l = []
	x = start
	stop -= 0.000001
	while x < stop:
		l.append(x)
		x += step
	return l

toBytes = lambda s: s.encode('utf8') if isinstance(s, str) else bytes(s)
toStr = lambda s: str(s, 'utf8') if isinstance(s, bytes) else str(s)

cmp = lambda a, b: 0 if a==b else (1 if a>b else -1)

def versionLessThan(v0, v1):
	if v0=='':
		if v1=='':
			return 0
		else:
			return -1
	elif v1=='':
		return 1
	return [ int(p) for p in v0.split('.') ] < [ int(p) for p in v1.split('.') ]

def printError(text):
	sys.stderr.write('%s\n'%text)

class FallbackLogger:
	def __init__(self):
		pass
	def error(self, text):
		sys.stderr.write('ERROR: %s\n'%text)
	def warning(self, text):
		print('WARNING: %s'%text)
	def debug(self, text):
		print(text)

def myRaise(File=None):
	i = sys.exc_info()
	typ, value, tback = sys.exc_info()
	text = 'line %s: %s: %s\n'%(tback.tb_lineno, typ.__name__, value)
	if File:
		text = 'File "%s", '%File + text
	sys.stderr.write(text)

def myRaiseTback():
	import traceback
	typ, value, tback = sys.exc_info()
	sys.stderr.write("".join(traceback.format_exception(typ, value, tback)))

restartLow = lambda: os.execl(
	sys.executable,
	sys.executable,
	*sys.argv
)## will not return from the function

class StrOrderedDict(dict):
	## A dict from strings to objects, with ordered keys
	## and some looks like a list
	def __init__(self, arg=[], reorderOnModify=True):
		self.reorderOnModify = reorderOnModify
		if isinstance(arg, (list, tuple)):
			self.keyList = [item[0] for item in arg]
		elif isinstance(arg, dict):
			self.keyList = sorted(arg.keys())
		else:
			raise TypeError('StrOrderedDict: bad type for first argument: %s'%type(arg))
		dict.__init__(self, arg)
	keys = lambda self: self.keyList
	values = lambda self: [dict.__getitem__(self, key) for key in self.keyList]
	items = lambda self: [(key, dict.__getitem__(self, key)) for key in self.keyList]
	def __getitem__(self, arg):
		if isinstance(arg, int):
			return dict.__getitem__(self, self.keyList[arg])
		elif isinstance(arg, str):
			return dict.__getitem__(self, arg)
		elif isinstance(arg, slice):## not tested FIXME
			return StrOrderedDict([
				(key, dict.__getitem__(self, key)) \
				for key in self.keyList.__getitem__(arg)
			])
		else:
			raise ValueError('Bad type argument given to StrOrderedDict.__getitem__: %s'%type(arg))
	def __setitem__(self, arg, value):
		if isinstance(arg, int):
			dict.__setitem__(self, self.keyList[arg], value)
		elif isinstance(arg, str):
			if arg in self.keyList:## Modifying value for an existing key
				if reorderOnModify:
					self.keyList.remove(arg)
					self.keyList.append(arg)
			#elif isinstance(arg, slice):## ???????????? is not tested
			#	#assert isinstance(value, StrOrderedDict)
			#	if isinstance(value, StrOrderedDict):
			#		for key in self.keyList.__getitem__(arg):
			else:
				self.keyList.append(arg)
			dict.__setitem__(self, arg, value)
		else:
			raise ValueError('Bad type argument given to StrOrderedDict.__setitem__: %s'
				%type(item))
	def __delitem__(self, arg):
		if isinstance(arg, int):
			self.keyList.__delitem__(arg)
			dict.__delitem__(self, self.keyList[arg])
		elif isinstance(arg, str):
			self.keyList.remove(arg)
			dict.__delitem__(self, arg)
		elif isinstance(arg, slice):## ???????????? is not tested
			for key in self.keyList.__getitem__(arg):
				dict.__delitem__(self, key)
			self.keyList.__delitem__(arg)
		else:
			raise ValueError('Bad type argument given to StrOrderedDict.__delitem__: %s'%type(arg))
	pop = lambda self, key: self.__delitem__(key)
	def clear(self):
		self.keyList = []
		dict.clear(self)
	def append(self, key, value):
		assert isinstance(key, str) and not key in self.keyList
		self.keyList.append(key)
		dict.__setitem__(self, key, value)
	def insert(self, index, key, value):
		assert isinstance(key, str) and not key in self.keyList
		self.keyList.insert(index, key)
		dict.__setitem__(self, key, value)
	def sort(self, attr=None):
		if attr==None:
			self.keyList.sort()
		else:
			self.keyList.sort(key=lambda k: getattr(dict.__getitem__(self, k), attr))
	__iter__ = lambda self: self.keyList.__iter__()
	def iteritems(self):## OR lambda self: self.items().__iter__()
		for key in self.keyList:## OR self.keyList.__iter__()
			yield (key, dict.__getitem__(self, key))
	__str__ = lambda self: 'StrOrderedDict(%r)'%self.items()
	#'StrOrderedDict{' + ', '.join([repr(k)+':'+repr(self[k]) for k in self.keyList]) + '}'
	__repr__ = lambda self: 'StrOrderedDict(%r)'%self.items()


class NullObj:## a fully transparent object
	def __setattr__(self, attr, value):
		pass
	__getattr__ = lambda self, attr: self
	__call__ = lambda self, *args, **kwargs: self
	__str__ = lambda self: ''
	__repr__ = lambda self: ''
	__int__ = lambda self: 0


int_split = lambda s: [int(x) for x in s.split()]

s_join = lambda l: ' '.join([str(x) for x in l])


def cleanCacheDict(cache, maxSize, currentValue):
	n = len(cache)
	if n >= maxSize > 2:
		keys = sorted(cache.keys())
		if keys[n//2] < currentValue:
			rm = keys[0]
		else:
			rm = keys[-1]
		cache.pop(rm)

def urlToPath(url):
	if len(url)<7:
		return url
	if url[:7]!='file://':
		return url
	path = url[7:]
	if path[-2:]=='\r\n':
		path = path[:-2]
	elif path[-1]=='\r':
		path = path[:-1]
	## here convert html unicode symbols to utf8 string:
	if not '%' in path:
		return path
	path2 = ''
	n = len(path)
	i = 0
	while i<n:
		if path[i]=='%' and i<n-2:
			path2 += chr(int(path[i+1:i+3], 16)) ## OR chr(eval('0x%s'%path[i+1:i+3]))
			i += 3
		else:
			path2 += path[i]
			i += 1
	return path2

def findNearestNum(lst, num):
	if not lst:
		return
	best = lst[0]
	for x in lst[1:]:
		if abs(x-num) < abs(best-num):
			best = x
	return best

def findNearestIndex(lst, num):
	if not lst:
		return
	index = 0
	count = len(lst)
	for i in range(1, count):
		if abs(lst[i]-num) < abs(lst[index]-num):
			index = i
	return index

def strFindNth(st, sub, n):
	pos = 0
	for i in range(n):
		pos = st.find(sub, pos+1)
		if pos == -1:
			break
	return pos


def numRangesEncode(values):
	parts = []
	for value in values:
		if isinstance(value, int):
			parts.append(str(value))
		elif isinstance(value, (tuple, list)):
			parts.append('%d-%d'%(value[0], value[1]))
	return ', '.join(parts)

def numRangesDecode(text):
	values = []
	for part in text.split(','):
		pparts = part.strip().split('-')
		try:
			if len(pparts)==1:
				values.append(int(pparts[0]))
			elif len(pparts) > 1:
				values.append((
					int(pparts[0]),
					int(pparts[1]),
				))
		except:
			myRaise()
	return values

def inputDate(msg):
	while True:
		try:
			date = input(msg)
		except KeyboardInterrupt:
			return
		if date.lower() == 'q':
			return
		try:
			return dateDecode(date)
		except Exception as e:
			print(str(e))

def inputDateJd(msg):
	date = inputDate(msg)
	if date:
		y, m, d = date
		return to_jd(y, m, d, DATE_GREG)


#if __name__=='__main__':
#	print(findNearestNum([1, 2, 4, 6, 3, 7], 3.6))



