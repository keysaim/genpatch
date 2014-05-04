import sys

from base import *



class InputArgs( BaseObject ):
	def __init__( self ):
		self.configPath = None
		self.debugMode = 'info'

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
		print '\tmain.py -x <config file> [-d <debug level>]' 


def set_debug_mode( self, mode ):
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

if __name__ == '__main__':
	main()
