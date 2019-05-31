#!/usr/bin/python

# cellpars2manyhocs.pl by Ted Ballou, Version 2. 2/7/2011.

# The purpose of this script is to create a set of cell models that
# incorporate mechanism and geometric parameters and global values that are
# extrapolated between two extremes; for convenience these two extremes are
# identified as "low threshold" and "high threshold." Each desired parameter
# or global along with their associated extreme values must be represented by
# a line in the "csv" input file according to the format described below. The
# number of cells to be generated is specified by the user, with a default
# value of 11. For each generated cell a directory is created and a "hoc" file
# that contains the hoc statements to assign the interpolated values
# appropriate to that cell is placed in its directory. The directory and the
# hoc file names are based on the csv file name, with the cell number
# appended.
#
# There are two applications for this at present: 
#
# 1. Generate a set of cells for sensitivity analysis, to illustrate the
# effects of gradually changing various parameters.
#
# 2. Generate sets of cells with gradually changing properties in
# order to simulate populations of neurons with incrementally varying
# properties; for example, spinal motoneurons with continuously varying
# properties representing slow and fatiguing muscle motor units.

# This code takes a comma-delimited file (with extension "csv" standing for
# "commma-separated-values") with four required fields and one optional field: 
#
# 1. NEURON segment name, OR the string "Global", OR "*" (see below)
# 2. NEURON mechanism, OR the global parameter name
# 3. low-threshold value ("lt") for the parameter or global
# 4. high-threshold value ("ht") for the parameter or global
# 5. (optional) nonlinear "indicator"
#
# If "*" is in the first field then what ever is in the second field is
# transferred directly to the output cell files so you can place hoc
# statements in the csv file to be transferred into the cell files.
# 
# On execution the code will prompt for the "Number of cells" to generate,
# which will be assigned to the variable $Ncells. The default value for
# $Ncells is 11, resulting in cell numbers 0, 1, 2, ..., 10.
#
# The code will generate hoc files for $Ncells cells, containing an assignment
# line for each parameter or global, with assignment values extrapolated
# between the two extremes. The low threshold value will be assigned to cell
# number 0, and the high threshold value will be assigned to cell number
# ($Ncells-1); in the default case $Ncells is ll and the ht value is assigned
# to cell number 10. For cell numbers 1 through $Ncells-2, an extrapolated
# value will be assigned based on the nonlinear indicator; if this 5th field
# is absent, the default nonlinear indicator of 0 will be used, which assigns
# a linear extrapolation between the lt and ht values.
#
# For positive nonlinear indicator values, the population will be skewed with
# most of the cells having extrapolated values less than the mean of lt and
# ht; this "$skew" is caluclated as the fraction of the range from lt to ht,
# taken to the power of (1+$nonlin_ind). For negative nonlinear indicator
# values, the population will be skewed with most of the cells having
# extrapolated values more than the mean of lt and ht; this "$skew" is
# calculated as (1 minus the fraction of the range from lt to ht), taken to
# the power of (1-$nonlin_ind), subtracted from 1. These formulas result in a
# nicely symmetric chart for positive, negative, and fractional values of
# $nonlin_ind. See subroutine intrpolate() for the details. Also see the
# documentation and examples in the excel file doc/NonlinearityScaling.xls.
#
# EXAMPLE: say the parameter soma.diam has lt=45 and ht=65. The following
# table shows sample interpolations for nonlinear indicator values of 0 (the
# default), 1, and 2. Note that most of the values for the last two columns
# are LESS than the mean of 45 and 65 (55).
#
# Indicator 	0     1     2
# Cell  0	45.00 45.00 45.00
# Cell  1 	47.00 45.20 45.02
# Cell  2 	49.00 45.80 45.16
# Cell  3 	51.00 46.80 45.54
# Cell  4 	53.00 48.20 46.28
# Cell  5 	55.00 50.00 47.50
# Cell  6 	57.00 52.20 49.32
# Cell  7 	59.00 54.80 51.86
# Cell  8 	61.00 57.80 55.24
# Cell  9 	63.00 61.20 59.58
# Cell 10 	65.00 65.00 65.00
#
# I find it convenient to create the input csv file as a table using excel or
# Open Office calc "OOcalc" and then "SaveAs" a comma-delimited csv file, but
# any text editor can be used to create the csv file.

# File structure:
# First line: ,,lt header, ht header (this line is not used by the script)
# The remaining lines have four OR five fields:
# section, mechanism, lt value, ht value, (nonlin_ind)
# OR
# designation as "Global", global parameter name, lt value, ht value, (nonlin_ind)

###############
# CODE BEGINS
###############
# Invoke perl module to get current working directory

import os # has os.getcwd()
import sys # for args passed on command line

Ncells = 11	# the total number of cells, including lt and ht
cur_cell_no = 0	# globalize this variable, "current cell #"
skew = 0.0 # a global variable
# optionally put csv file on command line, or as reply to prompt when program runs
# [Note: it's easier on command line since <TAB> provides file expansion]
global nonlin_ind
nonlin_ind=0.0 # global variable
fields=[]

print "%%%%%%%%   to abort type <ctrl-c>    %%%%%%%%\n"

if (len(sys.argv)!=2):
  myf=raw_input("Enter the name of the ht/lt parameters \".csv\" file: ")
else:
  myf = sys.argv[1]

if (len(myf)>1):
  try:
    fid=open(myf,"r")
  except:
    print("Cannot open file " + myf + " for reading" )
    print("Invoke with csv file in current directory")
    sys.exit(1)
else:
  print "No txt file supplied as input."
  exit(1)

print("Default number of cells is "+str(Ncells))
test=raw_input("If this is ok hit <return>; otherwise type the desired number: ")
if len(test):
  test_num=eval(test)
  if test_num>0:
    Ncells = float(test_num)
  else:
    print "non-numeric or zero input; using default Ncells value = ", Ncells

#Generate a base name for generated sensitivity directories & files
# mydir array is the list of directories in the full path to current dir

absolute_dir=os.getcwd()
mydir=absolute_dir.split('/')
# get the name of the parent directory: last member of the array split by '/'
basen = mydir[-1].strip()
# strip it down to only the characters preceding the first underscore

basen=basen.split('_')[0]

# Read the data into an array
datalist = fid.readlines()
fid.close()

# scrub the quotes generated by the conversion of spreadsheet to cvs
dl=[]
for line in datalist:
  dl.append(line.replace('"', '').strip())

# The first line of the data file contains the low threshold and high
# threshold headers
# [these variable are not currently used]
fields = dl[0].split(',')	# first line of the csv file

ltidx = 2
lthdr = fields[ltidx]
htidx = 3
hthdr = fields[htidx]
print("lthdr = "+lthdr+", hthdr = " + hthdr)

# scrub the first line
del dl[0]

# The remaining lines in this file have four fields:
# section, mechanism, lt value, ht value
# OR
# designation as "Global", global parameter name, lt value, ht value

# now treat each segment mechanism, generating a cell array between the 
# lt and ht values

# Use values linearly extrapolated between the lt and ht cells, and
# generate hoc files for Ncells cells, each in its own directory

##########################################
# functions

#######################


#################
# isnumeric() subroutine
#
# arg 1: string to be tested for being a numeric value
#
# Utility to validate argument as numeric  

# from 
# http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-float-in-python

def isnumeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

########################################
# getintrp subroutine
#
# arg 1: lt variable value
# arg 2: ht variable value
#
# interpolates lt and ht values; uses global variables Ncells, skew, and
# cur_cell_no. lt and ht non-ranging parameter values are passed as
# arguments

def getintrp(start, end):  
  global skew
  #print "start="+repr(start)+",end="+repr(end)+", skew="+repr(skew)
  if ((not isnumeric(start)) or (not isnumeric(end))):
    print("getintrp() bad args: "+ start +" and "+end)
    sys.exit("getintrp() requires numeric arguments")

  # The following line calculates the interpolation for the cur_cell_no'th
  # interval between the start and end values. This is a nonlinear mechanism
  # for the nonlin_ind being non-zero: skewed towards lt for positive values,
  # and skewed towards ht for negative values. See calculation of skew above.
  tmp=eval(start) + skew*(eval(end)-eval(start))
  #print "returning "+repr(tmp)
  return tmp

##########################
# extract_range subroutine
# 
# arg 1: colon-delimited lt ranging variable
# arg 2: colon-delimited ht ranging variable
#
# Returns: interpolated colon-delimited ranging variable
#
# This function extracts the start and end range values for lt and for ht,
# uses them to generate interpolated start and end range values, and returns
# the interpolated ranging variable

def extract_range(ltarg, htarg):
  # extract values from colon-delimited fields
  ltarg = ltarg.split(":")
  htarg = htarg.split(":")

  # and construct the interpolated ranging variable that is returned
  #print "debugging:"+repr(ltarg)+"|"+repr(htarg)
  #print len(ltarg)
  #print len(htarg)
  if len(ltarg)==1:
    return repr(getintrp(ltarg[0], htarg[0]))
  else:
    return repr(getintrp(ltarg[0], htarg[0]))+":"+repr(getintrp(ltarg[1], htarg[1]))

# intrpolate subroutine
#
# No arguments for this function; the cell number is accessed via the global
# variable cur_cell_no, and the low threshold (lt) and high threshold (ht)
# values are accessed via the glabal array elements fields[2] and fields[3].
#
# The "nonlinear indicator" nonlin_ind value is used to skew the interpolation,
# where skew is a value between 0 and 1, according to the formula below.
#
# Single values are interpolated between lt and ht.
# For colon-delimited ranges ("ranging variables") the range limits are
# extracted for low and high thresholds, and extrapolations between both
# elements are used, to generate the desired colon-delimited result, in the
# extract_range() subroutine.
#
# The cell number is accessed via the global variable cur_cell_no

def intrpolate():
  global fields
  global skew
  global nonlin_ind
  # Generate the "skew" for nonlinear interpolations. This converts the
  # nonlinear indicator nonlin_ind from a single number to a list of values,
  # one for each of the generated cells.
  fraction = float(cur_cell_no)/(Ncells-1)  # fraction of the range from start to
  #print "fraction = "+repr(fraction)+" for cell num " +repr(cur_cell_no)       # end 
  if (nonlin_ind >= 0):
    skew = fraction**(1+nonlin_ind)
  else:
    skew = 1-(1-fraction)**(1-nonlin_ind)
  
  #print "*** skew = ", skew;
  # Generate linearly interpolated value between lt and ht
  #print "len(fields)="+repr(len(fields))
  #print "fields = "+repr(fields)
  #print "fields[2]="+repr(fields[2])
  if (":" not in fields[2]):	# here if lt is NOT a ranging variable
    if (":" in fields[3]):
      sys.exit("high threshold (ht) is ranging but low threshold (lt) is not in "+line)
    # just a number, linearly interpolated based on the distance cur_cell_no
    # is between 0 and Ncells-1
    getintrp(fields[2], fields[3]);
  else:
    # Here if lt IS a ranging variable
    if ":" not in fields[3]:
      sys.exit("low threshold (lt) is ranging but high threshold (ht) is not")

    # generate the interpolated ranging value (two colon-delimited numbers)
  return extract_range(fields[2], fields[3])

# The make_cell() subroutine: create the interpolated hoc files.
# make_cell() argument is the cell # being generated

def make_cell(i):
  global fields
  global cur_cell_no
  global nonlin_ind
  #print "in make_cell("+str(i)+")"
  # Assign this global variable to the argument passed by caller
  cur_cell_no = i # shift;	# global variable used throughout the subroutines

  # Generate the output directory and file for the cell
  myfile = basen+"_"+str(cur_cell_no)

  # Continue even if the directory was previously present
  if not os.path.exists(myfile):
    os.makedirs(myfile)

  # Create the new hoc file; overwrite if already present
  MYF=open(myfile+"/"+myfile+".hoc","w")

  # calculate and write the values interpolated between lt and ht
  for line in dl:
    line=line.strip()

    # Populate the fields[] array with the current line from the csv file
    fields = line.split(',')
    #print "Processing line = "+repr(line)+" with fields = "+repr(fields)
    if fields[0]=='*': # asterisk transfers next field into program
      hocstatement=fields[1]
      MYF.write(hocstatement+"\n")
      continue
    else:
      if len(fields)>3:
        # Discard lines that have the lt or ht value field blank
        if (not len(fields[2])) or (not len(fields[3])):
          continue
      if len(fields)<4:
        # Discard lines that have less than 4 fields
        if not cur_cell_no:  # limit error print to one per line
          print "Less than four fields in discarded line="+repr(line)
        continue

    # fields 2 and 3 are low and high threshold values; if they are BOTH
    # colon-delimited ranging variables then field 1 (mechanism) MUST ALSO be
    # a colon-delimited ranging variable, ie Diam(10:4) intrp will then be
    # the interpolated colon-delimited ranging values

    # The nonlinear indicator field is set to 0 (NO nonlinearity) by default,
    # if 5th field is absent.
    if len(fields)>=5:
      if not len(fields[4]):
        nonlin_ind = 0.0
      else:
        # any rational number is ok
        nonlin_ind = float(fields[4])
        # print "setting nonlin_ind ="+repr(nonlin_ind)
    else:
	nonlin_ind = 0.0
    if fields[0]=='':
      hocstatement=""
    else:
      intrp = intrpolate()
      #print "intrp = "+intrp

    # generate hoc statement for:

    #  Global variables
    if ("Global" in fields[0]):
      hocstatement = fields[1]+" = "+intrp

      # OR "forall" directive
    elif ("forall" in fields[0]):
      hocstatement = fields[0]+"{"+fields[1]+" = "+intrp+"}"

      # OR (default) section.mechanism=value
    elif len(fields)>1:
      hocstatement = fields[0]+"."+fields[1]+" = "+intrp

    # save in the hoc file
    MYF.write(hocstatement+"\n")
  MYF.close()
# end of make_cell

for i in range(int(Ncells)):
  make_cell(i)	# Create each hoc file in its own directory

print("SUCCESS: created directories and hoc files for "+str(Ncells)+" cells")


############################
# END of MAIN
############################






