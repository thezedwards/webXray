# webXray

webXray is a tool for analyzing webpage traffic and content, extracting legal policies, and identifying the companies which collect user data.  A command line user interface makes webXray easy for non-programmers to use, and those with advanced needs may analyze billions of requests by fully leveraging webXray's distributed architecture.  webXray has been used to run hundreds of concurrent browser sessions distributed across multiple continents.

webXray performs scans of single pages, random crawls within websites, and supports following pre-scripted sequences of page loads.  Unlike tools which rely on browsers with negligible user bases, webXray uses the consumer version of Chrome, the most popular browser in the world.  This means webXray is the best tool for producing scans which accurately reflect the experiences of most desktop web users.

webXray performs both "haystack" scans which give insights into large volumes of network traffic, cookies, local storage, and websockets, as well as "forensic" scans which preserve all file contents for use in reverse-engineering scripts, extracting advertising content, and verifying page execution in a forensically sound way.  An additional module of webXray, policyXray, finds and extracts the text of privacy policies, terms of service, and other related documents in several languages.  

Small sets of pages may be stored in self-contained SQLite databases and large datasets can be stored in Postgres databases which come pre-configured for optimum indexing and data retrieval.  In both cases, webXray produces several preconfigured reports which are rendered as CSV files for easy importing into programs such as Excel, R, and Gephi.  Users proficient in SQL may use advanced queries to perform their own analyses with ease.

webXray uses a custom library of domain ownership to chart the flow of data from a given third-party domain to a corporate owner, and if applicable, to parent companies.  Domain ownership is further enhanced with classifications of what domains are used for (e.g. 'marketing', 'fonts', 'hosting'), links to several types of policies in numerous languages, as well as links to homepages, and lists of medical terms used by specific advertisers.

webXray and policyXray are professional tools designed for academic research, and may be used by anybody operating in the non-profit and public-interest space.  Commercial use of webXray is prohibited, as is redistributing the code.

More information and detailed installation instructions may be found on the [project website](http://webXray.org).

# Installation

webXray requires Python 3.4+ and Google Chrome to function, pip3 for dependency installation, and Readability.js for text extraction.  These may be installed in the following steps:

1) Install the latest version of Python3 along with pip3, there are various guides online to doing this for your OS of choice.

2) Install Google Chrome.  For desktop systems (e.g. Mac, Windows, Linux) you can get Chrome from Google's website.  When running in headless linux environments, installing from the official .deb file is recommended.

3)  Clone this repository from GitHub:

        git clone https://github.com/timlib/webXray.git

4) To install Python dependencies (websocket-client, textstat, lxml, and psycopg2), run the following command:

        pip3 install -r requirements.txt

5) If you want to extract page text (eg policies), you must download the file Readability.js from [this address](https://raw.githubusercontent.com/mozilla/readability/master/Readability.js) and copy it into the directory "webxray/resources/policyxray/".  You can also do this via the  command line as follows:
    
        cd webxray/resources/policyxray/
        wget https://raw.githubusercontent.com/mozilla/readability/master/Readability.js

# Using webXray

To start webXray in interactive mode type:

    python3 run_webXray.py

The prompts will guide you to scanning a sample list of websites using the default settings of Chrome in windowed mode and a SQLite database.  If you wish to run several browsers in parallel to increase speed, leverage a more powerful database engine, or perform other advanced tasks, please see the [project website](http://webXray.org/#advanced_options) for details.

To see how to control webXray via command-line flags, type the following:

    python3 run_webXray.py -h

# Using webXray to Analyze Your Own List of Pages

The raison d'être of webXray is to allow you to analyze pages of your choosing.  In order to do so, first place all of the page addresses you wish to scan into a text file and place this file in the "page_lists" directory.  Make sure your addresses start with "http://" or "https://", if not, webXray will not recognize them as valid addresses.  Once you have placed your page list in the proper directory you may run webXray and it will allow you to select your page list.

# Viewing and Understanding Reports

Use the interactive mode to guide you to generating an analysis once you have completed your data collection.  When it is completed it will be output to the '/reports' directory.  This will contain a number of csv files:

* __db\_summary.csv__: a basic report of what is in the database and how many pages loaded
* __stats.csv__: provides top-level stats on how many domains are contacted, cookies, javascript, etc.
* __aggregated\_tracking\_attribution.csv__: details on percentages of sites tracked by different companies and their subsidiaries
* __3p\_domain.csv__: most frequently occurring third-party domains
* __3p\_request.csv__: most frequently occurring third-party requests
* __3p\_javascript.csv__: most frequently occurring third-party javascript
* __3p\_uses.csv__: percentages of pages with third-parties performing specified functions
* __per_site_network_report__: pairings between page domains and third-party domains, you can import this info to network visualization software
 
# Important Note on Speed and Parallelization

webXray can load many pages in parallell and is capable of scanning over one million pages a day when leveraging a cluster of machines.  However, out-of-the-box, webXray is configured to only scan one page at a time on a normal laptop.  If you think your system can handle more concurrent browsers (and chances are it can!), open the 'run\_webXray.py' file and search for the first occurrence of the 'pool\_size' variable.  When you find that there are instructions on how to increase the numbers of pages you can do concurrently.  

# Leveraging Distributed Architecture for Massive Scans

Future documentation updates will detail how to deploy webXray on a cluster of machines, which may be geographically distributed.

# Academic Citation

This tool is produced by Timothy Libert, if you are using it for academic research, please cite the most pertinent publication from his [Google Scholar page](https://scholar.google.com/citations?user=pR9YdCcAAAAJ&hl=en&oi=ao).

# License

This software is *not* open source, it is *source available* and licensed for non-commercial use only.  You may not distribute webXray in whole or in part or sell data generated by webXray without prior written permission.
