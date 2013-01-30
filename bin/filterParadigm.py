#!/usr/bin/env python
"""
filterParadigm.py: performs the na sample and filtering on the paradigm output file
"""
## Written by: Sam Ng
import getopt, os, os.path, re, sys
from optparse import OptionParser

basedir = os.path.dirname(os.path.abspath(__file__))

filterFeatures = "%s/%s" % (basedir, "filterFeatures.py")
pyJoin = "%s/%s" % (basedir, "join.py")

def main():
    ## parse arguments
    parser = OptionParser(usage = "%prog [options] unfiltered_all")
    parser.add_option("--fr", "--filter-real", dest="filtered_real", help="Filtered Output", default="filtered.real.tab")
    parser.add_option("--fa", "--filter-all", dest="filtered_all", help="Filtered Output", default="filtered.all.tab")
    parser.add_option("--ur", "--unfilter-real", dest="unfiltered_real", help="Filtered Output", default="unfiltered.real.tab")
    parser.add_option("--na", "--filter-na", dest="filter_na", help="Filter NA", action="store_true", default=False)
    parser.add_option("-c", "--count", dest="count", help="Filter Count", type=int, default=1)
    parser.add_option("-m", "--min", dest="min", help="Min Value", type=float, default=0.5)
    
    
    options, args = parser.parse_args()
    
    inputFile = os.path.abspath(args[0]) 
    if len(args) != 1:
        sys.stderr.write("ERROR: incorrect number of arguments\n")
        sys.exit(1)

    select = {}
    f = open(inputFile, "r")
    o = open(options.filtered_all, "w")
    
    header = f.readline()
    o.write(header)
    headerA = header.split("\t")
    headerA.pop(0)

    for line in f:
        lineA = line.strip("\n").split("\t")
        row_name = lineA.pop(0)
        currCount = 0
        #for val in lineA:
        for i in range(len(lineA)):
            val = lineA[i]
            if options.filter_na and headerA[i][:3] == "na_":
                continue
            try:
                if abs(float(val)) >= options.min:
                    currCount += 1
            except ValueError:
                pass
            if currCount >= options.count:
                o.write(line)
                select[row_name] = True
                break
    o.close()
    f.close()
    
    o_ur = open(options.unfiltered_real, "w")
    o_fr = open(options.filtered_real, "w")    
    f = open(inputFile, "r")
    sampleNames = f.readline().rstrip().split("\t")[1:]
    includeCols = []
    for i, sample in enumerate(sampleNames):
        if sample.startswith("na_") or sample.startswith("nw_"):
            continue
        includeCols.append(i)
    data = [sampleNames[i] for i in includeCols]
    o_ur.write("%s\t%s\n" % ("id", "\t".join(data)))
    o_fr.write("%s\t%s\n" % ("id", "\t".join(data)))
    for line in f:
        pline = line.rstrip().split("\t")
        feature = pline[0]
        data = [pline[i+1] for i in includeCols]
        
        o_ur.write("%s\t%s\n" % (feature, "\t".join(data)))
        if feature in select:
            o_fr.write("%s\t%s\n" % (feature, "\t".join(data)))

    f.close()
    o_ur.close()
    o_fr.close()
    
  
if __name__ == "__main__":
    main()
