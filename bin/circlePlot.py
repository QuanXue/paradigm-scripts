#!/usr/bin/env python
"""
circlePlot.py
    by Sam Ng, Steve Benz, Zack Sanborn, and Evan Paull
"""
import math, os, sys, re

import numpy as np
import pandas
from matplotlib import *
use("Agg")
from pylab import *

from optparse import OptionParser

color_parameters = ["min_color", "zero_color", "max_color", "min_value", "max_value", "boundary_method"]
tstep = 0.01
image_format = "png"

class RGB:
    """
    Describes a color stored in RGB scale [CirclePlot specific]
    """
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
        hex_characters = "0123456789ABCDEF"
        return("#" + hex_characters[self.r / 16] + hex_characters[self.r % 16]
                   + hex_characters[self.g / 16] + hex_characters[self.g % 16]
                   + hex_characters[self.b / 16] + hex_characters[self.b % 16])

def logger(message, log_file = None, die = False):
    """
    Writes messages to either stderr or file [2014-11-7]
    """
    if log_file is None:
        sys.stderr.write(message)
    else:
        o = open(log_file, "a")
        o.write(message)
        o.close()
    if die:
        sys.exit(1)

def readList(input_file):
    """
    Reads a simple one column list [2014-11-7]
    """
    input_list = []
    f = open(input_file, "r")
    input_list = [line.rstrip() for line in f]
    f.close()
    return(input_list)

def parseColorMap(input_file):
    """
    Reads a color map that describes plot settings for each ring [CirclePlot specific]
    """
    ## initialize the color mapping, valid attributes are min_color, zero_color,
    ## max_color, min_value, max_value, and boundary_method *or* direct mappings from value to color
    color_map = {}
    ring_index = None
    f = open(input_file, "r")
    for line in f:
        ## set the ring index, an index of 0 refers to the center circle, 1 is the first
        ## ring, and -1 is the last ring
        if line.startswith(">"):
            ring_index = int(line.lstrip(">"))
        ## assign attributes to rings
        else:
            if ring_index is None:
                raise Exception("unspecified ring for attribute")
            if ring_index not in color_map:
                color_map[ring_index] = {}
            parts = line.rstrip().split("\t")
            color_map[ring_index][parts[0]] = parts[1]
    f.close()
    return(color_map)

def scmp(a, b, feature, ring_list):
    """
    Recursive cmp function for hierarchical sorting [CirclePlot specific]
    """
    ## handle cases in which a sample is not in the sorting dataset
    if (a not in ring_list[0].columns) and (b in ring_list[0].columns):
        return(1)
    elif (a in ring_list[0].columns) and (b not in ring_list[0].columns):
        return(-1)
    elif (a not in ring_list[0].columns) and (b not in ring_list[0].columns):
        if len(ring_list) == 1:
            return(0)
        else:
            return(scmp(a, b, feature, ring_list[1:]))
    ## handle cases in which the feature is not in the sorting dataset, use * if possible
    ring_feature = feature
    if ring_feature not in ring_list[0].index:
        if "*" in ring_list[0].index:
            ring_feature = "*"
        else:
            if len(ring_list) == 1:
                return(0)
            else:
                return(scmp(a, b, feature, ring_list[1:]))
    
    value = cmp(ring_list[0][a][ring_feature], ring_list[0][b][ring_feature])
    if value == 0:
        if len(ring_list) == 1:
            return(0)
        else:
            return(scmp(a, b, feature, ring_list[1:]))
    else:
        return(value)

def getColorFromMap(key, color_map):
    """
    Returns a color based on color map [CirclePlot specific]
    """
    if key not in color_map:
        raise Exception("key not assigned in color map")
    try:
        (r, g, b) = color_map[key].split(".")
    except KeyError:
        raise Exception("key not assigned in color map")
    except ValueError:
        raise Exception("mapped value not a valid color")
    return(RGB(int(r), int(g), int(b)).hex())

def getColorFromValue(value, min_value, max_value, min_color = RGB(0, 0, 255), zero_color = RGB(255, 255, 255), max_color = RGB(255, 0, 0)):
    """
    Returns a color scaled between min, zero, and max color [CirclePlot specific]
    """
    ## try to convert the value to a float, otherwise return gray
    try:
        fvalue = float(value)
        if fvalue != fvalue:
            raise ValueError
    except ValueError:
        return(RGB(200, 200, 200).hex())
    ## scale value between -1 and 1, linearly
    svalue = 0.0
    if fvalue < 0.0:
        if fvalue < min_value:
            svalue = 1.0
        else:
            svalue = fvalue / min_value
        base_color = min_color
    else:
        if fvalue > max_value:
            svalue = 1.0
        else:
            svalue = fvalue / max_value
        base_color = max_color
    ## compute rgb
    r = svalue * float(base_color.r - zero_color.r) + zero_color.r
    g = svalue * float(base_color.g - zero_color.g) + zero_color.g
    b = svalue * float(base_color.b - zero_color.b) + zero_color.b
    return(RGB(r, g, b).hex())

def polar(r, value):
    """
    Returns Euclidean coordinates from polar coordinates [CirclePlot specific]
    """
    theta = -2.0 * math.pi * value + math.pi / 2.0
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return(x, y)

def plotCircle(image_file, image_label = "", center_color = RGB(255, 255, 255).hex(), ring_colors = [[RGB(200, 200, 200).hex()]], border_color = RGB(0, 0, 0).hex(), inner_radius_total = 0.2, outer_radius_total = 0.5, width = 5):
    """
    Generates the circle image by building each ring from a list of colors [CirclePlot specific]
    """
    ## set image settings
    image_size = (width, width)
    fig = plt.figure(figsize = image_size, dpi = 100, frameon = True, facecolor = "w")
    axes([0, 0, 1, 1], frameon = True, axisbg = "w")
    axis("off")
    ring_width = (outer_radius_total - inner_radius_total) / float(len(ring_colors))
    
    ## color center
    outer_radius = inner_radius_total
    outer_radius -= .01
    x_list = []
    y_list = []
    x, y = polar(outer_radius, 0)
    x_list.append(x)
    y_list.append(y)
    ti = 0
    while ti < 1:
        x, y = polar(outer_radius, ti)
        x_list.append(x)
        y_list.append(y)
        ti += tstep
        if ti > 1:
            break
    x, y = polar(outer_radius, 1)
    x_list.append(x)
    y_list.append(y)
    fill(x_list, y_list, center_color, lw = 1, ec = center_color)
    
    ## color rings
    for ring_index in range(len(ring_colors)):
        inner_radius = (ring_index * ring_width) + inner_radius_total
        outer_radius = ((ring_index + 1) * ring_width) + inner_radius_total-.01
        for spoke_index in range(len(ring_colors[ring_index])):
            t0 = float(spoke_index) / len(ring_colors[ring_index])
            t1 = float(spoke_index + 1) / len(ring_colors[ring_index])
            x_list = []
            y_list = []
            x, y = polar(inner_radius, t0)
            x_list.append(x)
            y_list.append(y)
            ti = t0
            while ti < t1:
                x, y = polar(outer_radius, ti)
                x_list.append(x)
                y_list.append(y)
                ti += tstep
                if ti > t1:
                    break
            x, y = polar(outer_radius, t1)
            x_list.append(x)
            y_list.append(y)
            ti = t1
            while ti > t0:
                x, y = polar(inner_radius, ti)
                x_list.append(x)
                y_list.append(y)
                ti -= tstep
                if ti < t0:
                    break
            x, y = polar(inner_radius, t0)
            x_list.append(x)
            y_list.append(y)
            fill(x_list, y_list, ring_colors[ring_index][spoke_index], lw = 1, ec = ring_colors[ring_index][spoke_index])
    
    ## color ring borders
    if border_color != RGB(255, 255, 255).hex():
        for ring_index in range(len(ring_colors) + 1):
            ## do not draw a border if previous and next ring are empty, else plot
            inner_ring_empty = False
            outer_ring_empty = False
            if ring_index == 0:
                inner_ring_empty = True
            elif len(ring_colors[ring_index - 1]) == 0:
                inner_ring_empty = True
            else:
                inner_ring_empty = False
            if ring_index == len(ring_colors):
                outer_ring_empty = True
            elif len(ring_colors[ring_index]) == 0:
                outer_ring_empty = True
            else:
                outer_ring_empty = False
            if inner_ring_empty and outer_ring_empty:
                continue
            inner_radius = (ring_index * ring_width) + inner_radius_total - .01 + 0.0025
            outer_radius = (ring_index * ring_width) + inner_radius_total - 0.0025
            t0 = 0.0
            t1 = 1.0
            x_list = []
            y_list = []
            x, y = polar(inner_radius, t0)
            x_list.append(x)
            y_list.append(y)
            ti = t0
            while ti < t1:
                x, y = polar(outer_radius, ti)
                x_list.append(x)
                y_list.append(y)
                ti += tstep
                if ti > t1:
                    break
            x, y = polar(outer_radius, t1)
            x_list.append(x)
            y_list.append(y)
            ti = t1
            while ti > t0:
                x, y = polar(inner_radius, ti)
                x_list.append(x)
                y_list.append(y)
                ti -= tstep
                if ti < t0:
                    break
            x, y = polar(inner_radius, t0)
            x_list.append(x)
            y_list.append(y)
            fill(x_list, y_list, border_color, lw = 1, ec = border_color)

    ## save image
    text(0, 0, image_label, ha = "center", va = "center")
    xlim(-0.5, 0.5)
    ylim(-0.5, 0.5)
    savefig(image_file)
    close()

def main(args):
    ## parse arguments
    parser = OptionParser(usage = "%prog [options] output_directory input_matrix [input_matrix ...]")
    parser.add_option("-s", "--samples", dest = "sample_file", default = None,
                      help = "")
    parser.add_option("-f", "--features", dest = "feature_file", default = None,
                      help = "")
    parser.add_option("-o", "--order", dest = "order_parameters", default = None,
                      help = "")
    parser.add_option("-c", "--center", dest = "center_file", default = None,
                      help = "")
    parser.add_option("-m", "--mapping", dest = "color_map_file", default = None,
                      help = "")
    parser.add_option("-e", "--extension", dest = "file_extension", default = "png",
                      help = "")
    parser.add_option("-l", "--label", dest = "print_label", action = "store_true", default = False,
                      help = "")
    options, args = parser.parse_args()
    
    assert(len(args) >= 2)
    output_directory = os.path.abspath(args[0])
    ring_files = args[1:]
    
    global image_format
    sample_file = options.sample_file
    feature_file = options.feature_file
    if options.order_parameters is not None:
        parts = options.order_parameters.split(";")
        if len(parts) == 1:
            order_feature = parts[0]
            order_files = []
        else:
            order_feature = parts[0]
            order_files = parts[1].split(",")
    else:
        order_feature = None
        order_files = []
    center_file = options.center_file
    if options.color_map_file is not None:
        color_map = parseColorMap(options.color_map_file)
    else:
        color_map = {}
    image_format = options.file_extension
    print_label = options.print_label
    
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
        center_data = pandas.read_csv(center_file, sep = "\t", index_col = 0).icol(0)
    
    ## read circle files
    ring_data = []
    for index in range(len(ring_files)):
        data = pandas.read_csv(ring_files[index], sep = "\t", index_col = 0)
        if sample_file is not None:
            data = data[sorted(list(set(data.columns) & set(samples)))]
        else:
            samples = list(set(data.columns) | set(samples))
        if feature_file is not None:
            pass
        else:
            features = list(set(data.index) | set(features))
        ring_data.append(data)
    
    ## determine sample sort
    if order_feature is not None:
        if len(order_files) > 0:
            order_data = []
            for index in range(len(order_files)):
                data = pandas.read_csv(order_files[index], sep = "\t", index_col = 0)
                if sample_file is not None:
                    data = data[sorted(list(set(data.columns) & set(samples)))]
                if feature_file is not None:
                    data = data.loc[sorted(list(set(data.index) & set(features + ["*"])))]
                order_data.append(data)
        else:
            order_data = ring_data
        samples.sort(lambda x, y: scmp(x, y, order_feature, order_data))
    
    ## determine color parameters
    if center_data is not None:
        ring_index = 0
        if ring_index not in color_map:
            color_map[ring_index] = {}
        if len(filter(lambda x: x not in color_parameters, color_map[ring_index].keys())) == 0:
            if "min_value" not in color_map[ring_index] or "max_value" not in color_map[ring_index]:
                if "boundary_method" not in color_map[ring_index]:
                    color_map[ring_index]["boundary_method"] = "global"
                if color_map[ring_index]["boundary_method"] == "global":
                    ring_values = np.asarray(center_data.values)
                    ring_values = list(ring_values[~np.isnan(ring_values)])
                    if "min_value" not in color_map[ring_index]:
                        color_map[ring_index]["min_value"] = min([0.0] + ring_values)
                    if "max_value" not in color_map[ring_index]:
                        color_map[ring_index]["max_value"] = max([0.0] + ring_values)
                elif color_map[ring_index]["boundary_method"] == "selected":
                    ring_values = center_data[features].values
                    ring_values = list(ring_values[ring_values != "nan"])
                    if "min_value" not in color_map[ring_index]:
                        color_map[ring_index]["min_value"] = min([0.0] + ring_values)
                    if "max_value" not in color_map[ring_index]:
                        color_map[ring_index]["max_value"] = max([0.0] + ring_values)
                else:
                    raise Exception("boundary method for center is not valid")
    for index in range(len(ring_data)):
        try:
            ring_index = filter(lambda x: x in color_map, [index + 1, index - len(ring_data)])[0]
        except IndexError:
            ring_index = index + 1
            color_map[ring_index] = {}
        if len(filter(lambda x: x not in color_parameters, color_map[ring_index].keys())) == 0:
            if "min_value" not in color_map[ring_index] or "max_value" not in color_map[ring_index]:
                if "boundary_method" not in color_map[ring_index]:
                    color_map[ring_index]["boundary_method"] = "single"
                if color_map[ring_index]["boundary_method"] == "global":
                    ring_values = np.asarray([value for row in ring_data[index].values for value in row])
                    ring_values = list(ring_values[~np.isnan(ring_values)])
                    if "min_value" not in color_map[ring_index]:
                        color_map[ring_index]["min_value"] = min([0.0] + ring_values)
                    if "max_value" not in color_map[ring_index]:
                        color_map[ring_index]["max_value"] = max([0.0] + ring_values)
                elif color_map[ring_index]["boundary_method"] == "selected":
                    ring_values = np.asarray([value for row in ring_data[index].loc[sorted(list(set(ring_data[index].index) & set(features + ["*"])))].values for value in row])
                    ring_values = list(ring_values[~np.isnan(ring_values)])
                    if "min_value" not in color_map[ring_index]:
                        color_map[ring_index]["min_value"] = min([0.0] + ring_values)
                    if "max_value" not in color_map[ring_index]:
                        color_map[ring_index]["max_value"] = max([0.0] + ring_values)
                elif color_map[ring_index]["boundary_method"] == "single":
                    color_map[ring_index]["min_value"] = {}
                    color_map[ring_index]["max_value"] = {}
                    for feature in features + ["*"]:
                        if feature not in ring_data[index].index:
                            color_map[ring_index]["min_value"][feature] = 0.0
                            color_map[ring_index]["max_value"][feature] = 0.0
                        else:
                            ring_values = np.asarray([value for row in ring_data[index].loc[[feature]].values for value in row])
                            ring_values = list(ring_values[~np.isnan(ring_values)])
                            color_map[ring_index]["min_value"][feature] = min([0.0] + ring_values)
                            color_map[ring_index]["max_value"][feature] = max([0.0] + ring_values)
                else:
                    raise Exception("boundary method for ring is not valid")
    
    ## plot images
    for feature in features:
        ## set name and label
        logger("Drawing %s\n" % (feature))
        image_name = re.sub("[/:]", "_", feature)
        if len(image_name) > 100:
            image_name = image_name[:100]
        image_file = "%s/%s.%s" % (output_directory, image_name, image_format)
        image_label = ""
        if print_label:
            image_label = feature
        ## set center color
        if center_data is not None:
            ring_index = 0
            if feature in center_data:
                if "min_value" in color_map[ring_index] and "max_value" in color_map[ring_index]:
                    min_value = color_map[ring_index]["min_value"]
                    max_value = color_map[ring_index]["max_value"]
                    center_color = getColorFromValue(center_data[feature], min_value, max_value)
                else:
                    center_color = getColorFromMap(str(center_data[feature]), color_map[ring_index])
            else:
                center_color = RGB(200, 200, 200).hex()
        else:
            center_color = RGB(255, 255, 255).hex()
        ## set ring colors
        ring_colors = []
        for index in range(len(ring_data)):
            current_ring = []
            if feature in ring_data[index].index:
                ring_feature = feature
            elif "*" in ring_data[index].index:
                ring_feature = "*"
            else:
                ring_feature = None
            ring_index = filter(lambda x: x in color_map.keys(), [index + 1, index - len(ring_data)])[0]
            ## first check if this ring is to be skipped
            if "skip_ring" in color_map[ring_index]:
                ring_colors.append(current_ring)
                continue
            for sample in samples:
                try:
                    if "min_value" in color_map[ring_index] and "max_value" in color_map[ring_index]:
                        if ring_feature in color_map[ring_index]["min_value"]:
                            min_value = color_map[ring_index]["min_value"][ring_feature]
                        else:
                            min_value = color_map[ring_index]["min_value"]
                        if ring_feature in color_map[ring_index]["max_value"]:
                            max_value = color_map[ring_index]["max_value"][ring_feature]
                        else:
                            max_value = color_map[ring_index]["max_value"]
                        min_color = RGB(0, 0, 255)
                        zero_color = RGB(255, 255, 255)
                        max_color = RGB(255, 0, 0)
                        if "min_color" in color_map[ring_index]:
                            min_color = RGB(color_map[ring_index]["min_color"][0], color_map[ring_index]["min_color"][1], color_map[ring_index]["min_color"][2])
                        if "zero_color" in color_map[ring_index]:
                            zero_color = RGB(color_map[ring_index]["zero_color"][0], color_map[ring_index]["zero_color"][1], color_map[ring_index]["zero_color"][2])
                        if "max_color" in color_map[ring_index]:
                            max_color = RGB(color_map[ring_index]["max_color"][0], color_map[ring_index]["max_color"][1], color_map[ring_index]["max_color"][2])
                        current_ring.append(getColorFromValue(ring_data[index][sample].loc[ring_feature], min_value, max_value, min_color = min_color, zero_color = zero_color, max_color = max_color))
                    else:
                        current_ring.append(getColorFromMap(str(ring_data[index][sample].loc[ring_feature]), color_map[ring_index]))
                except:
                    current_ring.append(RGB(200, 200, 200).hex())
            ring_colors.append(current_ring)
        ## plot
        plotCircle(image_file, image_label = image_label, center_color = center_color, ring_colors = ring_colors, inner_radius_total = 0.2, outer_radius_total = 0.5, width = 5, border_color = RGB(0, 0, 0).hex())

if __name__ == "__main__":
    main(sys.argv[1:])
