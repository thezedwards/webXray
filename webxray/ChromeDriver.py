# standard python packages
import os
import re
import json
import time
import random
import sqlite3

# check if non-standard packages are installed
try:
	from selenium import webdriver
	from selenium.webdriver.chrome.options import Options
except:
	print('*****************************************************************')
	print(' FATAL ERROR: Selenium is not installed, required to use Chrome! ')
	print('*****************************************************************')
	exit()

class ChromeDriver:
	"""
	This class allows for using the production Chrome browser with webXray.
	Requirements are Selenium, Chrome, and ChromeDriver.

	Pros:
		Production browser which is largely identical to real-world use
		By turning headless off it is very similar to a 'real' session
		By turning headless on the CPU/Mem usage is lower than otherwise
	Cons:
		Less testing with webxray than phantomjs, does not handle many paralell instances very well
		In headless mode prior to 64.0.3254.0, the cookie database does not get created and no cookies are returned
	"""

	def __init__(self,ua=False):
		"""
		set various global options here
		"""

		# set here if you want to use headless mode for Chrome
		self.headless = True

		# if you want to get potentially dangerous requests, set 
		#	this to true.
		# false by default for hopefully obvious reasons
		self.allow_insecure = False

		# if you have trouble getting chrome to start
		#	change these values manually
		self.chromedriver_path = None
		self.chrome_binary_path = None

		# we want to give our browsers a full minute to try to
		#	download content, but gracefully timeout thereafter
		self.page_timeout_seconds = 60

		# Set ua if we have it, see get_ua_for_headless
		#	for details
		self.ua = ua
		
		return None
	# init

	def create_chromedriver(self):
		"""
		Since we have many functions we can perform we consolidate
			chromedriver code here.
		"""

		# set up options object
		chrome_options = Options()

		# if we have chrome binary set it up
		if self.chrome_binary_path:
			chrome_options.binary_location = self.chrome_binary_path
		
		# live dangerously
		if self.allow_insecure:
			chrome_options.add_argument('--allow-running-insecure-content')

		# thank god for this option
		chrome_options.add_argument('--mute-audio')
		
		# if we are headless we also mix up window size a bit
		if self.headless:
			chrome_options.add_argument('headless')
			chrome_options.add_argument('disable-gpu')
			window_x = random.randrange(1050,1920)
			window_y = random.randrange(900,1080)
			chrome_options.add_argument('window-size=%sx%s' % (window_x,window_y))

		# if we have a ua set it here
		if self.ua: 
			chrome_options.add_argument('user-agent='+self.ua)

		# attempt to start driver, fail gracefull otherwise
		try:
			# if we have chromedriver path set it up
			if self.chromedriver_path:
				driver = webdriver.Chrome(
					self.chromedriver_path,
					desired_capabilities={'loggingPrefs': {'performance': 'ALL'}},
					chrome_options=chrome_options
				)
			else:
				driver = webdriver.Chrome(
					desired_capabilities={'loggingPrefs': {'performance': 'ALL'}},
					chrome_options=chrome_options
				)
		except:
			print('Unable to start Chrome!')
			return None

		# allow one minute before we kill it, seperate from browser_wait
		driver.set_page_load_timeout(self.page_timeout_seconds)

		return driver
	# init_headless_driver

	def get_ua_for_headless(self):
		"""
		Using chrome in headless sends a 'Headless' ua string,
			here we figure out the current ua and remove the 
			'Headless' part to help with compatability

		This requires firing up a new browser instance
			and destroying it, so this should be called once
			and resused if possible and this is not in
			__init___ on purpose
		"""
		driver = self.create_chromedriver()
		if driver != None:
			ua = driver.execute_script('return navigator.userAgent')
			driver.quit()
			return ua.replace('Headless','')
		else:
			return None
	# get_ua_for_headless

	def get_webxray_scan_data(self, url, browser_wait):
		"""
		This function loads the page, monitors network traffic, and returns relevant data/logs.

		IMPORTANT: headless will miss all cookies in chrome versions < 64.0.3254.0

		This uses the chrome performance log to get network traffic details, see following for details:
			- https://gist.githubusercontent.com/klepikov/5457750/raw/ecedc6dd4eed82f318db91adb923627716fb6b58/test.py
			- https://sites.google.com/a/chromium.org/chromedriver/logging/performance-log
		"""

		driver = self.create_chromedriver()

		# browser hasn't started and error already printed to cli
		if driver == None: return None

		# allow one minute before we kill it, seperate from browser_wait
		driver.set_page_load_timeout(60)

		# start the page load process, return nothing if we fail
		try:
			driver.get(url)
		except:
			# quit the driver or it will never die!
			driver.quit()
			return None

		# if the page has an alert window open it will throw the following exception when trying
		#	to get the current_url: selenium.common.exceptions.UnexpectedAlertPresentException
		# in theory we should be able to set an option for UNEXPECTED_ALERT_BEHAVIOUR to ACCEPT
		# 	but it does not seem to be supported by chromedriver at present
		# in some cases we can catch the items we need before an alert fires, otherwise
		# 	we fail gracefully, but this is a bug that needs resolution
		try:
			final_url = driver.current_url
			title = driver.title
			page_source = driver.page_source
		except:
			# quit the driver or it will never die!
			driver.quit()
			return None

		# handle odd bug where title is a 'webelement' object
		if not isinstance(title, str): title = None

		# while the browser may be finished loading the page, scripts may still making
		# 	additional requests, so we wait to let all that finish
		time.sleep(browser_wait)

		# keep all requests in a dict keyed to the requestID
		# before export we re-key the requests to the url
		requests = {}

		# use the chrome performance log to find Network events for requests sent, received, and loading finished
		for item in driver.get_log('performance'):
			for key,val in item.items():
				if key == 'message':
					data = json.loads(val)

					if data['message']['method'] == 'Network.requestWillBeSent':
						# initialize the key in the dict so we can add to it
						if data['message']['params']['requestId'] not in requests:
							requests[data['message']['params']['requestId']] = {}
						
						# we set received to false to start with
						requests[data['message']['params']['requestId']].update({'received':False})

						# this will be the new key before we return
						requests[data['message']['params']['requestId']].update({'url':data['message']['params']['request']['url']})

						# each request has a start_time, we use this to figure out the time it took to download
						requests[data['message']['params']['requestId']].update({'start_time':data['message']['params']['timestamp']})
						
						# get the request headers
						requests[data['message']['params']['requestId']].update({'request_headers':data['message']['params']['request']['headers']})

						# these can fail, insert null and move on
						try:
							requests[data['message']['params']['requestId']].update({'user_agent':data['message']['params']['request']['headers']['User-Agent']})
						except:
							requests[data['message']['params']['requestId']].update({'user_agent':None})

						try:
							requests[data['message']['params']['requestId']].update({'referer':data['message']['params']['request']['headers']['Referer']})
						except:
							requests[data['message']['params']['requestId']].update({'referer':None})
					
					if data['message']['method'] == 'Network.responseReceived':
						# initialize the key in the dict so we can add to it
						if data['message']['params']['requestId'] not in requests:
							requests[data['message']['params']['requestId']] = {}

						# the request was received, mark it
						requests[data['message']['params']['requestId']].update({'received':True})

						# record status code and text
						requests[data['message']['params']['requestId']].update({'status':data['message']['params']['response']['status']})
						requests[data['message']['params']['requestId']].update({'status_text':data['message']['params']['response']['statusText']})
						
						# try to get reponse headers, fail gracefully
						try:
							requests[data['message']['params']['requestId']].update({'response_headers':data['message']['params']['response']['headersText']})
						except:
							requests[data['message']['params']['requestId']].update({'response_headers':None})
						
						try:
							requests[data['message']['params']['requestId']].update({'content_type':data['message']['params']['response']['headers']['Content-Type']})
						except:
							requests[data['message']['params']['requestId']].update({'content_type':None})

					if data['message']['method'] == 'Network.loadingFinished':
						# initialize the key in the dict so we can add to it
						if data['message']['params']['requestId'] not in requests:
							requests[data['message']['params']['requestId']] = {}

						# size is updated during loading and is shown in logs, but we only want the final size which is here
						requests[data['message']['params']['requestId']].update({'body_size':data['message']['params']['encodedDataLength']})

						# we use this to calculate the total time for all requests
						requests[data['message']['params']['requestId']].update({'endTime':data['message']['params']['timestamp']})
		# end log processing loop

		# to get page load time we will figure out when the first request and final load finished occured
		first_start_time = 0
		last_endTime = 0

		# figure out per-request timings
		for item in requests:
			try:
				# multiply load difference by 1k to convert to miliseconds
				requests[item].update({'load_time':(requests[item]['endTime'] - requests[item]['start_time'])*1000})

				# update globals
				if first_start_time == 0 or requests[item]['start_time'] < first_start_time:
					first_start_time = requests[item]['start_time']

				if last_endTime == 0 or requests[item]['endTime'] > last_endTime:
					last_endTime = requests[item]['endTime']
			except:
				requests[item].update({'load_time':None})

		# this dict is keyed by url, reprocess the extant requestID-keyed dict
		processed_requests = {}

		for item in requests:
			# why does this sometimes fail...?
			try:
				processed_requests[requests[item]['url']] = requests[item]
			except:
				continue

			processed_requests[requests[item]['url']]['start_time_offset'] = int((processed_requests[requests[item]['url']]['start_time'] - first_start_time) * 1000)

		# return all the links for later processing
		all_links = []
		try:
			links = driver.find_elements_by_tag_name('a')
			for link in links:
				all_links.append([link.get_attribute('text'),link.get_attribute('href')])
		except:
			pass

		# get the page meta description
		try:
			meta_desc = driver.find_element_by_xpath("//meta[@name='description']").get_attribute("content")
		except:
			meta_desc = None

		# get all the cookies
		# 	the selenium get_cookies method does not return third-party cookies
		#	so we open the cookie db directly from the chrome profile
		#	note that in headless mode this does not work in chrome versions
		#	prior to 64.0.3254.0 and no cookies will be returned
		cookies = []
		try:
			conn = sqlite3.connect(driver.capabilities['chrome']['userDataDir']+'/Default/Cookies')
			c = conn.cursor()
			c.execute("SELECT name,secure,path,host_key,expires_utc,httponly,value FROM cookies")
			for cookie in c.fetchall():
				cookies.append({
					'name': 		cookie[0],
					'secure':		cookie[1],
					'path':			cookie[2],
					'domain': 		cookie[3],
					'expiry':		cookie[4],
					'httponly':		cookie[5],
					'value':		cookie[6]
				})
		except:
			print('Could not load Chrome cookie database for %s, if this message appears often something is fundamentally wrong and requires attention!' % url)
			return None

		if self.headless == True:
			browser_version = driver.capabilities['version'] + ' [headless]'
		else:
			browser_version = driver.capabilities['version']

		# other parts of webxray expect this data format, common to all browser drivers used
		return_dict = {
			'browser_type':			driver.capabilities['browserName'],
			'browser_version':		browser_version,
			'browser_wait':			browser_wait,
			'start_url':			url, 
			'final_url': 			final_url,
			'title': 				title,
			'meta_desc': 			meta_desc,
			'load_time': 			int((last_endTime - first_start_time)*1000),
			'processed_requests': 	processed_requests,
			'cookies': 				cookies,
			'all_links':			all_links,
			'source':				page_source
		}
		
		# quit the driver or it will never die!
		driver.quit()

		return return_dict
	# get_webxray_scan_data
# ChromeDriver
