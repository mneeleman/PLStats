# code to read in the stats of a pipeline directory and provide manipulation of this data.
# ideally the code would take info only from stats file, but for know allow other inputs
import json
from aquareport import load_aquareport
from tables import load_tables
import glob
import numpy as np


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
        self.mous['mous_uid'] = {'value': mouslist[0]}
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
            tlist = glob.glob(workdir + '/pipeline-*.timetracker.json')
            tlist.sort()
            self.timefile = tlist[-1]
            if self.timefile and use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile, timefile=self.timefile).mous)
            elif self.timefile and not use_timefile:
                self.__mergedict__(self.from_aquareport(self.workdir + '/' + self.arfile).mous)
        self.tablelist = [x.split('/')[-1] for x in glob.glob(workdir + '/*.tbl')]
        if self.tablelist and use_tables:
            self.__mergedict__(self.from_tablelist([self.workdir + '/' + x for x in self.tablelist]).mous)
        return self

    @classmethod
    def from_uidname(cls, uid_name, searchdir='.', index=0):
        self = cls()
        uid_list = glob.glob(searchdir + '/pipeline_stats_*.json')
        all_uid = [x for x in uid_list if uid_name in x]
        self.statsfile = all_uid[index]
        self.__mergedict__(self.from_statsfile(self.statsfile).mous)
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
        if 'STAGE' in self.mous.keys():
            sublevel = {'MOUS': '', 'EB': list(self.mous['EB'].keys())[0], 'SPW': list(self.mous['SPW'].keys())[0],
                        'TARGET': list(self.mous['TARGET'].keys())[0], 'STAGE': list(self.mous['STAGE'].keys())[0]}
        else:
            sublevel = {'MOUS': '', 'EB': list(self.mous['EB'].keys())[0], 'SPW': list(self.mous['SPW'].keys())[0],
                        'TARGET': list(self.mous['TARGET'].keys())[0]}
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

    def analyze_stats(self):
        for eb in self.mous['EB']:
            n_manualflags = len(self.mous['EB'][eb]['flagdata_manual_flags']['value'])
            self.mous['EB'][eb]['n_manualflags'] = {'value': n_manualflags}
        for target in self.mous['TARGET']:
            cubes, mfss, conts = [[], [], [], [], []], [[], [], [], [], []], [[], [], [], [], []]
            pars = ['bmaj', 'bmin', 'bpa', 'rms', 'max']
            for x in self.mous['TARGET'][target]:
                for par, cube, mfs, cont in zip(pars, cubes, mfss, conts):
                    if 'makeimages_science_cube_' + par in self.mous['TARGET'][target][x]:
                        cubemed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_cube_' +
                                                                              par]['value'])
                        cube.append(cubemed.astype(float).item())
                    elif 'makeimages_science_cube_selfcal_' + par in self.mous['TARGET'][target][x]:
                        cubemed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_cube_selfcal_' +
                                                                              par]['value'])
                        cube.append(cubemed.astype(float).item())
                    if 'makeimages_science_mfs_' + par in self.mous['TARGET'][target][x]:
                        mfsmed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_mfs_' + par]['value'])
                        mfs.append(mfsmed.astype(float).item())
                    elif 'makeimages_science_mfs_selfcal_' + par in self.mous['TARGET'][target][x]:
                        mfsmed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_mfs_selfcal_' +
                                                                             par]['value'])
                        mfs.append(mfsmed.astype(float).item())
                    if 'makeimages_science_cont_' + par in self.mous['TARGET'][target][x]:
                        contmed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_cont_' +
                                                                              par]['value'])
                        cont.append(contmed.astype(float).item())
                    elif 'makeimages_science_cont_selfcal_' + par in self.mous['TARGET'][target][x]:
                        contmed = np.nanmedian(self.mous['TARGET'][target][x]['makeimages_science_cont_selfcal_' +
                                                                              par]['value'])
                        cont.append(contmed.astype(float).item())

            #print(len(vals))
            for par, cube, mfs, cont in zip(pars, cubes, mfss, conts):
                self.mous['TARGET'][target]['median_cube_' + par] = {'value': np.nanmedian(cube)}
                self.mous['TARGET'][target]['median_mfs_' + par] = {'value': np.nanmedian(mfs)}
                self.mous['TARGET'][target]['median_cont_' + par] = {'value': np.nanmedian(cont)}
            self.mous['TARGET'][target]['median_cube_sn'] = {'value': np.nanmedian(cubes[4]) / np.nanmedian(cubes[3])}
            self.mous['TARGET'][target]['median_mfs_sn'] = {'value': np.nanmedian(mfss[4]) / np.nanmedian(mfss[3])}
            self.mous['TARGET'][target]['median_cont_sn'] = {'value': np.nanmedian(conts[4]) / np.nanmedian(conts[3])}

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
