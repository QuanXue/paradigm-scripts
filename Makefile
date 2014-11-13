THISDIR = ${CURDIR}
THISOS = ${shell uname -s}

JOBTREE_GIT = git://github.com/benedictpaten/jobTree.git
JOBTREE_COMMIT = 649252f55d73c10c634e313a064b62b61af747c0
SONLIB_GIT = git://github.com/benedictpaten/sonLib.git
PATHMARK_GIT = git://github.com/ucscCancer/pathmark-scripts.git

all : init.sh init.csh

init.sh : jobTree exe
	echo export PATH=${THISDIR}/bin:\$${PATH} > init.sh
	echo if [ -n "\$${PYTHONPATH+x}" ] >> init.sh
	echo then >> init.sh
	echo export PYTHONPATH=${THISDIR}:${THISDIR}/bin:\$${PYTHONPATH} >> init.sh
	echo else >> init.sh
	echo export PYTHONPATH=${THISDIR}:${THISDIR}/bin >> init.sh
	echo fi >> init.sh

init.csh : jobTree exe
	echo setenv PATH ${THISDIR}/bin:\$${PATH} > init.csh
	echo if \$$?PYTHONPATH then >> init.csh
	echo setenv PYTHONPATH ${THISDIR}:${THISDIR}/bin:\$${PYTHONPATH} >> init.csh
	echo else >> init.csh
	echo setenv PYTHONPATH ${THISDIR}:${THISDIR}/bin >> init.csh
	echo endif >> init.csh

jobTree : sonLib
	git clone ${JOBTREE_GIT}
	cd jobTree; git checkout 649252f55d73c10c634e313a064b62b61af747c0; make

sonLib :
	git clone ${SONLIB_GIT}

exe :
	mkdir exe
	if (test -d /inside); then \
	cd exe; cp /inside/grotto/users/sng/bin/Paradigm/paradigm /inside/grotto/users/sng/bin/Paradigm/collectParameters .; \
	fi
	if (! test -e exe/paradigm); then \
	if [ ${THISOS} == Darwin ]; then \
	cd exe; cp ../public/exe/collectParameters ../public/exe/MACOSX/paradigm .; \
	elif [ ${THISOS} == Linux ]; then \
	cd exe; cp ../public/exe/collectParameters ../public/exe/LINUX/paradigm .; \
	else \
	echo "paradigm not compiled for ${THISOS}"; \
	fi \
	fi
	ln -s ${THISDIR}/exe/paradigm bin/
	ln -s ${THISDIR}/exe/collectParameters bin/

pathmark-scripts :
	if [ ! -d '../pathmark-scripts' ]; then \
		cd ..; git clone ${PATHMARK_GIT}; cd pathmark-scripts; make; \
	fi
	ln -s ../pathmark-scripts pathmark-scripts

galaxy : pathmark-scripts
	mkdir -p paradigm_module
	cp bin/* paradigm_module/
	cp -r pathmark-scripts/bin/* paradigm_module/

clean :
	rm -rf bin/paradigm bin/collectParameters pathmark-scripts jobTree sonLib exe init.sh init.csh
	if [ -d 'example' ]; then \
		cd example; make clean; \
	fi
