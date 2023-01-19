# AUTOGENERATED! DO NOT EDIT! File to edit: ../02_tree.ipynb.

# %% auto 0
__all__ = ['AmbigouosTreeEdge', 'AmbigouosRootNode', 'TremauxTree']

# %% ../02_tree.ipynb 4
import numpy as np
from copy import deepcopy

import pdb

import networkx as nx
from networkx.algorithms.operators.binary import compose
from networkx import NetworkXNoPath,NetworkXNoCycle

from pangraph_constructor.utils import bidict

# %% ../02_tree.ipynb 6
class AmbigouosTreeEdge(nx.AmbiguousSolution):
    """Raised if special edge in Tremaux tree cannot be identified as loop or bubble.
    """
    
class AmbigouosRootNode(nx.AmbiguousSolution):
    """Raised if more than 1 root node is found in a tree.
    """

# %% ../02_tree.ipynb 7
class TremauxTree(nx.DiGraph):
    def __init__(self,graphToTree=None,parentGraph=None,byPath=True,**attr):
        if graphToTree is None:
            super().__init__(**attr)
        else:
            self.originalGraph = graphToTree
            self.parentGraph = parentGraph
            self.startingNodes = None
            
            treeCombined = self._generateTree(byPath)
            
            super().__init__(treeCombined,**attr)
            
            self.loopEdges = bidict()
            self.bubbleEdges = bidict()

            addEdges = self._getMissingEdges()

            self.processSpecialEdges(addEdges)
            
            for root in self.startingNodes.copy():
                incomingBubbles = self.bubbleEdges.inverse.get(root,[])
                incomingBubbles = [node for node in incomingBubbles if len(self.edges(node))==0]
                if len(incomingBubbles)>0:
                    incomingBubbles.sort(key=lambda node: self.parentGraph.edgePathsUnique.get((node,root),0))
                    upNode = incomingBubbles[-1]
                    self.add_edge(upNode,root)
                    self.bubbleEdges.remove(upNode,root)
                    self.startingNodes.remove(root)
    # unused?
    def _getNodeStartFit(self):
        nodeStartTest = []
        for node in range(1,len(self.parentGraph.nodes)+1):
            nodeStartTest.append(self.parentGraph.pathStarts[node-1] - \
                                 max([pathN for edge,pathN in self.parentGraph.edgePaths.items() if edge[1]==node],default=0))
        return nodeStartTest
            
    def _generateTree(self,byPath=True):
#         if byPath:
#             inEdge = self.parentGraph.inPath
#             outEdge = self.parentGraph.outPath
#             nodeStartPath = self._getNodeStartFit()
#             startingNodes = np.where(nodeStartPath==np.max(nodeStartPath))[0]+1
#         else:
#             inEdge = self.originalGraph.in_degree
#             outEdge = self.originalGraph.out_degree
#             startingNodes = np.arange(1,len(inEdge)+1)
        
#         selectedOutPaths = np.array(outEdge)[startingNodes-1]    
#         self.startingNodes = startingNodes[np.where(selectedOutPaths==np.max(selectedOutPaths))]
#         selectedInPaths = np.array(inEdge)[startingNodes-1]
#         self.startingNodes = startingNodes[np.where(selectedInPaths==np.min(selectedInPaths))].tolist()
#         self.startingNodes = set(self.startingNodes)
#         self.startingNodes.update((np.where(np.array(inEdge)==0)[0]+1).tolist())
#         self.startingNodes = list(self.startingNodes)
# #         self.startingNodes.sort(key=[self.parentGraph.pathStarts[node] for node in self.startingNodes])
        
        tremauxTree = nx.dfs_tree(self.originalGraph)
        
        self.startingNodes = []
        
        
            
#         if len(self.startingNodes)>0:
#             treeCombined = nx.DiGraph()
#             for startNode in self.startingNodes:
#                 if startNode not in treeCombined:
#                     treeCombined = compose(treeCombined,nx.dfs_tree(self.originalGraph,source=startNode))
            
        if byPath:
#                 preprocessIter = 1
            self._preprocessPathTree(tremauxTree)
#                 try:
#                     nx.find_cycle(treeCombined,orientation='original')
#                     raise RuntimeError(f'Found cycle in tree after preprocessing')
#                 except NetworkXNoCycle:
#                     pass

#                 accessibleNodes = set()
#                 for rootNode in self.startingNodes:
#                     accessibleNodes = accessibleNodes.update(list(nx.dfs_preorder_nodes(treeCombined,source=rootNode)))

#                 assert len(accessibleNodes)==len(self.parentGraph.nodes)

#                 incorrectEdges = [(node,len(treeCombined.in_edges(node))) \
#                                   for node in accessibleNodes \
#                                   if len(treeCombined.in_edges(node))>1]
#                 if len(incorrectEdges)>0:
#                     print(f'Nodes with more than 1 in edges: {incorrectEdges}')
#                 assert len(incorrectEdges)==0

#                 print(f'Preprocessing run {preprocessIter:02d}')
#                 while True:
#                     try:
#                         nx.find_cycle(treeCombined,orientation='original')
#                     except NetworkXNoCycle:
#                         break
#                     preprocessIter += 1
#                     self._preprocessPathTree(treeCombined)
#                     print(f'Preprocessing run {preprocessIter:02d}')
        else:
            for toNode,numDeg in tremauxTree.in_degree:
                if numDeg>1:
                    for fromNode,_ in list(tremauxTree.in_edges(nbunch=toNode))[1:]:
                        tremauxTree.remove_edge(edge,toNode)
#         else:
#             raise ValueError("Something went wrong. I cannot find a single suitable starting node. It seems there is no nodes in the graph.")
        
        for treeNum,tree in enumerate(nx.weakly_connected_components(tremauxTree)):
            subgraphNode = next(iter(tree))
            while True:
                treeInEdges = list(tremauxTree.in_edges(subgraphNode))
                if len(treeInEdges)>0:
                    subgraphNode = treeInEdges[0][0]
                else:
                    break
            self.startingNodes.append(subgraphNode)
                
        self.startingNodes.sort(key=lambda node: self.parentGraph._getEdgeValue(None,node))
        
        return tremauxTree
    
    # unused
    def _preprocessPathTree(self,treeCombined):
        processedNodes = []
        
        dfsNodeOrder = list(nx.dfs_preorder_nodes(treeCombined))
        
        for nodeNum,node in enumerate(dfsNodeOrder):
#             if node==4006:
#                 pdb.set_trace()
            
            print(f'\rPreprocessing tree {(nodeNum+1)/len(dfsNodeOrder)*100:0.0f}%',end='')
    
            processedNodes.append(node)

            # get all edges coming to given node in the full graph
            graphInEdgeList = list(self.originalGraph.in_edges(node))
            # get all edges coming to a given node in the tremaux tree
            try:
                # treeInEdgeList can be either 1 edge or zero (in the tree only one incoming edge is allowed)
                treeInEdgeList = list(treeCombined.in_edges(node))
            except nx.NetworkXError:
                # treeInEdgeList = []
                warnings.warn(f"Node {node} in the Tremaux tree does not have any incoming edges. \
                Only root node(s) are allowed to have no incoming edges. If it is not an intended root node,\
                then it is an error and you have inaccessible nodes in the tree (which will fail sorting later).")
                continue
            
#             if len(treeInEdgeList)>1:
#                 raise RuntimeError(f"The node {node} in the Tremaux tree have more than one incoming edge,\
#                 which is contradictory to the definition of the Tremaux tree. Something went wrong!")
            
            # Because there can be only one (or none) incoming edge to every node in Tremaux tree, we extract it.
#             treeInEdge = treeInEdgeList[0]
            # And calculate its value (number of paths passing through this edge)
#             treeInEdgeValue = self.parentGraph.edgePathsUnique.get(treeInEdge,0)
            
            # Remove self-cycle or reverse (cycle making) paths larger cycles will be removed later.
            graphInEdgeList = [edge for edge in graphInEdgeList if edge[0]!=node]
            
            graphInEdgeValueList = [self.parentGraph._getEdgeValue(*edge) \
                                    for edge in graphInEdgeList]
            
            graphInEdgeValueSortIndex = np.flip(np.argsort(graphInEdgeValueList))
            
            for edgeToKeepInd in graphInEdgeValueSortIndex:
                # Find the edge with maximum number of paths passing
                edgeToKeep = graphInEdgeList[edgeToKeepInd]
                
                if edgeToKeep[0]==edgeToKeep[1]:
                    raise RuntimeError(f'Self loop on node {edge[0]} is suggested for substitution.')
                
                edgeToKeepValue = graphInEdgeValueList[edgeToKeepInd]
                if nx.has_path(treeCombined,edgeToKeep[1],edgeToKeep[0]):
#                     print(f'Node: {node}')
#                     print(f'Graph edges: {graphInEdgeList}')
#                     print(f'Tree edge: {treeInEdgeList}')
#                     print(f'Edge to keep: {edgeToKeep}')

#                     print('Cycle found!')
                    # Get all posible cycle path:
                    edgesToRemove = []
                    edgesToAdd = []
                    breakSubstitute = False

                    for path in nx.all_shortest_paths(treeCombined,edgeToKeep[1],edgeToKeep[0]):
#                         print(f'Path to break: {path}')
                        if len(path)==2 and list(edgeToKeep[::-1])==path:
                            if path[1] not in processedNodes:
                                edgesToRemove.append(path)
                            else:
                                breakSubstitute = True
                                break
                        else:
                            pathBreakpoint = self._severePathPoint(treeCombined,path,edgeToKeepValue,processedNodes)
                            if pathBreakpoint is not None:
                                edgesToRemove.append(pathBreakpoint[0])
                                edgesToAdd.append(pathBreakpoint[1])
                            else:
#                                 print('Unbreakable path!')
                                breakSubstitute = True
                                break

                    if not breakSubstitute:
#                         print('Edge substituted!')
                        self._substituteEdges(treeCombined,[edgeToKeep],treeInEdgeList)
#                             for edgeToRemove,edgeToAdd in zip(edgesToRemove,edgesToAdd):
#                         print(f'Edges {edgesToAdd} added instead of {edgesToRemove}')
                        self._substituteEdges(treeCombined,edgesToAdd,edgesToRemove)
                        break
                    else:
                        continue
                else:
                    self._substituteEdges(treeCombined,[edgeToKeep],treeInEdgeList)
                    break
        print()
    #unused
    def _severePathPoint(self,G,path,newEdgeValue,processedNodes):
        '''
            Heuristics for finding the best position in the path to severe (and substitute).
            It will find the lowest value possible edge in the path and find the highest possible value of alternative.
            
            If there is no alternative, it will return None
        '''

#         if path==[3869, 3867]:
#             pdb.set_trace()

        # get number of paths passing (value) each edge in the path
        pathValues = [self.parentGraph._getEdgeValue(path[i-1],path[i]) for i in range(1,len(path))]
        # sort the values of the path
        pathValIndSort = np.argsort(pathValues)
        
        res = None
        
        # For each edge in path starting from the least valuable, we check the most valuable substitution and check that it is still does not 
        edgeToSubstitute = None
        edgeToSubValue = None
        for pathPos in pathValIndSort:
            if pathValues[pathPos]>newEdgeValue:
                # If we get to the edge that has a value higher than the edge that we try to preserve, 
                # then this substitute does not make any sense.
                return res
            
            # Start and end of current edge in the path
            curStart = path[pathPos]
            curEnd = path[pathPos+1]
            
            if curEnd in processedNodes:
                # We cannot remove edges ending in the nodes that were already processed. 
                # Otherwise we can break something that we already established.
                continue
            
            edgeRemoved = False
            # Combine tuple of current edge
            curEdge = (curStart,curEnd)
            if not G.has_edge(*curEdge):
                edgeRemoved = True
                break
            # Calculate value of current edge in the path
            curEdgeValue = pathValues[pathPos]
            
            # If it is higher than new substitution, then disregard it, severing it will make our consensus tree worse.
#             if curEdgeValue>newEdgeValue:
#                 continue
            
            # Get all incoming edges to the end of the current edge (alternative edges)
            allIncomingEdges = list(self.originalGraph.in_edges(curEnd))
            
            # If there is only one incoming edge, do not substitute it.
            if len(allIncomingEdges)<2:
                continue
            
            # Calc values of all incoming edges to the end of edge
            incomingEdgesValue = [self.parentGraph._getEdgeValue(*edge) for edge in allIncomingEdges]
            # Get the sorting order (decreasing) of incoming edges
            edgeSortInd = np.flip(np.argsort(incomingEdgesValue))
            
            if not edgeRemoved:
                G.remove_edge(*curEdge)
            
            for edgeInd in edgeSortInd:
                altEdge = allIncomingEdges[edgeInd]
                altEdgeValue = incomingEdgesValue[edgeInd]
                # We consider only substitutions
                if altEdge[0]==altEdge[1]:
                    continue
                    
                if altEdge == curEdge:
#                     if curEdgeValue>newEdgeValue:
#                         break
#                     else:
                    continue
                
#                 if altEdge[0] == 6861:
#                     pdb.set_trace()
                if altEdge[1] in processedNodes:
                    continue
                
                # Add alt edge temporarily!
                # if the alternative still manifest loop, disregard this option
                if (nx.has_path(G,path[0],altEdge[0]) \
                    and nx.has_path(G,altEdge[-1],path[-1])) \
                    or (nx.has_path(G,*altEdge[::-1])):
#                     G.add_edge(*curEdge)
                    continue
                
                edgeToSubstitute = altEdge
                edgeToSubValue = altEdgeValue
                break
            
            if edgeToSubstitute is not None:
                res = [curEdge,edgeToSubstitute,edgeToSubValue]
                break
            elif not edgeRemoved:
                G.add_edge(*curEdge)
                    
        return res
    
    def _substituteEdges(self,G,edgesToAddList,edgesToRemoveList):
        # Remove current incoming edge in the tree
        if len(edgesToRemoveList)>0:
            G.remove_edges_from(edgesToRemoveList)
        # and replace it with newly identified best edge
        if len(edgesToAddList)>0:
            G.add_edges_from(edgesToAddList)
    
    def _getMissingEdges(self):
        graphEdges = set(list(self.originalGraph.edges))
        treeEdges = set(list(self.edges))
        return list((graphEdges - treeEdges))

    def processSpecialEdges(self,missingLinks):
        combinedGraph = nx.DiGraph(self)
        processedEdges = []
        for fromNode,toNode in missingLinks:
            edgeStatus = self.isBubbleLoop(fromNode,toNode,combinedGraph)
            if edgeStatus == -1:
#                 try:
#                     if self.parentGraph.edgePaths[(toNode,fromNode)]>self.parentGraph.edgePaths[(fromNode,toNode)]:
#                         self.loopEdges.add(fromNode,toNode)
#                     else:
#                         self.loopEdges.add(toNode,fromNode)
#                         if self.has_edge(toNode,fromNode):
#                             self.remove_edge(toNode,fromNode)
#                             self.add_edge(fromNode,toNode)
#                         else:
#                             self.bubbleEdges.add(fromNode,toNode)
#                             combinedGraph.add_edge(fromNode,toNode)
#                             processedEdges.append((toNode,fromNode))
#                 except KeyError:
#                     self.loopEdges.add(fromNode,toNode)
                self.loopEdges.add(fromNode,toNode)

            elif edgeStatus > 0 and (fromNode,toNode) not in processedEdges:
                self.bubbleEdges.add(fromNode,toNode)
                combinedGraph.add_edge(fromNode,toNode)

    # !!! Test this function with case on the paper!!! Incorrectly identify one of the links.
    def isBubbleLoop(self,start,end,treeBubbleGraph):
        '''
        return one of three statuses 
            - -1 (mark as loop link), ignored during sort, or
            - 1 (mark as bubble forward link), can changes sort order, or
            - 2 (mark as bubble cross link), can changes sort order, or 
            - raises error AmbiguousTreeEdge, which means that the special link class is not identified.
        '''
        
        # link forward jumping (bubble) at least one node (check length > 2), otherwise, raise error of repeat link.
        if start==end:
            return -1
        
        # Check which one of the two options to mark as loop.
        if start in dict(self[end]) or start in self.bubbleEdges.get(end,[]):
            return -1
        
        try:
            shortPath = nx.shortest_path(self,start,end)
        except nx.NetworkXNoPath:
            shortPath = None
        if shortPath is not None:
            if len(shortPath)>2:
                return 1
                
        else:
            # !!! test if there is a path from end to start (in combination of tremauxTree and bubbles)
            if (end in nx.ancestors(self,start)) or \
                (start in list(self[end].keys())) or \
                (start in self.bubbleEdges.get(end,[]) or \
                (nx.has_path(treeBubbleGraph,end,start))):
                return -1
            else:
                return 2
        
        raise AmbigouosTreeEdge('Path between start and end is only two nodes (not jumping nodes).')
        
    def draw(self):
        bubbleEdges = [(u,v) for u,ends in self.bubbleEdges.items() for v in ends ]
        loopEdges = [(u,v) for u,ends in self.loopEdges.items() for v in ends ]

        tempGraph = nx.DiGraph(self)
        tempGraph.add_edges_from(bubbleEdges+loopEdges)
        colours = []
        for edge in tempGraph.edges:
            if edge in self.edges:
                colours.append('blue')
            elif edge in bubbleEdges:
                colours.append('green')
            elif edge in loopEdges:
                colours.append('red')
        nx.draw(tempGraph,edge_color=colours,pos=nx.kamada_kawai_layout(tempGraph),with_labels=True)
    
    def draw_original(self):
        nx.draw(self.originalGraph,pos=nx.kamada_kawai_layout(self.originalGraph),with_labels=True)
    def getRootNodes(self):
        return deepcopy(self.startingNodes)
#         inCond = dict([(node,in_degree==0) for node,in_degree in self.in_degree])

#         outCond = dict([(node,in_degree!=0) for node,in_degree in self.out_degree])
        
#         rootList = []
        
#         for node,deg_in in inCond.items():
#             if outCond[node] and deg_in:
#                 rootList.append(node)
        
#         if len(rootList)>1:
#             raise AmbigouosRootNode(f'Only 1 root node is expected, but {len(roorList)} are found')
            
#         return rootList[0]

