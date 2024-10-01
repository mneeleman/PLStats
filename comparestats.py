# this is a place where all of the comparison code lives. This could be
# comparison between single files or between a list of files.
from benchmarkstats import get_stages


def compare_timestats(inputdir1, inputdir2, tasklist=None):
    stages1 = get_stages(inputdir1)
    stages2 = get_stages(inputdir2)
    ex_stage1 = stages1[list(stages1.keys())[0]]
    ex_stage2 = stages2[list(stages2.keys())[0]]
    tasklist = __get_tasklistfromstagesdict__(ex_stage1, ex_stage2, tasklist=tasklist)
    comptime = {}
    for idx in tasklist:
        comptime[idx[0] + ':' + ex_stage1[idx[0]]['stage_name']['value']] = {'dir1': [], 'dir2': [], 'diff': []}
    for s1 in stages1:
        try:
            s2 = stages2.pop(s1)
        except KeyError:
            print('Project: {} does not exist in directory: {}'.format(s1, inputdir2))
            continue
        for idx in tasklist:
            val1 = stages1[s1][idx[0]]['task_time']['value']
            val2 = s2[idx[1]]['task_time']['value']
            diff = (val2 / val1)
            comptime[idx[0] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['dir1'].append(val1)
            comptime[idx[0] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['dir2'].append(val2)
            comptime[idx[0] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['diff'].append(diff)
    return comptime


def __get_tasklistfromstagesdict__(stage1, stage2, tasklist=None):
    if tasklist is None:
        s1numbers = [x for x in stage1.keys()]
        s1names = [stage1[x]['stage_name']['value'] for x in stage1.keys()]
        s2numbers = [x for x in stage2.keys()]
        s2names = [stage2[x]['stage_name']['value'] for x in stage2.keys()]
        tasklist = []
        for s1number, s1name in zip(s1numbers, s1names):
            try:
                idx2 = s2names.index(s1name)
                tasklist.append((s1number, s2numbers.pop(idx2)))
                s2names.pop(idx2)
            except ValueError:
                continue
    elif type(tasklist) == str:
        s1 = [x for x in stage1 if stage1[x]['stage_name']['value'] == tasklist]
        s2 = [y for y in stage2 if stage2[y]['stage_name']['value'] == tasklist]
        tasklist = [(x, y) for x, y in zip(s1, s2)]  # throws error if lengths are different (hif_makeimages)
    return tasklist

