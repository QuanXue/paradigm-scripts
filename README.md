PARADIGM: Pathway Recognition Algorithm using Data Integration on Genomic Models
========

Current Version 
--------

1.0

Authors
--------

Charles Vaske, Stephen Benz, Sam Ng, Kyle Ellrott, David Haussler and Joshua M. Stuart


Requirements
--------

- [python](http://www.python.org/) >= 2.7
   - [scipy](http://www.scipy.org/) >= 0.12.0
   - [numpy](http://numpy.scipy.org/)
   - [pandas](http://pandas.pydata.org/)

Installation
-------

Note: This repository contains code that allows users to parallelize PARADIGM on a large cohort of samples, the PARADIGM binary is separate and may need to be compiled from https://sbenz.github.com/Paradigm

- Install dependencies
- Download the paradigm-scripts repository to the desired location
- Run "make" in paradigm-scripts/ to generate source files
- Source init files for paradigm-scripts (init.sh for bash and init.csh for csh)
- Run code on example data in examples/ with "make"

Command-Line
------
```
galaxyParadigm.py [options] attachment file:path [attachment file:path ...]

attachment - dogma node to attach evidence to
file:path - type of and path to evidence file

-w work_directory - path to directory where work is to be done (default: ./)
-n null_size - number of null samples to be generated per sample
-d dogma_library - path or zip file describing the PARADIGM plate model
-p pathway_library - path, zip, or file containing PARADIGM pathway interactions
-b discretization_bounds - value cutoffs for data discretization
-t param_file - parameter file to use as initial state
-s - skip EM parameter training
-y - utilizing the public PARADIGM binary
```

Folders
------
* bin : executables
* dogmas : dogma plate models for PARADIGM
* examples : OV inputs for demonstration purposes
* exe : pre-compiled paradigm binaries for select architectures
* pathways : paradigm compatible pathway files

