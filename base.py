#*********************************************************************************************#
#*********************************************************************************************#
#******************witten by Neil Hao(nbaoping@cisco.com), 2014/04/25*************************#
#*********************************************************************************************#
#*********************************************************************************************#
#*********************************************************************************************#

from datetime import datetime
from datetime import timedelta
import os
import sys
import inspect
from  xml.dom import  minidom
import traceback
import logging

import recipe

NEW_VERSION = True

RES_DIR = 'output'

LOGGING_FORMAT = '%(asctime)s %(levelname)5s: %(filename)s:%(lineno)s[%(funcName)s]-> %(message)s'
__TIME_FMT = '%Y/%m/%d-%H:%M:%S'
__START_TIME = datetime( 1970, 1, 1 )

def init_logging( level=logging.INFO ):
	logging.basicConfig( level=level, format=LOGGING_FORMAT )

def is_new_version( ):
	return NEW_VERSION

def check_version():
	global NEW_VERSION
	global LOGGING_FORMAT

	if not sys.version.startswith( '2.7' ):
		NEW_VERSION = False
		#for old version, the funcName may not support
		LOGGING_FORMAT = '%(asctime)s %(levelname)5s: %(filename)s:%(lineno)s-> %(message)s'

def std_fmt_name( fmtName ):
	if fmtName.startswith( '$' ):
		nstr = fmtName[1:len(fmtName)]
		if nstr[0] == '-':
			nstr = nstr.replace( '-', '_' )
		fmtName = '_commonVal' + nstr
	return fmtName

def form_common_fmt_name( num ):
	nstr = str(num)
	if num < 0:
		nstr = nstr.replace( '-', '_' )
	fmtName = '_commonVal' + nstr
	return fmtName

def is_common_fmt_name( fmtName ):
	return fmtName.startswith( '_commonVal' )

def strptime( tstr, fmt ):
	if NEW_VERSION:
		return datetime.strptime( tstr, fmt )
	else:
		time = recipe.strptime( tstr, fmt )
		dtime = datetime( time[0], time[1], time[2], time[3], time[4], time[5] )
		return dtime

def total_seconds( dtime ):
	delta = dtime - __START_TIME
	if NEW_VERSION:
		return delta.total_seconds()
	else:
		return delta.seconds + delta.days*24*3600

def to_datetime( seconds ):
	return __START_TIME + timedelta( 0, seconds )

def delta_time( dtime1, dtime2 ):
	delta = dtime2 - dtime1
	return delta.total_seconds()

def str_time( dtime, fmt=__TIME_FMT ):
	return datetime.strftime( dtime, fmt )

def time_str( tstr, fmt=__TIME_FMT ):
	return strptime( tstr, fmt )

def seconds_str( tstr, fmt=__TIME_FMT ):
	dtime = strptime( tstr, fmt )
	return total_seconds( dtime )

def str_seconds( seconds, fmt=__TIME_FMT ):
	dtime = to_datetime( seconds )
	return str_time( dtime, fmt )

def cur_timestr( ):
	now = datetime.now()
	return str_time( now )

def mkdir( dname ):
	try:
		if not os.path.exists( dname ):
			os.makedirs( dname )
		return True
	except:
		logging.error( '\n'+traceback.format_exc() )
		logging.error( 'create directory:'+dname+' failed' )
		return False

def splitall(path):
	allparts = []
	while 1:
		parts = os.path.split(path)
		if parts[0] == path:  # sentinel for absolute paths
			allparts.insert(0, parts[0])
			break
		elif parts[1] == path: # sentinel for relative paths
			allparts.insert(0, parts[1])
			break
		else:
			path = parts[0]
			allparts.insert(0, parts[1])
	return allparts

def func_name():
	return inspect.stack()[1][3]

def raise_virtual( func ):
	raise Exception( 'derived must implement '+func+' virtual function' )

def has_attr(node, attrname):
	return node.hasAttribute( attrname )

def get_attr_value(node, attrname):
     return node.getAttribute(attrname).encode('utf-8','ignore')

def get_node_value(node, index = 0):
    return node.childNodes[index].nodeValue.encode('utf-8','ignore')

def get_xml_node(node, name):
    return node.getElementsByTagName(name)

class BaseObject( object ):
	def __init__( self ):
		pass

	def set_member( self, mname, value ):
		self.__dict__[mname] = value

	def get_member( self, mname ):
		return self.__dict__[mname]

	def exist( self, member ):
		return member in self.__dict__

	def exist_member( self, mname ):
		return mname in self.__dict__

	def copy_object( self, obj ):
		for mname in self.__dict__.keys():
			value = self.__dict__[mname]
			obj.set_member( mname, value )

	def __str__( self ):
		return str( self.__dict__ ) + '\t' + str( type(self) )


