# code to read in the stats of a pipeline directory and provide manipulation of this data.
# ideally the code would take info only from stats file, but for know allow other inputs
import json
from aquareport import load_aquareport
# from tables import load_tables
import glob
import numpy as np
import os.path


class PLStats:
    @classmethod
    def from_statsfile(cls, statsfile, suppl_statsfile=None):
        tempjson = json.load(open(statsfile, 'r'))
        self = cls()
        self.statsfile = statsfile
        self.statsheader = tempjson['header']
        mouslist = [x for x in list(tempjson.keys()) if 'uid' in x]
        if len(mouslist) != 1:
            raise ValueError('There should be a unique MOUS in each json file, but found: {}'.format(mouslist))
        self.mous = tempjson[mouslist[0]]
        self.mous['mous_uid'] = {'value': mouslist[0]}
        self.mous['eb_list'] = {'value': list(self.get_keywords(level='EB', return_sublevel=False))}
        self.mous['spw_list'] = {'value': list(self.get_keywords(level='SPW', return_sublevel=False))}
        if suppl_statsfile is None:
            suppl_statsfile = statsfile.replace('pipeline_stats_', 'pipeline-suppl_stats_')
        if os.path.isfile(suppl_statsfile):
            self.suppl_statsfile = suppl_statsfile
            self.__mergedict__(json.load(open(self.suppl_statsfile, 'r')))
            self.analyze_stats()
        else:
            print('Suppl_statsfile was not used for {}'.format(statsfile))
        return self

    @classmethod
    def from_aquareport(cls, arfile, timefile=None):
        self = cls()
        self.arfile = arfile
        self.mous = load_aquareport(arfile, timefile=timefile)
        return self

    # @classmethod
    # def from_tablelist(cls, tablelist):
    #     self = cls()
    #     self.tablelist = tablelist
    #     self.mous = load_tables(tablelist)
    #     return self

    @classmethod
    def from_workingdir(cls, workdir, use_statsfile=True, use_arfile=True, use_tables=False, use_timefile=True):
        self = cls()
        self.workdir = workdir
        self.statsfile = glob.glob(workdir + '/pipeline_stats_*.json')[0].split('/')[-1]
        if self.statsfile and use_statsfile:
            self.__mergedict__(self.from_statsfile(self.workdir + '/' + self.statsfile).mous)
        self.arfile = glob.glob(workdir + '/pipeline_aquareport.xml')[0].split('/')[-1]
        if self.arfile and use_arfile:
            tlist = glob.glob(workdir + '/pipeline-*.timetracker.json')
            tlist.sort()
            self.timefile = tlist[-1]
            if self.timefile and use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile, timefile=self.timefile).mous)
            elif self.timefile and not use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile).mous)
        self.tablelist = [x.split('/')[-1] for x in glob.glob(workdir + '/*.tbl')]
        if self.tablelist and use_tables:
            pass
        #     self.__mergedict__(self.from_tablelist([self.workdir + '/' + x for x in self.tablelist]).mous)
        return self

    @classmethod
    def from_uidname(cls, uid_name, searchdir='.', index=0):
        self = cls()
        uid_list = glob.glob(searchdir + '/pipeline_stats_*.json')
        all_uid = sorted([x for x in uid_list if uid_name in x])
        self.statsfile = all_uid[index]
        self.__mergedict__(self.from_statsfile(self.statsfile).mous)
        uid_supplist = glob.glob(searchdir + '/pipeline_aquareport-*.xml')
        ar_file = self.statsfile.replace('pipeline_stats_', 'pipeline_aquareport-')
        ar_file = ar_file.replace('json', 'xml')
        self.arfile = ar_file if ar_file in uid_supplist else ''
        if self.arfile != '':
            self.__mergedict__(self.from_aquareport(self.arfile).mous)
        uid_supplist = glob.glob(searchdir + '/pipeline-suppl_stats_*.json')
        suppl_file = self.statsfile.replace('pipeline', 'pipeline-suppl')
        self.suppl_statsfile = suppl_file if suppl_file in uid_supplist else ''
        if self.suppl_statsfile != '':
            self.__mergedict__(json.load(open(self.suppl_statsfile, 'r')))
            self.analyze_stats()
        return self

    def get_keywords(self, level='MOUS', return_sublevel=True, ignore=None):
        if level == 'MOUS':
            keywords = list(self.mous.keys())
        else:
            if level not in self.mous.keys():
                return []
            if return_sublevel:
                sublevel = list(self.mous[level].keys())[0]
                keywords = list(self.mous[level][sublevel].keys())
                for key in keywords.copy():  # remove teritiary dictionaries (which are often mous-specific)
                    if 'value' not in self.mous[level][sublevel][key]:
                        keywords.pop(keywords.index(key))
            else:
                keywords = list(self.mous[level].keys())
        if ignore:
            if type(ignore) == list:
                for x in ignore:
                    if x in keywords:
                        keywords.pop(keywords.index(x))
            else:
                if ignore in keywords:
                    keywords.pop(keywords.index(ignore))
        return keywords

    def get_values(self, key, level=None, subkey=None, value_only=False):
        if not level:
            level = self.__get_level__(key)
            if level == 'N/A':
                return {}
        if key in self.mous and level == 'MOUS':
            if value_only:
                try:
                    if subkey:
                        values = {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]['value'][subkey]}
                    else:
                        values =  {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]['value']}
                except KeyError:
                    values =  {'|'.join([self.mous['mous_uid']['value'], key]): list(self.mous[key].keys())}
            else:
                values = {'|'.join([self.mous['mous_uid']['value'], key]): self.mous[key]}
        else:
            if 'STAGE' in self.mous.keys():
                sublevel = {'MOUS': '', 'EB': list(self.mous['EB'].keys())[0], 'SPW': list(self.mous['SPW'].keys())[0],
                            'TARGET': list(self.mous['TARGET'].keys())[0], 'STAGE': list(self.mous['STAGE'].keys())[0]}
            else:
                sublevel = {'MOUS': '', 'EB': list(self.mous['EB'].keys())[0], 'SPW': list(self.mous['SPW'].keys())[0],
                            'TARGET': list(self.mous['TARGET'].keys())[0]}
            if key in self.mous[level]:
                values = {'|'.join([self.mous['mous_uid']['value'], level, key]): self.mous[level][key]}
            elif key in self.mous[level][sublevel[level]]:
                if value_only:
                    if subkey:
                        values = {'|'.join([self.mous['mous_uid']['value'], level, x, key]):
                                  self.mous[level][x][key]['value'][subkey] for x in self.mous[level]}
                    else:
                        values =  {'|'.join([self.mous['mous_uid']['value'], level, x, key]):
                                   self.mous[level][x][key]['value'] for x in self.mous[level]}
                else:
                    values = {'|'.join([self.mous['mous_uid']['value'], level, x, key]): self.mous[level][x][key]
                              for x in self.mous[level]}
            else:
                values = {}
        return values

    def analyze_stats(self):
        self.mous['manual_flags'] = {'value': []}
        for eb in self.mous['EB']:
            n_manualflags = len(self.mous['EB'][eb]['flagdata_manual_flags']['value'])
            self.mous['EB'][eb]['n_manualflags'] = {'value': n_manualflags}
            self.mous['manual_flags']['value'].extend(eb + ' ' + self.mous['EB'][eb]['flagdata_manual_flags']['value'])
        for target in self.mous['TARGET']:
            for spw in self.mous['TARGET'][target]:
                n_images = len([x for x in self.mous['TARGET'][target][spw].keys() if 'rms' in x])
                self.mous['TARGET'][target][spw]['n_images'] = {'value': n_images}
            n_images = np.sum([self.mous['TARGET'][target][spw]['n_images']['value']
                               for spw in self.mous['TARGET'][target]])
            self.mous['TARGET'][target]['n_images'] = {'value': n_images}
        n_images = np.sum([self.mous['TARGET'][target]['n_images']['value']
                           for target in self.mous['TARGET']])
        self.mous['n_images'] = {'value': int(n_images)}

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
            return 'N/A'


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
