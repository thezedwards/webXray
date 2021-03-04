# standard lib
import bz2
import json
import base64
import hashlib

# custom classes
from webxray.OutputStore		import OutputStore
from webxray.PostgreSQLDriver	import PostgreSQLDriver

class Server:
	"""
	The server runs as a flask application which is served by NGINX.

	The server loads its configuration data whenever it is called and thus 
		changes made to wbxr_server_config are immediately made active.

	The server manages several primary tasks:
		- filtering incoming requests based on whitelisted client_ips (stored in server_config db)
		- responding to requests for scanning tasks from remote scan nodes
		- either immediately processing and storing, or queuing, results from scans

	TODO Items:
		- currently we rely on ip whitelisting, but we could move to an authentication scheme
			for clients with unstable ip addrs
	"""

	def __init__(self):
		"""
		Set up our server configuration here.

		Note we store config details in server_config.json
			because __init__ is run each time a worker
			processes a request this means we can
			modify our config on the fly without having
			to restart the server
		"""

		# connect to server config db to get client_config
		self.server_sql_driver = PostgreSQLDriver('server_config')

		# important parts of config currently are to
		#	generate our whitelist of allowed ips
		#	and to map our clients to their respective
		#	databases
		self.whitelisted_ips = []
		self.client_id_to_db = {}
		for client in self.server_sql_driver.get_client_configs():
			if client['live']:
				if self.server_sql_driver.check_db_exist(client['mapped_db']):
					self.whitelisted_ips.append(client['client_ip'])
					self.client_id_to_db[client['client_id']] = client['mapped_db']
				else:
					print(f"Database {client['mapped_db']} for client {client['client_id']} does not exist")
	# __init__

	def get_client_task(self, client_ip, client_id):
		"""
		We determine what the client should be doing when it
			sends us a 'READY' message.  If we find a task
			in our queue we sent it back, otherwise we send 'WAIT' 
			and the client will contact us again.
		"""

		# connect to appropriate db for this client, if none found
		#	return wait command
		if client_id in self.client_id_to_db:
			sql_driver = PostgreSQLDriver(self.client_id_to_db[client_id])
		else:
			print('client_id not in client_id_to_db list, returning wait command')
			return {
				'task':'wait'
			}

		# get config for this db
		config = sql_driver.get_config()

		# get client config
		client_config = {}
		for item in config:
			if 'client' in item:
				client_config[item] = config[item]

		# if we have items in task_queue we send them back, otherwise
		#	we sent a wait command
		if sql_driver.get_task_queue_length(max_attempts=config['max_attempts'], unlocked_only=True) != 0:
			# if this fails we wait
			try:
				target, task = sql_driver.get_task_from_queue(max_attempts=config['max_attempts'],client_id=client_id)
			except:
				print('✋ Returning command to wait.')
				return {
					'task':'wait'
				}

			if task == 'get_scan':
				print(f'👉 Returning command to scan {target}')
				return {
					'task'						: 'get_scan',
					'target'					: target,
					'client_config'				: client_config
				}
			elif task == 'get_crawl':
				print(f'👉 Returning command to crawl {target[:30]}...')
				return {
					'task'						: 'get_crawl',
					'target'					: json.loads(target),
					'client_config'				: client_config
				}
			elif task == 'get_policy':
				print(f'👉 Returning command to get_policy {target}')
				return {
					'task'						: 'get_policy',
					'target'					: target,
					'client_config'				: client_config
				}
			elif task == 'get_random_crawl':
				print(f'👉 Returning command to get_random_crawl {target}')
				return {
					'task'						: 'get_random_crawl',
					'target'					: target,
					'client_config'				: client_config
				}
		else:
			print('✋ Returning command to wait.')
			return {
				'task':'wait'
			}
		sql_driver.close()
		del sql_driver
	# get_client_task

	def store_result(self, data):
		"""
		We've gotten data from a client, attempt to store it.
		"""

		# unpack params
		client_id		= data['client_id']
		client_ip		= data['client_ip']
		success			= data['success']
		task			= data['task']
		task_result		= data['task_result']

		# we only load the json string if it is 
		#	not a crawl
		if task != 'get_crawl':
			target = json.loads(data['target'])
		else:
			target = data['target']

		# get db connection from config
		mapped_db = self.client_id_to_db[client_id]

		# create db connection
		if client_id in self.client_id_to_db:
			sql_driver = PostgreSQLDriver(mapped_db)
		else:
			return 'FAIL: client_id not in client_id_to_db list'

		# get config for this db
		config = sql_driver.get_config()

		# if we're not expecting this result we ignore it
		if not sql_driver.is_task_in_queue({'task':task,'target':target}):
			return 'FAIL: task not in queue, ignoring'

		# if browser failed we increment attempts and log the error
		if success == False:
			print(f'👎 Error for {target}: %s' % {task_result})

			# for times we don't want to retry, such as a rejected 
			#	redirect or network resolution failure, this could be expanded
			fail_cases = [
				'reached fail limit',
				'rejecting redirect',
				'did not find enough internal links'
			]
			
			if task_result in fail_cases or 'ERR_NAME_NOT_RESOLVED' in task_result:
				sql_driver.set_task_as_failed(target, task)
			else:
				sql_driver.unlock_task_in_queue(target, task)

			sql_driver.log_error({
				'client_id'	: client_id, 
				'target'	: target,
				'task'		: task,
				'msg'		: task_result
			})
			sql_driver.close()
			del sql_driver
			return 'FAIL'

		# we only need to put the result in the queue, allows
		#	us to respond to clients faster and keep the results
		#	compressed
		self.server_sql_driver.add_result_to_queue({
			'client_id'		: client_id,
			'client_ip'		: client_ip,
			'mapped_db'		: mapped_db,
			'target'		: target,
			'task'			: task,
			'task_result'	: task_result
		})
		
		# close out db connection and send back our response
		sql_driver.close()
		del sql_driver
		return 'OK'
	# store_result

	def process_request(self, request):
		"""
		Process requests from clients here, note we
			only process POST data and ignore GET data.

		IP whitelist checking is performed here, if we implement
			additional security checks that can be done
			here as well.
		"""

		# if we're running behind nginx/gunicorn
		#	we get the ip from the headers otherwise
		#	only flask is running and we get ip from 
		#	request.remote_addr
		if 'X-Real-IP' in request.headers:
			client_ip = request.headers['X-Real-IP']
		else:
			client_ip = request.remote_addr

		# we whitelist the ips we accept commands from
		#	ignore anything not in the list			
		if client_ip not in self.whitelisted_ips:
			# print('ip (%s) not whitelisted!' % client_ip)
			return

		# read the post data from the form
		form = request.form

		# default response is failed, gets overwritten on success
		response = 'FAIL'

		# client is sending us data, store it and send back result (OK/FAIL)
		if 'task_result' in form.keys():
			print(f'📦 got data from {client_ip}')

			# store result can either process it or queue it based on config
			msg = self.store_result({
				'client_id'		: form['client_id'],
				'client_ip'		: client_ip,
				'success'		: json.loads(form['success']),
				'target'		: form['target'],
				'task'			: form['task'],
				'task_result'	: form['task_result']
			})

			# tell the cient what happened
			response = bytes(msg,'utf8')

		# client is ready, send a command back
		if 'ready' in form.keys():
			print(f'🙋‍♂️ got request for command from {client_ip}')
			command_set = json.dumps(self.get_client_task(client_ip, form['client_id']))
			response = bytes(command_set, 'utf8')
		
		# all done
		return(response)
	# process_request
# Server
