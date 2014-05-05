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
				patcher.serviceBlock = self.__parse_services( cnode )
				logging.debug( 'one service block parsed:'+str(patcher.serviceBlock) )
			elif name == 'component':
				comp = self.__parse_component( cnode, node )
				logging.debug( 'one component parsed:'+str(comp) )
				patcher.add_component( comp )

		return patcher

	def __parse_services( self, node ):
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
				service.add_process( process )

		logging.debug( 'parsed one service:'+str(service) )
		return service

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
			elif name == 'bins':
				comp.binBlock = self.__parse_bins( cnode, comp )
			elif name == 'libs':
				comp.libBlock = self.__parse_libs( cnode, comp )
			elif name == 'services':
				comp.serviceBlock = self.__parse_services( self, comp )
		
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

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'src':
				binary.src = get_node_value( cnode )
			elif name == 'dst':
				binary.dst = get_node_value( cnode )

		logging.debug( 'parsed one binary:'+str(binary) )
		return binary

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

		for cnode in node.childNodes:
			name = cnode.nodeName
			if name == 'src':
				lib.src = get_node_value( cnode )
			elif name == 'dst':
				lib.dst = get_node_value( cnode )

		logging.debug( 'parsed one library:'+str(lib) )
		return lib

		
