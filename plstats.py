# code to read in the stats of a pipeline directory and provide manipulation of this data.
# ideally the code would take info only from stats file, but for know allow other inputs
import json
from aquareport import load_aquareport
from tables import load_tables
import glob


class PLStats:
    @classmethod
    def from_statsfile(cls, statsfile):
        tempjson = json.load(open(statsfile, 'r'))
        self = cls()
        self.statsfile = statsfile
        self.statsheader = tempjson['header']
        mouslist = [x for x in list(tempjson.keys()) if 'uid' in x]
        if len(mouslist) != 1:
            raise ValueError('There should be a unique MOUS in each json file, but found: {}'.format(mouslist))
        self.mous = tempjson[mouslist[0]]
        self.mousname = mouslist[0]
        self.mous['eb_list'] = {'value': list(self.get_keywords(level='EB'))}
        self.mous['spw_list'] = {'value': list(self.get_keywords(level='SPW'))}
        return self

    @classmethod
    def from_aquareport(cls, arfile, timefile=None):
        self = cls()
        self.arfile = arfile
        self.mous = load_aquareport(arfile, timefile=timefile)
        return self

    @classmethod
    def from_tablelist(cls, tablelist):
        self = cls()
        self.tablelist = tablelist
        self.mous = load_tables(tablelist)
        return self

    @classmethod
    def from_workingdir(cls, workdir):
        self = cls()
        self.workdir = workdir
        self.statsfile = glob.glob(workdir + '/pipeline_stats_*.json')[0].split('/')[-1]
        if self.statsfile:
            self.__mergedict__(self.from_statsfile(self.workdir + '/' + self.statsfile).mous)
        self.arfile = glob.glob(workdir + '/pipeline_aquareport.xml')[0].split('/')[-1]
        if self.arfile:
            self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile).mous)
        self.tablelist = [x.split('/')[-1] for x in glob.glob(workdir + '/*.tbl')]
        if self.tablelist:
            self.__mergedict__(self.from_tablelist([self.workdir + '/' + x for x in self.tablelist]).mous)
        return self

    def get_keywords(self, level='MOUS', sublevel='', ignore=None):
        if level == 'MOUS':
            keywords = list(self.mous.keys())
        elif sublevel == '':
            keywords = list(self.mous[level].keys())
        else:
            keywords = list(self.mous[level][sublevel].keys())
        if ignore:
            if type(ignore) == list:
                for x in ignore:
                    keywords.pop(keywords.index(x))
            else:
                keywords.pop(keywords.index(ignore))
        return keywords

    def findkeys(self, kv, node=None):
        if not node:
            node = self.mous
        if isinstance(node, list):
            for i in node:
                for x in self.findkeys(kv, node=i):
                    yield x
        elif isinstance(node, dict):
            if kv in node:
                yield node[kv]
            for j in node.values():
                for x in self.findkeys(kv, node=j):
                    yield x

    def __init__(self):
        self.mous = {}

    def __mergedict__(self, b: dict, a=None, path=None):
        if not a:
            a = self.mous
        if path is None:
            path = []
        for key in b:
            if key in a.keys():
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.__mergedict__(b[key], a=a[key], path=path + [str(key)])
            else:
                a[key] = b[key]
