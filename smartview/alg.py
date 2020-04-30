import gzip
import os
from scipy import sparse
import numpy as np
from collections import Counter
import time


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


class TreeAlignment(object):
    def __init__(self, alg, n2content):
        self.n2content = n2content
        self.alg = alg

    def __contains__(self, item):
        r = item in self.n2content if self.n2content else False
        return r

    def __getitem__(self, item):
        node = item
        if node.children:
            leaves = [leaf.name for leaf in self.n2content[node]]
            return self.alg.consensus(leaves)
        else:
            return self.alg[node.name]
