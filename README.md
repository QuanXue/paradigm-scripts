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
galaxyParadigm.py [options] attachment file:path [attachment file:path ...]

- **attachment** - text 
- **file:path** - text

- **-w work_directory** - text
- **-n null_size** - text
- **-d dogma_library** - text
- **-p pathway_library** - text
- **-b discretization_bounds** - text
- **-t param_file** - text
- **-s** - text
- **-y** - text


Folders
------
* bin : executables
* dogmas : dogma plate models for PARADIGM
* examples : OV inputs for demonstration purposes
* exe : pre-compiled paradigm binaries for select architectures
* pathways : paradigm compatible pathway files

