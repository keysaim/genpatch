import logging
import os
import shutil

from base import *

STRICT_PARSE = True

def format_device_name( deviceList ):
	if deviceList:
		nlist = list()
		for de in deviceList:
			if de == 'se':
				de = 'service-engine'
			elif de == 'sr':
				de = 'service-router'
			elif de == 'cdsm':
				de = 'content-delivery-system-manager'
			nlist.append( de )
			return nlist
	
	return None

def gen_md5sum_value( spath ):
	cmd = 'md5sum ' + spath
	logging.debug( 'popen cmd:'+cmd )
	fin = os.popen( cmd, 'r' )
	md5sum = ''
	for line in fin:
		logging.debug( line )
		segs = line.split()
		md5sum = segs[0]
		break
	fin.close()
	return md5sum

def gen_check_version_func( fout ):
	lines  = 'function check_version() {\n'
	lines += '	local target_version="$1"\n'
	lines += '	cds_version=$(/ruby/bin/exec -c "show version" | grep "Content Delivery System Software Release" | awk \'{ print $6$8 }\')\n'
	lines += '	if [[ "$cds_version" = "$target_version" ]]; then\n'
	lines += '		echo "Current cds-is version $cds_version"\n'
	lines += '		return 0\n'
	lines += '	else\n'
	lines += '		echo "Patch is only applied to cds-is $target_version (but current is $cds_version), aborting."\n'
	lines += '		return 23\n'
	lines += '	fi\n'
	lines += '}\n'
	lines += '	\n'
	fout.write( lines )

def gen_mount_sw( fout, lhead, perm, sleepTime=10 ):
	lines  = lhead + 'mount -n -o remount,' + perm + ' /sw\n'
	lines += lhead + 'if [ $? -ne 0 ]; then\n'
	lines += lhead + '	echo "ERROR: unable to remount partition as ' + perm + ' mode"\n'
	lines += lhead + '	echo "Please try the patch later or reload the device and retry."\n'
	lines += lhead + '	exit 28\n'
	lines += lhead + 'fi\n'
	lines += lhead + 'sleep ' + str(sleepTime) + '\n'
	fout.write( lines )


def __gen_stop_service_func( self, fout ):
	lines = 'function stop_service(){\n'
	lines += '	##### check and stop\n'
	lines += '	local tarsvc="$1"\n'
	lines += '	local tarproc="$2"\n'
	lines += '	local stime=$3\n'
	lines += '	echo "stopping service $tarsvc..."\n'
	lines += '	/ruby/bin/nodemgr_clt stop $tarsvc\n'
	lines += '	sleep $stime\n\n'
	lines += '	pidof $tarproc > /dev/null\n'
	lines += '	pidof_rc=$?\n'
	lines += '	if [ $pidof_rc -eq 0 ]; then\n'
	lines += '		echo "ERROR: process $tarproc not stopped"\n'
	lines += '		echo "please check the $tarproc process and retry the patch later."\n'
	lines += '		echo "exit 25"\n'
	lines += '	else\n'
	lines += '		echo "process stopped, go on..."\n'
	lines += '	fi\n'
	lines += '}\n'

	fout.write( lines )


def __gen_start_service_func( self, fout ):
	lines = 'function start_service(){\n'
	lines += '	##### check and start\n'
	lines += '	local tarsvc="$1"\n'
	lines += '	local tarproc="$2"\n'
	lines += '	local stime=$3\n'
	lines += '	echo "starting service $tarsvc..."\n'
	lines += '	/ruby/bin/nodemgr_clt start $tarsvc\n'
	lines += '	sleep $stime\n\n'
	lines += '	pidof $tarproc > /dev/null\n'
	lines += '	pidof_rc=$?\n'
	lines += '	if [ $pidof_rc -eq 0 ]; then\n'
	lines += '		echo "process restarted, patching succeeded on this."\n'
	lines += '	else\n'
	lines += '		echo "ERROR: process $tarproc restarting failed"\n'
	lines += '		echo "please revert the patch and check the $tarproc process"\n'
	lines += '		echo "exit 26"\n'
	lines += '	fi\n'
	lines += '}\n'

	fout.write( lines )

def gen_check_device_mode_func( fout, lhead ):
	lines  = lhead + 'function check_device_mode() {\n'
	lines += lhead + '	local setMode="$1"\n'
	lines += lhead + '    local device_mode=$(/ruby/bin/exec -c "show device-mode current" | grep mode | awk \'{ print $4 }\')\n'
	lines += lhead + '    if [[ "$device_mode" = "$setMode" ]]; then\n'
	lines += lhead + '        echo "Current device mode $device_mode"\n'
	lines += lhead + '	  		return 1	\n'
	lines += lhead + '    else\n'
	lines += lhead + '        #echo "Patch is not allowed to install in $device_mode"\n'
	lines += lhead + '        return 0\n'
	lines += lhead + '    fi\n'
	lines += lhead + '}\n'
	
	fout.write( lines )
	
def gen_check_device_mode( fout, lhead, deviceList ):
	if not deviceList:
		return
	lines  = ''
	lines += lhead + 'echo ""\n'
	lines += lhead + 'local isRightMode=0\n'
	lines += lhead + 'local allowMode=0\n'
	lines += lhead + 'echo "checking device mode, allowed:' + str(deviceList) + '"\n'
	for de in deviceList:
		lines += lhead + 'if [ $isRightMode -eq 0 ]; then\n'
		lines += lhead + '	check_device_mode "' + de + '"\n'
		lines += lhead + '	isRightMode=$?\n'
		lines += lhead + '	if [ $isRightMode -eq 1 ]; then\n'
		lines += lhead + '		echo "patch will install for ' + de + '"\n'
		lines += lhead + '		allowMode=1\n'
		lines += lhead + '	fi\n'	
		lines += lhead + 'fi\n'	

	lines += lhead + 'if [ $allowMode -eq 0 ]; then\n'
	lines += lhead + '	echo "patch is not allowed for this device mode"\n'
	lines += lhead + '	/ruby/bin/exec -c "show device-mode current"\n'
	lines += lhead + '	exit 44\n'
	lines += lhead + 'fi\n'
	fout.write( lines )
	
def gen_check_service_func( fout, lhead ):
	lines  = lhead + 'function check_service(){\n'
	lines += lhead + '	local cmd="$1"\n'
	lines += lhead + '	local gstr="$2"\n'
	lines += lhead + '	ret=`/sw/merlot/bin/runExecCLI $cmd | grep "$gstr"`\n'
	lines += lhead + '	echo "$ret"\n'
	lines += lhead + '	if [ -z "$ret" ]; then\n'
	lines += lhead + '		return 0\n'
	lines += lhead + '	else\n'
	lines += lhead + '		return 1\n'
	lines += lhead + '	fi\n'
	lines += lhead + '}\n\n'

	fout.write( lines )

def gen_check_proc_started( fout, lhead, proc, isKeyword, svc=None ):
	lines = ''
	if isKeyword:
		lines += lhead + 'ret=`ps aux | grep "' + proc + '" | grep -v "grep"`\n'
	else:
		lines += lhead + 'ret=`pidof ' + proc + '`\n'
	lines += lhead + 'if [ -z "$ret" ]; then\n'
	if svc:
		lines += lhead + '	echo "ERROR: ' + proc + ' retarting failed in service:' + svc + ' with ret:$ret"\n'
	else:
		lines += lhead + '	echo "ERROR: ' + proc + ' retarting failed with ret:$ret"\n'
	lines += lhead + '	echo "Please run patch revert and then check the ' + proc + ' proccess."\n'
	lines += lhead + '	exit 26\n'
	lines += lhead + 'else\n'
	lines += lhead + '	echo "Process ' + proc + ' started, go on..."\n'
	lines += lhead + 'fi\n\n'
	fout.write( lines )

def gen_check_proc_stopped( fout, lhead, proc, isKeyword, svc=None ):
	lines = ''
	if isKeyword:
		lines += lhead + 'ret=`ps aux | grep "' + proc + '" | grep -v "grep"`\n'
	else:
		lines += lhead + 'ret=`pidof ' + proc + '`\n'
	lines += lhead + 'if [ -z "$ret" ]; then\n'
	lines += lhead + '	echo "Process ' + proc + ' stopped, go on..."\n'
	lines += lhead + 'else\n'
	if svc:
		lines += lhead + '	echo "ERROR: ' + proc + ' stopping failed in service:' + svc + ' with ret:$ret"\n'
	else:
		lines += lhead + '	echo "ERROR: ' + proc + ' stopping failed with ret:$ret"\n'
	lines += lhead + '	echo "Please check the ' + proc + ' process and retry the patch later."\n'
	lines += lhead + '	exit 25\n'
	lines += lhead + 'fi\n\n'
	fout.write( lines )

class ServiceCheck( BaseObject ):
	def __init__( self, parent ):
		self.cli = None
		self.enable = None
		self.disable = None
	
	def init_config( self, parent ):
		if not self.cli:
			return False

		if not self.enale and not self.disable:
			return False

		return True


class Service( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.waitTime = parent.waitTime
		self.processList = None
		self.check = None

	def add_process( self, process, isKeyword, checkType ):
		if self.processList is None:
			self.processList = list()

		self.processList.append( (process, isKeyword, checkType) )

	def init_config( self, parent ):
		if self.name is None:
			logging.error( 'servie name not set' )
			return False

		return True

	def gen_start( self, fout, lhead ):
		lines = ''
		if self.check:
			lines += lhead + 'if [ $' + self.name + '_enable -eq 1 ]; then\n'
			lines += lhead + 'echo "starting service:' + self.name + '..."\n'
			lines += lhead + '	/ruby/bin/nodemgr_clt start ' + self.name + '\n'
			lines += lhead + 'fi\n'
		else:
			lines += lhead + 'echo "starting service:' + self.name + '..."\n'
			lines += lhead + '/ruby/bin/nodemgr_clt start ' + self.name + '\n'
		fout.write( lines )

	def gen_check_service( self, fout, lhead ):
		lines = ''
		if self.check:
			lines += lhead + 'echo "check service:' + self.name + '"...\n'
			cstr = self.check.enable
			if not cstr:
				cstr = self.check.disable
			lines += lhead + 'check_service "' + self.check.cli + '" "' + cstr + '"\n'
			if self.check.enable:
				lines += lhead + self.name + '_enable=$?\n'
			else:
				lines += lhead + self.name + '_enable=$((1-$?))\n'
			lines += lhead + 'if [ $' + self.name + '_enable -eq 1 ]; then\n'
			lines += lhead + '	echo "' + self.name + ' is enabled"\n'
			lines += lhead + 'else\n'
			lines += lhead + '	echo "' + self.name + ' is disabled"\n'
			lines += lhead + 'fi\n'

		fout.write( lines )

	def gen_stop( self, fout, lhead ):
		lines  = ''
		lines += lhead + 'echo "stopping service:' + self.name + '..."\n'
		lines += lhead + '/ruby/bin/nodemgr_clt stop ' + self.name + '\n'
		fout.write( lines )

	def gen_check_started( self, fout, lhead, cmdType ):
		if not self.processList:
			return
		
		ihead = lhead
		if self.check:
			lines = lhead + 'if [ $' + self.name + '_enable -eq 1 ]; then\n'
			fout.write( lines )
			ihead += '\t'

		checkCmd = 'apply'
		if cmdType == 'apply':
			checkCmd = 'revert'
		for (proc, isKeyword, checkType) in self.processList:
			if checkType.find('stop') < 0 and checkType.find(checkCmd) < 0:
				gen_check_proc_started( fout, ihead, proc, isKeyword, self.name )

		if self.check:
			lines = lhead + 'fi\n'
			fout.write( lines )

	def gen_check_stopped( self, fout, lhead, cmdType ):
		if not self.processList:
			return
		checkCmd = 'apply'
		if cmdType == 'apply':
			checkCmd = 'revert'
		for (proc, isKeyword, checkType) in self.processList:
			if checkType.find('start') < 0 and checkType.find(checkCmd) < 0:
				gen_check_proc_stopped( fout, lhead, proc, isKeyword, self.name )


class Process( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.startCmd = None
		self.stopCmd = None

	def init_config( self, parent ):
		if self.name is None:
			logging.error( 'process name not set' )
			return False

		if self.startCmd is None:
			logging.error( 'startCmd not set' )
			return False

		if self.stopCmd is None:
			self.stopCmd = 'kill -9 ' + self.name

		return True

	def gen_start( self, fout, lhead ):
		lines  = lhead + self.startCmd + '\n'
		fout.write( lines )

	def gen_check_service( self, fout, lhead ):
		pass

	def gen_stop( self, fout, lhead ):
		lines  = lhead + self.stopCmd + '\n'
		fout.write( lines )

	def gen_check_started( self, fout, lhead ):
		gen_check_proc_started( fout, lhead, self.name, False )

	def gen_check_stopped( self, fout, lhead ):
		gen_check_proc_stopped( fout, lhead, self.name, False )


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

	def init_config( self, parent ):
		slist = list()
		for (service, isSer) in self.services:
			if service.init_config(self):
				slist.append( (service, isSer) )
				logging.debug( 'inited one service:'+str(service) )
			else:
				logging.error( 'invalid service'+str(service) )
				if STRICT_PARSE:
					return False

		self.services = slist
		return len(self.services) > 0

	def gen_start( self, fout, lhead, cmdType ):
		lines = lhead + 'echo "try starting services..."\n'
		fout.write( lines )
		idx = len(self.services) - 1
		while idx >= 0:
			(service, isSer) = self.services[idx]
			idx -= 1
			service.gen_start( fout, lhead )

		lines  = lhead + 'sleep ' + str(self.waitTime) + '\n'
		lines += lhead + 'echo ""\n'
		lines += lhead + 'echo ""\n'
		lines += lhead + 'echo "checking if services started..."\n'
		fout.write( lines )

		idx = len(self.services) - 1
		while idx >= 0:
			(service, isSer) = self.services[idx]
			idx -= 1
			service.gen_check_started( fout, lhead, cmdType )
	
	def gen_stop( self, fout, lhead, cmdType ):
		for (service, isSer) in self.services:
			service.gen_check_service( fout, lhead )

		lines = lhead + 'echo "try stopping services..."\n'
		fout.write( lines )
		for (service, isSer) in self.services:
			service.gen_stop( fout, lhead )

		lines  = lhead + 'sleep ' + str(self.waitTime) + '\n'
		lines += lhead + 'echo ""\n'
		lines += lhead + 'echo ""\n'
		lines += lhead + 'echo "checking if services stopped..."\n'
		fout.write( lines )

		for (service, isSer) in self.services:
			service.gen_check_stopped( fout, lhead, cmdType )


class Binary( BaseObject ):
	def __init__( self, parent ):
		self.src = None
		self.dst = None
		self.dstfile = None
		self.itype = None


class BinBlock( BaseObject ):
	def __init__( self, parent, defSrcDir=None, defDstDir=None ):
		self.defSrcDir = defSrcDir
		self.defDstDir = defDstDir
		self.binList = list()
		self.isInSW = False
		self.specialList = None

	def add_binary( self, binary ):
		self.binList.append( binary )

	def init_config( self, parent ):
		if self.defSrcDir is None:
			self.defSrcDir = '/sw/unicorn/bin'
		if self.defDstDir is None:
			self.defDstDir = '/sw/unicorn/bin'

		bmap = dict()
		for binary in self.binList:
			if not self.__init_bin( bmap, binary ):
				if STRICT_PARSE:
					return False

		self.binList = bmap.values()
		if not self.binList or len(self.binList) == 0:
			logging.error( 'no available binary set in this block:'+str(self) )
			return False

		#check if is in /sw
		for binary in self.binList:
			dst = binary.dst
			if dst.startswith( '/sw' ):
				self.isInSW = True
				break

		return True

	def __init_bin( self, bmap, binary ):
		src = binary.src
		if src is None or len(src) == 0:
			return False

		dst = binary.dst

		#if indicate the source files
		if os.path.exists( src ):
			if os.path.isfile(src):
				if dst is None:
					dst = self.defDstDir

				bname = os.path.basename( src )
				if binary.dstfile:
					dst = binary.dstfile
				else:
					dst = os.path.join( dst, bname )
				binary.src = src
				binary.dst = dst
				bmap[dst] = binary
				logging.debug( 'inited one binary:'+str(binary) )
			else:
				if dst is None:
					logging.error( 'you must set the dst element for directory binary:'+str(binary) )
					return False

				#include many files here
				for fname in os.listdir(src):
					fpath = os.path.join( src, fname )
					if os.path.isdir(fpath):
						continue
					
					#the dst must be a directory
					#we won't consider dstfile here, as the src is a directory
					cdst = os.path.join( dst, fname )

					subBin = Binary( self )
					subBin.src = fpath
					subBin.dst = cdst
					subBin.itype = binary.itype
					bmap[cdst] = subBin
					logging.debug( 'inited one sub binary:'+str(subBin) )

		#if not set the source files, it means only set the source name
		#try to get the source file from the default directory
		else:	
			if dst is None:
				dst = self.defDstDir

			src = os.path.join( self.defSrcDir, src )
			if not os.path.exists( src ):
				logging.error( 'source file not exist:'+src )
				return False

			if binary.dstfile:
				dst = binary.dstfile
			else:
				dst = os.path.join( dst, bname )
			binary.src = src
			binary.dst = dst
			bmap[dst] = binary
			logging.debug( 'inited one binary:'+str(binary) )

		return True

	def gen_file_vars( self, fout, lhead, offset ):
		lines = ''
		idx = offset
		self.specialList = list()
		for bnry in self.binList:
			if bnry.itype:
				#this is special binary, need special way to install it
				self.specialList.append( bnry )
				if bnry.itype == 'new':
					continue

			lines += lhead + 'source_file' + str(idx) + '="' + bnry.src + '"\n'
			lines += lhead + 'target_file' + str(idx) + '="' + bnry.dst + '"\n'
			lines += lhead + 'backup_file' + str(idx) + '="' + bnry.dst + '-${time_tag}-bak"\n\n'
			idx += 1

		fout.write( lines )
		self.totalTargets = idx - offset
		return self.totalTargets

	def gen_special_apply( self, fout, lhead ):
		if not self.specialList:
			return

		for bnry in self.specialList:
			if bnry.itype == 'kofile':
				lines = lhead + 'echo ""\n'
				lines += lhead + 'echo "applying kofile:' + bnry.src + '..."\n'
				fout.write( lines )
				self.__gen_kofile( fout, lhead, bnry.src, bnry.dst )
			elif bnry.itype == 'new':
				lines  = lhead + 'mv ' + bnry.src + ' ' + bnry.dst + '\n'
				fout.write( lines )

	def gen_special_revert( self, fout, lhead ):
		if not self.specialList:
			return

		for bnry in self.specialList:
			if bnry.itype == 'kofile':
				lines = lhead + 'echo ""\n'
				lines += lhead + 'echo "\nreverting kofile:' + bnry.src + '..."\n'
				fout.write( lines )
				self.__gen_kofile( fout, lhead, bnry.dst, bnry.dst )
			elif bnry.itype == 'new':
				lines  = lhead + 'rm -rf ' + bnry.dst + '\n'
				fout.write( lines )

	def __gen_kodir( self, fout, lhead, dst ):
		idx = dst.rfind( '/' )
		kodir = dst[0:idx]
		lines  = lhead + 'kodir=' + kodir + '\n'
		lines += lhead + 'if [ ! -d $kodir ];then\n'
		lines += lhead + '	mkdir -p $kodir\n'
		lines += lhead + 'fi\n\n'
		fout.write( lines )

	def __gen_kofile( self, fout, lhead, src, dst ):
		bname = os.path.basename( src )
		koname = bname.split( '.' )[0]
		logging.info( 'gen ko:'+koname )

		self.__gen_kodir( fout, lhead, dst )

		lines  = lhead + '#check the used part of ' + koname + ', must be 0 before patching\n'
		lines += lhead + 'echo "Check if the ' + koname + ' used is 0 ..."\n'
		lines += lhead + 'lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + '\n'
		lines += lhead + 'used=`lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + ' | awk \'{print $3}\'`\n'
		lines += lhead + 'if [ ! -z "$used" ]; then\n'
		lines += lhead + '	if [ "$used" != "0" ]; then\n'
		lines += lhead + '		echo "Fatal error, the ' + koname + ' is still being used, cannot patch"\n'
		lines += lhead + '		exit 1\n'
		lines += lhead + '	fi\n'
		lines += lhead + '	#only remove when it exists\n'
		lines += lhead + '	`rmmod ' + koname + '`;\n'
		lines += lhead + '	status=$?\n'
		lines += lhead + '	if [ $status -ne 0 ]; then\n'
		lines += lhead + '		echo "Fatal error, rmmod ' + koname + ' failed"\n'
		lines += lhead + '		exit $status\n'
		lines += lhead + '	fi\n'
		lines += lhead + 'fi\n'
		lines += lhead + '\n'
		lines += lhead + '#check ' + koname + ', no any more\n'
		lines += lhead + 'echo "Check if the ' + koname + ' is removed ..."\n'
		lines += lhead + 'lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + '\n'
		lines += lhead + 'used=`lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + ' | awk \'{print $3}\'`\n'
		lines += lhead + 'if [ ! -z "$used" ]; then\n'
		lines += lhead + '	echo "Fatal error, failed to remove the ' + koname + ', cannot patch"\n'
		lines += lhead + '	exit 1\n'
		lines += lhead + 'fi\n'
		lines += lhead + '\n'
		lines += lhead + '`insmod ' + src + '`;\n'
		lines += lhead + 'status=$?\n'
		lines += lhead + 'if [ $status -ne 0 ]; then\n'
		lines += lhead + '	echo "Fatal error, insmod ' + koname + ' failed"\n'
		lines += lhead + '	exit $status\n'
		lines += lhead + 'fi\n'
		lines += lhead + '\n'
		lines += lhead + '#check ' + koname + ' again, appear\n'
		lines += lhead + 'echo "Check if the ' + koname + ' is inserted ..."\n'
		lines += lhead + 'lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + '\n'
		lines += lhead + 'used=`lsmod | awk \'{print $1, $2, $3}\' | grep ' + koname + ' | awk \'{print $3}\'`\n'
		lines += lhead + 'if [ -z "$used" ]; then\n'
		lines += lhead + '	echo "Fatal error, failed to insert the ' + koname + ', patch failed"\n'
		lines += lhead + '	exit 1\n'
		lines += lhead + 'fi\n\n'

		fout.write( lines )

	def gen_sanity_check( self, fout, lhead ):
		total = self.totalTargets
		lines  = lhead + 'local bkupCount=0\n'
		lines += lhead + 'for (( i=1; i <=' + len(total) + '; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	backup_file=backup_file$i\n'
		lines += lhead + '	backup_file=${!backup_file}\n'
		lines += lhead + '	if [[ -f $backup_file ]]; then\n'
		lines += lhead + '		bkupCount=$(($bkupCount+1))\n'
		lines += lhead + '	fi\n'
		lines += lhead + 'done\n'
		lines += lhead + '# check if all files were installed\n'
		lines += lhead + 'if [ $bkupCount -eq 0 ]; then\n'
		lines += lhead + '	echo "patch not installed\n'	
		lines += lhead + 'elif [ $bkupCount -lt ' + str(total) + ' ]; then\n'
		lines += lhead + '	echo "ERROR: patch not install completely($bkupCount/' + str(total) + '), please revert the patch and try again!\n'
		lines += lhead + '	return 22\n'
		lines += lhead + 'else\n'
		lines += lhead + '	echo "patch already exists, aborting."\n'
		lines += lhead + '	return 21\n'
		lines += lhead + 'fi\n'

		fout.write( lines )


class Library( Binary ):
	def __init__( self, parent ):
		super(Library, self).__init__( parent )


class LibBlock( BinBlock ):
	def __init__( self, parent ):
		super(LibBlock, self).__init__( parent, '/sw/unicorn/lib', '/sw/unicorn/lib' )



class Component( BaseObject ):
	def __init__( self, parent ):
		self.name = None
		self.deviceList = None
		self.serviceBlock = None
		self.binBlock = None
		self.libBlock = None
		self.isInSW = False
		self.skipMount = False

		self.deviceMode = None
		self.compDir = None
		self.orgCompDir = None
		self.md5File = None
		self.scriptName = None

		self.needReload = False

	def init_config( self, parent ):
		if self.name is None:
			logging.error( 'component name not set:'+str(self) )
			return False

		if self.deviceList:
			nlist = list()
			for de in self.deviceList:
				if de == 'se':
					de = 'service-engine'
				elif de == 'sr':
					de = 'service-router'
				elif de == 'cdsm':
					de = 'content-delivery-system-manager'
				nlist.append( de )
			self.deviceList = nlist

		if self.serviceBlock:
			if not self.serviceBlock.init_config( self ):
				logging.error( 'init service block failed:'+str(self.serviceBlock) )
				self.serviceBlock = None
			else:
				logging.debug( 'inited one service block:'+str(self.serviceBlock) )

		if self.binBlock:
			if not self.binBlock.init_config( self ):
				logging.error( 'init binary block failed:'+str(self.binBlock) )
				self.binBlock = None
				if STRICT_PARSE:
					return False
			else:
				logging.debug( 'inited one bin block:'+str(self.binBlock) )
				if self.binBlock.isInSW:
					self.isInSW = True

		if self.libBlock:
			if not self.libBlock.init_config( self ):
				logging.error( 'init library block failed:'+str(self.libBlock) )
				self.libBlock = None
				if STRICT_PARSE:
					return False
			else:
				logging.debug( 'inited one lib block:'+str(self.libBlock) )
				if self.libBlock.isInSW:
					self.isInSW = True

		if not self.binBlock and not self.libBlock:
			logging.error( 'no available binary file in this component:'+str(self) )
			return False

		return True

	def generate( self, pdir, orgPdir ):
		logging.info( 'gen in component:'+str(self) )
		self.compDir = os.path.join( pdir, self.name )
		self.orgCompDir = os.path.join( orgPdir, self.name )
		if not mkdir(self.compDir):
			logging.error( 'create component directory failed:'+str(self) )
			return False
		srcDir = os.path.join( self.compDir, 'src' )
		orgSrcDir = 'src'
		if not mkdir(srcDir):
			logging.error( 'create component src directory failed:'+str(self) )
			return False
		self.__copy_source_files( srcDir, orgSrcDir )
		self.__gen_md5sum_file( srcDir )

		self.scriptName = self.name + '.sh'
		spath = os.path.join( self.compDir, self.scriptName )
		fout = open( spath, 'w' )

		self.__gen_head( fout )
		fout.write( '\n' )
		gen_check_device_mode_func( fout, '' )
		fout.write( '\n' )
		gen_check_service_func( fout, '' )
		fout.write( '\n' )
		self.__gen_apply_func( fout )
		fout.write( '\n' )
		self.__gen_revert_func( fout )
		fout.write( '\n' )
		self.__gen_verify_func( fout )
		fout.write( '\n' )

		lines  = 'case "$1" in\n'
		lines += '	apply)\n'
		lines += '    patch_apply\n'
		lines += '    ;;\n'
		lines += '	revert)\n'
		lines += '    patch_revert\n'
		lines += '    ;;\n'
		lines += '	verify)\n'
		lines += '    patch_verify\n'
		lines += '    ;;\n'
		lines += '	*)\n'
		lines += '    echo $"Usage: $0 {apply|revert|verify}"\n'
		lines += 'esac\n'
		lines += 'cd $org_pwd\n'
		fout.write( lines )

		fout.close()
		return True

	def __gen_head( self, fout ):
		lines  = '#!/bin/sh\n'
		lines += '# patch for ' + self.name + '\n\n'
		lines += 'component="' + self.name + '"\n'
		lines += 'md5sum_file="' + self.md5File + '"\n\n'
		lines += 'org_pwd=$PWD\n'
		lines += 'cd ' + self.orgCompDir + '\n\n'

		fout.write( lines )

		offset = 1
		if self.binBlock:
			offset += self.binBlock.gen_file_vars( fout, '', offset )
		if self.libBlock:
			offset += self.libBlock.gen_file_vars( fout, '', offset )

		lines  = 'total_files=' + str(offset-1) + '\n'
		fout.write( lines )

	def __gen_apply_func( self, fout ):
		lines = 'function patch_apply(){\n'
		lines += '	echo ""\n'
		lines += '	echo "#########################################################"\n'
		lines += '	echo "# Patching $component..."\n\n'
		fout.write( lines )

		lhead = '\t'
		self.__gen_check_patched( fout, lhead )
		self.__gen_check_device_mode( fout, lhead )
		self.__gen_check_md5sum( fout, lhead )
		if self.serviceBlock:
			fout.write( '\n' )
			self.serviceBlock.gen_stop( fout, lhead, 'apply' )
		else:
			logging.info( 'no service block to stop' )
		self.__gen_mount( fout, lhead, 'rw' )
		self.__gen_install_bin( fout, lhead )
		if self.skipMount:
			self.__gen_mount( fout, lhead, 'ro' )
		if self.serviceBlock:
			fout.write( '\n' )
			self.serviceBlock.gen_start( fout, lhead, 'apply' )
		else:
			logging.info( 'no service block to start' )

		lines  = ''
		lines += '}\n'
		fout.write( lines )

	def __gen_revert_func( self, fout ):
		lines = 'function patch_revert(){\n'
		lines += '	echo ""\n'
		lines += '	echo "#########################################################"\n'
		lines += '	echo "# Reverting $component..."\n\n'
		fout.write( lines )

		lhead = '\t'
		self.__gen_check_reverted( fout, lhead )
		if self.serviceBlock:
			self.serviceBlock.gen_stop( fout, lhead, 'revert' )
		self.__gen_mount( fout, lhead, 'rw' )
		self.__gen_revert_bin( fout, lhead )
		if self.skipMount:
			self.__gen_mount( fout, lhead, 'ro' )
		if self.serviceBlock:
			self.serviceBlock.gen_start( fout, lhead, 'revert' )

		lines  = ''
		lines += '}\n'
		fout.write( lines )

	def __gen_verify_func( self, fout ):
		lines = 'function patch_verify(){\n'
		lines += '	echo ""\n'
		lines += '	echo "#########################################################"\n'
		lines += '	echo "# Verifying $component..."\n\n'

		lhead  = '\t'
		lines += lhead + 'local installed=1\n'
		lines += lhead + 'for (( i=1; i<=total_files; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	file_to_check=target_file$i\n'
		lines += lhead + '	file_to_check=${!file_to_check}\n'
		lines += lhead + '	filename_nopath=$(echo "$file_to_check" | sed "s/.*\/\(.\+\)$/\\1/")\n'
		lines += lhead + '	expected_md5=$(grep "/$filename_nopath$" $md5sum_file | awk \'{ print $1 }\')\n'
		lines += lhead + '	patched_md5=$(md5sum "$file_to_check" | awk \'{ print $1 }\')\n'
		lines += lhead + '	\n'
		lines += lhead + '	echo "Actual checksum is   $patched_md5 for target file $file_to_check."\n'
		lines += lhead + '	echo "Expected checksum is $expected_md5."\n'
		lines += lhead + '	\n'
		lines += lhead + '	if [[ "$patched_md5" = "$expected_md5" ]]; then \n'
		lines += lhead + '	    installed=$(($installed&1))\n'
		lines += lhead + '	else\n'
		lines += lhead + '	    installed=$(($installed&0))\n'
		lines += lhead + '	fi\n'
		lines += lhead + 'done\n'
		lines += lhead + 'if [[ $installed -ne 0 ]]; then\n'
		lines += lhead + '	echo "Verification: patch has been installed."\n'
		lines += lhead + 'else\n'
		lines += lhead + '	echo "Verification: patch is not installed."\n'
		lines += lhead + 'fi\n' 

		lines += '}\n'
		fout.write( lines )


	def __gen_check_patched( self, fout, lhead ):
		lines  = lhead + '##### sanity check\n'
		lines += lhead + 'local bkupCount=0\n'
		lines += lhead + 'for (( i=1; i<=total_files; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	backup_file=backup_file$i\n'
		lines += lhead + '	backup_file=${!backup_file}\n'
		lines += lhead + '	if [[ -f $backup_file ]]; then\n'
		lines += lhead + '		bkupCount=$(($bkupCount+1))\n'
		lines += lhead + '	fi\n'
		lines += lhead + 'done\n\n'
		lines += lhead + '# check if all files were installed\n'
		lines += lhead + 'if [ $bkupCount -eq 0 ]; then\n'
		lines += lhead + '	echo "sanity check: patch not installed, go on..."\n'	
		lines += lhead + 'elif [ $bkupCount -lt $total_files ]; then\n'
		lines += lhead + '	echo "ERROR: patch not install completely($bkupCount/$total_files), please revert the patch and try again!"\n'
		lines += lhead + '	return 22\n'
		lines += lhead + 'else\n'
		lines += lhead + '	echo "patch already exists, aborting."\n'
		lines += lhead + '	return 21\n'
		lines += lhead + 'fi\n\n'
		
		fout.write( lines )

	def __gen_check_reverted( self, fout, lhead ):
		lines  = lhead + '##### sanity check\n'
		lines += lhead + 'local bkupCount=0\n'
		lines += lhead + 'for (( i=1; i<=total_files; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	backup_file=backup_file$i\n'
		lines += lhead + '	backup_file=${!backup_file}\n'
		lines += lhead + '	if [[ -f $backup_file ]]; then\n'
		lines += lhead + '		bkupCount=$(($bkupCount+1))\n'
		lines += lhead + '	fi\n'
		lines += lhead + 'done\n\n'
		lines += lhead + '# check if all files were installed\n'
		lines += lhead + 'if [ $bkupCount -eq 0 ]; then\n'
		lines += lhead + '	echo "sanity check: patch not installed, aborting."\n'
		lines += lhead + '	return 31\n'
		lines += lhead + 'elif [ $bkupCount -lt $total_files ]; then\n'
		lines += lhead + '	echo "ERROR: patch not install completely($bkupCount/$total_files)"\n'
		lines += lhead + 'else\n'
		lines += lhead + '	echo "sanity check: patch installed, go on..."\n'
		lines += lhead + 'fi\n\n'
		
		fout.write( lines )

	def __gen_check_device_mode( self, fout, lhead ):
		if not self.deviceList:
			return
		lines  = ''
		lines += lhead + 'echo ""\n'
		lines += lhead + 'local isRightMode=0\n'
		lines += lhead + 'local allowMode=0\n'
		lines += lhead + 'echo "checking device mode, allowed:' + str(self.deviceList) + '"\n'
		for de in self.deviceList:
			lines += lhead + 'if [ $isRightMode -eq 0 ]; then\n'
			lines += lhead + '	check_device_mode "' + de + '"\n'
			lines += lhead + '	isRightMode=$?\n'
			lines += lhead + '	if [ $isRightMode -eq 1 ]; then\n'
			lines += lhead + '		echo "patch will install for ' + de + '"\n'
			lines += lhead + '		allowMode=1\n'
			lines += lhead + '	fi\n'	
			lines += lhead + 'fi\n'	

		lines += lhead + 'if [ $allowMode -eq 0 ]; then\n'
		lines += lhead + '	echo "patch is not allowed for this device mode"\n'
		lines += lhead + '	/ruby/bin/exec -c "show device-mode current"\n'
		lines += lhead + '	exit 44\n'
		lines += lhead + 'fi\n'
		fout.write( lines )
	
	def __gen_check_md5sum( self, fout, lhead ):
		lines  = lhead + 'md5sum --status -c $md5sum_file\n'
		lines += lhead + 'md5_rc=$?\n'
		lines += lhead + 'if [ $md5_rc -ne 0 ]; then\n'
		lines += lhead + '	echo "ERROR: patch file corrupted, aborting, please check"\n'
		lines += lhead + '	exit 24\n'
		lines += lhead + 'fi\n'
		fout.write( lines )

	def __gen_mount( self, fout, lhead, perm ):
		if not self.isInSW:
			return

		if perm == 'ro' and self.needReload:
			#if needReload, no need to remount
			logging.info( 'needReload, no need to remount in component:'+str(self) )
			return

		lines  = lhead + 'mount -n -o remount,' + perm + ' /sw\n'
		lines += lhead + 'if [ $? -ne 0 ]; then\n'
		lines += lhead + '	echo "ERROR: unable to remount partition as ' + perm + ' mode"\n'
		lines += lhead + '	echo "Please try the patch later or reload the device and retry."\n'
		lines += lhead + '	exit 28\n'
		lines += lhead + 'fi\n'
		lines += lhead + 'sleep 10\n'
		fout.write( lines )

	def __gen_install_bin( self, fout, lhead ):
		lines  = lhead + '##### replace binary\n'
		lines += lhead + 'for (( i=1; i<=total_files; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	target_file=target_file$i\n'
		lines += lhead + '	backup_file=backup_file$i\n'
		lines += lhead + '	source_file=source_file$i\n'
		lines += lhead + '	target_file=${!target_file}\n'
		lines += lhead + '	backup_file=${!backup_file}\n'
		lines += lhead + '	source_file=${!source_file}\n'
		lines += lhead + '	mv -f $target_file $backup_file\n'
		lines += lhead + '	cp -f $source_file $target_file\n'
		lines += lhead + '	chmod a+x $target_file\n'
		lines += lhead + 'done\n'
		fout.write( lines )

		if self.binBlock:
			self.binBlock.gen_special_apply( fout, lhead )
		if self.libBlock:
			self.libBlock.gen_special_apply( fout, lhead )

		lines  = lhead + 'echo "Patch files installed."\n'
		lines += lhead + 'sleep 10\n'
		fout.write( lines )

	def __gen_revert_bin( self, fout, lhead ):
		lines  = lhead + '##### replace binary\n'
		lines += lhead + 'for (( i=1; i<=total_files; i++ ))\n'
		lines += lhead + 'do\n'
		lines += lhead + '	target_file=target_file$i\n'
		lines += lhead + '	backup_file=backup_file$i\n'
		lines += lhead + '	source_file=source_file$i\n'
		lines += lhead + '	target_file=${!target_file}\n'
		lines += lhead + '	backup_file=${!backup_file}\n'
		lines += lhead + '	source_file=${!source_file}\n'
		lines += lhead + '	rm -f $target_file\n'
		lines += lhead + '	mv -f $backup_file $target_file\n'
		lines += lhead + '	chmod a+x $target_file\n'
		lines += lhead + 'done\n'
		fout.write( lines )

		if self.binBlock:
			self.binBlock.gen_special_revert( fout, lhead )
		if self.libBlock:
			self.libBlock.gen_special_revert( fout, lhead )

		lines  = lhead + 'echo "Patch files reverted."\n'
		lines += lhead + 'sleep 10\n'
		fout.write( lines )

	def __copy_source_files( self, srcDir, orgSrcDir ):
		try:
			if self.binBlock:
				for bnry in self.binBlock.binList:
					shutil.copy( bnry.src, srcDir )
					nsrc = os.path.join( orgSrcDir, os.path.basename(bnry.src) )
					bnry.src = nsrc

			if self.libBlock:
				for lib in self.libBlock.binList:
					shutil.copy( lib.src, srcDir )
					nsrc = os.path.join( orgSrcDir, os.path.basename(lib.src) )
					lib.src = nsrc

			return True
		except:
			return False

	def __gen_md5sum_file( self, srcDir ):
		self.md5File = 'sum.md5'
		cmd  = 'cd ' + self.compDir
		cmd += ';md5sum ' + 'src/* > ' + self.md5File
		logging.debug( 'run cmd:'+cmd )
		os.system( cmd )


class Patcher( BaseObject ):
	def __init__( self ):
		self.customer = ''
		self.version = ''
		self.bugs = ''
		self.timeTag = None
		self.outDir = './'

		self.packageDir = None
		self.needReload = False
		self.warn = None
		self.serviceBlock = None
		self.compList = list()

	def add_component( self, comp ):
		self.compList.append( comp )

	def init_config( self ):
		if self.serviceBlock:
			if not self.serviceBlock.init_config( self ):
				logging.error( 'init service block failed:'+str(self.serviceBlock) )
				self.serviceBlock = None
			else:
				logging.debug( 'inited one service block:'+str(self.serviceBlock) )

		clist = list()
		for comp in self.compList:
			if comp.init_config( self ):
				comp.needReload = self.needReload
				clist.append( comp )
				logging.debug( 'inited one component:'+str(comp) )
			else:
				logging.error( 'invalid component:'+str(comp) )
				if STRICT_PARSE:
					return False

		self.compList = clist
		return len(self.compList) > 0

	def generate( self ):
		logging.info( 'patch obj:'+str(self) )
		logging.info( '\nbegin to generate patch...\n\n' )
		if not self.timeTag:
			now = datetime.now()
			self.timeTag = str_time( now, '%Y%m%d' )
		
		mkdir( self.outDir )
		if not self.packageDir:
			self.packageDirName = 'patch_package_' + self.version + '_' + self.timeTag
			self.packageDir = os.path.join( self.outDir, self.packageDirName )

		logging.debug( 'make directory:'+self.packageDir )
		if not mkdir(self.packageDir):
			logging.fatal( 'create package directory failed:'+str(self) )
			return False

		self.__gen_comps()
		self.__gen_main_script()


	def __gen_comps( self ):
		if self.compList:
			for comp in self.compList:
				if not comp.generate( self.packageDir, self.packageDirName ):
					logging.error( 'generate failed on compent:'+str(comp) )
					return False

		return True

	def __gen_main_script( self ):
		scriptName = 'cdsis_' + self.version + '_patch_' + self.timeTag + '.sh.sign'
		spath = os.path.join( self.outDir, scriptName )
		fout = open( spath, 'w' )

		self.__gen_head( fout )
		fout.write( '\n' )
		if self.needReload:
			self.__gen_reload_warning_func( fout )
			fout.write( '\n' )
		if self.warn:
			self.__gen_warning_func( fout )
			fout.write( '\n' )
		self.__gen_uncompress_func( fout )
		fout.write( '\n' )
		self.__gen_validate_func( fout )
		fout.write( '\n' )
		self.__gen_apply_func( fout )
		fout.write( '\n' )
		self.__gen_revert_func( fout )
		fout.write( '\n' )
		self.__gen_verify_func( fout )
		fout.write( '\n' )
		self.__gen_clean_func( fout )
		fout.write( '\n' )

		lines  = 'case "$1" in\n'
		lines += '		apply)\n'
		lines += '			patch_apply $2\n'
		lines += '			;;\n'
		lines += '		revert)\n'
		lines += '			patch_revert\n'
		lines += '			;;\n'
		lines += '		verify)\n'
		lines += '			patch_verify\n'
		lines += '			;;\n'
		lines += '		clean)\n'
		lines += '			patch_clean\n'
		lines += '			;;\n'
		lines += '		*)\n'
		lines += '			echo $"Usage: $0 {apply|revert|verify|clean}"\n'
		lines += 'esac\n'
		fout.write( lines )
		fout.close()

		cmd  = 'cd ' + self.outDir
		cmd += ';tar czf ' + self.packageDirName + '.tar.gz ' + self.packageDirName
		logging.debug( 'run cmd:'+cmd )
		os.system( cmd )
		
		cmd = '/ruby/bin/exec_script emit-checksum ' + spath + ' >> ' + spath
		logging.debug( 'run cmd:'+cmd )
		os.system( cmd )

	def __gen_head( self, fout ):
		lines  = '#!/bin/sh\n'
		lines += '# patch on ' + self.version + ' for ' + self.customer + '\n'
		lines += '# CDETS: ' + self.bugs + '\n'
		lines += '\n'
		lines += 'export customer="' + self.customer + '"\n'
		lines += 'export target_version="' + self.version + '" # major(.)minor(.)maintenance(b)build\n'
		lines += 'export version_tag="vds-is $target_version(For $customer)"\n'
		lines += 'export time_tag="' + self.timeTag + '"\n'
		lines += '\n'
		lines += 'package_name="patch_package_${target_version}_${time_tag}"\n'
		lines += 'package_file="./$package_name.tar.gz"\n\n'
		
		idx = 0
		for comp in self.compList:
			idx += 1
			spath = os.path.join( comp.compDir, comp.scriptName )
			opath = os.path.join( comp.orgCompDir, comp.scriptName )
			cmd = 'md5sum ' + spath
			logging.debug( 'popen cmd:'+cmd )
			fin = os.popen( cmd, 'r' )
			md5sum = ''
			for line in fin:
				logging.debug( line )
				segs = line.split()
				md5sum = segs[0]
				break
			fin.close()

			lines += 'script_file' + str(idx) + '="' + opath + '"\n'
			lines += 'script_md5sum' + str(idx) + '="' + md5sum + '"\n'
		
		lines += 'total_scripts=' + str(idx) + '\n'
		lines += '\n\n'
		fout.write( lines )
		
	def __gen_reload_warning_func( self, fout ):
		lines  = 'reload_warning() {\n'
		lines += '	local yn=""\n'
		lines += '	while [ "$yn" != "y" ] && [ "$yn" != "Y" ] && [ "$yn" != "n" ] && [ "$yn" != "N" ]\n'
		lines += '	do\n'
		lines += '		read -p "May reboot this device in processing, please offload the device, continue? [y/n]: " yn\n'
		lines += '	done\n'
		lines += '	echo\n'
		lines += '	if [ "$yn" == "n" ] || [ "$yn" == "N" ]; then\n'
		lines += '		echo "Abort."\n'
		lines += '		exit 101\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )
	
	def __get_reload_code( self, fout, lhead ):
		lines  = lhead + '##### 4. reload device\n'
		lines += lhead + 'echo "reload device..."\n'
		lines += lhead + '/ruby/bin/exec -c "reload"\n'
		lines += lhead + 'echo\n'
		lines += lhead + 'echo\n'
		lines += lhead + 'echo "********Please reload manually!********"\n'
		return lines

	def __gen_warning_func( self, fout ):
		lines  = 'patch_warning() {\n'
		lines += '	local yn=""\n'
		lines += '	while [ "$yn" != "y" ] && [ "$yn" != "Y" ] && [ "$yn" != "n" ] && [ "$yn" != "N" ]\n'
		lines += '	do\n'
		lines += '		read -p "' + self.warn + ', continue? [y/n]:" yn\n'
		lines += '	done\n'
		lines += '	echo\n'
		lines += '	if [ "$yn" == "n" ] || [ "$yn" == "N" ]; then\n'
		lines += '		echo "Abort."\n'
		lines += '		exit 102\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )

	def __gen_uncompress_func( self, fout ):
		lines  = 'package_uncompress() {\n'
		lines += '	\n'
		lines += '	if [ ! -f $package_file ]; then\n'
		lines += '		echo "ERROR: patch package file $package_file does not exist, aborting, please check"\n'
		lines += '		exit 11\n'
		lines += '	fi\n'
		lines += '	\n'
		lines += '	tar xzf $package_file\n'
		lines += '	if [ $? -ne 0 ]; then\n'
		lines += '		echo "ERROR: patch package file $package_file is corrupted, aborting, please check"\n'
		lines += '		exit 12\n'
		lines += '	fi\n'
		lines += '\n'
		lines += '}\n'
		fout.write( lines )

	def __gen_validate_func( self, fout ):
		lines  = 'scripts_validate() {\n'
		lines += '	\n'
		lines += '	for (( n=1; n<=$total_scripts; n++ ))\n'
		lines += '	do\n'
		lines += '		script_file_name=script_file$n\n'
		lines += '		expected_script_md5=script_md5sum$n\n'
		lines += '		\n'
		lines += '		script_file_name=${!script_file_name}\n'
		lines += '		expected_script_md5=${!expected_script_md5}\n'
		lines += '		\n'
		lines += '		actual_script_md5=$(md5sum $script_file_name | awk \'{ print $1 }\')\n'
		lines += '		\n'
		lines += '		if [[ "$expected_script_md5" != "$actual_script_md5" ]]; then\n'
		lines += '			echo "Patch files do not exist or scripts have been modified, aborting."\n'
		lines += '			exit 41\n'
		lines += '		fi\n'
		lines += '	done\n'
		lines += '}\n'
		fout.write( lines )

	def __gen_apply_func( self, fout ):
		lines  = 'patch_apply() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## Patch for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	cds_version=$(/ruby/bin/exec -c "show version" | grep "Content Delivery System Software Release" | awk \'{ print $6$8 }\')\n'
		lines += '	if [[ "$cds_version" = "$target_version" ]]; then\n'
		lines += '		echo "Current cds-is version $cds_version"\n'
		lines += '	else\n'
		lines += '		echo "Patch is only applied to cds-is $target_version (but current is $cds_version), aborting."\n'
		lines += '		exit 23\n'
		lines += '	fi\n'
		lines += '	\n'
		if self.needReload:
			lines += '	reload_warning\n'
		if self.warn:
			lines += '	patch_warning\n'
		lines += '	echo "Uncompressing package file..."\n'
		lines += '	package_uncompress\n'
		lines += '	echo "Package file uncompressed."\n'
		lines += '	scripts_validate\n'
		lines += '	\n'
		lines += '	ret=0\n'
		lines += '	for (( n=1; n<=total_scripts; n++ ))\n'
		lines += '	do\n'
		lines += '		script_file_name=script_file$n\n'
		lines += '		script_file_name=${!script_file_name}\n'
		lines += '		sh $script_file_name apply\n'
		lines += '		ret=$(($ret|$?))\n'
		lines += '	done\n'
		lines += '\n'
		lines += '	echo ""\n'
		lines += '	echo "" \n'
		lines += '	if [[ $ret -eq 0 ]]; then\n'
		lines += '		echo "Patch apply succeeded for all applicable modules."\n'
		if self.needReload:
			lines += self.__get_reload_code( fout, '\t\t' )
		lines += '	else\n'
		lines += '		echo "Patch apply succeeded for only some of the module(s), code $ret."\n'
		lines += '		echo "Please refer to above details to examine which module(s) failed/succeeded."\n'
		lines += '		echo "Please note that the modules not being installed might be those are not applicable to this device."		\n'
		lines += '	fi  \n'
		lines += '}\n'
		fout.write( lines )
	
	def __gen_revert_func( self, fout ):
		lines  = 'patch_revert() {\n'
		lines += '	check_required=0\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## Patch revert for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		if self.needReload:
			lines += '	reload_warning\n'
		lines += '	scripts_validate\n'
		lines += ' \n'
		lines += '	ret=0\n'
		lines += '	for (( n=1; n<=total_scripts; n++ ))\n'
		lines += '	do\n'
		lines += '		script_file_name=script_file$n\n'
		lines += '		script_file_name=${!script_file_name}\n'
		lines += '		sh $script_file_name revert\n'
		lines += '		ret=$(($ret|$?))\n'
		lines += '	done\n'
		lines += '\n'
		lines += '	echo ""\n'
		lines += '	echo ""\n'
		lines += '	if [[ $ret -eq 0 ]]; then\n'
		lines += '		echo "Patch revert succeeded for all applicable modules."\n'
		if self.needReload:
			lines += self.__get_reload_code( fout, '\t\t' )
		lines += '	else\n'
		lines += '		echo "Patch revert succeeded for only some of the module(s), code $ret."\n'
		lines += '		echo "Please refer to above details to examine which module(s) failed/succeeded."\n'
		lines += '		echo "Please note that the modules not being reverted might be those are not applicable to this device."\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )
	
	def __gen_verify_func( self, fout ):
		lines  = 'patch_verify() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## Patch verification for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	# force to uncompress the package every time do verification\n'
		lines += '	package_uncompress\n'
		lines += '	scripts_validate\n'
		lines += '	\n'
		lines += '	ret=0\n'
		lines += '	for (( n=1; n<=total_scripts; n++ ))\n'
		lines += '	do\n'
		lines += '		script_file_name=script_file$n\n'
		lines += '		script_file_name=${!script_file_name}\n'
		lines += '		sh $script_file_name verify\n'
		lines += '		ret=$(($ret|$?))\n'
		lines += '	done\n'
		lines += '}\n'
		fout.write( lines )
	
	def __gen_clean_func( self, fout ):
		lines  = 'patch_clean() {\n'
		lines += '	rm -fr ./$package_name/\n'
		lines += '	echo "Files generated while running the patch have been cleaned."\n'
		lines += '	echo "Please note that the original .tar.gz and script files are not removed. You might want to delete them manually."\n'
		lines += '}\n'
		fout.write( lines )
