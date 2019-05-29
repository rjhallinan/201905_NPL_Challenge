#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" This python script is written for the NPL challenge for May 2019. The goal is to read in
	the output of a 'show ip route' command from a router. Then analyze it and show a summary of how many
	routes are:
		Connected
		EIGRP
		Local
		OSPF
		Static
	
	I used the textfsm module to accomplish this. I also used a pre-built template from the ntc-templates project
	which was already setup to analyze 'show ip route' output. I included the template in this script if the file is not present.
	
	In order to run this file - the template should be in the same directory - it will be added if not there.
	
	Arguments:
		1) Filename - a relative path to the 'sh ip route' output.
	
	Outputs:
		1) Text with the analysis of the file
"""

# import modules HERE

# import the standard Python modules
import sys											# this allows us to analyze the arguments	
import os											# this allows us to check on the file
from datetime import datetime						# useful for getting timing information and for some data translation from Excel files
from contextlib import contextmanager

# import any extras
try:
	import textfsm									# output formatter
except:
	print("Need to have textfsm installed. Try:\n  pip<version> install textfsm")
	sys.exit()

# additional information about the script
__filename__ = "analyzeIPRoute.py"
__author__ = "Robert Hallinan"
__email__ = "rhallinan@netcraftsmen.com"

#
# version history
#


"""
	20190524 - Initial version
"""

@contextmanager
def open_file(path, mode):
	the_file = open(path, mode)
	yield the_file
	the_file.close()

def build_iproute_template():
	""" 
	This is the information for the show ip route template. It comes directly from:
		https://github.com/networktocode/ntc-templates/blob/master/templates/cisco_ios_show_ip_route.template
	This script will make this file.	
	"""

	fileContents = [
		'Value Filldown PROTOCOL (\w)\n', 
		'Value Filldown TYPE (\w{0,2})\n', 
		'Value Required,Filldown NETWORK (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\n', 
		'Value Filldown MASK (\d{1,2})\n', 
		'Value DISTANCE (\d+)\n', 
		'Value METRIC (\d+)\n', 
		'Value NEXTHOP_IP (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\n', 
		'Value NEXTHOP_IF ([A-Z][\w\-\.:/]+)\n', 
		'Value UPTIME (\d[\w:\.]+)\n', 
		'\n', 
		'Start\n', 
		'  ^Gateway.* -> Routes\n', 
		'\n', 
		'Routes\n', 
		'  # For "is (variably )subnetted" line, capture mask, clear all values.\n', 
		'  ^\s+\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}\/${MASK}\sis -> Clear\n', 
		'  #\n', 
		'  # Match directly connected route with explicit mask\n', 
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\/${MASK}\sis\sdirectly\sconnected,\s${NEXTHOP_IF} -> Record\n', 
		'  #\n', 
		'  # Match directly connected route (mask is inherited from "is subnetted")\n', 
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\sis\sdirectly\sconnected,\s${NEXTHOP_IF} -> Record\n', 
		'  #\n',
		'  # Match regular routes, with mask, where all data in same line\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\/${MASK}\s\[${DISTANCE}/${METRIC}\]\svia\s${NEXTHOP_IP}(,\s${UPTIME})?(,\s${NEXTHOP_IF})? -> Record\n',
		'  #\n',
		'  # Match regular route, all one line, where mask is learned from "is subnetted" line\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\s\[${DISTANCE}\/${METRIC}\]\svia\s${NEXTHOP_IP}(,\s${UPTIME})?(,\s${NEXTHOP_IF})? -> Record\n',
		'  #\n',
		'  # Match route with no via statement (Null via protocol)\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\/${MASK}\s\[${DISTANCE}/${METRIC}\],\s${UPTIME},\s${NEXTHOP_IF} -> Record\n',
		'  #\n',
		'  # Match "is a summary" routes (often Null0)\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\/${MASK}\sis\sa\ssummary,\s${UPTIME},\s${NEXTHOP_IF} -> Record\n',
		'  #\n',
		'  # Match regular routes where the network/mask is on the line above the rest of the route\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK}\/${MASK} -> Next\n',
		'  #\n',
		'  # Match regular routes where the network only (mask from subnetted line) is on the line above the rest of the route\n',
		'  ^${PROTOCOL}(\s|\*)${TYPE}\s+${NETWORK} -> Next\n',
		'  #\n',
		'  # Match the rest of the route information on line below network (and possibly mask)\n',
		'  ^\s+\[${DISTANCE}\/${METRIC}\]\svia\s${NEXTHOP_IP}(,\s${UPTIME})?(,\s${NEXTHOP_IF})? -> Record\n',
		'  #\n',
		'  # Match load-balanced routes\n',
		'  ^\s+\[${DISTANCE}\/${METRIC}\]\svia\s${NEXTHOP_IP} -> Record\n',
		'  #\n',
		'  # Clear all variables on empty lines\n',
		'  ^\s* -> Clearall\n',
		'\n',
		'EOF\n',	
	]
	with open_file('cisco_ios_show_ip_route.template','w') as fileOut:
		fileOut.writelines(fileContents)

def main(system_arguments):

	# get a python list of dictionaries by parsing the CSV file - validate that there is even an argument there using try
	try:
		fileName = system_arguments[1]
	except:
		if len(system_arguments) == 1:
			print("No filename provided. Exiting...")
			sys.exit()		

	# Does the file exist?
	if not os.path.exists(fileName):
		print("File name provided to analyze does not exist. Closing now...")
		sys.exit()

	# build the template
	build_iproute_template()

	# read in the input files
	with open_file(fileName,'r') as fileIn:
		inputFile = fileIn.read()

	# read in the template file
	with open('cisco_ios_show_ip_route.template','r') as fileIn:
		# with open('test.template','w') as fileOut:
			# fileOut.writelines(fileIn.readlines())
		# sys.exit()
		re_table = textfsm.TextFSM(fileIn)
		# sys.exit()

	# read in the data
	routeInfo = re_table.ParseText(inputFile)

	# get a set of the unique protocol, network, and mask
	# protocol is field 0, network is 2, mask is 3
	uniqueRoutes = set()
	for eachItem in routeInfo:
		uniqueRoutes.add((eachItem[0],eachItem[2],eachItem[3]))

	# delete the file that I added
	try:
		os.remove('cisco_ios_show_ip_route.template')
	except:
		pass

	# print out a report for the user
	print("************************************************")
	print("*                                              *")
	print("*              Route Summary                   *")
	print("*                                              *")
	print("************************************************")
	print()
	print("The following file was analyzed: " + fileName)
	print()
	print("The number of connected routes is: " + str(len([ x for x in uniqueRoutes if x[0]=="C" ])))
	print("The number of EIGRP routes is: " + str(len([ x for x in uniqueRoutes if x[0]=="D" ])))
	print("The number of Local routes is: " + str(len([ x for x in uniqueRoutes if x[0]=="L" ])))
	print("The number of OSPF routes is: " + str(len([ x for x in uniqueRoutes if x[0]=="O" ])))
	print("The number of static routes is: " + str(len([ x for x in uniqueRoutes if x[0]=="S" ])))

if __name__ == "__main__":

	# this gets run if the script is called by itself from the command line
	main(sys.argv)