#!/usr/bin/env python

from xml.dom.minidom import Document
import xml.sax
import sys


class SimpleGraph:
	def __init__(self):
		self.node = {}
		self.edge = {}

	def add_node(self, node):
		self.node[node] = {}
		self.edge[node] = {}

	def add_edge(self, src, target):
		if target not in self.node:
			self.add_node(target)
		if target not in self.edge[src]:
			self.edge[src][target] = {}
		self.edge[src][target][len(self.edge[src][target])] = {}



class GraphComp:
    def __init__(self, parser, attrs):
        self.graph = SimpleGraph()

    def add_att(self, name, value):
        self.graph.graph[name] =  value

    def pop(self):
        return self.graph

class NodeComp:
    def __init__(self, parser, parent, attrs):
        self.label = attrs.getValue('label')
        self.parser = parser
        self.parent = parent
        parser.id_map[attrs.getValue('id')] = self.label
        parent.graph.add_node( self.label )

    def add_att(self, name, value):
        self.parent.graph.node[self.label][name] =  value

    def pop(self):
        pass


class EdgeComp:
    def __init__(self, parser, parent, attrs):
        self.parent = parent
        self.src = parser.id_map[attrs.getValue('source')]
        self.target = parser.id_map[attrs.getValue('target')]
        self.key = 0
        if self.target in parent.graph.edge[self.src]:
            self.key=len(parent.graph.edge[self.src][self.target])
        parent.graph.add_edge(self.src,self.target)

    def add_att(self, name, value):
        self.parent.graph.edge[self.src][self.target][self.key][name] =  value

    def pop(self):
        pass


class AttComp:
    def __init__(self, parser, parent, attrs):
        self.parent = parent
        self.name = attrs.getValue('name')
        if attrs.has_key('value'):
            parent.add_att(attrs.getValue('name'), attrs.getValue('value'))
        self.att_list = None
        if attrs.has_key('type') and attrs.getValue("type") == "list":
            self.att_list = []

    def add_att(self, name, value):
        self.att_list.append( value )

    def pop(self):
        if self.att_list is not None:
            self.parent.add_att(self.name, self.att_list)


class XGMMLHandler(xml.sax.ContentHandler):
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.elem_stack = []
        self.id_map = {}
        self.last_value = None

    def startElement(self, name, attrs):
        #print("startElement '" + name + "'")
        if name == "graph":
            self.elem_stack.append(GraphComp(self, attrs))
        elif name == 'node':
            self.elem_stack.append(NodeComp(self, self.elem_stack[-1], attrs))
        elif name == 'edge':
            self.elem_stack.append(EdgeComp(self, self.elem_stack[-1], attrs))
        elif name == 'att':
            self.elem_stack.append(AttComp(self, self.elem_stack[-1], attrs))
        else:
            self.elem_stack.append(None)
            
 
    def endElement(self, name):
        last_node = self.elem_stack.pop()
        if last_node is not None:
            self.last_value = last_node.pop()

    def result(self):
        return self.last_value

def read_xgmml(handle):
    handler = XGMMLHandler()
    xml.sax.parse(handle, handler)
    return handler.result()

def write_paradigm_graph(gr, handle, node_type_field='type', node_type_default='protein', edge_type_field='interaction', edge_type_default='-a>'):
    for e in sorted(gr.node):
        handle.write("%s\t%s\n" % (gr.node[e].get(node_type_field, node_type_default), e))

    for src in gr.edge:
        for dst in gr.edge[src]:
            for edge in gr.edge[src][dst]:
                handle.write("%s\t%s\t%s\n" % (src, dst, gr.edge[src][dst][edge].get(edge_type_field, edge_type_default)))


def main(src, dst):
	ihandle = open(src)
	gr = read_xgmml(ihandle)
	ihandle.close()

	ohandle = open(dst, "w")
	write_paradigm_graph(gr, ohandle)
	ohandle.close()

if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])



