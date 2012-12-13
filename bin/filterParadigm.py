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
    parser.add_option("-w", "--workdir", dest="workdir", help="Common Work directory", default="./")
    parser.add_option("--fr", "--filter-real", dest="filtered_real", help="Filtered Output", default=None)
    parser.add_option("--fa", "--filter-all", dest="filtered_all", help="Filtered Output", default=None)
    parser.add_option("--ur", "--unfilter-real", dest="unfiltered_real", help="Filtered Output", default=None)
    
    options, args = parser.parse_args()
    
    inputFile = os.path.abspath(args[0]) 
    if len(args) != 1:
        sys.stderr.write("ERROR: incorrect number of arguments\n")
        sys.exit(1)
    
    workdir = os.path.abspath(options.workdir)
    
    o = open("merge_merged_unfiltered.tab", "w")
    f = open(inputFile, "r")
    sampleNames = f.readline().rstrip().split("\t")[1:]
    includeCols = []
    for i, sample in enumerate(sampleNames):
        if sample.startswith("na_") or sample.startswith("nw_"):
            continue
        includeCols.append(i)
    data = [sampleNames[i] for i in includeCols]
    o.write("%s\t%s\n" % ("id", "\t".join(data)))
    for line in f:
        pline = line.rstrip().split("\t")
        feature = pline[0]
        data = [pline[i+1] for i in includeCols]
        o.write("%s\t%s\n" % (feature, "\t".join(data)))
    f.close()
    o.close()
    os.system("python %s -n merge_merged_unfiltered.tab 1,0.5 > merge_merged.tab" % (filterFeatures))
    os.system("cut -f1 merge_merged.tab > filter.include")
    os.system("python %s -h filter.include merge_merged_unfiltered.all.tab > merge_merged.all.tab" % (pyJoin))
    os.system("rm -f filter.include")

if __name__ == "__main__":
    main()
