import glob
from casatools import table
import numpy as np


def get_tablelist(inputdir):
    # look in directory itself else try the standard pl directory structure
    lst = glob.glob(inputdir + '/*.tbl')
    if lst is None:
        lst = glob.glob(inputdir + '/S*/G*/M*/working/*.tbl')
    return lst


def load_tables(inputobj):
    if type(inputobj) == list:
        tablelist = inputobj
    else:
        tablelist = inputobj
    eb = {'EB': {}}
    for tname in tablelist:
        t = table()
        t.open(tname)
        ebname = '.'.join(tname.split('/')[-1].split('.')[0:2])
        stagename = tname.split('/')[-1].split('.')[2].split('_')[1]
        tableversion = tname.split('/')[-1].split('.')[3].split('_')[1]
        tabletype = '.'.join(tname.split('/')[-1].split('.')[4:])
        if ebname not in list(eb['EB'].keys()):
            eb['EB'][ebname] = {}
        if stagename not in list(eb['EB'][ebname].keys()):
            eb['EB'][ebname][stagename] = {}
        eb['EB'][ebname][stagename][tableversion] = {'tabletype': tabletype, 'fsum': get_columnsum(t, tname, 'FPARAM'),
                                                     'nflags': get_columnsum(t, tname, 'FLAG')}
    return eb


def get_columnsum(t, tname, columnname):
    if columnname == 'FPARAM':
        if 'FPARAM' in list(t.colnames()):
            columnname = 'FPARAM'
        else:
            columnname = 'CPARAM'
    if 'bcal' in tname:
        totsum = 0
        for row in np.arange(t.nrows()):
            totsum += np.sum(t.getcell(columnname, row))
    else:
        totsum = t.getcol(columnname).sum()
    return float(np.sqrt(totsum * np.conj(totsum)))
