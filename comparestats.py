# this is a place where all the comparison code lives. This could be
# comparison between single files or between a list of files.
from benchmarkstats import get_stages, BenchMarkStats
import matplotlib.pyplot as plt
import csv
import plstats
import numpy as np
import glob


def compare_benchmarks(input1, input2, parameter_comparison_list=None, **kwargs):
    bm1, bm2 = __get_input__(input1), __get_input__(input2)
    if not parameter_comparison_list:
        pcl = __get_parameter_comparison_list__(bm1, **kwargs)
    else:
        pcl = parameter_comparison_list
    return pcl


def compare_pldirs(pldir1, pldir2, **kwargs):
    """
    Function to compare all the aquareports within the given pipeline directories

    The function assumes that the aquareport are located within the working directory of the directory with the
    general structure of project/SOUS*/GOUS*/MOUS*/working. It will take the list af projects in the first directory
    and check for existence in the second directory. This function can take in all the keywords that c
    compare_aquareports can take in
    :param pldir1: first directory with pipeline runs
    :param pldir2: second directory with pipeline runs
    :return: A CSV file will be written
    """
    projects = np.unique([x.split('/')[-2].split('_')[0] for x in sorted(glob.glob(pldir1+'/*.*/'))])
    for proj in projects:
        plist = glob.glob('{0}/{1}_*/S*/G*/M*/working'.format(pldir1, proj))
        if len(plist) == 0:
            full_dir = glob.glob('{0}/{1}'.format(pldir1, proj))[0].split('/')[-1]
            print('{0} is not a valid project with an aquareport in the first directory.'.format(full_dir))
            continue
        else:
            pl1 = plist[-1]
        plist = glob.glob('{0}/{1}_*/S*/G*/M*/working'.format(pldir2, proj))
        if len(plist) == 0:
            print('{0} is not a valid project in the second directory.'.format(proj))
            continue
        else:
            pl2 = plist[-1]
        compare_plstats(pl1, pl2, **kwargs)


def compare_plstats(pl1, pl2, csvfile=None, stagemap=None, selection=None, diff_only=False, limit=1E-5,
                    compact=False):
    """ Creates a diff dictionary with the differences between the parameters. The parameters that are checked are
    (partly) hard-coded into this function. The result can also create a csv file of the output (if set).

    :param pl1: Either the location of the first working directory to be compared or a PLStats object
    :param pl2: Either the location of hte Second working directory to be compared or a PLStats object
    :param stagemap: ordered list of comparison between stages. If not set, the code will make a guess that can
    go quite wrong if the imaging stages between the pipeline runs have changed
    :param csvfile: If set, the diff dictionary will be translated into a csvfile, no diff dictionary will be returned
    :param selection: Selection of outputs to plot. Currently only works for top level products, so not very useful
    :param diff_only: If set, only the differences that fall above the limit set by the keyword limit will be shown
    :param limit: Set the percentage limit in order to include the keyword in the output. For instnance a limit of
    0.05 means that any absolute change greater than 5 percent will be included in the diff_only output
    :param compact: If set, a compact version will be returned with the information on a single line.
    :return: diff dictionary or None
    """
    # Load the data
    print(pl1, pl2)
    pl1 = plstats.PLStats.from_workingdir(pl1) if type(pl1) is str else pl1
    pl2 = plstats.PLStats.from_workingdir(pl2) if type(pl2) is str else pl2
    diff_dict = {'MOUS': {}, 'STAGE': {}, 'TARGET': {}, 'FLUX': {}}
    # get MOUS level parameters
    pcl = __get_parameter_comparison_list__(pl1, level='MOUS')
    if 'proposal_code' in pcl:
        pcl.sort()
        pcl.remove('proposal_code')
        pcl.insert(0, 'proposal_code')
    for key in pcl:
        if key not in pl2.mous:
            print('key: {} not preent in pl2 {}'.format(key, pl1.mous['proposal_code']))
        if 'value' not in pl1.mous[key]:
            print('value not preent in key: {}'.format(key))
            continue
        val1 = pl1.mous[key]['value'] if key in pl1.mous.keys() else '---'
        val2 = pl2.mous[key]['value'] if key in pl2.mous.keys() else '---'
        __add2diff__(diff_dict, 'MOUS', key, val1, val2, limit, diff_only)
    # get stage info (QA scores and timing)
    if stagemap is None:
        stagemap = __get_stagemap__(pl1, pl2)
    for stage in stagemap:
        for k in ['qa_score', 'task_time', 'result_time', 'total_time']:
            key = stage[0] + ':' + pl1.mous['STAGE'][stage[0]]['stage_name']['value'] + ':' + k
            val1 = pl1.mous['STAGE'][stage[0]][k]['value']
            val1 = float(val1) if val1 != 'None' else -1.
            val2 = pl2.mous['STAGE'][stage[1]][k]['value']
            val2 = float(val2) if val2 != 'None' else -1.
            __add2diff__(diff_dict, 'STAGE', key, val1, val2, limit, diff_only)
    # get sensitivity info
    for target in pl1.mous['TARGET']:
        if target not in pl2.mous['TARGET']:
            continue
        if 'SPW' not in pl1.mous['TARGET'][target]:
            continue
        for spw in pl1.mous['TARGET'][target]['SPW']:
            for k in pl1.mous['TARGET'][target]['SPW'][spw]:
                if k not in pl2.mous['TARGET'][target]['SPW'][spw]:
                    continue
                new_k_name = ':'.join(k.split('_')[2:])
                key = target + ':' + spw + ':' + new_k_name
                val1 = float(pl1.mous['TARGET'][target]['SPW'][spw][k]['value'])
                val2 = float(pl2.mous['TARGET'][target]['SPW'][spw][k]['value'])
                __add2diff__(diff_dict, 'TARGET', key, val1, val2, limit, diff_only)
    # get flux info
    for flux in pl1.mous['FLUX']:
        if flux not in pl2.mous['FLUX']:
            continue
        for spw in pl1.mous['FLUX'][flux]['SPW']:
            for asdm in pl1.mous['FLUX'][flux]['SPW'][spw]:
                key = flux + ':' + spw + ':' + asdm
                val1 = (float(pl1.mous['FLUX'][flux]['SPW'][spw][asdm]['fitted_value'])
                        if pl1.mous['FLUX'][flux]['SPW'][spw][asdm]['fitted_value'] != -1.0 else
                        float(pl1.mous['FLUX'][flux]['SPW'][spw][asdm]['value']))
                val2 = (float(pl2.mous['FLUX'][flux]['SPW'][spw][asdm]['fitted_value'])
                        if pl2.mous['FLUX'][flux]['SPW'][spw][asdm]['fitted_value'] != -1.0 else
                        float(pl2.mous['FLUX'][flux]['SPW'][spw][asdm]['value']))
                __add2diff__(diff_dict, 'FLUX', key, val1, val2, limit, diff_only)
    # output
    if csvfile is not None:
        if compact:
            diff_dict = {**diff_dict['MOUS'], **diff_dict['STAGE'], **diff_dict['FLUX'], **diff_dict['TARGET']}
            # clean up
            for key in list(diff_dict.keys()):
                if 'task_time' in key or 'result_time' in key:
                    del diff_dict[key]
            __convdiff2csv__(diff_dict, csvfile, comment=None)
        else:
            comm = {'MOUS': 'Mous level properties', 'STAGE': 'Pipeline Stage',
                    'FLUX': 'Flux measurements per spw for calibrator', 'TARGET': 'Imaging characteristics for target'}
            if selection is None:
                selection = diff_dict.keys()
            for item in selection:
                if item in ['STAGE']:
                    subs = ['qa_score', 'total_time']
                elif item in ['FLUX', 'TARGET']:
                    subs = list(set([x.split(':')[0] for x in diff_dict[item]]))
                else:
                    subs = ['']
                for sub in subs:
                    __convdiff2csv__(diff_dict[item], csvfile, sub=sub, comment=comm[item] + ':' + sub)
    else:
        return diff_dict


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


def __get_parameter_comparison_list__(pl, **kwargs):
    pcl = pl.get_keywords(**kwargs)
    [pcl.pop(pcl.index(x)) for x in ['EB', 'SPW', 'TARGET', 'STAGE', 'spw_list', 'eb_list', 'target_list', 'FLUX']]
    return pcl


def __get_stagemap__(pl1, pl2):
    s1numbers = [x for x in pl1.mous['STAGE'].keys()]
    s1names = [pl1.mous['STAGE'][x]['stage_name']['value'] for x in pl1.mous['STAGE'].keys()]
    s2numbers = [x for x in pl2.mous['STAGE'].keys()]
    s2names = [pl2.mous['STAGE'][x]['stage_name']['value'] for x in pl2.mous['STAGE'].keys()]
    tasklist = []
    for s1number, s1name in zip(s1numbers, s1names):
        try:
            idx2 = s2names.index(s1name)
            tasklist.append((s1number, s2numbers.pop(idx2)))
            s2names.pop(idx2)
        except ValueError:
            continue
    return tasklist


def __calc_diff__(val1, val2):
    if type(val1) == str and type(val2) == str:
        diff = val1 + ' -- ' + val2 if val1 != val2 else '---'
    elif type(val1) == float and type(val2) == float:
        diff = val2 - val1
    elif type(val1) == int and type(val2) == int:
        diff = int(val2 - val1)
    elif type(val1) == list and type(val2) == list:
        diff = 'Lists are different' if val1 != val2 else '---'
    else:
        print('unknown type for comparison, will not calculate difference.')
        print('Types are: {} and {}'.format(type(val1), type(val2)))
        diff = '---'
    return diff


def __calc_pdiff__(val1, val2):
    if type(val1) == str and type(val2) == str:
        pdiff = '---'
    elif type(val1) == float and type(val2) == float:
        pdiff = (val2 - val1) / val1 if val1 != 0 else -1
    elif type(val1) == int and type(val2) == int:
        pdiff = 0
    elif type(val1) == list and type(val2) == list:
        pdiff = '---'
    else:
        print('unknown type for comparison, will not calculate percentage difference.')
        print('Types are: {} and {}'.format(type(val1), type(val2)))
        pdiff = '---'
    return pdiff


def __convdiff2csv__(diff, csvfile, sub='', comment=None):
    with open(csvfile, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        if comment is not None:
            csvwriter.writerow([comment])
        csvwriter.writerow([name for name in diff if sub in name])
        csvwriter.writerow([diff[name]['PL1'] for name in diff if sub in name])
        csvwriter.writerow([diff[name]['PL2'] for name in diff if sub in name])
        csvwriter.writerow([diff[name]['diff'] for name in diff if sub in name])
        csvwriter.writerow([])


def __add2diff__(diff_dict, key1, key2, val1, val2, limit, diff_only):
    diff, pdiff = __calc_diff__(val1, val2), __calc_pdiff__(val1, val2)
    diff_dict[key1][key2] = {'PL1': val1, 'PL2': val2, 'diff': diff, 'pdiff': pdiff}
    if type(diff) == str:
        if diff_only and diff == '---' and key2 != 'proposal_code':
            del diff_dict[key1][key2]
    elif type(diff) == float:
        if diff_only and abs(pdiff) < limit:
            del diff_dict[key1][key2]
    elif type(diff) == int:
        if diff_only and abs(pdiff) < limit:
            del diff_dict[key1][key2]
    else:
        return
