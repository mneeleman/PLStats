# a global place to put get "benchmark" stats functions
# not that these funcction only apply to a single benchmark,
# which is defined as a directory of multiple PL runs in standard ouptut form
import glob
from plstats import PLStats


def get_stages(inputdir, overwrite=True):
    workdirs = __get_workingdirs__(inputdir)
    timestats = {}
    for workdir in workdirs:
        try:
            arfile = glob.glob(workdir + '/working/pipeline_aquareport.xml')[0]
        except IndexError:
            arfile = glob.glob(workdir + '/S*/G*/M*/working/pipeline_aquareport.xml')[0]
        try:
            timefile = glob.glob(workdir + '/working/pipeline-*.timetracker.json')[-1]
        except IndexError:
            timefile = glob.glob(workdir + '/S*/G*/M*/working/pipeline-*.timetracker.json')[-1]
        pl = PLStats.from_aquareport(arfile, timefile=timefile)
        if overwrite:
            timestats[pl.mous['proposal_code']['value']] = pl.mous['stages']
        else:
            if pl.mous['proposal_code']['value'] in list(timestats.keys()):
                timestats[pl.mous['proposal_code']['value'] + '_1'] = pl.mous['stages']
            else:
                timestats[pl.mous['proposal_code']['value']] = pl.mous['stages']
    return timestats


def __get_workingdirs__(inputdir):
    files = glob.glob(inputdir + '/*.*.*.*_*_*_*_*_*.*')
    return files
