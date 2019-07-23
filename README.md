# webXray

webXray is a tool for analyzing third-party content on webpages and identifying the companies which collect user data.  A command line user interface makes webXray easy to use for non-programmers, and those with advanced needs may analyze millions of pages with proper configuration.  webXray is a professional tool designed for academic research, and may be used by privacy compliance officers, regulators, and those who are generally curious about hidden data flows on the web.

webXray uses a custom library of domain ownership to chart the flow of data from a given third-party domain to a corporate owner, and if applicable, to parent companies.  Tracking attribution reports produced by webXray provide robust granularity.  Reports of the average numbers of third-parties and cookies per-site, most commonly occurring third-party domains and elements, volumes of data transferred, use of SSL encryption, and more are provided out-of-the-box.  A flexible data schema allows for the generation of custom reports as well as authoring extensions to add additional data sources.

The public version of webXray uses Chrome to load pages, stores data in a SQLite database, and can be used on a normal desktop computer.  There is also a private version of webXray which has enhanced capabilties for web-scale forensic analysis which is designed for academic research and litigation needs.  If you have academic needs please contact Tim Libert (https://timlibert.me), if you have litigation needs please contact us at the webXray company website (https://webxray.eu).

More information and detailed installation instructions may be found on the [project website](http://webXray.org).

# Dependencies

webXray depends on several pieces of software being installed on your computer in advance.  The webXray website has detailed instructions for setting up the software on [Ubuntu](http://webXray.org/#ubuntu) and [macOS](http://webXray.org/#macos).  If you are familiar with installing dependencies on your own, the following are needed:

Python 3.4+ is required:

	Python 3.4+ 			https://www.python.org
	
Google Chrome:

	Chrome 75+				https://www.google.com/chrome/
	Chrome Driver 75			https://sites.google.com/a/chromium.org/chromedriver/
	
Selenium:
	Selenium				https://pypi.python.org/pypi/selenium

# Installation

If the dependencies above are met all you can clone this repository and get started:

	git clone https://github.com/timlib/webXray.git

Again, see the webXray website for installation guides for [Ubuntu](http://webXray.org/#ubuntu) and [macOS](http://webXray.org/#macos).

# Using webXray

To start webXray in interactive mode type:

	python3 run_webXray.py

The prompts will guide you to scanning a sample list of websites using the default settings of Chrome in windowed mode and a SQLite database.  If you wish to run several browsers in paralell to increase speed, leverage a more powerful database engine, or perform other advanced tasks, please see the [project website](http://webXray.org/#advanced_options) for details.

# Using webXray to Analyze Your Own List of Pages

The raison d'être of webXray is to allow you to analyze pages of your choosing.  In order to do so, first place all of the page addresses you wish to scan into a text file and place this file in the "page_lists" directory.  Make sure your addresses start with "http://" or "https://", if not, webXray will not recognize them as valid addresses.  Once you have placed your page list in the proper directory you may run webXray and it will allow you to select your page list.

# Viewing and Understanding Reports

Use the interactive mode to guide you to generating an analysis once you have completed your data collection.  When it is completed it will be output to the '/reports' directory.  This will contain a number of csv files:

* __db\_summary.csv__: a basic report of what is in the database and how many pages loaded
* __stats.csv__: provides top-level stats on how many domains are contacted, cookies, javascript, etc.
* __aggregated\_tracking\_attribution.csv__: details on percentages of sites tracked by different companies and their subsidiaries
* __3p\_domain.csv__: most frequently occurring third-party domains
* __3p\_element.csv__: most frequently occurring third-party elements of all types
* __3p\_image.csv__: most frequently occurring third-party images
* __3p\_javascript.csv__: most frequently occurring third-party javascript
* __3p\_ssl\_use.csv__: rates at which detected third-parties encrypt requests
* __data\_xfer\_summary.csv__: volume and percentage of data received from first- and third-party domains
* __data\_xfer\_aggregated.csv__: volume and percentage of data received from various companies
* __data\_xfer\_by\_domain.csv__: volume and percentage of data received from specific third-party domains
* __network__: pairings between page domains and third-party domains, you can import this info to network visualization software
* __per\_page\_data\_flow.csv__: one giant file that lists the requests made for each page, off by default

# Important Note on Speed and Parallelization

webXray can load many pages in parallell and may be used for analyzing millions of pages fairly quickly.  However, out-of-the-box, webXray is configured to only scan one page at a time.  If you think your system can handle more (and chances are it can!), open the 'run\_webXray.py' file and search for the first occurance of the 'pool\_size' variable.  When you find that there are instructions on how to increase the numbers of pages you can do concurrently.  Please find additional information on the [project website](http://webXray.org/#advanced_options).

# Academic Citation

This tool is produced by Timothy Libert, if you are using it for academic research, please cite the most pertinent publication from his [Google Scholar page](https://scholar.google.com/citations?user=pR9YdCcAAAAJ&hl=en&oi=ao).

# License

webXray is FOSS and licensed under GPLv3, see LICENSE.md for details.
