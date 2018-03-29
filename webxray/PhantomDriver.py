# standard python packages
import os
import re
import json
import subprocess

class PhantomDriver:
	"""
	This class allows for using the PhantomJS browser with webXray.
	
	Requirements are phantomjs 1.9+ which is run under the subprocess module.

	Pros:
		Very low CPU/Mem over head
		Extensive testing, very stable
		User-Agent randomization works very well
	Cons:
		The phantomjs project is likely being discontinued!
		Not a 'real' browser
	"""

	def __init__(self):
		"""
		the main purpose of the init is to make sure we have the correct
			version of phantomjs installed and to build the command string
			with the appropriate arguments to allow bad ssl configs to load
		"""

		# the following can be changed as needed
		# on some systems it may work by default
		phantomjs_binary_path = None

		# first check is phantomjs version is ok
		if phantomjs_binary_path:
			process = subprocess.Popen(phantomjs_binary_path+' --version', shell=True, stdout=subprocess.PIPE)
		else:
			process = subprocess.Popen('phantomjs --version', shell=True, stdout=subprocess.PIPE)

		try:
			output, errors = process.communicate()
		except Exception as e:
			process.kill()
			print('phantomjs not returning version number, something must be wrong, check your installation!')
			exit()
		
		try:
			self.phantomjs_version = float(output.decode('utf-8')[:3])
		except:
			print('phantomjs not returning version number, something must be wrong, check your installation!')
			exit()

		if self.phantomjs_version < 1.9:
			print('you are running phantomjs version %s, webXray requires at least 1.9' % self.phantomjs_version)
			exit()

		# build the command_string, path is relative from root webxray directory
		if phantomjs_binary_path:
			self.command_string = phantomjs_binary_path+' --ignore-ssl-errors=true --ssl-protocol=any '+os.path.dirname(os.path.abspath(__file__))+'/resources/phantomjs_scripts/wbxr_logger.js'
		else:
			self.command_string = 'phantomjs --ignore-ssl-errors=true --ssl-protocol=any '+os.path.dirname(os.path.abspath(__file__))+'/resources/phantomjs_scripts/wbxr_logger.js'
	# __init__

	def get_webxray_scan_data(self, url, browser_wait):
		"""
		this function uses subprocess to spawn a phantomjs browser
			which returns json over the CLI
		the json is cleaned up and decoded as utf-8 and returns
			something nice to the calling function
		"""

		# build command string to pass over CLI
		command = '%s %s "%s"' % (self.command_string, browser_wait, url.replace('"','\"'))
		process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)

		# we use an additional timeout to allow phantomjs to finish running
		#	and add 15 seconds to allow for extra lag with phantomjs/os
		# 	but if we get nothing after number of seconds specified, we kill the 
		#	process and move on
		timeout = browser_wait+15
		try:
			output, errors = process.communicate(timeout=timeout)
		except Exception as e:
			process.kill()
			return None

		# output can be messy, decode utf-8 to save heartache
		phantom_output = ''
		for out_line in output.splitlines():
			phantom_output += out_line.decode('utf-8')

		# the phantomjs output is a json string, read it
		try:
			data = json.loads(re.search('(\{.+\})', phantom_output).group(1))
		except:
			return None

		# other parts of webxray expect this data format, common to all browser drivers used
		return_dict = {
			'browser_type':			'phantomjs',
			'browser_version':		self.phantomjs_version,
			'browser_wait':			browser_wait,
			'start_url':			url,
			'final_url': 			data['final_url'],
			'title': 				data['title'],
			'meta_desc': 			data['meta_desc'],
			'load_time': 			data['load_time'],
			'processed_requests': 	data['processed_requests'],
			'cookies': 				data['cookies'],
			'all_links':			data['all_links'],
			'source':				data['source']
		}
		
		return return_dict
	# get_webxray_scan_data
# PhantomDriver
