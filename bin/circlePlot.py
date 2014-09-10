#!/usr/bin/env python
"""
circlePlot.py: 

## Written By: Steve Benz and Zack Sanborn
## Modified By: Sam Ng and Evan Paull
## Last Updated: 08/27/2014
"""
import math, os, sys, re
from optparse import OptionParser
from matplotlib import *
use('Agg')

import numpy as np
import pandas

from pylab import *

verbose = True
tstep = 0.01
image_format = 'png'

class RGB:
    def __init__(self, r, g, b):
        self.r = int(round(r))
        self.g = int(round(g))
        self.b = int(round(b))
        
        if self.r > 255:
            self.r = 255
        elif self.r < 0:
            self.r = 0
        if self.g > 255:
            self.g = 255
        elif self.g < 0:
            self.g = 0
        if self.b > 255:
            self.b = 255
        elif self.b < 0:
            self.b = 0
    def hex(self):
        r = self.r
        g = self.g
        b = self.b
        hexchars = '0123456789ABCDEF'
        return('#' + hexchars[r / 16] + hexchars[r % 16] + hexchars[g / 16] + hexchars[g % 16] + hexchars[b / 16] + hexchars[b % 16])

def log(msg, die = False):
    if verbose:
        sys.stderr.write(msg)
    if die:
        sys.exit(1)

def syscmd(cmd):
    log("running:\n\t"+cmd+"\n")
    exitstatus = os.system(cmd)
    if exitstatus != 0:
        print "Failed with exit status %i" % exitstatus
        sys.exit(10)
    log("... done\n")

def readList(input_file, header = False):
    """
    Reads a simple 1 column list [2014-3-1]
    """
    input_list = []
    f = open(input_file, 'r')
    if header:
        f.readline()
    for line in f:
        if line.isspace():
            continue
        input_list.append(line.rstrip())
    f.close()
    return(input_list)

def parseColorMap(input_file):
    # by default ring index is the outer ring if not declared
    color_map = {}
    ring_index = -1
    f = open(input_file, 'r')
    for line in f:
        # a ring index of 0 refers to the center, 1 is the first ring, and -1 is the last
        if line.startswith('>'):
            ring_index = int(line.lstrip('>'))
            continue
        # third column may be a comment: ignore it
        parts = line.rstrip().split('\t')
        value = parts[0]
        try:
            value = float(value)
        except:
            raise Exception('ERROR: color map file not in proper format')
        
        if ring_index not in color_map:
            color_map[ring_index] = {}
        color_map[ring_index][value] = parts[1].split('.')
    f.close()
    return(color_map)

def scmp(a, b, feature, data_list):
    data_feature = feature
    if (a not in data_list[0]) & (b in data_list[0]):
        return(1)
    elif (a in data_list[0]) & (b not in data_list[0]):
        return(-1)
    elif (a not in data_list[0]) & (b not in data_list[0]):
        if len(data_list) == 1:
            return(0)
        else:
            return(scmp(a, b, feature, data_list[1:]))
    if data_feature not in data_list[0][a]:
        if '*' in data_list[0].index:
            data_feature = '*'
        else:
            if len(data_list) == 1:
                return(0)
            else:
                return(scmp(a, b, feature, data_list[1:]))
    val = cmp(data_list[0][a][data_feature], data_list[0][b][data_feature])
    if val == 0:
        if len(data_list) == 1:
            return(0)
        else:
            return(scmp(a, b, feature, data_list[1:]))
    else:
        return(val)

def getColorFromMap(val, color_map):
    try:
        val = float(val)
    except:
        raise Exception('ERROR: value not a number for color mapping')
    return(RGB(int(color_map[val][0]), int(color_map[val][1]), int(color_map[val][2])).hex())
    

def getColorFromValue(val, min_value, max_value, min_color = RGB(0, 0, 255), zero_color = RGB(255, 255, 255), max_color = RGB(255, 0, 0)):
    try:
        fval = float(val)
        if fval != fval:
            raise ValueError
    except ValueError:
        col = RGB(200,200,200)
        return col.hex()
    if fval < 0.0:
        if fval < min_value:
            fval = -1.0
        else:
            fval = fval / min_value
        col = min_color
    else:
        if fval > max_value:
            fval = 1.0
        else:
            fval = fval/max_value
        col = max_color
    r = fval * float(col.r - zero_color.r) + zero_color.r
    g = fval * float(col.g - zero_color.g) + zero_color.g
    b = fval * float(col.b - zero_color.b) + zero_color.b
    try:
        color = RGB(r,g,b)
    except ValueError:
        color = RGB(200,200,200)
    return(color.hex())

def plotScale(image_file, min_value, max_value):
    image_size = (2, 4)
    fig = plt.figure(figsize=image_size, dpi=100, frameon=True, facecolor='w')
    for i in range(10):
        val = min_value+i*(max_value-min_value)/10
        col = getColorFromValue(val, min_value, max_value)
        X = [float(i)/10, float(i+1)/10, float(i+1)/ 10, float(i)/10, float(i)/10]
        Y = [1, 1, 0, 0, 1]
        fill(X, Y, col, lw = 1, ec = col)
    savefig(image_file)
    close()

def polar(r, value):
    theta = -2.0 * math.pi * value + math.pi/2.0
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return(x, y)

def plotCircle(image_file, image_label = '', center_color = RGB(255, 255, 255).hex(), circle_colors = [[RGB(200, 200, 200).hex()]], inner_radius_total = 0.2, outer_radius_total = 0.5, width = 5):
    ## image settings
    image_size = (width, width)
    fig = plt.figure(figsize = image_size, dpi = 100, frameon = True, facecolor = 'w')
    axes([0, 0, 1, 1], frameon=True, axisbg='w')
    axis('off')
    circle_width = (outer_radius_total-inner_radius_total)/float(len(circle_colors))
    
    ## color center
    outer_radius = inner_radius_total
    outer_radius -= .01
    X = []
    Y = []
    x, y = polar(outer_radius, 0)
    X.append(x)
    Y.append(y)
    ti = 0
    while ti < 1:
        x, y = polar(outer_radius, ti)
        X.append(x)
        Y.append(y)
        ti += tstep
        if ti > 1:
            break
    x, y = polar(outer_radius, 1)
    X.append(x)
    Y.append(y)
    fill(X, Y, center_color, lw = 1, ec = center_color)
    
    ## color rings
    for i in range(len(circle_colors)):
        inner_radius = (i*circle_width)+inner_radius_total
        outer_radius = ((i+1)*circle_width)+inner_radius_total-.01
        for j in range(len(circle_colors[i])):
            t0 = float(j)/len(circle_colors[i])
            t1 = float(j+1)/len(circle_colors[i])
            X = []
            Y = []
            x, y = polar(inner_radius, t0)
            X.append(x)
            Y.append(y)
            ti = t0
            while ti < t1:
                x, y = polar(outer_radius, ti)
                X.append(x)
                Y.append(y)
                ti += tstep
                if ti > t1:
                    break
            x, y = polar(outer_radius, t1)
            X.append(x)
            Y.append(y)
            ti = t1
            while ti > t0:
                x, y = polar(inner_radius, ti)
                X.append(x)
                Y.append(y)
                ti -= tstep
                if ti < t0:
                    break
            x, y = polar(inner_radius, t0)
            X.append(x)
            Y.append(y)
            fill(X, Y, circle_colors[i][j], lw = 1, ec = circle_colors[i][j])
    
    ## save image
    text(0, 0, image_label, ha = 'center', va = 'center')
    xlim(-0.5, 0.5)
    ylim(-0.5, 0.5)
    savefig(image_file)
    close()

def main(args):
    ## parse arguments
    parser = OptionParser(usage = '%prog [options] output_directory input_matrix [input_matrix ...]')
    parser.add_option('-s', '--samples', dest='sample_file', default=None)
    parser.add_option('-f', '--features', dest='feature_file', default=None)
    parser.add_option('-o', '--order', dest='order_parameters', default=None)
    parser.add_option('-c', '--center', dest='center_file', default=None)
    parser.add_option('-m', '--mapping', dest='color_map_file', default=None)
    parser.add_option('-e', '--extension', dest='file_extension', default='png')
    parser.add_option('-l', '--label', dest='print_label', action='store_true', default=False)
    options, args = parser.parse_args()
    
    assert(len(args) >= 2)
    output_directory = os.path.abspath(args[0])
    ring_files = args[1:]
    
    global image_format
    sample_file = options.sample_file
    feature_file = options.feature_file
    if options.order_parameters is not None:
        parts = options.order_parameters.split(';')
        if len(parts) == 1:
            order_feature = parts[0]
            order_files = []
        else:
            order_feature = parts[0]
            order_files = parts[1].split(',')
    else:
        order_feature = None
        order_files = []
    center_file = options.center_file
    if options.color_map_file is not None:
        color_map = parseColorMap(options.color_map_file)
    else:
        color_map = None
    print_label = options.print_label
    image_format = options.file_extension
    
    ## read sample and feature files
    samples = []
    features = []
    if sample_file is not None:
        samples = readList(sample_file)
    if feature_file is not None:
        features = readList(feature_file)
    
    ## read center file
    center_data = None
    if center_file is not None:
        center_data = pandas.read_csv(center_file, sep = '\t', index_col = 0).icol(0)
    
    ## read ring files
    circle_data = []
    for index in range(len(ring_files)):
        data = pandas.read_csv(ring_files[index], sep = '\t', index_col = 0)
        if sample_file is not None:
            data = data[sorted(list(set(data.columns) & set(samples)))]
        else:
            samples = list(set(data.columns) | set(samples))
        if feature_file is not None:
            data = data.loc[sorted(list(set(data.index) & set(features + ['*'])))]
        else:
            features = list(set(data.index) | set(features))
        circle_data.append(data)
    
    ## determine sample sort
    if order_feature is not None:
        if len(order_files) > 0:
            order_data = []
            for index in range(len(order_files)):
                data = pandas.read_csv(order_files[index], sep = '\t', index_col = 0)
                if sample_file is not None:
                    data = data[sorted(list(set(data.columns) & set(samples)))]
                if feature_file is not None:
                    data = data.loc[sorted(list(set(data.index) & set(features + ['*'])))]
                order_data.append(data)
        else:
            order_data = circle_data
        samples.sort(lambda x, y: scmp(x, y, order_feature, order_data))
    
    ## plot images
    for feature in features:
        log('Drawing %s\n' % (feature))
        image_name = re.sub('[/:]', '_', feature)
        if len(image_name) > 100:
            image_name = image_name[:100]
        image_file = '%s/%s.%s' % (output_directory, image_name, image_format)
        image_label = ''
        if print_label:
            image_label = feature
        center_color = RGB(255, 255, 255).hex()
        if center_data is not None:
            if feature in center_data:
                min_value = min([-0.01] + list(center_data[~np.isnan(center_data)].values))
                max_value = max([0.01] + list(center_data[~np.isnan(center_data)].values))
                center_color = getColorFromValue(center_data[feature], min_value, max_value)
                log('\t%s,%s,%s,%s\n' % (center_data[feature], min_value, max_value, center_color))
        circle_colors = []
        for index in range(len(circle_data)):
            ring_colors = []
            ring_index = (index + 1, index - len(circle_data))
            if feature in circle_data[index].index:
                ring_data = circle_data[index].loc[feature]
            elif '*' in circle_data[index].index:
                ring_data = circle_data[index].loc['*']
            else:
                ring_data = pandas.Series()
            min_value = min([-0.01] + list(ring_data[~np.isnan(ring_data)].values))
            max_value = max([0.01] + list(ring_data[~np.isnan(ring_data)].values))
            # min_value = min([-0.01] + list(circle_data[index].values[~np.isnan(circle_data[index].values)]))
            # max_value = max([0.01] + list(circle_data[index].values[~np.isnan(circle_data[index].values)]))
            for sample in samples:
                # first check if we have data
                if sample in ring_data:
                    # redirect to color map if it exists
                    if color_map is not None:
                        # check ring index
                        if ring_index[0] in color_map or ring_index[1] in color_map:
                            if ring_index[0] in color_map:
                                ring_map = color_map[ring_index[0]]
                            else:
                                ring_map = color_map[ring_index[1]]
                            # in the case of these keywords use standard function with alternate colors
                            if 'min_color' in ring_map or 'zero_color' in ring_map or 'max_color' in ring_map:
                                min_color = RGB(0, 0, 255)
                                zero_color = RGB(255, 255, 255)
                                max_color = RGB(255, 0, 0)
                                if 'min_color' in ring_map:
                                    min_color = RGB(ring_map['min_color'][0], ring_map['min_color'][1], ring_map['min_color'][2])
                                if 'zero_color' in ring_map:
                                    zero_color = RGB(ring_map['zero_color'][0], ring_map['zero_color'][1], ring_map['zero_color'][2])
                                if 'max_color' in ring_map:
                                    max_color = RGB(ring_map['max_color'][0], ring_map['max_color'][1], ring_map['max_color'][2])
                                ring_colors.append(getColorFromValue(ring_data[sample], min_value, max_value, min_color = min_color, zero_color = zero_color, max_color = max_color))
                            # use direct color mapping
                            else:
                                ring_colors.append(getColorFromMap(ring_data[sample], ring_map))
                        # default behavior
                        else:
                            ring_colors.append(getColorFromValue(ring_data[sample], min_value, max_value))
                    # default behavior
                    else:
                        ring_colors.append(getColorFromValue(ring_data[sample], min_value, max_value))
                # fill in missing data
                else:
                    ring_colors.append(RGB(200, 200, 200).hex())
            circle_colors.append(ring_colors)
        plotCircle(image_file, image_label = image_label, center_color = center_color, circle_colors = circle_colors, inner_radius_total = 0.2, outer_radius_total = 0.5, width = 5)

if __name__ == "__main__":
    main(sys.argv[1:])
