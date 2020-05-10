import gzip
import os
from scipy import sparse
import numpy as np
from collections import Counter
import time
import random
from .utils import timeit

def iter_fasta_seqs(source):
    """Iter records in a FASTA file"""

    if os.path.isfile(source):
        if source.endswith('.gz'):
            _source = gzip.open(source)
        else:
            _source = open(source, "r")
    else:
        _source = iter(source.split("\n"))

    seq_chunks = []
    seq_name = None
    for line in _source:
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        elif line.startswith('>'):
            # yield seq if finished
            if seq_name and not seq_chunks:
                raise ValueError(
                    "Error parsing fasta file. %s has no sequence" % seq_name)
            elif seq_name:
                yield seq_name, ''.join(seq_chunks)

            seq_name = line[1:].split('\t')[0].strip()
            seq_chunks = []
        else:
            if seq_name is None:
                raise Exception("Error reading sequences: Wrong format.")
            seq_chunks.append(line.replace(" ", ""))

    # return last sequence
    if seq_name and not seq_chunks:
        raise ValueError(
            "Error parsing fasta file. %s has no sequence" % seq_name)
    elif seq_name:
        yield seq_name, ''.join(seq_chunks)


class SparseAlg(dict):
    def __init__(self, fastafile):
        super().__init__()
        self.algmatrix = None
        self.index = None

        if fastafile:
            self.load_alg(fastafile)

    def load_alg(self, fname):
        self.index = {}
        matrix = []
        for seqnum, (seq_name, seq) in enumerate(iter_fasta_seqs(fname)):
            self.index[seq_name] = seqnum
            vector = np.array(
                [ord(pos.upper()) - 45 for pos in seq], dtype='byte')
            matrix.append(vector)

        self.algmatrix = sparse.lil_matrix(matrix)

    def __contains__(self, item):
        return item in self.index

    def __getitem__(self, item):
        return self.consensus([item])

    def consensus(self, items):
        print("consensus of %d items" % len(items))
        rows = [self.index[i] for i in items]
        t1 = time.time()
        submatrix = self.algmatrix[tuple(rows), ]

        # size = matrix.shape[0] * matrix.shape[1]
        # gappyness = (matrix.size / size)
        consensus = []
        for col in submatrix.T:
            values = col[col.nonzero()].data[0]
            counter = Counter(values)
            if counter:
                most_common_res = counter.most_common()[0][0]
                # print(most_common_res)
                consensus.append(chr(most_common_res+45))
            else:
                consensus.append('-')

        print(time.time()-t1)
        return ''.join(consensus)


class Alg(dict):
    def __init__(self, fastafile):
        super().__init__()
        for seq_name, seq in iter_fasta_seqs(fastafile):
            self[seq_name] = seq

    def consensus(self, items):
        return self[items[0]]
    
import diskhash
import tqdm 

class DiskHashAlg(dict):
    def __init__(self, keysize, dbfile):
        super().__init__()
        self.dbfile = dbfile
        self.db = None
        self.keysize = int(keysize)
        self.alg_length = None        
            
    def load_fasta(self, fname):
        self.db = None
        if os.path.exists(self.dbfile): 
            os.remove(self.dbfile)
            
        for i, (name, seq) in enumerate(iter_fasta_seqs(fname)):                  
            if self.db is None: 
                self.alg_length = len(seq)
                self.db = diskhash.StructHash(self.dbfile, self.keysize, '%sc' %(self.alg_length), 'rw')
            self.db.insert(name, *[bytes(x, "utf-8") for x in seq])
        self.opendb()
        
    def opendb(self):
        self.db = diskhash.StructHash(self.dbfile, self.keysize, '%sc' %self.alg_length, 'r')
        
    def __contains__(self, item):
        try: 
            self.db.lookup(item) 
        except: 
            return False
        else: 
            return True
    
    def __getitem__(self, item):
        byteseq = self.db.lookup(item) 
        if byteseq: 
            seq = b''.join(byteseq)
        else: 
            seq = b''
        return seq.decode('utf-8')
    

AA2IDX = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'K': 9, 
          'L': 10, 'M': 11, 'N': 12, 'P': 13, 'Q': 14, 'R': 15, 'S': 16, 'T': 17, 'V': 18, 'W': 19, 'X': 20, 'Y': 21, 'Z': 22, '-':23}


IDX2AA = {idx:aa for aa,idx in AA2IDX.items()}

class TreeAlignment(object):
    def __init__(self, alg, n2content, consensus_method='random10'):
        self.n2content = n2content
        self.alg = alg
        self.node2matrix = {}
        self.consensus = {}
        self.consensus_method = consensus_method        
    def load_seqs(self, tree, alg): 
        for i, node in enumerate(tree.traverse("postorder")): 
            #print ("node", i, node.__repr__())
            if not node.children: 
                seq = alg[node.name]
                counter = np.zeros((len(seq), 24), dtype="int32")
                for i, site in enumerate(seq):                 
                    residx = AA2IDX[site]
                    counter[i, residx] = 1                
                self.node2matrix[node] = counter
            else:                                 
                counter = np.sum([self.node2matrix[ch] for ch in node.children], axis=0)                    
                self.node2matrix[node] = counter
                max_vector = counter.argmax(axis=1)
                self.consensus[node] = ''.join([IDX2AA[v] for v in max_vector])

    def get_consensus(self, node):
        if node not in self.consensus:
            if self.consensus_method == 'random10':
                leaves = self.n2content[node]
                if len(leaves) > 10:                    
                    leaves = random.sample(leaves, 10)
                sequences = [self.alg[leaf.name] for leaf in leaves]
            elif self.consensus_method == 'full':
                sequences = [self.alg[leaf.name] for leaf in self.n2content[node]]
            self.consensus[node] = self.calculate_consensus(sequences)
        return self.consensus[node]

    #@timeit
    def calculate_consensus(self, sequences):
        m = None                
        for seq in sequences:
            if not seq: 
                continue
            #seq = seq[:1000]
            counter = np.zeros((len(seq), 24), dtype="int32")            
            for i, site in enumerate(seq):                 
                residx = AA2IDX[site]
                counter[i, residx] = 1
            if m is None: 
                m = counter
            else:
                m += counter 
        max_vector = m.argmax(axis=1)
        return ''.join([IDX2AA[v] for v in max_vector])
    
    def __contains__(self, item):
        r = item in self.n2content if self.n2content else False
        return r
    
    def __getitem__(self, item):
        node = item
        if node.children:
            return self.get_consensus(node)
        else:
            return self.alg[node.name]


