# this is a place where all of the comparison code lives. This could be
# comparison between single files or between a list of files.
from benchmarkstats import get_stages, BenchMarkStats
import matplotlib.pyplot as plt


def compare_benchmarks(input1, input2, parameter_comparison_list=None, **kwargs):
    bm1, bm2 = __get_input__(input1), __get_input__(input2)
    if not parameter_comparison_list:
        pcl = __get_parameter_comparison_list__(bm1, **kwargs)
    else:
        pcl = parameter_comparison_list
    
    return pcl


def compare_timestats(inputdir1, inputdir2, tasklist=None, time='task_time', plot=False, **kwargs):
    print('get stages for input directory: {}'.format(inputdir1))
    stages1 = get_stages(inputdir1)
    print('get stages for input directory: {}'.format(inputdir2))
    stages2 = get_stages(inputdir2)
    ex_stage1 = stages1[list(stages1.keys())[0]]
    ex_stage2 = stages2[list(stages2.keys())[0]]
    tasklist = __get_tasklistfromstagesdict__(ex_stage1, ex_stage2, tasklist=tasklist)
    comptime = {'proposal_code': []}
    for idx in tasklist:
        comptime[idx[0] + ',' + idx[1] + ':' + ex_stage1[idx[0]]['stage_name']['value']] = {'dir1': [],
                                                                                            'dir2': [], 'diff': []}
    for s1 in stages1:
        print(s1)
        try:
            s2 = stages2.pop(s1)
        except KeyError:
            print('Project: {} does not exist in directory: {}'.format(s1, inputdir2))
            continue
        comptime['proposal_code'].append(s1)
        for idx in tasklist:
            val1 = stages1[s1][idx[0]][time]['value']
            val2 = s2[idx[1]][time]['value']
            diff = (val1 / val2)
            comptime[idx[0] + ',' + idx[1] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['dir1'].append(val1)
            comptime[idx[0] + ',' + idx[1] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['dir2'].append(val2)
            comptime[idx[0] + ',' + idx[1] + ':' + stages1[s1][idx[0]]['stage_name']['value']]['diff'].append(diff)
    if plot:
        plot_compare_time_stats(comptime, time=time, **kwargs)
    else:
        return comptime


def plot_compare_time_stats(comptime, time='', stages=None, ylim=4, figfile=None):
    if stages:
        stagenames, nstages = [], []
        for stage in stages:
            for key in comptime.keys():
                if stage in key:
                    stagenames.append(key.split(':')[1])
                    nstages.append(key)
        stages = nstages
    else:
        stages = list(comptime.keys())[1:]
        stagenames = [x.split(':')[1] for x in stages]
    ds = [comptime[x]['diff'] for x in stages]
    fig, ax = plt.subplots(1, 1, figsize=(16, 7))
    plt.subplots_adjust(left=0.06, right=0.98, bottom=0.20, top=0.96)
    ax.violinplot(ds, showmedians=True)
    ax.axhline(1, ls='--', color='black')
    ax.set_xticks([y + 1 for y in range(len(stages))], labels=stagenames, rotation=60, ha='right')
    ax.set_ylabel('Ratio of time PL2024/PL2023')
    ax.set_title('Violin plot per task for {}'.format(time))
    ax.set_ylim(0, ylim)
    if figfile:
        plt.savefig(figfile + '_violin.pdf', dpi=300)
        plt.close()
    # individual figures
    for stage, name in zip(stages, stagenames):
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        plt.subplots_adjust(left=0.14, right=0.98, bottom=0.08, top=0.94)
        ax.plot(comptime[stage]['dir1'], comptime[stage]['dir2'], 'o', color='black')
        xmax = max(comptime[stage]['dir1'])
        ax.plot(comptime[stage]['dir1'], comptime[stage]['dir2'], 'o', color='black')
        ax.plot([0, xmax], [0, xmax], '--')
        ax.set_xlabel('PL2024 - time (s)')
        ax.set_ylabel('PL2023 - time (s)')
        ax.set_title(stage + '--' + time)
        plt.savefig(figfile + '_' + stage + '.pdf')
        plt.close()


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


def __get_input__(inpt):
    if type(inpt) == str:
        bm = BenchMarkStats(inpt)
        if not bm.mouslist:
            raise IOError('No valid pipeline runs were found in {}'.format(inpt))
    else:
        bm = inpt
    return bm


def __get_parameter_comparison_list__(bm, eb_level=False, stage_level=False):
    pcl = ['proposal_code', 'total_time']
    if eb_level:
        pcl.append('flagdata_percentage')
    if stage_level:
        pcl.append('qa_score')
    return bm.get_keywords()
