all : unfiltered.all.tab filtered.all.tab

unfiltered.all.tab :
	galaxyParadigm.py -y -p data/pathways_v1_pid66.zip genome rankAllFile:data/Genome_Wide_SNP_6.genome.shared.tab mRNA rankAllFile:data/AgilentG4502A_07.mRNA.shared.tab

filtered.all.tab : unfiltered.all.tab
	filterParadigm.py unfiltered.all.tab

clean :
	rm -rf merge* unfiltered.* filtered.* clusterFiles pathway dogma config* jobs* outputFiles* params* *.dogma *.imap Genome_Wide_SNP_6.genome.shared.tab AgilentG4502A_07.mRNA.shared.tab *.log .jobTree*
