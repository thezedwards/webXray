"""
	Welcome to webxray!  This file both launches an interactive mode and is 
		pre-configured to store data in sqlite, which is sufficient for many
		users.  For advanced users, the software supports also a massively
		distributed scan infrastrcture, backend storage in postgres,
		and has been used to build multi-billion record datasets.  Many of
		these options are available via command-line flags.
"""

# standard python packages
import datetime
import multiprocessing
import optparse
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request

# set up database connection
db_engine = 'sqlite'
if db_engine == 'sqlite':
	from webxray.SQLiteDriver import SQLiteDriver
	sql_driver = SQLiteDriver()
elif db_engine == 'postgres':
	from webxray.PostgreSQLDriver import PostgreSQLDriver
	sql_driver = PostgreSQLDriver()
else:
	print('INVALID DB ENGINE FOR %s, QUITTING!' % db_engine)
	quit()

# import our custom utilities
from webxray.Utilities import Utilities
utilities = Utilities(db_engine=db_engine)

# check for various dependencies, python version, etc.
utilities.check_dependencies()

# SET CONFIG
#
# There are a large number of setting for webXray, which are
#	set in a 'config' variable.  Two default configurations are 
#	'haystack' which collects data needed for examining data transfers
#	and 'forensic' which collects everything, including images,
#	page text, and the content of files.  It is A VERY BAD IDEA
#	to conduct forensic scans on lists of random webpages
#	as you may be downloading and storing files you do not want.
#
# Only use forensic when you are TOTALLY SURE you want to retain
#	all site content on your machine.  Advanced users can either
#	edit config details directly in the database or create their
#	own custom config in Utilities.py.
config = utilities.get_default_config('haystack')

# SET NUMBER OF PARALLEL BROWSING ENGINES
#
# 'pool_size' sets how many browser processes get run in parallel, 
#	by default it is set to 1 so no parallel processes are run.
#	Setting this to 'None' will use all available cores on your
#	machine.
pool_size = None


# Set the client_id based on the hostname, you can put in 
#	 a custom value of your choosing as well.
client_id = socket.gethostname()

####################
# HELPER FUNCTIONS #
####################

def quit():
	"""
	Make sure we close the db connection before we exit.
	"""
	print('------------------')
	print('Quitting, bye bye!')
	print('------------------')
	sql_driver.close()
	exit()
# quit

def interaction():
	"""
	Handles user interaction, alternative to command line flags, good
		for most people.
	"""

	print('\tWould you like to:')
	print('\t\t[C] Collect Data')
	print('\t\t[A] Analyze Data')
	print('\t\t[V] Visualize Data')
	print('\t\t[PC] Policy Collect')
	print('\t\t[PA] Policy Analyze')
	print('\t\t[Q] Quit')

	# loop until we get acceptable input
	while True:
		selection = input("\tSelection: ").lower()

		acceptable_input = ['c','a','v','pc','pa','q']
		
		if selection 	== 'q':
			quit()
		elif selection in acceptable_input:
			break
		else:
			print('\t\tInvalid select, please try again.')
			continue

	# we are collecting new data
	if selection == 'c':
		print('\t===============')
		print('\tCollecting Data')
		print('\t===============')
		print('\tWould you like to:')
		print('\t\t[C] Create a New Database')
		print('\t\t[A] Add to an Existing Database')
		print('\t\t[Q] Quit')
	
		# interaction: loop until we get acceptable input
		while True:
			selection = input("\tSelection: ").lower()
		
			if selection 	== 'c':
				break
			elif selection 	== 'a':
				break
			elif selection 	== 'q':
				quit()
			else:
				print('\t\tValid selections are C, A, and Q.  Please try again.')
				continue

		if selection == 'c':
			# collect - new db
			print('\t----------------------')
			print('\tCreating New Database')
			print('\t----------------------')
			print('\tDatabase name must be alpha numeric, and may contain a "_"; maximum length is 20 characters.')

			# interaction: loop until we get acceptable input
			while True:
				db_name = input('\tEnter new database name: ').lower()

				if len(db_name) <= 40 and re.search('^[a-zA-Z0-9_]*$', db_name):
					print(f'\tCreating new db with name {db_name}')
					break
				else:
					print('\tName was invalid, try again.')
					continue
			sql_driver.create_wbxr_db(db_name)
			sql_driver.set_config(config)

		elif selection == 'a':	
			# collect - add to db
			print('\t---------------------------')
			print('\tAdding to Existing Database')
			print('\t---------------------------')
			print('\tThe following webXray databases are available:')
			
			db_name = utilities.select_wbxr_db()
			print('\tUsing database: %s' % db_name)
		
		# we have selected the db to use, now move on to collection	
		print('\t--------------------')
		print('\tSelecting Page List')
		print('\t--------------------')
		print('\tPlease select from the available files in the "page_lists" directory:')

		# webXray needs a file with a list of page urls to scan, these files should be kept in the
		#	'page_lists' directory.  this function shows all available page lists and returns
		#	the name of the selected list.
		files = os.listdir(path='./page_lists')
		
		if len(files) == 0:
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			print('ERROR: No page lists found, check page_lists directory.')
			print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
			quit()

		# alpha sort file list for easier selection
		files.sort()

		# print out pages lists to choose from
		print('\tPage Lists Available:')
		for index,file in enumerate(files):
			print('\t\t[%s] %s' % (index, file))

		# interaction: loop until we get acceptable input
		while True:
			selection = input("\n\tChoose a page list by number: ")
			if selection.isdigit():
				selection = int(selection)
				if selection >= 0 and selection < len(files):
					break
				else:
					print('\tInvalid choice, try again.')
					continue
			else:
				print('\tInvalid choice, try again.')
				continue

		pages_file_name = files[selection]
		
		print('\tPages file is "%s"' % pages_file_name)
		
		print('\t------------------')
		print('\tBeginning webXray')
		print('\t------------------')		
		time.sleep(1)
	
		collect(db_name, pages_file_name)

		print('\t---------------------')
		print('\t Collection Finished!')
		print('\t---------------------')
		
		# let's us go back to analyze
		interaction()
	elif selection == 'a':	
		# analyze
		print('\t==============')
		print('\tAnalyzing Data')
		print('\t==============')

		print('\t----------------------------------------------')
		print('\tThe following webXray databases are available:')
		print('\t----------------------------------------------')
		
		db_name = utilities.select_wbxr_db()

		print('\tUsing database: %s' % db_name)

		# go do the analysis
		analyze(db_name)
		
		# restart interaction
		interaction()
	elif selection == 'pc':	
		# analyze
		print('\t=====================')
		print('\t Collecting Policies ')
		print('\t=====================')

		print('\t----------------------------------------------')
		print('\tThe following webXray databases are available:')
		print('\t----------------------------------------------')
		
		db_name = utilities.select_wbxr_db()

		print('\tUsing database: %s' % db_name)

		# go get the policies
		collect(db_name,task='get_policy')
		
		# restart interaction
		interaction()
	elif selection == 'pa':
		# analyze
		print('\t====================')
		print('\t Analyzing Policies ')
		print('\t====================')

		print('\t----------------------------------------------')
		print('\tThe following webXray databases are available:')
		print('\t----------------------------------------------')
		
		db_name = utilities.select_wbxr_db()

		print('\tUsing database: %s' % db_name)

		# go get the policies
		policy_report(db_name)
		
		# restart interaction
		interaction()
# interaction

def collect(db_name, pages_file_name=None, task='get_scan'):
	"""
	manage the loading of pages, extracting relevant data, and storing to db
	may also be called in stand-alone with 'run_webxray.py -c [DB_NAME] [PAGE_FILE_NAME]'
	"""

	from webxray.Collector import Collector

	# if db doesn't exist, create it
	if sql_driver.db_exists(db_name) == 0:
		print('\t------------------------------')
		print('\tCreating DB: %s' % db_name)
		print('\t------------------------------')
		sql_driver.create_wbxr_db(db_name)
		sql_driver.set_config(config)

	# needed to display runtime info
	start_time = datetime.datetime.now()

	# the main event
	collector = Collector(db_name,db_engine,client_id)
	if task == 'get_scan':
		build_task_queue(db_name, 'get_scan', pages_file_name=pages_file_name)
	elif task=='get_policy':
		build_task_queue(db_name, 'get_policy')
	elif task=='get_random_crawl':
		build_task_queue(db_name, 'get_random_crawl', pages_file_name=pages_file_name)

	collector.run(task='process_tasks_from_queue', pool_size=pool_size)

	# fyi
	utilities.print_runtime('Data collection', start_time)
# collect

def build_task_queue(db_name, task, pages_file_name=None, crawl_file_name=None):
	"""
	builds the queue of pages to be scanned, does no scanning itself, can 
		only be called by CLI
	"""

	from webxray.Collector import Collector

	# if db doesn't exist, create it
	if sql_driver.db_exists(db_name) == 0:
		print('\t------------------------------')
		print('\tCreating DB: %s' % db_name)
		print('\t------------------------------')
		sql_driver.create_wbxr_db(db_name)
		sql_driver.set_config(config)

	# needed to display runtime info
	start_time = datetime.datetime.now()

	# the main event
	collector = Collector(db_name,db_engine,client_id)
	if task == 'get_scan':
		print('\t---------------------------------')
		print('\t Adding page scans to task queue ')
		print('\t---------------------------------')

		collector.build_scan_task_queue(params = {
			'pages_file_name'		: pages_file_name, 
			'flush_scan_task_queue'	: True,
			'task'					: 'get_scan'
		})
	elif task == 'get_random_crawl':
		print('\t-----------------------------------------')
		print('\t Adding random crawl scans to task queue ')
		print('\t-----------------------------------------')

		collector.build_scan_task_queue(params = {
			'pages_file_name'		: pages_file_name, 
			'flush_scan_task_queue'	: True,
			'task'					: 'get_random_crawl'
		})
	elif task == 'get_crawl':
		print('\t-----------------------------')
		print('\t Adding crawls to task queue ')
		print('\t-----------------------------')
		collector.build_crawl_task_queue(params = {
			'crawl_file_name'			: crawl_file_name,
			'flush_crawl_task_queue'	: True
		})
	elif task == 'get_policy':
		print('\t-----------------------------------')
		print('\t Adding policy scans to task queue ')
		print('\t-----------------------------------')
		collector.build_policy_task_queue(flush_policy_task_queue=True)

	# fyi
	utilities.print_runtime('Build task queue', start_time)
# build_task_queue

def worker_collect(db_name):
	"""
	manage the loading of pages, extracting relevant data, and storing to db
	may also be called in stand-alone with 'run_webxray.py --worker [DB_NAME]'
	"""

	from webxray.Collector import Collector

	# needed to display runtime info
	start_time = datetime.datetime.now()

	# the main event
	collector = Collector(db_name,db_engine,client_id)
	collector.run(task='process_tasks_from_queue', pool_size=pool_size)

	# fyi
	utilities.print_runtime('Data collection', start_time)
# worker_collect

def analyze(db_name):
	"""
	perform analysis, generate reports and store them in ./reports
	may also be called in stand-alone with 'run_webxray.py -a [DB_NAME]'
	"""

	from webxray.Reporter import Reporter

	# needed to display runtime info
	start_time = datetime.datetime.now()
	
	# set how many tlds you want to produce sub-reports for
	num_tlds	= None

	# set reports to only get the top X results, set to None to get everything
	num_results	= 500

	# set up a new reporter
	reporter = Reporter(db_name, db_engine, num_tlds, num_results, flush_domain_owners=True)

	# this is the main suite of reports, comment out those you don't need
	reporter.generate_db_summary_report()
	reporter.generate_stats_report()
	reporter.generate_aggregated_tracking_attribution_report()
	reporter.generate_3p_domain_report()
	reporter.generate_3p_request_report()
	reporter.generate_3p_request_report('script')
	reporter.generate_use_report()

	# the following reports may produce very large files and are off by default
	reporter.generate_per_site_network_report()
	# reporter.generate_per_page_network_report()
	# reporter.generate_all_pages_request_dump()
	# reporter.generate_all_pages_cookie_dump()

	# fyi
	utilities.print_runtime('Report generation', start_time)
# analyze

def single(url):
	"""
	For one-off analyses printed to CLI, avoids db calls entirely
	"""

	from webxray.SingleScan import SingleScan
	single_scan = SingleScan()
	single_scan.execute(url, haystack_config)
# single

def policy_report(db_name):
	"""
	perform of policies, generate reports and store them in ./reports
	may also be called in stand-alone with 'run_webxray.py -p [DB_NAME]'
	"""

	from webxray.Reporter import Reporter

	# needed to display runtime info
	start_time = datetime.datetime.now()
	
	# set how many tlds you want to produce sub-reports for
	num_tlds	= None

	# set reports to only get the top X results, set to None to get everything
	num_results	= 100

	# set up a new reporter
	reporter = Reporter(db_name, db_engine, num_tlds, num_results, flush_domain_owners=True)

	# do relevant policy reports
	reporter.initialize_policy_reports()
	reporter.generate_policy_summary_report()
	reporter.generate_policy_owner_disclosure_reports()
	reporter.generate_policy_gdpr_report()
	reporter.generate_policy_pacification_report()
	reporter.generate_policy_pii_report()

	# fyi
	utilities.print_runtime('Report generation', start_time)
# policy_report

def rate_estimate(db_name, client_id):
	"""
	Tells us how much longer to go...
	"""
	print('Showing scan rate for database %s' % db_name)
	if client_id:
		print('\tclient_id is %s' % client_id)
	else:
		client_id = None

	print()
	print()

	print('elapsed_minutes\tcurrent_rate\taverage_rate\tremaining_tasks\tremaining_hours')
	print('---------------\t------------\t------------\t---------------\t---------------')
	utilities = Utilities(db_name=db_name,db_engine=db_engine)
	for result in utilities.stream_rate():
		print('%s\t\t%s\t\t%s\t\t%s\t\t%s' % (
				result[client_id]['elapsed_minutes'],
				result[client_id]['current_rate'],
				result[client_id]['average_rate'],
				result[client_id]['remaining_tasks'],
				result[client_id]['remaining_hours']
			)
		)

# rate_estimate

def store_results_from_queue():
	"""
	If we have results in our result_queue we will
		process/store them.  Can be run in parallell
		with server if set to queue results.
	"""
	from webxray.Collector import Collector
	collector = Collector(db_engine=db_engine)
	collector.run(task='store_results_from_queue', pool_size=pool_size)
# store_results_from_queue

def run_client():
	"""
	Start the remote client, note this only performs scans
		and uploads to the server and runs until stopped.
	
	However, since Chrome can crash it is a good idea
		to have this restarted periodically by a 
		cron job.

	"""
	from webxray.Client import Client
	client = Client('https://wbxrcac.andrew.cmu.edu', pool_size=pool_size)
	client.run_client()
# run_client

if __name__ == '__main__':
	print('''   
               _   __  __                
 __      _____| |__\ \/ /_ __ __ _ _   _ 
 \ \ /\ / / _ \ '_ \\\\  /| '__/ _` | | | |
  \ V  V /  __/ |_) /  \| | | (_| | |_| |
   \_/\_/ \___|_.__/_/\_\_|  \__,_|\__, |
                                   |___/
		[Forensic Edition v1.0]
    ''')

	# set up cli args
	parser = optparse.OptionParser()
	parser.add_option(
		'--scan_pages',	
		action='store_true',
		dest='scan_pages',
		help='Scan Pages: Only scan URL specified - Args: [db_name] [page_file_name]'
	)
	parser.add_option(
		'--crawl_sites',	
		action='store_true',
		dest='crawl_sites',
		help='Crawl Sites: Scan URL specified and 3 random internal pages - Args: [db_name] [page_file_name]'
	)
	parser.add_option(
		'--build_queue',
		action='store_true',
		dest='build_queue',
		help='Build page queue: Should be run on db server, leave scanning to workers - Args: [db_name] [page_file_name or crawl_file_name]'
	)
	parser.add_option(
		'--worker',
		action='store_true',
		dest='worker',
		help='Collect Unattended as Worker: Simpler Alternative to Distributed Client - Args: [db_name]'
	)
	parser.add_option(
		'-s',
		action='store_true',
		dest='single',
		help='Single Site: for One-Off Tests - Args [url to analyze]'
	)
	parser.add_option(
		'-a',
		action='store_true',
		dest='analyze',
		help='Analyze Unattended: Best for Large Datasets - Args: [db_name]'
	)
	parser.add_option(
		'--policy_collect',
		action='store_true',
		dest='policy_collect',
		help='Policy Collect Unattended: Best for Large Datasets - Args: [db_name]'
	)
	parser.add_option(
		'--policy_analyze',
		action='store_true',
		dest='policy_report',
		help='Policy Report Unattended: Best for Large Datasets - Args: [db_name]'
	)
	parser.add_option(
		'--rate',
		action='store_true',
		dest='rate_estimate',
		help='Estimates time remaining on scan - Args: [db_name]'
	)
	parser.add_option(
		'--store_queue',
		action='store_true',
		dest='store_results_from_queue',
		help='Stores any results in the queue - Args: [db_name]'
	)
	parser.add_option(
		'--run_client',
		action='store_true',
		dest='run_client',
		help='Runs the distributed client'
	)
	(options, args) = parser.parse_args()

	# set mode
	if options.scan_pages:
		mode = 'scan_pages'
	elif options.crawl_sites:
		mode = 'crawl_sites'
	elif options.build_queue:
		mode = 'build_queue'
	elif options.store_results_from_queue:
		mode = 'store_results_from_queue'
	elif options.worker:
		mode = 'worker'
	elif options.single:
		mode = 'single'
	elif options.analyze:
		mode = 'analyze'
	elif options.policy_collect:
		mode = 'policy_collect'
	elif options.policy_report:
		mode = 'policy_report'
	elif options.rate_estimate:
		mode = 'rate_estimate'
	elif options.run_client:
		mode = 'run_client'
	else:
		mode = 'interactive'

	# do what we're supposed to do		
	if mode == 'interactive':
		interaction()
	elif mode == 'scan_pages':
		try:
			db_name 		= args[0]
			pages_file_name = args[1]
		except:
			print('Need a db name and pages file name!')
			quit()
		collect(db_name, pages_file_name=pages_file_name, task='get_scan')
	elif mode == 'crawl_sites':
		try:
			db_name 		= args[0]
			pages_file_name = args[1]
		except:
			print('Need a db name and pages file name!')
			quit()
		collect(db_name, pages_file_name=pages_file_name, task='get_random_crawl')
	elif mode == 'single':
		try:
			url = args[0]
		except:
			print('URL needs to be supplied as an argument!')
			quit()
		single(url)
	elif mode == 'analyze':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		analyze(db_name)
	
	elif mode == 'policy_collect':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		collect(db_name,task='get_policy')
	
	elif mode == 'policy_report':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		policy_report(db_name)
	
	elif mode == 'worker':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		worker_collect(db_name)

	elif mode == 'build_queue':
		try:
			db_name = args[0]
			task = args[1]
		except:
			print('Need a db name and task name')
			quit()

		# if we are doing get_scan we also need a page file name
		if task == 'get_scan' or task == 'get_random_crawl':
			try:
				page_file = args[2]
			except:
				print('Need a page file name for get_scan')
				quit()
			build_task_queue(db_name, task, pages_file_name=page_file)
		elif task == 'get_crawl':
			try:
				page_file = args[2]
			except:
				print('Need a crawl file name for get_crawl')
				quit()
			build_task_queue(db_name, task, crawl_file_name=page_file)
		else:
			# get_policy
			build_task_queue(db_name, task)

	elif mode == 'store_results_from_queue':
		store_results_from_queue()

	elif mode == 'rate_estimate':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		try:
			client_id = args[1]
		except:
			client_id = None
		rate_estimate(db_name,client_id)

	elif mode == 'run_client':
		run_client()
	quit()
# main
