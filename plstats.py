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
        self.mous['eb_list'] = {'value': list(self.get_keywords(level='EB', return_sublevel=False))}
        self.mous['spw_list'] = {'value': list(self.get_keywords(level='SPW', return_sublevel=False))}
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
    def from_workingdir(cls, workdir, use_statsfile=True, use_arfile=True, use_tables=False, use_timefile=True):
        self = cls()
        self.workdir = workdir
        self.statsfile = glob.glob(workdir + '/pipeline_stats_*.json')[0].split('/')[-1]
        if self.statsfile and use_statsfile:
            self.__mergedict__(self.from_statsfile(self.workdir + '/' + self.statsfile).mous)
        self.arfile = glob.glob(workdir + '/pipeline_aquareport.xml')[0].split('/')[-1]
        if self.arfile and use_arfile:
            self.timefile = glob.glob(workdir + '/pipeline-*.timetracker.json')[0]
            if self.timefile and use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile, timefile=self.timefile).mous)
            elif self.timefile and not use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile).mous)
        self.tablelist = [x.split('/')[-1] for x in glob.glob(workdir + '/*.tbl')]
        if self.tablelist and use_tables:
            self.__mergedict__(self.from_tablelist([self.workdir + '/' + x for x in self.tablelist]).mous)
        return self

    def get_keywords(self, level='MOUS', return_sublevel=True, ignore=None):
        if level == 'MOUS':
            keywords = list(self.mous.keys())
        else:
            if return_sublevel:
                sublevel = list(self.mous[level].keys())[0]
                keywords = list(self.mous[level][sublevel].keys())
            else:
                keywords = list(self.mous[level].keys())
        if ignore:
            if type(ignore) == list:
                for x in ignore:
                    keywords.pop(keywords.index(x))
            else:
                keywords.pop(keywords.index(ignore))
        return keywords

    def get_values(self, key, level=None, subkey=None, value_only=False):
        if not level:
            level = self.__get_level__(key)
        if key in self.mous and level == 'MOUS':
            if value_only:
                try:
                    if subkey:
                        return {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]['value'][subkey]}
                    else:
                        return {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]['value']}
                except KeyError:
                    return {'|'.join([self.mous['mous_uid']['value'], key]): list(self.mous[key].keys())}
            else:
                return {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]}
        sublevel = {'MOUS': '', 'EB': list(self.mous['EB'].keys())[0], 'SPW': list(self.mous['SPW'].keys())[0],
                    'TARGET': list(self.mous['TARGET'].keys())[0], 'STAGE': list(self.mous['STAGE'].keys())[0]}
        if key in self.mous[level]:
            return {'|'.join([self.mous['mous_uid']['value'], level, key]): self.mous[level][key]}
        elif key in self.mous[level][sublevel[level]]:
            if value_only:
                if subkey:
                    return {'|'.join([self.mous['mous_uid']['value'], level, x, key]):
                            self.mous[level][x][key]['value'][subkey] for x in self.mous[level]}
                else:
                    return {'|'.join([self.mous['mous_uid']['value'], level, x, key]):
                            self.mous[level][x][key]['value'] for x in self.mous[level]}
            else:
                return {'|'.join([self.mous['mous_uid']['value'], level, x, key]): self.mous[level][x][key]
                        for x in self.mous[level]}

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

    def __get_level__(self, key):
        if key in self.get_keywords(level='MOUS'):
            return 'MOUS'
        elif key in self.get_keywords(level='EB'):
            return 'EB'
        elif key in self.get_keywords(level='SPW'):
            return 'SPW'
        elif key in self.get_keywords(level='TARGET'):
            return 'TARGET'
        elif key in self.get_keywords(level='STAGE'):
            return 'STAGE'
        else:
            return ValueError('Keyword not found: {}'.format(key))


def findkeys(node, kv):
    if isinstance(node, list):
        for i in node:
            for x in findkeys(i, kv):
                yield x
    elif isinstance(node, dict):
        if kv in node:
            yield node[kv]
        for j in node.values():
            for x in findkeys(j, kv):
                yield x
