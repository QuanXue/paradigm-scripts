#!/usr/bin/env python
"""prepareParadigm.py: gather data files and create job lists

Creates in the current directory:
  clusterFiles/  the specified database tables or tab files
                 will be rank transformed and also pathway 
                 files are placed in this directory

  configEM.txt  the configuration file for EM runs
  jobsEM.list   the list of parasol jobs for EM

  config.txt     the configuration for the final run
  jobs.list      the list of parasol jobs fro the final run

Usage:
  prepareParadigm.py [options] attach1 evid1 [attach2 evid2 ...]

Evidence is specified as:
    table:<hg18_tablename>   where <hg18_tablename> is a table in hg18
    tableNoNorm:<hg18        like table:, but without median centering genes
    bioInt:<tablename>       where <tablename> is a table in bioInt
    http:<url>               read file from URL
    http:<url>               read file from URL, no quantile transform
    file:<tabfile_name>      where <tabfile_name> is the path to a file
    rawFile:<tabfile>        where <tabfile> is a file that won't be run
                             through quantile transformation

Options:
   -n int               the number of null batches (500 each) to create (default: 2)
   -s int               size of null batches (or 'same', see createNullSamples.py)
   -e path              path to paradigm exe (default: /hive/users/$USER/bin)
   -d dir               dogma directory (take top of config from here)
   -p dir               the directory containing pathway files 
                        (default is /hive/groups/cancerGB/paradigm/pathwayfiles/v1)
   -t str               use initial parameters stored from another params.txt
   -i string            inference parameters 
                        (default is method=JTREE,updates=HUGIN,verbose=1)
   -c options           options to pass to createNullFiles.py (quote them all)
   -b flt;flt[,flt;flt] boundaries for discretization, use comma to specify different
                        boundaries per evidence (default 0.333;0.667)
   -y                   using the public version of paradigm
   -q                   run quietly, don't output status
"""
## Written by: Charles Vaske
## Modifications by: Sam Ng
import os, sys, glob, getopt, re, subprocess, math, json
import pandas

###
### Experiments to find the path of the currently executing script
###
# print "os.path.curdir:", os.path.curdir
# print "os.path.realpath(os.path.curdir):", os.path.realpath(os.path.curdir)
# print "sys.argv[0]:", sys.argv[0]
# print "os.path.dirname(sys.argv[0]):", os.path.dirname(sys.argv[0])
# print "os.path.realpath(os.path.dirname(sys.argv[0])):", os.path.realpath(os.path.dirname(sys.argv[0]))
scriptDirectory = os.path.realpath(os.path.dirname(sys.argv[0]))
evidenceTypes = {
    "file":  (("cat %%s" +
               " | %s %s/quantileTransform.py /dev/stdin") % (sys.executable, scriptDirectory)),
    "rankAllFile":  (("cat %%s" +
               " | %s %s/quantileTransform.py /dev/stdin") % (sys.executable, scriptDirectory)),
    "rawFile":  "cat %s",
    "rawTrans": "%s %s/transpose.py -f %%s -" % (sys.executable, scriptDirectory)
    }

dataDir = "clusterFiles"
#outputEmDir = "outputFilesEM"
#outputDir = "outputFiles"

verbose = True
publicParadigm = False
publicBatchFix = False
standardAttach = ["genome", "mRNA", "protein", "active"]
standardDataFeatures = ["protein"]
paradigmExec = os.path.join(os.path.abspath(os.path.dirname(__file__)), "paradigm")

dryrun = False

nullOptions = ""
nullBatches = 2
nullBatchSize = 500

targetJobLength = 45 # seconds

disc = "0.333;0.667"
paramFile = ""

### If dogmaDir is defined, files in that directory are copied to the 
### destination directory.  Additionally, if the files 'configTop' or
### 'configTopEM' are in that directory, their contents replace
### the following two variables (don't forget the %s for inference!)
dogmaDir = ''
configTop = """pathway [max_in_degree=5,param_file=params.txt]
inference [%s]\n"""
configTopEM = """pathway [max_in_degree=5,param_file=params.txt]
inference [%s]
em_step ["""
inference="method=JTREE,updates=HUGIN,verbose=1"
configEmLine = "em [max_iters=1,log_z_tol=1e-10]\n"
def configELine(evidStub):
    if "disc" in evidStub:
        b = evidStub["disc"]
    else:
        b = disc
    return "evidence [suffix=%s,node=%s,disc=%s,epsilon=0.01,epsilon0=0.2]\n" \
        % (evidStub["suffix"], evidStub["attachment"], b)

paramHeader="> parameters em_iters=0 logZ=-1e300\n"

mutationParams="""> shared CondProbEstimation [pseudo_count=1,target_dim=3,total_dim=9] %s=codeMut
0.0
0.2
0.8
0.9998
0.0001
0.0001
0.0
0.2
0.8
"""

mutationParamsMask="""> mask shared CondProbEstimation [pseudo_count=1,target_dim=3,total_dim=9] %s=codeMut
0
nan
nan
nan
nan
nan
0
nan
nan
"""

def norm(array):
    s = sum(array)
    return [v/float(s) for v in array]

def initParams(numBins, reverse=False):
    base = [v for v in norm(range(1, 1+numBins))]
    up   = [str(v) for v in base]
    if (reverse):
        up.reverse()
    zero = norm([base[min(i, len(base) - i - 1)] for i in range(len(base))])
    zero = [str(v) for v in zero]
    down = [v for v in up]
    down.reverse()
    if not publicParadigm:
        return "\n".join(down + zero + up) + "\n"
    else:
        paramLines = ""
        for i, j in enumerate(down):
            paramLines += "%s\t%s\t%s\n" % (i, 0, j)
        for i, j in enumerate(down):
            paramLines += "%s\t%s\t%s\n" % (i, 1, j)
        for i, j in enumerate(down):
            paramLines += "%s\t%s\t%s\n" % (i, 2, j)
        return paramLines

def readParams(paramFile):
    storedParams = {}
    f = open(paramFile, "r")
    f.readline()
    for line in f:
        if line.isspace():
            continue
        line = line.rstrip("\n\r")
        if line.startswith(">"):
            attachment = re.split("=", line)[-1]
            storedParams[attachment] = ""
        else:
            storedParams[attachment] += "%s\n" % (line)
    f.close()
    return storedParams

def writeBaseParamsFile(pfilename, evidence, storedParams = {}):
    writeHeader = not os.path.exists(pfilename)
    pfile = open(pfilename, "a")
    if writeHeader:
        pfile.write(paramHeader)
    for e in evidence:
        bins = len(e["disc"].split(";")) + 1
        if not publicParadigm:
            spec = e["attachment"]
        else:
            spec = "-obs>"
        if e["attachment"] != "codeMut":
            if not publicParadigm:
                pfile.write("> shared CondProbEstimation [pseudo_count=1,target_dim=%i,total_dim=%i] %s=%s\n" % (bins, 3*bins, e["suffix"], e["attachment"]))
                if e["attachment"] in storedParams:
                    pfile.write(storedParams[e["attachment"]])
                else:
                    pfile.write(initParams(bins, reverse=("reversed" in e)))
            else:
                pfile.write("> child='%s' edge1='%s'\n" % (e["suffix"], "-obs>"))
                if e["attachment"] in storedParams:
                    pfile.write(storedParams[e["attachment"]])
                else:
                    pfile.write(initParams(bins, reverse=("reversed" in e)))
        else:
            pfile.write(mutationParams % e["suffix"])
            if os.path.exists("mask.params"):
                mfile = open("mask.params", mode="a")
                mfile.write(mutationParamsMask % e["suffix"])
                mfile.close()
    pfile.close()

def readPathwayFeatures(pathway):
    features = []
    f = open(pathway, "r")
    for line in f:
        parts = line.rstrip().split("\t")
        if parts[0] in standardDataFeatures:
            features.append(parts[1])
    return features

def readPathwayTiming(directory, pathways):
    if not os.path.exists(directory + "/timings.tab"):
        return {pathway.split('/')[-1] : 900.0 for pathway in pathways}
    tfile = open(directory + "/timings.tab", "r")
    samplesline = tfile.readline().rstrip();
    m = re.search('^#\s*samples\s*(\d+)\s*', samplesline)
    if not m:
        print "missing samples line on pathway timings"
        sys.exit(1)
    samples = int(m.group(1))
    result = {}
    for line in tfile:
        timestring, pathway = line.rstrip().split("\t")
        result[pathway] = float(timestring) / samples
    return result

def numBuckets(pathway, samples, timings, targetLength):
    if pathway not in timings:
        return samples
    length = timings[pathway] * samples
    return min(int(math.ceil(length / targetLength)), samples)

def usage(code=0):
    print __doc__
    if code != None: sys.exit(code)

def log(msg):
    if (verbose):
        sys.stderr.write(msg)

def evidenceStreamCommand(evidenceSpec):
    (type, sep, name) = evidenceSpec.partition(":")
    if type not in evidenceTypes:
        print "Unrecognized evidence spec \"%s:\"" % evidenceSpec 
        usage(1)
    return (evidenceTypes[type] % name)

def evidenceStub(attachment, evidspec, index):
    (type, sep, name)= evidspec.partition(":")
    bname = os.path.basename(name)
    (where, sep, options) = attachment.partition(":")
    if (len(re.split(",", disc)) > 1):
        eviddisc = re.split(",", disc)[index]
    else:
        eviddisc = disc
    stub = {"attachment" : where, 
            "spec" : evidspec, 
            "suffix" : bname, 
            "outputFile" : dataDir + "/" + bname,
            "disc" : eviddisc}
    if options != "":
        stub.update(json.loads(options))
    return stub

def readFileLineNumber(filename):
    wcArgs = ["sh", "-c", "cat %s | wc -l" % filename]
    return int(subprocess.Popen(wcArgs, 
                                stdout=subprocess.PIPE).communicate()[0])

def syscmd(cmd):
    log("running:\n    " + cmd + "\n")
    if dryrun:
        exitstatus = 0
    else:
        exitstatus = os.system(cmd)
    if exitstatus != 0:
        print "Failed with exit status %i" % exitstatus
        sys.exit(10)
    log(" ... done\n")

def mkdir(dirname):
    try:
        os.mkdir(dirname)
    except OSError, err:
        if err.strerror == "File exists":
            print "WARNING: directory %s already exists" % dirname
        else:
            print "couldn't make directory %s: %s" % (dirname, str(err))
            sys.exit(1)

def prepareParadigm(args):
    pathwayDir = None
    try:
        opts, args = getopt.getopt(args, "p:n:e:qc:b:s:t:i:d:y")
    except getopt.GetoptError, err:
        print str(err)
        usage(2)
    
    if len(args) < 2 or len(args) % 2 != 0:
        print "need an even number of arguments"
        usage(1)
    
    global paradigmExec, dryrun, nullOptions, disc
    global nullBatches, nullBatchSize, paramFile, inference, dogmaDir
    global configTop, configTopEM
    global publicParadigm, publicBatchFix
    for o, a in opts:
        if o == "-p":
            pathwayDir = a
        elif o == "-y":
            publicParadigm = True
        elif o == "-d":
            dogmaDir = a
            fn = os.path.join(dogmaDir, "configTop")
            if os.path.exists(fn):
                cfile = open(fn)
                configTop = cfile.read()
                cfile.close()
            fn = os.path.join(dogmaDir, "configTopEM")
            if os.path.exists(fn):
                cfile = open(fn)
                configTopEM = cfile.read().rstrip("\n")
                cfile.close()
        elif o == "-n":
            nullBatches = int(a)
        elif o == "-s":
            if a == "same":
                nullBatchSize = a
            else:
                nullBatchSize = int(a)
        elif o == "-e":
            paradigmExec = a
        elif o == "-q":
            verbose = False
        elif o == "-c":
            nullOptions = a
        elif o == "-b":
            disc = a
        elif o == "-t":
            paramFile = a
        elif o == "-i":
            inference = a
    
    log("Making sub-directories\n")
    mkdir(dataDir)
    
    evidence = [evidenceStub(a,e,i) for a, e, i in zip(args[0::2], args[1::2], range(len(args[0::2])))]
    for e in evidence:
        log("Evidence:\n")
        for k in e.keys():
            log("    %s\t%s\n" % (k,e[k]))
    
    for e in evidence:
        if (e["attachment"] not in standardAttach):
            print "WARNING: %s is non-standard: " % e["attachment"]
            print "         standard attachments are: " + str(standardAttach)
        cmd = evidenceStreamCommand(e["spec"]) + " > " + e["suffix"]
        syscmd(cmd)
    
    cmd = "%s %s/createNullFiles.py %s -t %s -p %s/na_batch -b %i %s " % \
        (sys.executable, scriptDirectory, nullOptions, dataDir, dataDir, 
         nullBatches, str(nullBatchSize)) \
        + " ".join([e["suffix"] for e in evidence])
    syscmd(cmd)
    
    # minus 1 for header
    samples = readFileLineNumber(evidence[0]["outputFile"]) - 1
    
    log("Writing config file for EM\n")
    confFile = open("configEM.txt", "w")
    if not publicParadigm:
        confFile.write("# " + " ".join(sys.argv) + "\n")
    confFile.write(configTopEM % inference)
    if not publicParadigm:
        confFile.write(",".join([e["suffix"] + "=" + e["attachment"]
                                 for e in evidence]))
    else:
        confFile.write(",".join([e["suffix"] + "=-obs>" for e in evidence]))
    
    confFile.write("]\n")
    confFile.write(configEmLine)
    [confFile.write(configELine(e)) for e in evidence]
    confFile.close()
    
    log("Writing config file for final run\n")
    confFile = open("config.txt", "w")
    if publicParadigm:
        parse_configTop = re.split("\n", configTop)
        configTop = ""
        for line in parse_configTop:
            if not line.startswith("output"):
                configTop += "%s\n" % (line)
    confFile.write(configTop % inference)
    [confFile.write(configELine(e)) for e in evidence]
    confFile.close()
    
    if dogmaDir:
        log("Copying dogma files\n")
        syscmd("cp %s/* ." % dogmaDir)
    
    log("Copying pathway files\n")
    syscmd("cp %s/*_pathway.tab %s" % (pathwayDir, dataDir))
    
    pathFiles = glob.glob(dataDir + "/*_pathway.tab")
    timings = readPathwayTiming(pathwayDir, pathFiles)
    
    log("writing EM jobs list\n")
    jfile = open("jobsEM.list", "w")
    for p in pathFiles:
        pathway = os.path.basename(p)
        buckets = numBuckets(pathway, samples, timings, targetJobLength)
        pid = pathway[0:-len("_pathway.tab")]
        if buckets == 1:
            emOut = "outputFilesEM/" + pid + "_learned_parameters.fa"
            jfile.write("%s -p %s -c configEM.txt -b %s/ -e %s\n" % 
                        (paradigmExec, p, dataDir, emOut))
        elif not publicParadigm:
            for b in range(buckets):
                pbid = "%s_b%i_%i" % (pid, b, buckets)
                emOut = "outputFilesEM/" + pbid + "_learned_parameters.fa"
                out = "outputFilesEM/" + pbid + "_output.fa"
                c = "%s -p %s -c configEM.txt -b%s/ -e %s -s %i,%i\n" % \
                    (paradigmExec, p, dataDir, emOut, b, buckets)
                jfile.write(c)
        else:
            publicBatchFix = True
            buckets = samples
            for b in range(buckets):
                pbid = "%s_b%i_%i" % (pid, b, buckets)
                emOut = "outputFilesEM/" + pbid + "_learned_parameters.fa"
                out = "outputFilesEM/" + pbid + "_output.fa"
                c = "%s -p %s -c configEM.txt -b%s/%s_ -e %s\n" % \
                    (paradigmExec, p, dataDir, pbid, emOut)
                jfile.write(c)
    jfile.close()
    
    log("writing jobs list\n")
    jfile = open("jobs.list", "w")
    for p in pathFiles:
        pathway = os.path.basename(p)
        buckets = numBuckets(pathway, samples, timings, targetJobLength)
        pid = pathway[0:-len("_pathway.tab")]
        if (buckets == 1):
            out = "outputFiles/" + pid + "_output.fa"
            jfile.write("%s -p %s -c config.txt -b %s/ -o %s\n" % 
                        (paradigmExec, p, dataDir, out))
        elif not publicParadigm:
            for b in range(buckets):
                pbid = "%s_b%i_%i" % (pid, b, buckets)
                out = "outputFiles/" + pbid + "_output.fa"
                c = "%s -p %s -c config.txt -b %s/ -o %s -s %i,%i\n" % \
                    (paradigmExec, p, dataDir, out, b, buckets)
                jfile.write(c)
        else:
            publicBatchFix = True
            buckets = samples
            for b in range(buckets):
                pbid = "%s_b%i_%i" % (pid, b, buckets)
                out = "outputFiles/" + pbid + "_output.fa"
                c = "%s -p %s -c config.txt -b %s/%s_ -o %s\n" % \
                    (paradigmExec, p, dataDir, pbid, out)
                jfile.write(c)
        for n in range(1, nullBatches + 1):
            if nullBatchSize == "same":
                numNullSamples = samples
            else:
                numNullSamples = nullBatchSize
            buckets = numBuckets(pathway, numNullSamples, 
                                 timings, targetJobLength)
            if buckets == 1:
                out = "outputFiles/" + pid + "_batch_" + str(n) + "_output.fa"
                c = "%s -p %s -c config.txt -b %s/na_batch_%i_ -o %s\n" % \
                    (paradigmExec, p, dataDir, n, out)
                jfile.write(c)
            elif not publicParadigm:
                for b in range(buckets):
                    pbid = "%s_b%i_%i" % (pid, b, buckets)
                    out = "outputFiles/%s_batch_%s_output.fa" % (pbid, str(n))
                    batch = "%s/na_batch_%i_" % (dataDir, n)
                    c = "%s -p %s -c config.txt -b %s -o %s -s %i,%i\n" % \
                        (paradigmExec, p, batch, out, b, buckets)
                    jfile.write(c)
            else:
                publicBatchFix = True
                buckets = numNullSamples
                for b in range(buckets):
                    pbid = "%s_b%i_%i" % (pid, b, buckets)
                    out = "outputFiles/%s_batch_%s_output.fa" % (pbid, str(n))
                    batch = "%s/%s_na_batch_%i_" % (dataDir, pbid, n)
                    c = "%s -p %s -c config.txt -b %s -o %s\n" % \
                        (paradigmExec, p, batch, out)
                    jfile.write(c)
    jfile.close()
    
    if len(paramFile) > 0:
        writeBaseParamsFile("params0.txt", evidence, storedParams = readParams(paramFile))
    else:
        writeBaseParamsFile("params0.txt", evidence)
    
    if os.path.exists("params.txt"):
        os.unlink("params.txt")
    syscmd("ln -s params0.txt params.txt")
    
    if publicBatchFix:
        log("Batching data for Paradigm\n")
        dataFiles = []
        for file in os.listdir(dataDir):
            for e in evidence:
                if file.endswith(e["outputFile"].split("/")[-1]):
                    dataFiles.append(file)
        for file in dataFiles:
            data_frame = pandas.read_csv("%s/%s" % (dataDir, file), sep = '\t', index_col = 0)
            dataFeatures = list(data_frame.columns)
            dataFeatures.sort()
            dataSamples = list(data_frame.index)
            dataSamples.sort()
            
            for p in pathFiles:
                pathway = os.path.basename(p)
                pid = pathway[0:-len("_pathway.tab")]
                pathFeatures = readPathwayFeatures(p)
                buckets = len(dataSamples)
                for b in range(buckets):
                    pbid = "%s_b%i_%i" % (pid, b, buckets)
                    data_frame[list(set(dataFeatures) & set(pathFeatures))].loc[[dataSamples[b]]].to_csv("%s/%s" % (dataDir, pbid + "_" + file), sep = '\t', na_rep = 'NA', index_label = 'id')

if __name__ == "__main__":
    prepareParadigm(sys.argv[1:])
