/*
*	originally based on netlog.js example from phantomjs docs
*
*	major modification is that when a page has a chain of redirects phantomjs doesn't
*	follow all of them to completion so we wait for a set period of time (20sec) to
*	allow redirects to complete
*
*	note that this was significantly refactored after phantomjs 2 was released
*	so the code is not identical to the 1.9 version which was used to generate
*	earlier data sets and findings, further be on the lookout for bugs in
*	phantomjs 2!
*
*	example of a page with several redirects:
*	https://timlibert.me/redirects/1.html
*/

//enable, then empty cookie jar
phantom.cookiesEnabled = true;
phantom.clearCookies()

// set up vars
var page = require('webpage').create(),
    system = require('system'),
    address,
    requested_uris = [],
    received_uris = [],
    final_uri;

// go try to load the page
if (system.args.length === 1) {
    console.log('Usage: wbxr_logger.js <some URL>');
    phantom.exit(1);
} else {
    address = system.args[1];

	var final_uri = address;

	// randomize user agent to assist in compatibility checks, etc
	// pulled the top 32 from here: https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
	
	ua_strings = [
		'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0',
		'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0',
		'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
		'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
		'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
		'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
		'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:49.0) Gecko/20100101 Firefox/49.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
		'Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0',
		'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:50.0) Gecko/20100101 Firefox/50.0',
		'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/53.0.2785.143 Chrome/53.0.2785.143 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
	]

	page.settings.userAgent = ua_strings[Math.floor(Math.random()*ua_strings.length)];

    // suppress errors from output
	page.onError = function (msg, trace) {}

	// keep track of what uri we are on so we can find redirects later
	page.onUrlChanged = function(targetUrl) {
	  final_uri = targetUrl;
	};

	// get all requests made
    page.onResourceRequested = function (request) {
    	// javascript returns -1 if item is not in array
    	if(requested_uris.indexOf(request.url) === -1){
	        requested_uris.push(request.url);
        }
    };

	// only get requests which successfully returned (OK)
    page.onResourceReceived = function (received) {
    	if(received.statusText == "OK" && received_uris.indexOf(received.url) === -1){
			received_uris.push(received.url);
		}
    };

	// python does a regex match on string 'FAIL' so this is non-arbitrary
	// and removing it will screw things up
    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('FAIL to load the address '+address);

            // if there is no phantom.exit() the program will never return!
            phantom.exit();
        }
    });
}

// this timeout waits for 30 seconds, when done evaluates page data and prints JSON
// to console

setTimeout(function() {
	// get the page description, retreat to null
	meta_desc = page.evaluate(function() {
		var metas = document.getElementsByTagName('meta'), i, meta_desc = '';
		for (i = 0; i < metas.length; i++) {
			if(metas[i].name.match(/description/i)){
				meta_desc = metas[i].content;
			}
		}
		return meta_desc;
	});
	
	if(!meta_desc){
		meta_desc = 'NULL';
	}
	
	// get title, retreat to null
	title = page.title;
	if(!title){
		title = 'NULL';
	}

	// build the JSON format python will expect
	// note that you can return the source if you like, the db schema supports
	big_out = {
		final_uri: final_uri,
		title: title,
		meta_desc : meta_desc,
		requested_uris: requested_uris,
		received_uris: received_uris,
		cookies: phantom.cookies,
		// return source w/out line breaks
		// source: page.content.replace(/[\t\n\r]/g, ""),
		source: 'NULL',
	};

	// prints JSON to CLI, python reads this and processes
	console.log(JSON.stringify(big_out, undefined, 4));
	
	// if there is no phantom.exit() the program will never return!
	phantom.exit();
}, 30000);