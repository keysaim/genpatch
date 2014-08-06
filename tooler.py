import os
import shutil
import logging
import traceback

from base import *
from patcher import *

class ToolFile( BaseObject ):
	def __init__( self, src ):
		super(ToolFile, self).__init__()
		self.src = src


class ToolFileBlock( BaseObject ):
	def __init__( self ):
		super(ToolFileBlock, self).__init__()
		self.fileList = list()

	def add_file( self, tfile ):
		self.fileList.append( tfile )

	def init_config( self, parent ):
		if not self.fileList:
			return False

		newList = list()
		for tfile in self.fileList:
			flist = self.__init_file( tfile )
			if flist:
				newList += flist

		self.fileList = newList
		if not newList:
			return False

		return True

	def __init_file( self, tfile ):
		src = tfile.src
		if os.path.exists(src):
			if os.path.isfile(src):
				return [tfile]

			flist = list()
			for fname in os.listdir(src):
				fpath = os.path.join(src, fname)
				nfile = ToolFile( fpath )
				flist.append( nfile )

			return flist
	
		return None
		


class Tooler( BaseObject ):
	def __init__( self ):
		self.toolsDir = '/sw/tools'
		self.name = ''
		self.customer = ''
		self.version = ''
		self.bugs = ''
		self.timeTag = None
		self.outDir = './'

		self.packageDir = None
		self.packageDirName = None
		self.deviceList = None
		self.script = None
		self.fileBlock = None

	def init_config( self ):
		if not self.name:
			logging.error( 'no valid tool name defined' )
			return False

		if not self.script:
			logging.error( 'no valid script parsed in tool:'+str(self) )
			return False

		if not self.script or not os.path.isfile(self.script.src):
			logging.error( 'no valid script defined in tool:'+str(self) )
			return False

		if self.deviceList:
			self.deviceList = format_device_name( self.deviceList )
			if not self.deviceList:
				logging.error( 'no valid device name defined in tool:'+str(self) )
				return False

		if self.fileBlock:
			if not self.fileBlock.init_config( self ):
				logging.error( 'init fileBlock failed:'+str(self.fileBlock) )
				return False

		return True

	def generate( self ):
		logging.info( 'generate tool obj:'+str(self) )
		logging.info( '\nbegin to generate tool...\n\n' )
		
		self.__prepare_package()
		self.__gen_main_script()
		
	def __prepare_package( self ):
		if not self.timeTag:
			now = datetime.now()
			self.timeTag = str_time( now, '%Y%m%d' )
		
		mkdir( self.outDir )
		if not self.packageDir:
			self.packageDirName = 'tool_' + self.name + '_' + self.version + '_' + self.timeTag
			self.packageDir = os.path.join( self.outDir, self.packageDirName )

		logging.debug( 'make directory:'+self.packageDir )
		if not mkdir(self.packageDir):
			logging.fatal( 'create package directory failed:'+str(self) )
			return False

		self.__copy_script( self.packageDir )
		self.__copy_tool_files( self.packageDir )

	def __gen_main_script( self ):
		scriptName = 'cdsis_' + self.version + '_' + self.name + '_' + self.timeTag + '.sh.sign'
		spath = os.path.join( self.outDir, scriptName )
		fout = open( spath, 'w' )

		self.__gen_head( fout )
		fout.write( '\n' )
		gen_check_version_func( fout )
		fout.write( '\n' )
		gen_check_device_mode_func( fout, '' )
		fout.write( '\n' )
		self.__gen_uncompress_func( fout )
		fout.write( '\n' )
		self.__gen_check_installed_func( fout )
		fout.write( '\n' )
		self.__gen_validate_func( fout )
		fout.write( '\n' )
		self.__gen_install_func( fout )
		fout.write( '\n' )
		self.__gen_uninstall_func( fout )
		fout.write( '\n' )
		self.__gen_run_func( fout )
		fout.write( '\n' )
		self.__gen_verify_func( fout )
		fout.write( '\n' )

		script = self.__get_path_in_tool( os.path.basename(self.script.src) )
		lines  = 'case "$1" in\n'
		lines += '		install)\n'
		lines += '			tool_install\n'
		lines += '			;;\n'
		lines += '		uninstall)\n'
		lines += '			tool_uninstall\n'
		lines += '			;;\n'
		lines += '		verify)\n'
		lines += '			tool_verify\n'
		lines += '			;;\n'
		lines += '		run)\n'
		lines += '			shift\n'
		lines += '			arguments="$@"\n'
		lines += '			tool_run\n'
		lines += '			cd ' + self.__get_tool_dir() + ';sh ' + script + ' "$@"\n'
		lines += '			rc=$?\n'
		lines += '			if [ $rc -eq 1 ]; then\n'
		lines += '				echo "invalid arguments for run command"\n'
		lines += '			fi\n'
		lines += '			exit $rc\n'
		lines += '			;;\n'
		lines += '		*)\n'
		lines += '			echo $"Usage: $0 {install|uninstall|verify|run <argvs>}"\n'
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
		lines += '# tool on ' + self.version + ' for ' + self.customer + '\n'
		lines += '# CDETS: ' + self.bugs + '\n'
		lines += '\n'
		lines += 'export customer="' + self.customer + '"\n'
		lines += 'export target_version="' + self.version + '" # major(.)minor(.)maintenance(b)build\n'
		lines += 'export version_tag="vds-is $target_version(For $customer)"\n'
		lines += 'export time_tag="' + self.timeTag + '"\n'
		lines += '\n'
		lines += 'package_name="' + self.packageDirName + '"\n'
		lines += 'package_file="./$package_name.tar.gz"\n\n'
		lines += 'arguments="$@"\n'
		
		idx = 1
		lines += self.__get_gen_md5sum_code( self.script.src, idx )
		if self.fileBlock:
			for tfile in self.fileBlock.fileList:
				idx += 1
				lines += self.__get_gen_md5sum_code( tfile.src, idx )
		
		lines += 'total_scripts=' + str(idx) + '\n'
		lines += '\n\n'
		fout.write( lines )
	
	def __gen_uncompress_func( self, fout ):
		lines  = 'function package_uncompress() {\n'
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
		lines  = 'function scripts_validate() {\n'
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

	def __gen_check_installed_func( self, fout ):
		toolDir = self.__get_tool_dir()
		lines  = 'function check_tool_installed() {\n'
		lines += '	local tool_dir="' + toolDir + '"\n'
		lines += '	if [ -d "$tool_dir" ]; then\n'
		lines += '		return 1\n'
		lines += '	else\n'
		lines += '		return 0\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )

	def __gen_install_func( self, fout ):
		lines  = 'function tool_install() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## tool install for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	check_version $target_version\n'
		lines += '	if [ $? -ne 0 ]; then\n'
		lines += '		echo "cannot install for this version"\n'
		lines += '		exit 23\n'
		lines += '	fi\n'
		fout.write( lines )

		if self.deviceList:
			gen_check_device_mode( fout, '\t', self.deviceList )

		lines  = '	check_tool_installed\n'
		lines += '	if [ $? -eq 1 ]; then\n'
		lines += '		echo "tool is already installed, please uninstall it before installing again!"\n'
		lines += '		exit 22\n'
		lines += '	fi\n'
		lines += '	echo "Uncompressing package file..."\n'
		lines += '	package_uncompress\n'
		lines += '	echo "Package file uncompressed."\n'
		lines += '	scripts_validate\n'
		lines += '	\n'
		fout.write( lines )

		lines  = '	echo "installing tool ..."\n'
		fout.write( lines )
		gen_mount_sw( fout, '\t', 'rw', 5 )
		lines  = '	if [ ! -d ' + self.toolsDir + ' ]; then\n'
		lines += '		mkdir ' + self.toolsDir + '\n'
		lines += '	fi\n'
		lines += '	mv -f ' + self.packageDirName + ' ' + self.toolsDir + '/\n'
		lines += '	local ret=$?\n'
		fout.write( lines )
		gen_mount_sw( fout, '\t', 'ro', 5 )

		lines  = '	echo "" \n'
		lines += '	if [[ $ret -eq 0 ]]; then\n'
		lines += '		echo "tool install succeeded!"\n'
		lines += '	else\n'
		lines += '		echo "tool install failed, please try again!"\n'
		lines += '	fi  \n'
		lines += '}\n'
		fout.write( lines )
	
	def __get_tool_dir( self ):
		tpath = os.path.join( self.toolsDir, self.packageDirName )
		return tpath

	def __gen_uninstall_func( self, fout ):
		script = self.__get_path_in_tool( os.path.basename(self.script.src) )
		lines  = 'function tool_uninstall() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## tool uninstall for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	check_tool_installed\n'
		lines += '	if [ $? -ne 1 ]; then\n'
		lines += '		echo "the tool is not installed, please install it first!"\n'
		lines += '		exit 22\n'
		lines += '	fi\n'
		fout.write( lines )

		lines  = '	cd ' + self.__get_tool_dir() + ';sh ' + script + ' uninstall\n'
		lines += '	if [ $? -eq 0 ]; then\n'
		lines += '		echo ""\n'
		lines += '	else\n'
		lines += '		echo "canot uninstall the tool!"\n'
		lines += '		return\n'
		lines += '	fi\n'
		fout.write( lines )

		lines  = '	echo "uninstalling tool ..."\n'
		fout.write( lines )
		gen_mount_sw( fout, '\t', 'rw', 5 )
		lines  = '	rm -rf ' + self.__get_tool_dir() + '\n'
		lines += '	local ret=$?\n'
		fout.write( lines )
		gen_mount_sw( fout, '\t', 'ro', 5 )

		lines  = '	if [[ $ret -eq 0 ]]; then\n'
		lines += '		echo "tool uninstall succeeded!"\n'
		lines += '	else\n'
		lines += '		echo "tool uninstall failed, please try again!"\n'
		lines += '	fi  \n'
		lines += '}\n'
		fout.write( lines )
	
	def __gen_run_func( self, fout ):
		script = self.__get_path_in_tool( os.path.basename(self.script.src) )
		lines  = 'function tool_run() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## tool run for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	check_tool_installed\n'
		lines += '	if [ $? -ne 1 ]; then\n'
		lines += '		echo "the tool is not installed, please install it first!"\n'
		lines += '		exit 22\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )
	
	def __gen_verify_func( self, fout ):
		lines  = 'function tool_verify() {\n'
		lines += '	echo "############################################################"\n'
		lines += '	echo "## tool verify for $version_tag"\n'
		lines += '	echo "############################################################"\n'
		lines += '	\n'
		lines += '	check_tool_installed\n'
		lines += '	if [ $? -ne 1 ]; then\n'
		lines += '		echo "the tool is not installed!"\n'
		lines += '	else\n'
		lines += '		echo "the tool is installed!"\n'
		lines += '	fi\n'
		lines += '}\n'
		fout.write( lines )
	
	def __get_path_in_tool( self, name ):
		opath = os.path.join( self.__get_tool_dir(), name )
		return opath

	def __get_gen_md5sum_code( self, src, idx ):
		opath = os.path.join( self.packageDirName, os.path.basename(src) )
		md5sum = gen_md5sum_value( src )

		lines  = 'script_file' + str(idx) + '="' + opath + '"\n'
		lines += 'script_md5sum' + str(idx) + '="' + md5sum + '"\n'
		return lines

	def __copy_script( self, dstDir ):
		try:
			shutil.copy( self.script.src, dstDir )
			self.script.src = os.path.join( dstDir, os.path.basename(self.script.src) )
			return True
		except:
			traceback.print_exc()
			logging.error( 'copy script failed in:'+str(self) )
			return False

	def __copy_tool_files( self, dstDir ):
		try:
			if self.fileBlock:
				for tfile in self.fileBlock.fileList:
					shutil.copy( tfile.src, dstDir )
					tfile.src = os.path.join( dstDir, os.path.basename(tfile.src) )

			return True
		except:
			traceback.print_exc()
			logging.error( 'copy tool files failed in:'+str(self) )
			return False


