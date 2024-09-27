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
    def from_aquareport(cls, arfile):
        self = cls()
        self.arfile = arfile
        self.mous = load_aquareport(arfile)
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
            statsobj = self.from_statsfile(self.workdir + '/' + self.statsfile)
        else:
            statsobj = {'mous: {}'}
        self.arfile = glob.glob(workdir + '/pipeline_aquareport.xml')[0].split('/')[-1]
        if self.arfile:
            arobj = self.from_aquareport(self.workdir + '/' + self.arfile)
        else:
            arobj = {'mous': {}}
        self.tablelist = [x.split('/')[-1] for x in glob.glob(workdir + '/*.tbl')]
        if self.tablelist:
            tabobj = self.from_tablelist([self.workdir + '/' + x for x in self.tablelist])
        else:
            tabobj = {'mous': {}}
        self.mous = self.__mergedict__(statsobj.mous, arobj.mous)
        self.mous = self.__mergedict__(self.mous, tabobj.mous)
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

    def __init__(self):
        self.mous = {}

    def __mergedict__(self, a: dict, b: dict, path=None):
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.__mergedict__(a[key], b[key], path + [str(key)])
                # elif a[key] != b[key]:
                #     raise Exception('Conflict at ' + '.'.join(path + [str(key)]))
            else:
                a[key] = b[key]
        return a
