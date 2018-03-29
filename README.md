# webxray

webxray is a tool for analyzing third-party content on webpages and identifying the companies which collect user data.  A command line user interface makes webxray easy to use for non-programmers, and those with advanced needs may analyze millions of pages with proper configuration.  webxray is a professional tool designed for academic research, and may be used by privacy compliance officers, regulators, and those who are generally curious about hidden data flows on the web.

webxray uses a custom library of domain ownership to chart the flow of data from a given third-party domain to a corporate owner, and if applicable, to parent companies.  Tracking attribution reports produced by webxray provide robust granularity.  Reports of the average numbers of third-parties and cookies per-site, most commonly occurring third-party domains and elements, volumes of data transferred, use of SSL encryption, and more are provided out-of-the-box.  A flexible data schema allows for the generation of custom reports as well as authoring extensions to add additional data sources.

By default, webxray uses Chrome to load pages, stores data in a SQLite database, and can be used on a normal desktop computer.  Users with advanced needs may install webxray on a server and leverage MySQL or PostgreSQL for heavy-duty data storage.

More information and detailed installation instructions may be found on the [project website](http://webxray.org).

# Dependencies

webxray depends on several pieces of software being installed on your computer in advance.  The webxray website has detailed instructions for setting up the software on [Ubuntu](http://webxray.org/#ubuntu) and [macOS](http://webxray.org/#macos).  If you are familiar with installing dependencies on your own, the following are needed:

Python 3.4+ is required:

	Python 3.4+ 			https://www.python.org
	
If you want to use Google Chrome as your browser engine you must install:

	Chrome 64+				https://www.google.com/chrome/
	Chrome Driver			https://sites.google.com/a/chromium.org/chromedriver/
	Selenium				https://pypi.python.org/pypi/selenium
	
If you want to use the PhantomJS browser engine instead of Chrome you must install:
	
	PhantomJS 1.9+ 			http://phantomjs.org

If you want to use the MySQL database engine you must install:
	
	MySQL					https://www.mysql.com
	MySQL Python Connector	https://dev.mysql.com/downloads/connector/python/

If you want to use the PostgreSQL database engine you must install:
	
	PostgreSQL				https://www.postgresql.org
	psycopg					http://initd.org/psycopg/

# Installation

If the dependencies above are met all you can clone this repository and get started:

	git clone https://github.com/timlib/webxray.git

Again, see the webxray website for installation guides for [Ubuntu](http://webxray.org/#ubuntu) and [macOS](http://webxray.org/#macos).

# Using webxray

To start webxray in interactive mode type:

	python3 run_webxray.py

The prompts will guide you to scanning a sample list of websites using the default settings of Chrome in windowed mode and a SQLite database.  If you wish to run several browsers in paralell to increase speed, leverage a more powerful database engine, or perform other advanced tasks, please see the [project website](http://webxray.org/#advanced_options) for details.

# Using webxray to Analyze Your Own List of Pages

The raison d'être of webxray is to allow you to analyze pages of your choosing.  In order to do so, first place all of the page addresses you wish to scan into a text file and place this file in the "page_lists" directory.  Make sure your addresses start with "http://" or "https://", if not, webxray will not recognize them as valid addresses.  Once you have placed your page list in the proper directory you may run webxray and it will allow you to select your page list.

# Viewing and Understanding Reports

Use the interactive mode to guide you to generating an analysis once you have completed your data collection.  When it is completed it will be output to the '/reports' directory.  This will contain a number of csv files:

db\_summary.csv: a basic report of what is in the database and how many pages loaded
stats.csv: provides top-level stats on how many domains are contacted, cookies, javascript, etc.
aggregated\_tracking\_attribution.csv: details on percentages of sites tracked by different companies and their subsidiaries
3p\_domain.csv: most frequently occurring third-party domains
3p\_element.csv: most frequently occurring third-party elements of all types
3p\_image: most frequently occurring third-party images
3p\_javascript: most frequently occurring third-party javascript
3p\_ssl\_use.csv: rates at which detected third-parties encrypt requests
data\_xfer\_summary.csv: volume and percentage of data received from first- and third-party domains
data\_xfer\_aggregated.csv: volume and percentage of data received from various companies
data\_xfer\_by\_domain.csv: volume and percentage of data received from specific third-party domains
network: pairings between page domains and third-party domains, you can import this info to network visualization software
per\_page\_data\_flow.csv: one giant file that lists the requests made for each page, off by default

# Important Note on Speed and Parallelization

webxray can load many pages in parallell and may be used for analyzing millions of pages fairly quickly.  However, out-of-the-box, webxray is configured to only scan one page at a time.  If you think your system can handle more (and chances are it can!), open the 'run\_webxray.py' file and search for the first occurance of the 'pool\_size' variable.  When you find that there are instructions on how to increase the numbers of pages you can do concurrently.  Please find additional information on the [project website](http://webxray.org/#advanced_options).

# License

webxray is FOSS and licensed under GPLv3, see LICENSE.md for details.