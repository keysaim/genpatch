import logging
import os

from base import *



class Patcher( BaseObject ):
	def __init__( self ):
		self.serviceBlock = None
		self.compList = list()

	def add_component( self, comp ):
		self.compList.append( comp )

	def init( self ):
		if self.serviceBlock:
			slist = list()
			for service in self.serviceBlock:
				if service.init( self ):
					slist.append( service)
				else:
					logging.error( 'invalid service:'+str(service) )

			self.serviceBlock = slist

		clist = list()
		for comp in self.compList:
			if comp.init( self ):
				clist.append( comp )
			else:
				logging.error( 'invalid component:'+str(comp) )

		self.compList = clist
		return len(self.compList) > 0


class Service( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.waitTime = parent.waitTime
		self.processList = None

	def add_process( self, process ):
		if self.processList is None:
			self.processList = list()

		self.processList.append( process )

	def init( parent ):
		if self.name is None:
			logging.error( 'servie name not set' )
			return False

		return True


class Process( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.startCmd = None
		self.stopCmd = None

	def init( self, parent ):
		if self.name is None:
			logging.error( 'process name not set' )
			return False

		if self.startCmd is None:
			logging.error( 'startCmd not set' )
			return False

		if self.stopCmd is None:
			self.stopCmd = 'kill -9'

		return True

class ServiceBlock( BaseObject ):
	def __init__( self ):
		self.services = list()
		self.waitTime = 10	#seconds

	def is_empty( self ):
		return len(self.services) == 0

	def add_service( self, service ):
		self.services.append( (service, True) )

	def add_process( self, process ):
		self.services.append( (process, False) )

	def init( self, parent ):
		slist = list()
		for (service, isSer) in self.services:
			if service.init(self):
				slist.append( (service, isSer) )
			else:
				logging.error( 'invalid service'+str(service) )

		self.services = slist
		return len(self.services) > 0


class Binary( BaseObject ):
	def __init__( self, parent ):
		self.src = None
		self.dst = None


class BinBlock( BaseObject ):
	def __init__( self, parent ):
		self.defSrcDir = None
		self.defDstDir = None
		self.binList = list()

	def add_binary( self, binary ):
		self.binList.append( binary )

	def init( self, parent ):
		if self.defSrcDir is None:
			self.defSrcDir = '/sw/unicorn/bin'
		if self.defDstDir is None:
			self.defDstDir = '/sw/unicorn/bin'

		bmap = dict()
		for binary in self.binList:
			pass

	def __init_bin( self, bmap, binary ):
		src = binary.src
		if src is None or len(src) == 0:
			return False

		dst = binary.dst
		if dst is None:
			dst = self.defDstDir

		if os.path.exists( src ):
			if os.path.isfile(src):
				bname = os.path.basename( src )
				if os.path.isdir(dst):
					dst = os.path.join( dst, bname )
				binary.src = src
				binary.dst = dst
				bmap[dst] = binary
			else:
				#include many files here
				for fname in os.listdir(src):
					fpath = os.path.join( src, fname )
					if os.path.isdir(fpath):
						continue
					
					cdst = dst
					if os.path.isdir(cdst):

		else:
			pass


class Library( BaseObject ):
	def __init__( self, parent ):
		self.src = None


class LibBlock( BaseObject ):
	def __init__( self, parent ):
		self.defSrcDir = None
		self.defDstDir = None
		self.libList = list()

	def add_libray( self, library ):
		self.libList.append( library )


class Component( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.serviceBlock = None
		self.binBlock = None
		self.libBlock = None

