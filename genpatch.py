import sys
import re

from base import *
from configparser import *
from patcher import *



class InputArgs( BaseObject ):
	def __init__( self ):
		self.configPath = None
		self.debugMode = 'info'
		self.customer = None
		self.version = None
		self.bugs = None
		self.timeTag = None
		self.outDir = None

	def parse_argv( self, argv ):
		idx = 1
		size = len(argv)
		while idx < size:
			if idx >= size:
				logging.error( 'invalid input arguments' )
				self.__print_usage()
				return False
			arg = argv[ idx ]
			if arg == '-x':
				self.configPath = argv[ idx+1 ]
				idx += 2
			elif arg == '-d':
				self.debugMode = argv[idx+1]
				idx += 2
			elif arg == '-c':
				self.customer = argv[idx+1]
				idx += 2
			elif arg == '-v':
				self.version= argv[idx+1]
				idx += 2
			elif arg == '-o':
				self.outDir= argv[idx+1]
				idx += 2
			elif arg == '-b':
				self.bugs= argv[idx+1]
				idx += 2
			elif arg == '-t':
				self.timeTag= argv[idx+1]
				idx += 2
			else:
				idx += 2

		if not self.__check_arguments():
			logging.error( 'invalid input arguments' )
			self.__print_usage()
			return False

		return True

	def __check_arguments( self ):
		if not self.configPath:
			logging.error( 'config file must be set' )
			return False

		if not self.outDir:
			logging.error( 'output directory must be set' )
			return False

		if not self.customer:
			logging.error( 'customer must be set' )
			return False

		if not self.version:
			logging.error( 'version must be set' )
			return False
		else:
			if not self.__check_version( self.version ):
				return False

		if not self.bugs:
			logging.error( 'bugs must be set' )
			return False

		return True

	def __check_version( self, version ):
		pt = r'\d(\.\d)+b\d'
		res =  re.match( pt, version )

		if not res:
			logging.error( 'version format must be like: 3.1.2b60, not:'+version )
			return False
		return True

						
	def __print_usage( self ):
		print 'Usage:'
		print '\tpython', sys.argv[0], '-x <config file> -o <out dir> -c customer -v <version> -b <bug list> [-d <debug level> -t <patch tag>]' 


def set_debug_mode( mode ):
	level = logging.INFO
	if mode == 'debug':
		level = logging.DEBUG
	elif mode == 'info':
		level = logging.INFO
	elif mode == 'warn':
		level = logging.WARN
	elif mode == 'warning':
		level = logging.WARNING
	elif mode == 'error':
		level = logging.ERROR
	elif mode == 'critical':
		level = logging.CRITICAL

	init_logging( level )

def main():
	check_version()
	iargs = InputArgs()
	if not iargs.parse_argv( sys.argv ):
		return False
	
	set_debug_mode( iargs.debugMode )
	logging.info( 'args:'+str(iargs) )

	cparser = ConfigParser()
	plist = cparser.parse_config( iargs.configPath )
	if not plist:
		logging.error( 'parse config file failed' )
		return

	patcher = plist[0]
	iargs.copy_object( patcher )
	if not patcher.init_config():
		logging.error( 'init config failed' )
		return
	patcher.generate()
	

if __name__ == '__main__':
	main()
