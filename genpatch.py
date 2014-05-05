import sys

from base import *
from configparser import *
from patcher import *



class InputArgs( BaseObject ):
	def __init__( self ):
		self.configPath = None
		self.debugMode = 'info'
		self.customer = ''
		self.version = ''
		self.bugs = ''
		self.timeTag = None
		self.outDir = './'

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

		if not self.configPath:
			logging.error( 'invalid input arguments' )
			logging.error( 'config file must be setted\n' )
			self.__print_usage()
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
