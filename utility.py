#!/usr/bin/env python

import ConfigParser


def dump(obj):
    objList = []
    for attr in dir(obj):
        objList.append( 'obj.%s : %s'.format(attr, obj[attr]))
    return '\n'.join(objList)


def configSectionMap(conf, section):
    dict = {}
    config = ConfigParser.ConfigParser()
    config.read(conf)
    options = config.options(section)

    for option in options:
        try:
            dict[option] = config.get(section, option)
        except ConfigParser.Error as e:
            print e
            dict[option] = None
    return dict
 
