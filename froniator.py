#!/usr/bin/env python3.6

import signal
import sys
import argparse
import datetime
from dateutil import parser
from astral.geocoder import lookup, database
from astral.sun import sun
import csv
import pytz
import os
import os.path
import requests
import json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


#################### TEST MODE KNOB #####################
##### mode False can be overridden by cmd line args #####

TESTMODE = False                          # move file writes to test location
#TESTMODE = True

FORCEDAY = False                          # force daytime behaviour
#FORCEDAY = True

FORCEEOD = False                          # force EOD behaviour
#FORCEEOD = True

#########################################################


#   Set startup attribs used by script

VERSION = "20210911-01"
ERRORSTATUS = "OK"
FIRSTRUN = True
ENDOFDAY = False
HELPNOTES = """This tool captures data from Fronius inverters.

It is designed to be run every minute via a cron job with output to a
web server.

Most important variables are configurable near the top of the source. Dig deeper if
you want to customise more.

For testing, either use the param -t or set the variable in the code.

Froniator is Copyright (c) 2021 and released under the MIT license.
"""

#   User config

INVERTERIP = "192.168.1.123"              # IP address of inverter
TIMEZONE = "Europe/London"                # local timezone
CITYNAME = "Reading"                      # nearest major city for sun up/down
MYLOCATION = "My House"                   # name of system to appear on report
PVSTRING1 = "East Panels"                 # name of first PV string
PVSTRING2 = "South Panels"                # name of second PV string

PVMIN = 0                                 # min scale of PV graph kWh
PVMAX = 5250                              # max scale of PV graph kWh
PVSTEP = 250                              # step size on PV graph

CURR = "£"                                # local currency
KWHVALUE = 0.1872                         # saving | payment (currency/kWh)
EXPORTSTRING = "Saved"                    # 'Saved' | 'Earned'

LIVEPATH = "/var/www/html/pvmon"          # local path to place live data
ARCHIVEPATH = "/var/www/html/pvmon/data"  # local path to place archive
WEBPATH = "/pvmon/data"                   # public path written to history.html
LIVEIMAGE = "currentPwr.png"              # name of image updated each iter
SUMMARYCSV = "dailytotals.csv"            # this file updates once per day with
# timestamp, kWh total and peak kWh
HISTORYHTML ="history.html"               # name of HTML file with daily images

#   In test mode use this path for all files (def. same dir as the script)

TESTPATH = os.path.dirname(os.path.abspath(__file__))
#TESTPATH = LIVEPATH + "/test"

###############################################################################

#   Handle puke

def signal_handler(sig, frame):
    print()
    print()
    print("Thanks for all the fish, smeg head.")
    print()
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)

#   Capture cmd line arguments

def parse_cmdline():

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="inverterCapture version " + VERSION,
                                     epilog=HELPNOTES)
    parser.add_argument("-d", action='store_true', default=False, help="force daytime")
    parser.add_argument("-e", action='store_true', default=False, help="force end of day")
    parser.add_argument("-t", action='store_true', default=False, help="enable test mode")

    return parser.parse_args()

#   Pull data from inverter

def call_inverter(inverterUrl):
    try:
        response = requests.get(url=inverterUrl)
        data = json.loads(response.text)
        errorStatus = "OK"
    except requests.exceptions.ConnectionError as ex:
        errorStatus = "Cannot connect to inverter"
    except requests.exceptions.ReadTimeout as ex:
        errorStatus = "Timeout reading from API: " + inverterUrl
    return data, errorStatus

#   Plot the graph(s)

def draw_graph(plotFnames, plotCfg, plotLabel, plotSysVal):

    #   Read the data from the main and String CSV files

    data = np.genfromtxt(plotFnames['dCsv'],
                         unpack=True,
                         names=['timestamp','watts','total'],
                         dtype=None,
                         delimiter = ',',
                         converters={0: lambda x: parser.parse(x)})
    xAgg = data['timestamp']
    yAgg = data['watts']

    maxPwr = max(yAgg)

    data = np.genfromtxt(plotFnames['sCsv'],
                         unpack=True,
                         names=['timestamp','string1','string2'],
                         dtype=None,
                         delimiter = ',',
                         converters={0: lambda x: parser.parse(x)})
    xStr = data['timestamp']
    yStr1 = data['string1']
    yStr2 = data['string2']

    #   Calculate the total kWh generated.
    #   Sum the readings and divide by 60. (Because we read every minute &
    #   there are 60 minutes in an hour).
    #   Divide by 1,000 to get kWh
    #   Only need 2 decimal places of precision

    kWh = round((sum(yAgg) / 60 / 1000), 2)

    money = plotLabel['cur'] + '{:.2f}'.format((round((kWh * plotLabel['kWval']), 2)))

    #   Start the graph

    fig, ax = plt.subplots(figsize=(16, 9))

    #   Plot string data overlay

    ax.plot(xStr, yStr1, 'm', label=plotLabel['str1'], linewidth=1)
    ax.plot(xStr, yStr2, 'b', label=plotLabel['str2'], linewidth=1)

    #   Total power colour masks

    mask0 = yAgg <   500
    mask1 = yAgg >=  500
    mask2 = yAgg >= 1000
    mask3 = yAgg >= 1500
    mask4 = yAgg >= 2000
    mask5 = yAgg >= 2500
    mask6 = yAgg >= 3000
    mask7 = yAgg >= 3500
    mask8 = yAgg >= 4000

    #   Plot main power bars

    plt.bar(xAgg[mask0], yAgg[mask0], width=.002, color = '#F0FF00')
    plt.bar(xAgg[mask1], yAgg[mask1], width=.002, color = '#F1DF00')
    plt.bar(xAgg[mask2], yAgg[mask2], width=.002, color = '#F3BF00')
    plt.bar(xAgg[mask3], yAgg[mask3], width=.002, color = '#F59F00')
    plt.bar(xAgg[mask4], yAgg[mask4], width=.002, color = '#F77F00')
    plt.bar(xAgg[mask5], yAgg[mask5], width=.002, color = '#F95F00')
    plt.bar(xAgg[mask6], yAgg[mask6], width=.002, color = '#FB3F00')
    plt.bar(xAgg[mask7], yAgg[mask7], width=.002, color = '#FD1F00')
    plt.bar(xAgg[mask8], yAgg[mask8], width=.002, color = '#ff0000')

    #   Set legend

    legend = ax.legend(loc='upper right', shadow=True)

    #   X axis

    hours = mdates.HourLocator()
    hoursFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_locator(hours)
    ax.xaxis.set_major_formatter(hoursFmt)

    day = xAgg[0]
    xStart = day.replace(hour=5,  minute=0, second=0) # 0500
    xEnd   = day.replace(hour=23, minute=0, second=0) # 2300

    ax.set_xlim(xStart, xEnd)

    #   Y axis

    ax.set_ylim(plotCfg['min'], plotCfg['max'])
    ax.set_yticks(np.arange(plotCfg['min'], plotCfg['max'], step=plotCfg['step']))

    #   Axis properties

    ax.grid(axis='y', color='#FFFFFF', linestyle='-', linewidth=0.3)

    #   Rotates and right aligns the x labels, and moves the bottom of the
    #   axes up to make room for them

    fig.autofmt_xdate()

    #   Background colour

    ax.set_facecolor('#1f77b4')

    #   Set the labels

    plt.xlabel(today + "\nfroniator version: " + plotLabel['ver'] + "\nSunrise: " + \
               str(plotLabel['sunrise']) + " - Sunset: " + \
               str(plotLabel['sunset']))

    plt.ylabel("Generated Electricity (Watts)")

    graphTitle = plotLabel['loc'] + " PV at " + \
                 now.strftime("%d/%m/%Y, %H:%M:%S") + "\nGenerated " + \
                 str(kWh) + "kWh - " + plotLabel['expStr'] + ' ' + money

    if plotSysVal['eod']:
        graphTitle = graphTitle + " - Daily Summary"
    else:
        graphTitle = graphTitle +  " - Current Output " + str(watts) + " W"

    #   If testmode, mark up the graph to show this

    if plotSysVal['test']:
        graphTitle = "-TEST CODE-\n" + graphTitle
    if plotSysVal['err'] != "OK":
        graphTitle = graphTitle + "\nError: " + plotSysVal['err']
    plt.title(graphTitle)

    #   Save the 'live' image once per run

    plt.savefig(plotFnames['lPng'], bbox_inches='tight')

    #   Save the daily image if EOD

    if plotSysVal["eod"]:
        plt.savefig(plotFnames["dPng"], bbox_inches="tight")

    return kWh, maxPwr

#   Convert the raw inverter data to Watts and the string data to a consistent timestamp format

def calculate_power(pwrData, stringData):

    #   Calculate inverter total pwr output

    watts = pwrData['Body']['Data']['PAC']['Values']['1']

    #   Calculate per string power data

    string1cur = stringData['Body']['Data']['inverter/1']['Data'] \
                           ['Current_DC_String_1']['Values']
    #   Keys to ints, Values to floats
    string1cur = {int(k):float(v) for k,v in string1cur.items()}
    string1cur = sorted(string1cur.items())

    string2cur = stringData['Body']['Data']['inverter/1']['Data'] \
                           ['Current_DC_String_2']['Values']
    #   Keys to ints, Values to floats
    string2cur = {int(k):float(v) for k,v in string2cur.items()}
    string2cur = sorted(string2cur.items())

    string1volt = stringData['Body']['Data']['inverter/1']['Data'] \
                            ['Voltage_DC_String_1']['Values']
    #   Keys to ints, Values to floats
    string1volt = {int(k):float(v) for k,v in string1volt.items()}
    string1volt = sorted(string1volt.items())

    string2volt = stringData['Body']['Data']['inverter/1']['Data'] \
                            ['Voltage_DC_String_2']['Values']
    #   Keys to ints, Values to floats
    string2volt = {int(k):float(v) for k,v in string2volt.items()}
    string2volt = sorted(string2volt.items())

    timestampList = []
    str1watts  = []
    str2watts  = []

    #  Convert string timestamps into ISO timestamps and calculate P=IV

    for current, voltage in zip(string1cur, string1volt):
        timeFromMidnight = datetime.timedelta(seconds = current[0])
        timestamp = datetime.datetime.strptime("{} {}".format(today, \
                                              timeFromMidnight), "%Y-%m-%d %H:%M:%S")
        timestamp = zone.localize(timestamp)
        timestamp = timestamp.isoformat()
        timestampList.append(str(timestamp))
        str1watts.append(int(current[1] * voltage[1]))

    for current, voltage in zip(string2cur, string2volt):
        str2watts.append(int(current[1] * voltage[1]))

    #       Remove the first 4:30 hours (54 * 5 minutes)
    #       Earliest sunrise about 04:40
    #       Latest sunset about 2130

    timestampList = timestampList[54:]
    str1watts  = str1watts[54:]
    str2watts  = str2watts[54:]

    return watts, timestampList, str1watts, str2watts

#   Write out history.html

def write_history_html(isHistoryHtml, HISTORYHTML, histHtmlStr):
    if not isHistoryHtml:
        with open(HISTORYHTML, 'a') as file:
            file.write(histHtmlStr + "\n")
    else:
        with open(HISTORYHTML, 'r+') as file:
            historyContent = file.read()
            file.seek(0, 0)
            file.write(histHtmlStr + "\n")
            file.write(historyContent)
    return


#   General purpose CSV writer

def write_csv(filename, *args):
    csvRow = []
    for ar in args:
        csvRow.append(ar)
    with open(filename, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer = writer.writerow(csvRow)
    return

#   Error logs to stdout to be captured during cron runs

def log_errors(isDailyPng, isDailyCsv, isStringCsv, FIRSTRUN, ERRORSTATUS, timeIso):
    if isDailyPng and isDailyCsv and isStringCsv:
        sys.exit(0)
    elif isDailyPng:
        print("\n" + timeIso + " Daily PNG already exists")
    elif not isDailyCsv and not FIRSTRUN:
        print("\n" + timeIso + " Daily inverter CSV file is missing")
    elif not isStringCsv and not FIRSTRUN:
        print("\n" + timeIso + " Daily string CSV file is missing")

    if ERRORSTATUS != "OK":
        print("\n" + timeIso + " " + ERRORSTATUS)
    return


###############################################################################

#   Sun information

city = lookup(CITYNAME, database())
sun = sun(city.observer, tzinfo=city.timezone)  #Set TZ for sun up/down
tzInfo = (sun['sunrise']).tzinfo

#   Time information

mpl.rcParams['timezone'] = TIMEZONE  #Tell matplotlib to use local TZ
now   = datetime.datetime.now()
zone  = pytz.timezone(TIMEZONE)
now   = zone.localize(now)           #Create 'now' with TZ offset info
today = now.strftime("%Y-%m-%d")     #Date for filenames
timeIso = now.isoformat()            #Time written to CSV

timeNow = datetime.datetime.now(tzInfo)
sunrise = sun['sunrise']
sunset = sun['sunset']

#   API URLs

powerApiUrl = "http://" + INVERTERIP + \
              "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"

stringApiUrl = "http://" + INVERTERIP + \
               "/solar_api/v1/GetArchiveData.cgi?Scope=System&StartDate=" + \
               today + "&EndDate=" + today + "&Channel=Voltage_DC_String_1" + \
               "&Channel=Current_DC_String_1&Channel=Voltage_DC_String_2" + \
               "&Channel=Current_DC_String_2"

#   Check Test mode cmd line override

args = parse_cmdline()

if args.d:
    FORCEDAY = True

if args.e:
    FORCEEOD = True
    ENDOFDAY = True

if args.t:
    TESTMODE = True


#   Set up paths for test mode

if TESTMODE:
    LIVEPATH = TESTPATH
    ARCHIVEPATH = TESTPATH
    print("\nTEST MODE ON")

if FORCEEOD:
    print("\nFORCED EOD ON")

if FORCEDAY:
    print("\nFORCED DAYTIME ON")

#   Set the filenames to use timestamp and correct path

tstampFilename =  os.path.join(ARCHIVEPATH, today)
dailyCsv = tstampFilename + ".csv"
dailyPng = tstampFilename + ".png"
stringCsv = tstampFilename + "-string.csv"
stringPng = tstampFilename + "-string.png"
historyPngLoc = os.path.join(WEBPATH, today + ".png")

SUMMARYCSV = os.path.join(ARCHIVEPATH, SUMMARYCSV)
LIVEIMAGE = os.path.join(LIVEPATH, LIVEIMAGE)
HISTORYHTML = os.path.join(LIVEPATH, HISTORYHTML)


#   Check which files exist

isDailyCsv = os.path.exists(dailyCsv)
isDailyPng = os.path.isfile(dailyPng)
isStringCsv = os.path.isfile(stringCsv)
isHistoryHtml = os.path.exists(HISTORYHTML)

#   Set the HTML to write to the top of the history page source

histHtmlStr = '<p style="text-align:center;"><img src="' + \
              historyPngLoc + '" alt="' + today + \
              '"></p>'

#   Setup dictionaries to pass to draw_graph()

plotFnames = { 'dCsv' : dailyCsv, 'sCsv' : stringCsv, 'dPng' : dailyPng, \
               'lPng' : LIVEIMAGE }
plotCfg = {'min' : PVMIN, 'max' : PVMAX, 'step' : PVSTEP}
plotLabel = {'cur' : CURR, 'kWval' : KWHVALUE, 'str1' : PVSTRING1, \
             'str2' : PVSTRING2, 'loc' : MYLOCATION, \
             'expStr' : EXPORTSTRING, 'ver' : VERSION, 'sunrise' : sunrise,\
             'sunset' : sunset}
plotSysVal = {'test' : TESTMODE, 'err' : ERRORSTATUS, 'eod' : ENDOFDAY}


###############################################################################

#   When FIRSTRUN is true (start of new day) we don't draw the graph until we
#   have at least 2 entries in the CSV

if isDailyCsv:
    FIRSTRUN = False

#   During daylight try to connect to inverter

if (timeNow > sunrise and \
        timeNow < sunset and not FORCEEOD) or FORCEDAY:

    #   Collect data from inverter API

    pwrData, ERRORSTATUS = call_inverter(powerApiUrl)
    stringData, ERRORSTATUS = call_inverter(stringApiUrl)

    if ERRORSTATUS == "OK":

        watts, timestampList, str1watts, str2watts =  calculate_power(pwrData, \
                                                      stringData)

        #   Write out the aggregate and string CSVs

        write_csv(dailyCsv, timeIso, watts)

        #   Inverter returns the whole day of string data so this is an overwrite

        with open(stringCsv, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            for a, b in zip(zip(timestampList, str1watts), str2watts):
                t  = str(a[0])
                w1 = str(a[1])
                w2 = str(b)
                writer.writerow([t,w1,w2])

        #   Only draw the graph if the CSV file exists and its not the first
        #   iteration of the day

        if isDailyCsv and not FIRSTRUN:

            draw_graph(plotFnames, plotCfg, plotLabel, plotSysVal)

#   At the end of the day save an archive image and CSV of timestamp,
#   kWh and peak output for the day. Overlay per string data.

if (timeNow > sunset and not isDailyPng and isDailyCsv and \
    isStringCsv and not FORCEDAY) or FORCEEOD:

    plotSysVal['eod'] = True

    kWh, maxPwr = draw_graph(plotFnames, plotCfg, plotLabel, plotSysVal)

    #   Write daily summary CSV

    write_csv(SUMMARYCSV, timeIso, kWh, maxPwr)

    #   Write URL to history html at top of file

    write_history_html(isHistoryHtml, HISTORYHTML, histHtmlStr)

#   Log errors to stdout

log_errors(isDailyPng, isDailyCsv, isStringCsv, FIRSTRUN, ERRORSTATUS, timeIso)
