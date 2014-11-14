THISDIR = ${CURDIR}
THISOS = ${shell uname -s}

JOBTREE_GIT = git://github.com/benedictpaten/jobTree.git
JOBTREE_COMMIT = 649252f55d73c10c634e313a064b62b61af747c0
SONLIB_GIT = git://github.com/benedictpaten/sonLib.git
PATHMARK_GIT = git://github.com/ucscCancer/pathmark-scripts.git

all : init.sh init.csh

init.sh : jobTree bin/paradigm
	echo export PATH=${THISDIR}/bin:\$${PATH} > init.sh
	echo if [ -n "\$${PYTHONPATH+x}" ] >> init.sh
	echo then >> init.sh
	echo export PYTHONPATH=${THISDIR}:${THISDIR}/bin:\$${PYTHONPATH} >> init.sh
	echo else >> init.sh
	echo export PYTHONPATH=${THISDIR}:${THISDIR}/bin >> init.sh
	echo fi >> init.sh

init.csh : jobTree bin/paradigm
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

bin/paradigm :
	if (test -d /inside); then \
	cd bin; cp /inside/grotto/users/sng/bin/Paradigm/paradigm /inside/grotto/users/sng/bin/Paradigm/collectParameters .; \
	fi
	if (! test -e bin/paradigm); then \
	if [ ${THISOS} == Darwin ]; then \
	cd bin; cp ../exe/public/collectParameters ../exe/public/MACOSX/paradigm .; \
	elif [ ${THISOS} == Linux ]; then \
	cd bin; cp ../exe/public/collectParameters ../exe/public/LINUX/paradigm .; \
	else \
	echo "paradigm not compiled for ${THISOS}"; \
	fi \
	fi

pathmark-scripts :
	if [ ! -d '../pathmark-scripts' ]; then \
		cd ..; git clone ${PATHMARK_GIT}; cd pathmark-scripts; make; \
	fi
	ln -s ../pathmark-scripts pathmark-scripts

clean :
	rm -rf bin/paradigm bin/collectParameters pathmark-scripts jobTree sonLib init.sh init.csh
	if [ -d 'example' ]; then \
		cd example; make clean; \
	fi
