#!/usr/bin/python

import os
import os.path
from collections import OrderedDict

import _winreg as wreg


'''
def _addZoneNode(parentDict, zone, zoneNamesLevel):
    path = '/' + os.path.join(*tuple(infoDirL + zone))
    name = zone[-1]
    zoneNamesLevel[len(zone)].append(name)
    if os.path.isfile(path):
        parentDict[name] = ''
    elif os.path.isdir(path):
        parentDict[name] = OrderedDict()
        for chName in sorted(os.listdir(path)):
            _addZoneNode(
                parentDict[name],
                zone + [chName],
                zoneNamesLevel,
            )
    else:
        print('invalid path =', path)


def getZoneInfoTree():
    zoneTree = OrderedDict()
    zoneNamesLevel = [[] for i in range(4)]
    for group in [
        'Etc',
        'Africa',
        'America',
        'Antarctica',
        'Arctic',
        'Asia',
        'Atlantic',
        'Australia',
        'Brazil',
        'Canada',
        'Chile',
        'Europe',
        'Indian',
        'Mexico',
        'Mideast',
        'Pacific',
    ]:
        _addZoneNode(
            zoneTree,
            [group],
            zoneNamesLevel,
        )
    #zoneNamesList = []
    #for levelNames in zoneNamesLevel:
    #    zoneNamesList += sorted(levelNames)
    #from pprint import pprint ; pprint(zoneTree)
    return zoneTree
'''


def getSubKeys(key):
    i = 0
    while True:
        try:
            asubkey_name = wreg.EnumKey(key, i)
        except WindowsError:
            break
        else:
            subkey = wreg.OpenKey(key, asubkey_name)
            yield subkey
            i += 1


def getZoneInfoTree():
    aReg = wreg.ConnectRegistry(None, wreg.HKEY_LOCAL_MACHINE)
    rootKey = wreg.OpenKey(aReg, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones')
    for subkey in getSubKeys(rootKey):
        tz_display = wreg.QueryValueEx(subkey, 'Display')[0]
        tz_std = wreg.QueryValueEx(subkey, 'Std')[0]
        tz_dst = wreg.QueryValueEx(subkey, 'Dlt')[0]
        print tz_display, tz_std, tz_dst
        




if __name__=='__main__':
    getZoneInfoTree()




