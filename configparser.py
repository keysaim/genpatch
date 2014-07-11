import logging

from base import *
from patcher import *


class ConfigParser( BaseObject ):
	def __init__( self ):
		pass

	def parse_config( self, configFile ):
		patcherList = list()
		doc = minidom.parse( configFile )
		root = doc.documentElement
		if root:
			cnode = root
			name = cnode.nodeName
			if name == 'patch':
				patcher = self.__parse_patch( cnode )
				if patcher is not None:
					patcherList.append( patcher )

		return patcherList

	def __parse_patch( self, node ):
		logging.debug( 'parse patch element...' )
		patcher = Patcher()
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'services':
				patcher.serviceBlock = self.__parse_services( cnode, patcher )
				logging.debug( 'one service block parsed:'+str(patcher.serviceBlock) )
			elif name == 'component':
				comp = self.__parse_component( cnode, node )
				logging.debug( 'one component parsed:'+str(comp) )
				patcher.add_component( comp )
			elif name == 'reload':
				value = get_node_value( cnode )
				if value == 'true':
					patcher.needReload = True
				else:
					patcher.needReload = False
				logging.debug( "parsed reload node:"+value )
			elif name == 'warn':
				value = get_node_value( cnode )
				patcher.warn = value
				logging.debug( "parsed warn node:"+value )

		return patcher

	def __parse_services( self, node, parent ):
		sblock = ServiceBlock()

		#parse the common config
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'waitTime':
				sblock.waitTime = int( get_node_value(cnode) )

		#parse the services
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'service':
				service = self.__parse_service( cnode, sblock )
				sblock.add_service( service )
			elif name == 'process':
				process = self.__parse_process( cnode, sblock )
				sblock.add_process( process )

		if not sblock.is_empty():
			return sblock
		return None

	def __parse_service( self, node, parent ):
		service = Service( parent )

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'name':
				service.name = get_node_value( cnode )
			elif name == 'process':
				process = get_node_value( cnode )
				service.add_process( process, False )
			elif name == 'processgrep':
				process = get_node_value( cnode )
				service.add_process( process, True )
			elif name == 'check':
				service.check = self.__parse_svc_check( cnode, node )

		logging.debug( 'parsed one service:'+str(service) )
		return service

	def __parse_svc_check( self, node, parent ):
		check = ServiceCheck( parent )

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'cli':
				check.cli = get_node_value( cnode )
			elif name == 'enable':
				check.enable = get_node_value( cnode )
			elif name == 'disable':
				check.disable = get_node_value( cnode )
		
		logging.debug( 'parsed one service check:'+str(check) )
		return check

	def __parse_process( self, node, parent ):
		process = Process( parent )

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'name':
				process.name = get_node_value( cnode )
			elif name == 'start':
				process.startCmd = get_node_value( cnode )
			elif name == 'stop':
				process.stopCmd = get_node_value( cnode )

		logging.debug( 'parsed one process:'+str(process) )
		return process

	def __parse_component( self, node, parent ):
		comp = Component(parent)

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'name':
				comp.name = get_node_value( cnode )
			elif name == 'device':
				dstr = get_node_value( cnode ).lower().strip()
				comp.deviceList = list()
				for seg in dstr.split( ',' ):
					de = seg.strip()
					if de:
						comp.deviceList.append( de )
				if not comp.deviceList:
					comp.deviceList = None

			elif name == 'bins':
				comp.binBlock = self.__parse_bins( cnode, comp )
			elif name == 'libs':
				comp.libBlock = self.__parse_libs( cnode, comp )
			elif name == 'services':
				comp.serviceBlock = self.__parse_services( cnode, comp )
		
		logging.debug( 'parsed one component:'+str(comp) )
		return comp

	def __parse_bins( self, node, parent ):
		bblock = BinBlock(parent)

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'defSrcDir':
				bblock.defSrcDir = get_node_value( cnode )
			elif name == 'defDstDir':
				bblock.defDstDir = get_node_value( cnode )

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'bin':
				binary = self.__parse_binary( cnode, bblock )
				bblock.add_binary( binary )

		logging.debug( 'parsed one binary block:'+str(bblock) )
		return bblock

	def __parse_binary( self, node, parent ):
		binary = Binary( parent )

		self.__parse_file( binary, node )
		logging.debug( 'parsed one binary:'+str(binary) )
		return binary

	def __parse_file( self, bfile, node ):
		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'src':
				bfile.src = get_node_value( cnode )
			elif name == 'dst':
				bfile.dst = get_node_value( cnode )
			elif name == 'dstfile':
				bfile.dstfile = get_node_value( cnode )
			elif name == 'type':
				bfile.itype = get_node_value( cnode )


	def __parse_libs( self, node, parent ):
		lblock = LibBlock(parent)

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'defSrcDir':
				lblock.defSrcDir = get_node_value( cnode )
			elif name == 'defDstDir':
				lblock.defDstDir = get_node_value( cnode )

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'lib':
				library = self.__parse_binary( cnode, lblock )
				lblock.add_binary( library )

		logging.debug( 'parsed one library block:'+str(lblock) )
		return lblock

	def __parse_library( self, node, parent ):
		lib = Library( parent )

		self.__parse_file( lib, node )
		logging.debug( 'parsed one library:'+str(lib) )
		return lib

		
