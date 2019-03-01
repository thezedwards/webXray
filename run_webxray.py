"""
	Welcome to webxray!

	This file may be all you are ever be exposed to.  It has an interactive mode
		'-i' or no flag, which is what most people will need for small to moderate sets of pages (eg < 10k).
	
	If you are doing big sets you may want to use the unattended options 
		to collect ('-c') and analyze ('-a').
	
	Run with '-h' for details.
"""

# test we are on right version of python
import sys
if sys.version_info[0] < 3 or sys.version_info[1] < 4:
	print('******************************************************************************')
	print(' Python 3.4 or above is required for webXray; please check your installation. ')
	print('******************************************************************************')
	quit()

# import standard python packages
import os
import re
import time
from optparse import OptionParser

###################
# GLOBAL SETTINGS #
###################

# BROWSER SELECTION
# 	browser_type can be chrome or phantomjs
#	chrome is default
browser_type = 'chrome'

# BROWSER WAIT TIME
#	in order to give time for all elements to load the browser will wait for a set ammount of time
#	 DECREASING means faster collection, but you may miss slow-loading elements
#	 INCREASING means slower collection, but higher likelihood of getting slow-loading elements
#
#	extensive testing has determined 45 seconds performs well, and you are advised to keep it there,
#		but you may adjust to taste and network conditions
#		for example, on a very slow connection you may want to use 60 seconds
#
#	when using chrome a wait time below 30 seconds often results in lost cookies and is NOT RECCOMENDED!
browser_wait = 45

# PERFORMANCE: RUNNING PARALLEL BROWSING ENGINES
#	'pool_size' sets how many browser processes get run in parallel, 
#	by default it is set to 1 so no parallel processes are run
#	setting this to 'None' will use all available cores and is reccomended 
#		if doing over 1k pages
#
#	note that with manual tweaking the pool can be larger than the number
#		of available cores, but proceed with caution
pool_size = 1

# DATABASE ENGINE SELECTION
# 	db_engine can be 'mysql', 'postgres', or 'sqlite'
#	sqlite requires no configuation, but mysql and postgres
#		need user/pw set up in the relevant driver in the 
#		./webxray directory
db_engine = 'sqlite'

# set up database connection
if db_engine == 'mysql':
	from webxray.MySQLDriver import MySQLDriver
	sql_driver = MySQLDriver()
elif db_engine == 'sqlite':
	from webxray.SQLiteDriver import SQLiteDriver
	sql_driver = SQLiteDriver()
elif db_engine == 'postgres':
	from webxray.PostgreSQLDriver import PostgreSQLDriver
	sql_driver = PostgreSQLDriver()
else:
	print('INVALED DB ENGINE FOR %s, QUITTING!' % db_engine)
	quit()

####################
# HELPER FUNCTIONS #
####################

def select_wbxr_db():
	"""
	databases are stored with a prefix (default 'wbxr_'), this function helps select a database in interactive mode
	"""

	# you can optionally specify a different prefix here by setting "db_prefix = '[PREFIX]'"
	wbxr_dbs = sql_driver.get_wbxr_dbs_list()
	wbxr_dbs.sort()

	if len(wbxr_dbs) == 0:
		print('''\t\tThere are no databases to analyze, please try [C]ollecting data or 
				import an existing wbxr-formatted database manually.''')
		interaction()
		return

	for index,db_name in enumerate(wbxr_dbs):
		print('\t\t[%s] %s' % (index, db_name))

	max_index = len(wbxr_dbs)-1
	
	# interaction step: loop until we get acceptable input
	while True:
		selected_db_index = input("\n\tPlease select database by number: ")
		if selected_db_index.isdigit():
			selected_db_index = int(selected_db_index)
			if selected_db_index >= 0 and selected_db_index <= max_index:
				break
			else:
				print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
				continue
		else:
			print('\t\t You entered an invalid string, please select a number in the range 0-%s.' % max_index)
			continue

	db_name = wbxr_dbs[selected_db_index]
	return db_name
# select_wbxr_db

def quit():
	print('------------------')
	print('Quitting, bye bye!')
	print('------------------')
	sql_driver.close()
	exit()
# quit

def interaction():
	"""
	primary interaction function, most people should only be exposed to this
	"""

	print('\tWould you like to:')
	print('\t\t[C] Collect Data')
	print('\t\t[A] Analyze Data')
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
					print('\tNew db name is "%s"' % db_name)
					break
				else:
					print('\tName was invalid, try again.')
					continue
			sql_driver.create_wbxr_db(db_name)

		elif selection == 'a':	
			# collect - add to db
			print('\t---------------------------')
			print('\tAdding to Existing Database')
			print('\t---------------------------')
			print('\tThe following webXray databases are available:')
			
			db_name = select_wbxr_db()
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
		
		if len(files) is 0:
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

		print('\t-----------------------------------------------------------')
		print('\tThe following webXray databases are available for anlaysis:')
		print('\t-----------------------------------------------------------')
		
		db_name = select_wbxr_db()

		print('\tUsing database: %s' % db_name)

		# go do the report now
		analyze(db_name)
		
		# restart interaction
		interaction()
# interaction

def collect(db_name, pages_file_name):
	"""
	manage the loading of pages, extracting relevant data, and storing to db
	may also be called in stand-alone with 'run_webxray.py -c [DB_NAME] [PAGE_FILE_NAME]'
	"""

	from webxray.Collector import Collector
	collector = Collector(db_engine, db_name, pages_file_name, [browser_type], browser_wait)
	collector.run(pool_size)
# collect

def analyze(db_name):
	"""
	perform analysis, generate reports and store them in ./reports
	may also be called in stand-alone with 'run_webxray.py -a [DB_NAME]'
	"""

	from webxray.Analyzer import Analyzer
	
	# set how many tlds you want to produce sub-reports for
	num_tlds	= None

	# set reports to only get the top X results, set to None to get everything
	num_results	= 100

	# set up a new analyzer
	analyzer = Analyzer(db_engine, db_name, num_tlds, num_results)

	# this is the full suite of reports, comment out those you don't need
	analyzer.generate_db_summary_report()
	analyzer.generate_stats_report()
	analyzer.generate_aggregated_tracking_attribution_report()
	analyzer.generate_use_report()
	analyzer.generate_3p_domain_report()
	analyzer.generate_3p_element_report()
	analyzer.generate_3p_element_report('javascript')
	analyzer.generate_3p_element_report('image')
	analyzer.generate_data_transfer_report()
	analyzer.generate_aggregated_3p_ssl_use_report()
	
	# the following reports may produce very large files, you have been warned
	# analyzer.generate_per_page_data_flow_report()
	analyzer.generate_network_report()
	analyzer.print_runtime()
# report

def single(url):
	"""
	for one-off analyses printed to CLI, avoids db calls entirely
	"""

	from webxray.SingleScan import SingleScan
	single_scan = SingleScan(browser_type)
	single_scan.execute(url, browser_wait)
# single

if __name__ == '__main__':
	print('''   
	             | |                        
	__      _____| |____  ___ __ __ _ _   _ 
	\ \ /\ / / _ \ '_ \ \/ / '__/ _` | | | |
	 \ V  V /  __/ |_) >  <| | | (_| | |_| |
	  \_/\_/ \___|_.__/_/\_\_|  \__,_|\__, |
	                                   __/ |
	                                  |___/ 
                            	   	  [v 2.1]
    ''')

	# set up cli args
	parser = OptionParser()
	parser.add_option('-i', action='store_true', dest='interactive', help='Interactive Mode: Best for Small/Medium Size Datasets')
	parser.add_option('-a', action='store_true', dest='analyze', help='Analyze Unattended: Best for Large Datasets - Args: [db_name]')
	parser.add_option('-c', action='store_true', dest='collect', help='Collect Unattended: Best for Large Datasets - Args: [db_name] [page_file_name]')
	parser.add_option('-s', action='store_true', dest='single', help='Single Site: for One-Off Tests - Args [url to analyze]')
	(options, args) = parser.parse_args()

	mode_count = 0
	
	# set mode, make sure we don't have more than one specified
	if options.interactive:
		mode = 'interactive'
		mode_count += 1 

	if options.analyze:
		mode = 'analyze'
		mode_count += 1
		
	if options.collect:
		mode = 'collect'
		mode_count += 1
		
	if options.single:
		mode = 'single'
		mode_count += 1
		
	# if nothing is specified we do interactive
	if mode_count == 0:
		mode = 'interactive'
	elif mode_count > 1:
		print('Error: Too many modes specified, only one allowed!')
		parser.print_help()
		quit()

	# do what we're supposed to do		
	if mode == 'interactive':
		interaction()
	elif mode == 'analyze':
		try:
			db_name = args[0]
		except:
			print('Need a db name!')
			quit()
		analyze(db_name)
	elif mode == 'collect':
		try:
			db_name = args[0]
			page_file = args[1]
		except:
			print('Need a db name and pages file name!')
			quit()
		collect(db_name, page_file)
	elif mode == 'single':
		try:
			url = args[0]
		except:
			print('URL needs to be supplied as an argument!')
			quit()
		single(url)
	quit()
# main
