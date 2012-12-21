#!/usr/bin/env python

import string,sys
import getopt
import array

if __name__ == "__main__":

    opts, args = getopt.getopt(sys.argv[1:], "lf")
    if (len(args))!=2:
        sys.stderr.write("python transpose.py extractDataIn transposeOut-Paradigm\n")
        sys.exit(2)

    label_print = True
    use_float = True
    for o, a in opts:
            if o == "-l":
                label_print = False
            if o == "-f":
                use_float = True

    fin= open(args[0],'r')
    if args[1] == "-":
        fout = sys.stdout
    else:
        fout= open(args[1],'w')

    col_label = None
    row_label = []
    matrix=[]
    for line in fin.readlines():
        data = string.split(line.strip(),'\t')
        if col_label is None:
            col_label = data
        else:
            row_label.append(data[0])
            if use_float:
                o = array.array('f')
                for i in data[1:]:
                    try:
                        o.append(float(i))
                    except ValueError:
                        o.append(float('nan'))
            else:
                o = data[1:]
            row_label.append(data[0])
            matrix.append(o)

    #header
    out = []
    if label_print:
        out = [col_label[0]] + row_label
    else:
        out = row_label
    fout.write("\t".join(out) + "\n")

    #body
    for col in range(0, len(col_label)):
        out = []
        if label_print:
            out.append(col_label[col+1])
        for row in matrix:
            out.append(str(row[col]))
        fout.write("\t".join(out) + "\n")

    fin.close()
    fout.close()
