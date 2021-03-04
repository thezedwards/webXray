# standard python
import base64
import bz2
import datetime
import json
import multiprocessing
import optparse
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request

# custom browser driver
from webxray.ChromeDriver import ChromeDriver

class Client:
	def __init__(self, server_url, pool_size=None):
		"""
		Init allows us to set a custom pool_size, otherwise
			we base on CPU count.
		"""

		self.server_url = server_url

		if pool_size:
			self.pool_size = pool_size
		else:
			self.pool_size = multiprocessing.cpu_count()
	# __init__

	def get_and_process_client_tasks(self,proc_num):
		"""
		This is the main loop that should run indefintely. Purpose is to
			send server "ready" message to get tasks which are either wait,
			get_scan, or get_policy.  If unable to get commands it will
			wait and try again in 5 seconds.  If command is get_scan or
			get_policy, the appropriate action will be taken and results
			will be sent as POST data back to server.
		"""

		local_test = False
		debug = True

		if local_test:
			client_id = 'local_client'
			wbxr_server_url = 'http://127.0.0.1:5000/'
		else:
			client_id = socket.gethostname()
			wbxr_server_url = self.server_url
		 
		if debug: print(f'{client_id} [{proc_num}]\t😀 starting')

		# main loop
		while True:

			# set up request
			request = urllib.request.Request(
				wbxr_server_url,
				headers = {
					'User-Agent' : 'wbxr_client_v0_0',
				}
			)

			data = urllib.parse.urlencode({'ready':True,'client_id':client_id})
			data = data.encode('utf8')

			# attempt to get commands
			if debug: print(f'[{proc_num}]\t📥 fetching commands')

			try:
				command_params = json.loads(urllib.request.urlopen(request,data,timeout=60).read().strip().decode('utf-8'))
			except:
				print(f'[{proc_num}]\t👎 Unable to contact server, will wait and try again.')
				time.sleep(5)
				continue

			# process commands
			task = command_params['task']
			
			print('[%s]\t👉 TASK IS: %s' % (proc_num, task))
			if task == 'wait':
				time.sleep(10)
				continue # restarts main loop
			elif task == 'get_scan' or task == 'get_policy' or task == 'get_crawl' or task == 'get_random_crawl':
				target 			= command_params['target']
				client_config 	= command_params['client_config']
			else:
				print(f'[{proc_num}]\t🥴 CANNOT READ COMMAND SET, EXITING')
				return

			if debug: print('[%s]\t🚗 setting up driver' % proc_num)
			
			if client_config['client_browser_type'] == 'chrome':
				browser_driver 	= ChromeDriver(client_config, port_offset=proc_num)
			else:
				print('[%s]\t🥴 INVALID BROWSER TYPE, HARD EXIT!' % proc_num)
				exit()

			print(f'[{proc_num}]\t🏃‍♂️ GOING TO {task} on {str(target)[:30]}...')
			
			if task == 'get_scan':
				task_result = browser_driver.get_scan(target)
			elif task == 'get_crawl':
				task_result = browser_driver.get_crawl(target)
			elif task == 'get_policy':
				task_result = browser_driver.get_scan(target, get_text_only=True)
			elif task == 'get_random_crawl':
				task_result = browser_driver.get_random_crawl(target)

			# unpack result
			success 	= task_result['success']
			task_result	= task_result['result']

			# if scan was successful we will have a big chunk of data
			#	so we compress it to speed up network xfer and reduce disk
			#	utilization while it is in the result queue
			if success:
				if debug: print(f'[{proc_num}]\t🗜️ compressing output for {str(target)[:30]}...')
				task_result = base64.urlsafe_b64encode(bz2.compress(bytes(json.dumps(task_result),'utf-8')))

			# build request to post results to server
			if debug: print(f'[{proc_num}]\t📤 returning output')
			data = urllib.parse.urlencode({
				'client_id'		: client_id, 
				'success'		: json.dumps(success),
				'target'		: json.dumps(target),
				'task'			: task,
				'task_result' 	: task_result
			})

			data = data.encode('utf-8')

			# send the request
			request = urllib.request.Request(
				wbxr_server_url,
				headers = {
					'User-Agent' : 'wbxr_client_v0_0',
				}
			)

			# adding charset parameter to the Content-Type header.
			request.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")

			# note we can lose this result
			try:
				print(f'[{proc_num}]\t📥 RESPONSE: %s' % (urllib.request.urlopen(request,data,timeout=600).read().decode('utf-8')))
				continue
			except:
				print(f'[{proc_num}]\t😖 Unable to post results!!!')
				time.sleep(5)

		return
	# get_and_process_client_tasks

	def run_client(self):
		if sys.platform == 'darwin' and multiprocessing.get_start_method(allow_none=True) != 'forkserver':
			multiprocessing.set_start_method('forkserver')

		# processes all need a number, this also gets
		#	used as a port offset
		proc_nums = []
		for i in range(0,self.pool_size):
			proc_nums.append(i)

		# start workers
		myPool = multiprocessing.Pool(self.pool_size)
		myPool.map(self.get_and_process_client_tasks, proc_nums)
	# run_client
# Client