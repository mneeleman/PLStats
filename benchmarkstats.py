# a global place to put get "benchmark" stats functions
# note that these function only apply to a single benchmark,
# which is defined as a directory of multiple PL runs in standard ouptut form
import glob
from plstats import PLStats
import numpy as np


def get_stages(inputdir, overwrite=True):
    workdirs = __get_workingdirs__(inputdir)
    stages = {}
    for workdir in workdirs:
        try:
            arfile = glob.glob(workdir + '/working/pipeline_aquareport.xml')[0]
        except IndexError:
            arfile = glob.glob(workdir + '/S*/G*/M*/working/pipeline_aquareport.xml')[0]
        try:
            timefile = sorted(glob.glob(workdir + '/working/pipeline-*.timetracker.json'))[-1]
        except IndexError:
            timefile = sorted(glob.glob(workdir + '/S*/G*/M*/working/pipeline-*.timetracker.json'))[-1]
        # print('For workdir: {}, using timefile: {}'.format(workdir.split('/')[-1], timefile.split('/')[-1]))
        pl = PLStats.from_aquareport(arfile, timefile=timefile)
        if overwrite:
            stages[pl.mous['proposal_code']['value']] = pl.mous['STAGE']
        else:
            if pl.mous['proposal_code']['value'] in list(stages.keys()):
                stages[pl.mous['proposal_code']['value'] + '_1'] = pl.mous['STAGE']
            else:
                stages[pl.mous['proposal_code']['value']] = pl.mous['STAGE']
    return stages


class BenchMarkStats:
    def __init__(self, inputdir, statsfile_only=False, **kwargs):
        self.projects = []
        self.workdirs = []
        self.mouslist = []
        self.mousnames = []
        self.inputdir = inputdir
        if statsfile_only:
            files = glob.glob(inputdir + '/*.json')
            for file in files:
                self.mouslist.append(PLStats.from_statsfile(file))
            self.mousnames = [x.mous['mous_uid']['value'] for x in self.mouslist]
        self.__get_projects__()
        self.__get_workingdirs__()
        self.__load_mous__(**kwargs)

    def get_keywords(self,  level='MOUS', ignore=None):
        return self.mouslist[0].get_keywords(level=level, ignore=ignore)

    def get_values(self, key, level=None, subkey=None, value_only=True, return_list=False, flatten=False,
                   repeat=None):
        if return_list:
            value_only = True
        val_list = []
        for mous in self.mouslist:
            val = mous.get_values(key, level=level, subkey=subkey, value_only=value_only)
            if return_list:
                if not repeat:
                    val_list.append(list(val.values()))
                else:
                    n_x = len(list(mous.get_values(repeat, value_only=True).values())[0])
                    val_list.extend(list(val.values()) * n_x)
            else:
                val_list.append(val)
        if flatten:
            flat_list = []
            for x in val_list:
                flat_list.extend(x)
            return flat_list
        else:
            return val_list

    def select(self, key, operator, value, level=None, subkey=None):
        if not level:
            level = self.mouslist[0].__get_level__(key)
        xvals = self.get_values(key, level=level, subkey=subkey, value_only=True, return_list=False, flatten=True)
        values = self.get_values(key, level=level, subkey=subkey, value_only=True, return_list=True, flatten=True)
        sel_vals = [x for x, y in zip(xvals, values) if __comp__(y, operator, value)]
        newmousnames = list(np.unique([x.split('|')[0] for x in sel_vals]))
        for mousname in list(self.mousnames):
            if mousname not in newmousnames:
                self.remove_mous(mousname)
        if not sel_vals or len(sel_vals[0].split('|')) <= 1:
            return
        sublevel = sel_vals[0].split('|')[1]
        if sublevel in ['EB', 'SPW', 'TARGET', 'STAGE']:
            for mousname in newmousnames:
                if key in ['EB', 'SPW', 'TARGET', 'STAGE']:
                    for x in list(self.get_mous(mousname).mous[sublevel].keys()):
                        if not __comp__(x, operator, value):
                            self.get_mous(mousname).mous[sublevel].pop(x)
                else:
                    for x in list(self.get_mous(mousname).mous[sublevel]):
                        if mousname + '|' + sublevel + '|' + x + '|' + key not in sel_vals:
                            print(mousname + '|' + sublevel + '|' + x + '|' + key)
                            self.get_mous(mousname).mous[sublevel].pop(x)

    def __get_projects__(self):
        dirs = sorted(glob.glob(self.inputdir + '/*.*.*.*_*_*_*_*_*.*'))
        self.projects = np.unique([x.split('/')[-1].split('_')[0] for x in dirs]).tolist()

    def __get_workingdirs__(self):
        for proj in self.projects:
            plist = glob.glob('{0}/{1}_*/working'.format(self.inputdir, proj))
            if not plist:
                plist = glob.glob('{0}/{1}_*/S*/G*/M*/working'.format(self.inputdir, proj))
            if not plist:
                full_dir = glob.glob('{0}/{1}'.format(self.inputdir, proj))[0].split('/')[-1]
                print('{0} does not have a valid owrking directory.'.format(full_dir))
                self.workdirs.append('')
            else:
                self.workdirs.append(plist[-1])

    def __load_mous__(self, **kwargs):
        for workdir in self.workdirs:
            self.mouslist.append(PLStats.from_workingdir(workdir, **kwargs))
        self.mousnames = [x.mous['mous_uid']['value'] for x in self.mouslist]

    def get_mous(self, mousname):
        if mousname not in self.mousnames:
            raise IOError('mous: {} is not in the current mousname list'.format(mousname))
        return self.mouslist[self.mousnames.index(mousname)]

    def remove_mous(self, mous):
        if type(mous) == int:
            index = mous
            if index > len(self.projects) - 1:
                raise IOError('Index is too large got {}, maximmum index is {}'.format(index, len(self.projects) - 1))
        elif type(mous) == str:
            if mous in self.mousnames:
                index = self.mousnames.index(mous)
            elif mous in self.projects:
                index = self.projects.index(mous)
            else:
                raise IOError('Invalid MOUS name or project name, got {}'.format(mous))
        else:
            raise IOError('Invalid MOUS type needs to be string or integer, got {}'.format(type(mous)))
        # self.projects.pop(index)
        # self.workdirs.pop(index)
        self.mouslist.pop(index)
        self.mousnames.pop(index)


def __get_workingdirs__(inputdir):
    files = sorted(glob.glob(inputdir + '/*.*.*.*_*_*_*_*_*.*'))
    return files


def __comp__(x, operator, value):
    if operator == '==':
        return x == value
    elif operator == '<=':
        return x <= value
    elif operator == '>=':
        return x >= value
    elif operator == '!=':
        return x != value
    elif operator == 'contains':
        return value in x
    else:
        return ValueError('Operator not defined!')
    pass
