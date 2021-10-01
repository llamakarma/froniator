# Froniator

This tool captures data from Fronius inverters. It has been tested against
a grid-tied Primo using python3.6 under linux.

Froniator captures/graphs the overall inverter output overlaid with the
output of each string.

The Fronius API provides instantaneous current power generation but string
data is only available every 5 minutes - the graphs usually correlate well
but some deviation is expected.

Froniator is designed to be run every minute via a cron job with output
to a web server.

The script runs in two modes, outputs for each mode are explained below.

- During the day (when generating)
- End of day (after sunset)

Most important variables are configurable near the top of the source. 
Dig deeper if you want to customise more.

For testing, either use cli arguments or set override variables in the code.

froniator -d will force the script to run in daytime mode

froniator -e will force the script to run in end of day mode

froniator -t will output files to a different location to prevent stomping
             the production data you want to keep


## Outputs

CSV Files:
- Daily kWh updated per run (YYYY-MM-DD.csv)
- Daily kWh per string per run (5 min granularity) (YYYY-MM-DD-string.csv)
- End of day tracking of total kWh and peak kWh (dailytotals.csv)

Graphs as PNG Files:
- Output since day start (currentPwr.png) updated every run
- Day summary (YYYY-MM-DD.png) updated at the end of the day

HTML File:
- New to old simple html of each summary PNG (history.html) (end of day)

Files you might want to keep for the long term are stored by default in a
different location (data/ by default) to the live files.


## Useful Scripts

For dynamic viewing of currentPwr.png, a simple HTML page can be built.

Simple index.html:

````
<html>
        <head>
             <title>Current PV</title>
	      <meta http-equiv="refresh" content="30; url=index.html"> 
	</head>
	<body>
		<p style="text-align:center;"><img src="currentPwr.png" alt="Current PV"></p>
	</body>
</html>
````

As you may have to run as root to post to /var/www, something like this should
work and leave a log of any errors posted to stdout. I call the script from a shell 
script, it makes it easy to change the script filename during dev/debug without 
having to go to crontab -e each time.

crontab:

````
* * * * * /xxxx/inverter/runInverter.sh >> xxxx/inverter/inverter.log 2>&1
````

runInverter.sh:

````
#!/bin/bash
if [ "$EUID" -ne 0 ]
    then echo "Please run as root"
    exit
fi
/usr/local/bin/python3.6 xxxx/inverter/froniator.py
````

## Sources

Froniator is based on Fronius-DataManager-Solar-Logger available here:

https://github.com/edent/Fronius-DataManager-Solar-Logger

