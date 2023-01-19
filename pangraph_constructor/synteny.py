# AUTOGENERATED! DO NOT EDIT! File to edit: ../03_synteny.ipynb.

# %% auto 0
__all__ = ['readTransMap', 'generateOrder', 'getIDs', 'processAccession', 'recordSegment', 'recordAnnotation', 'addLink',
           'generatePathsLinks', 'writeLinks', 'writePath', 'writeSegmentIDs', 'readSegmentIDs']

# %% ../03_synteny.ipynb 4
import os
import glob
import json
import itertools

import pandas as pd

from skbio.io import read as skbio_read
from skbio.metadata import IntervalMetadata
from skbio.sequence import DNA

from dnasim.IO import writeFASTA
from dnasim.simulation import inverseSequence
from pangraph_constructor.utils import bidict

# %% ../03_synteny.ipynb 7
def readTransMap(transMapFile,ATaccessionName='araport'):
    # reading and preparing transmap in pandas format
    transMap = pd.read_csv(transMapFile,delimiter='\t')
    transMap.fillna('',inplace=True)
    transMap.rename(columns={'Orthogroup:':'orthogroup'},inplace=True)
    transMap['orthogroup'] = transMap.orthogroup.str.rstrip(':')
    transMap.set_index('orthogroup',inplace=True)
#     transMap.fillna('',inplace=True)
    if ATaccessionName is not None:
        ATTransMap = transMap[ATaccessionName]
        return bidict({og:ATTransMap[og].split(', ') for og in ATTransMap.index})
    else:
        return transMap

# %% ../03_synteny.ipynb 8
def generateOrder(files, priorityAccession='TIAR10'):
    idxList = list(range(len(files)))
    if priorityAccession is not None:
        ind = [idx for idx, file in enumerate(files) if priorityAccession in file][0]
        del idxList[ind]
        idxList = [ind] + idxList
    return idxList

# %% ../03_synteny.ipynb 9
def getIDs(iterator):
    idList = []
    for interval in iterator:
        idList.append(interval.metadata['ID'])
    
    return idList

# %% ../03_synteny.ipynb 10
def processAccession(annotationFile, sequenceFile=None,
                     ATmap=None, isRef=False, accID=None):
    if accID is None:
        accessionID = os.path.splitext(os.path.basename(annotationFile))[0]
    else:
        accessionID = accID
    annotationGen = skbio_read(annotationFile, format='gff3')
    
    sequenceDict = None
    
    if sequenceFile is not None:
        sequenceDict = {}
        sequenceGen = skbio_read(sequenceFile,format='fasta')
        for seq in sequenceGen:
            sequenceDict[seq.metadata['id']] = bytearray(seq.values).decode()
    
    genes = []
    for seqID,annotation in annotationGen:
        geneInts = annotation.query(metadata={'type':'gene'})
        
        for gene in geneInts:
            geneID = gene.metadata['ID'].split('.')[-1]
            if isRef and ATmap is not None:
                orthogroup = ATmap.inverse.get(geneID,[None])[0]
            elif isRef:
                raise ValueError("If reference is provided, then the TransMap (bidict) with bidirectional relation between reference and annotation IDs should be provided.")
                #orthogroup = gene.metadata['ID']
            else:
                orthogroup = gene.metadata['OG']
            
            if orthogroup is None:
                continue
            
            if ATmap is not None:
                atNamesStr = ATmap.get(orthogroup,[''])
            else:
                atNameStr = ['']
            forward = gene.metadata['strand']=='+'
            start,end = gene.bounds[0]
            
            if sequenceDict is not None:
                geneSeq = sequenceDict[seqID][start:end+1]
            else:
                geneSeq = ''
            if isRef:
                pass
            overlaps = getIDs(annotation.query(bounds=[(start,end)],metadata={'type':'gene'}))
            genes.append([geneID,orthogroup,seqID,accessionID,forward,start,end,atNamesStr,geneSeq,overlaps])
    
    genes = pd.DataFrame(genes,columns=['geneID','orthogroup','sequenceID','accessionID','forward','start','end','AT_str','geneSeq','overlapGenes'])
    genes.sort_values(by=['sequenceID','start'],inplace=True)
        
    return accessionID,genes,sequenceDict

# %% ../03_synteny.ipynb 11
def recordSegment(name,segmentIDs,segmentIDToNumDict,sequence=None,gfaFile=None,segmentData=None):
    segmentIDs.append(name)
    
    segmentIDToNumDict[name] = len(segmentIDs)-1
    segID = len(segmentIDs)
    
    if segmentData is not None and sequence is not None:
        segmentData.append(sequence)
    
    if gfaFile is not None:
        if sequence is not None:
            gfaFile.write(f'S\t{segID}\t{sequence}\n')        
        else:
            gfaFile.write(f'S\t{segID}\t{name}\n')
    return segID

# %% ../03_synteny.ipynb 12
def recordAnnotation(nodeID,accessionID,sequenceID,og,atList,sequence,nodesAnnotation,nodesChr):
    if len(nodesAnnotation)==nodeID-1:
        nodesAnnotation.append({})
        
    geneLen = 1
    if len(sequence)>0:
        geneLen = len(sequence)
    
    nodesAnnotation[nodeID-1].setdefault(accessionID,{})[og] = [(0,geneLen-1)]#[(0,len(og)-1)]
    for at in atList:
        nodesAnnotation[nodeID-1].setdefault(accessionID,{})[at] = [(0,geneLen-1)]#[(0,len(at)-1)]
    
    if len(nodesChr)==nodeID-1:
        nodesChr.append({})
        
    nodesChr[nodeID-1].setdefault(accessionID,[]).append(sequenceID)

# %% ../03_synteny.ipynb 13
def addLink(links,prevPathSegment,name,forward):
    '''
    `links`: mutable
    `prevPathSegment`: mutable
    '''
    if prevPathSegment is not None:
        links[prevPathSegment].add(f'{name}\t{"+" if forward else "-"}')
    return f'{name}\t{"+" if forward else "-"}'

# %% ../03_synteny.ipynb 14
def generatePathsLinks(genes,sequenceID,accessionID,
                       sequences,OGList,segmentIDs,
                       nodeAnnotation,nodesChr,
                       segmentIDToNumDict,links,usCounter,
                       doUS=True,segmentData=None,gfaFile=None):
    '''
    `gfaFile`: file handle to write segments to GFA file
    `OGList`: mutable
    `links`: mutable
    `usCounter`: mutable
    
    '''
    path = []
    cigar = []
    prevEnd = 0
    prevPathSegment = None
    curSeqID = ''
    for gene in genes.iterrows():
        og = gene[1].orthogroup
        
        geneSeqID = gene[1].sequenceID
        if curSeqID != geneSeqID:
            curSeqID = geneSeqID
        
        atStr = gene[1].AT_str
        if len(atStr[0])>0:
            atList = atStr
        else:
            atList = []
        
        geneStart = gene[1].start
        geneEnd = gene[1].end
        geneForward = gene[1].forward
        
        if sequences is not None:
            if geneForward:
                geneSeq = sequences[geneSeqID][geneStart:geneEnd+1]
            else:
                geneSeq = inverseSequence(sequences[geneSeqID][geneStart:geneEnd+1])
        else:
            geneSeq = ''
        
        if doUS:
        
            if sequences is not None:
                usSeq = sequences[geneSeqID][prevEnd:geneStart]
            else:
                usSeq = ''

            if len(usSeq)>0:
                isUS = True
                us = f'US{usCounter:07d}'
                usCounter += 1
            else:
                isUS = False

            if isUS:
                usID = recordSegment(us,segmentIDs,segmentIDToNumDict,usSeq,gfaFile=gfaFile,segmentData=segmentData)
                recordAnnotation(usID,accessionID,geneSeqID,us,[],usSeq,nodeAnnotation,nodesChr)
        
        if og not in OGList:
            ogID = recordSegment(og,segmentIDs,segmentIDToNumDict,geneSeq,gfaFile=gfaFile,segmentData=segmentData)
            OGList.append(og)
        else:
            ogID = segmentIDs.index(og)+1
        
        recordAnnotation(ogID,accessionID,geneSeqID,og,atList,geneSeq,nodeAnnotation,nodesChr)
        
        pathAdd = [f'{ogID}{"+" if geneForward else "-"}']
        if doUS and isUS:
            pathAdd.insert(0,f'{usID}+')
            
        path.extend(pathAdd)
        
        if len(cigar)>0 and doUS and isUS:
            cigar.extend(['0M','0M']) # with previous block and between two current blocks
        else:
            cigar.append('0M') # only between current blocks or between previous and current gene
                               # without unrelated sequence (intergenic) block.
        
        if doUS and isUS:
            prevPathSegment = addLink(links,prevPathSegment,usID,True)
            links[prevPathSegment] = set()
        
        prevPathSegment = addLink(links,prevPathSegment,ogID,geneForward)
        if prevPathSegment not in links:
            links[prevPathSegment] = set()
        
        prevEnd = geneEnd+1
    
    if doUS:
        
        if sequences is not None:
            usSeq = sequences[curSeqID][prevEnd:]
        else:
            usSeq = ''

        if len(usSeq)>0:
            us = f'US{usCounter:07d}'
            usID = recordSegment(us,segmentIDs,segmentIDToNumDict,usSeq,gfaFile=gfaFile,segmentData=segmentData)
            recordAnnotation(usID,accessionID,geneSeqID,us,[],nodeAnnotation,nodesChr)
            usCounter += 1
            path.append(f'{usID}+')
            cigar.append('0M')
            prevPathSegment = addLink(links,prevPathSegment,usID,True)

    return path,cigar,usCounter

# %% ../03_synteny.ipynb 15
def writeLinks(gfaFile,links,doCigars=True):
    for linkLeft,linksRight in links.items():
        for linkRight in linksRight:
            if doCigars:
                gfaFile.write(f'L\t{linkLeft}\t{linkRight}\t0M\n')
            else:
                gfaFile.write(f'L\t{linkLeft}\t{linkRight}\t*\n')
                
def writePath(gfaFile,AccessionID,path,cigar,doCigars):   
    if doCigars:
        cigarString = ",".join(cigar)
    else:
        cigarString = "*"
        
    gfaFile.write(f'P\t{AccessionID}\t{",".join(path)}\t{cigarString}\n')
    
def writeSegmentIDs(path,segmentIDs):
    with open(path,'w') as jsf:
        json.dump(segmentIDs,jsf)
        
def readSegmentIDs(path):
    with open(path,'r') as jsf:
        return json.load(jsf)
