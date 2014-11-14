#!/usr/bin/env python
"""
filterParadigm.py
    by Sam Ng, Steve Benz, Charles Vaske, and Kyle Ellrott
"""
import logging, os, re, sys
from optparse import OptionParser

## logger
logging.basicConfig(filename="filter.log", level=logging.INFO)

## executables
bin_dir = os.path.dirname(os.path.abspath(__file__))
filter_exec = "%s/%s" % (bin_dir, "filterFeatures.py")

def main():
    ## parse arguments
    parser = OptionParser(usage = "%prog [options] unfiltered_all")
    parser.add_option("--fr", "--filter-real", dest="filtered_real", default="filtered.real.tab",
                      help="Feature-filtered output with only reals")
    parser.add_option("--fa", "--filter-all", dest="filtered_all", default="filtered.all.tab",
                      help="Feature-filtered output with reals and nulls")
    parser.add_option("--ur", "--unfilter-real", dest="unfiltered_real", default="unfiltered.real.tab",
                      help="Unfiltered output with only reals")
    parser.add_option("--na", "--filter-na", dest="filter_na", action="store_true", default=False,
                      help="Filter out NA")
    parser.add_option("-c", "--count", dest="count", type=int, default=1,
                      help="Filter Count")
    parser.add_option("-m", "--min", dest="min", type=float, default=0.5,
                      help="Min IPL Value")
    
    options, args = parser.parse_args()
    
    input_file = os.path.abspath(args[0]) 
    if len(args) != 1:
        logging.error("ERROR: incorrect number of arguments\n")
        sys.exit(1)
    
    select = {}
    f = open(input_file, "r")
    o = open(options.filtered_all, "w")
    
    header = f.readline()
    o.write(header)
    headerA = header.split("\t")
    headerA.pop(0)
    
    for line in f:
        lineA = line.strip("\n").split("\t")
        row_name = lineA.pop(0)
        current_count = 0
        #for val in lineA:
        for i in range(len(lineA)):
            val = lineA[i]
            if options.filter_na and headerA[i][:3] == "na_":
                continue
            try:
                if abs(float(val)) >= options.min:
                    current_count += 1
            except ValueError:
                pass
            if current_count >= options.count:
                o.write(line)
                select[row_name] = True
                break
    o.close()
    f.close()
    
    o_ur = open(options.unfiltered_real, "w")
    o_fr = open(options.filtered_real, "w")    
    f = open(input_file, "r")
    sample_names = f.readline().rstrip().split("\t")[1:]
    include_cols = []
    for i, sample in enumerate(sample_names):
        if sample.startswith("na_") or sample.startswith("nw_"):
            continue
        include_cols.append(i)
    data = [sample_names[i] for i in include_cols]
    o_ur.write("%s\t%s\n" % ("id", "\t".join(data)))
    o_fr.write("%s\t%s\n" % ("id", "\t".join(data)))
    for line in f:
        parts = line.rstrip().split("\t")
        feature = parts[0]
        data = [parts[i+1] for i in include_cols]
        
        o_ur.write("%s\t%s\n" % (feature, "\t".join(data)))
        if feature in select:
            o_fr.write("%s\t%s\n" % (feature, "\t".join(data)))
    
    f.close()
    o_ur.close()
    o_fr.close()

if __name__ == "__main__":
    main()
