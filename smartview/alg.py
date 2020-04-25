class SmartAlg(object):
    def __init__(self, alg, n2content):
        self.n2content = n2content
        self.alg = alg        

    def __contains__(self, item):
        r = item in self.n2content if self.n2content else False
        return r

    def __getitem__(self, item):
        node = item 
        if node.children: 
            return self.get_consensus(node)
        else: 
            return self.alg[node.name]
      
    def get_consensus(self, node):
        seqs = [self.alg[leaf.name] for leaf in self.n2content[node] if leaf.name in self.alg]
        return get_consensus_seq(seqs)
    
def get_consensus_seq(seqs):
    return seqs[0]

