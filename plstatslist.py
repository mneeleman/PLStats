## test code to take in a list of projects and select sample of these list for
## future use. This code might get moved somewhere else. The end result of this
## code is a list of plstats objects that can then be viewed in the plstatsgui, or it
## can be used for further analysis
import glob
import numpy as np
from plstats import PLStats
from copy import deepcopy as dc


class PLStatsList:
    def __init__(self, directory):
        self.directory = directory
        self.statslist = []

    @classmethod
    def from_directory(cls, directory, index=0):
        self = cls(directory)
        uid_names = np.unique([x.split('___')[-1].split('-')[0] + '-'
                               for x in glob.glob(self.directory + '/pipeline_stats*')])
        for uid_name in uid_names:
            self.statslist.append(PLStats.from_uidname(uid_name, searchdir=self.directory, index=index))
        if len(self.statslist) == 0:
            raise IOError('No json stat files found in: {}'.format(self.directory))
        return self

    @classmethod
    def from_list(cls, listname, directory, index=0):
        self = cls(directory)
        with open(listname, 'r', encoding='utf-8') as f:
            for uid_name in f:
                uid_name = uid_name.strip()
                if uid_name[0] != '#':
                    self.statslist.append(PLStats.from_uidname(uid_name, searchdir=self.directory, index=index))
        return self

    def apply_criterion(self, key, operator, criterion):
        new_list = []
        for plstats in self.statslist:
            values = plstats.get_values(key, value_only=True)
            for y in values:
                if type(values[y]) is list:
                    values[y] = ' '.join(values[y])
                crit = {'==': values[y] == criterion, '!=': values[y] != criterion,
                        '>=': values[y] >= criterion, '<=': values[y] <= criterion,
                        'contains': str(criterion) in str(values[y])}
                if crit[operator]:
                    new_list.append(plstats)
                    break
        self.statslist = new_list

    def to_list(self, listname):
        with open(listname, "w") as file:
            for plstats in self.statslist:
                file.write(f"{plstats.mous['mous_uid']['value']}\n")
