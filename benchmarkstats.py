# a global place to put get "benchmark" stats functions
# note that these function only apply to a single benchmark,
# which is defined as a directory of multiple PL runs in standard ouptut form
import glob
from plstats import PLStats


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
            stages[pl.mous['proposal_code']['value']] = pl.mous['stages']
        else:
            if pl.mous['proposal_code']['value'] in list(stages.keys()):
                stages[pl.mous['proposal_code']['value'] + '_1'] = pl.mous['stages']
            else:
                stages[pl.mous['proposal_code']['value']] = pl.mous['stages']
    return stages


def __get_workingdirs__(inputdir):
    files = sorted(glob.glob(inputdir + '/*.*.*.*_*_*_*_*_*.*'))
    return files
