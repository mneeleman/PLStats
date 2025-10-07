# this is a place where all the comparison code lives. This could be
# comparison between single files or between a list of files.
import matplotlib.pyplot as plt
import csv
import plstats
import numpy as np
import glob
from matplotlib.backends.backend_pdf import PdfPages


def compare_benchmarks(pldir1, pldir2, csvfile=None, plot_timecomparison=True, plot_timefile='timeplot.pdf',
                       return_diff=True, **kwargs):
    """
    Function to compare all the aquareports within the given pipeline directories

    The function assumes that the aquareport are located within the working directory of the directory with the
    general structure of project/SOUS*/GOUS*/MOUS*/working. It will take the list af projects in the first directory
    and check for existence in the second directory. This function can take in all the keywords that
    compare_plstats can take in
    :param pldir1: first directory with pipeline runs
    :param pldir2: second directory with pipeline runs
    :param csvfile: the name of the CSV file in which to write the output
    :param plot_timecomparison: makes simple plots of the timing differences between plruns
    :param plot_timefile: name of the timeplot
    :param return_diff: will return the difference dictionary
    :return: if csvfile is set, a CSV file will be written. Also, will return the diff dictionary 
             if return_diff is set
    """
    projects = np.unique([x.split('/')[-2].split('_')[0] for x in sorted(glob.glob(pldir1+'/*.*/'))])
    diff = []
    for proj in projects:
        print('running comparison script on project: {}'.format(proj))
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
        pl1 = plstats.PLStats.from_workingdir(pl1)
        pl2 = plstats.PLStats.from_workingdir(pl2)
        diff.append(compare_plstats(pl1, pl2, csvfile=csvfile, **kwargs))
    if plot_timecomparison:
        __plot_timecomp__(diff, plot_timefile.replace('.pdf', '_tasktime.pdf'), mode='task_time', pldir1=pldir1,
                          pldir2=pldir2)
        __plot_timecomp__(diff, plot_timefile.replace('.pdf', '_resulttime.pdf'), mode='result_time', pldir1=pldir1,
                          pldir2=pldir2)
    if return_diff:
        return diff


def compare_plstats(pl1, pl2, csvfile=None, stagemap=None, selection=None, diff_only=False, limit=1E-5,
                    compact=False, ignore_time=False):
    """ Creates a diff dictionary with the differences between the parameters. The parameters that are checked are
    (partly) hard-coded into this function. The result can also create a csv file of the output (if set).

    :param pl1: The first PLStats object
    :param pl2: The second PLStats object that will be compared to the first.
    :param stagemap: ordered list of comparison between stages. If not set, the code will make a guess that can
    go quite wrong if the imaging stages between the pipeline runs have changed
    :param csvfile: If set, the diff dictionary will be translated into a csvfile, no diff dictionary will be returned
    :param selection: Selection of outputs to plot. Currently only works for top level products, so not very useful
    :param diff_only: If set, only the differences that fall above the limit set by the keyword limit will be shown
    :param limit: Set the percentage limit in order to include the keyword in the output. For instnance a limit of
    0.05 means that any absolute change greater than 5 percent will be included in the diff_only output
    :param compact: If set, a compact version will be returned with the information on a single line
    :param ignore_time: If set, will ignore any per-stage timing information in the comparison 
    :return: diff dictionary or None
    """
    diff_dict = {'MOUS': {}, 'STAGE': {}, 'TARGET': {}, 'FLUX': {}}
    # get MOUS level parameters
    pcl = __get_parameter_comparison_list__(pl1, level='MOUS')
    if 'proposal_code' in pcl:
        pcl.sort()
        pcl.remove('proposal_code')
        pcl.insert(0, 'proposal_code')
    for key in pcl:
        if key not in pl2.mous:
            print('key: {} not present in pl2 {}'.format(key, pl1.mous['proposal_code']))
        if 'value' not in pl1.mous[key]:
            print('value not present in key: {}'.format(key))
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
            if k in pl1.mous['STAGE'][stage[0]]:
                val1 = pl1.mous['STAGE'][stage[0]][k]['value']
                val1 = float(val1) if val1 != 'None' else -1.
                val2 = pl2.mous['STAGE'][stage[1]][k]['value']
                val2 = float(val2) if val2 != 'None' else -1.
                __add2diff__(diff_dict, 'STAGE', key, val1, val2, limit, diff_only)
    # get sensitivity info
    target_list = [x for x in pl1.mous['TARGET']] if 'TARGET' in pl1.mous else []
    for target in target_list:
        if target not in pl2.mous['TARGET']:
            continue
        if 'SPW' not in pl1.mous['TARGET'][target]:
            continue
        if 'SPW' not in pl2.mous['TARGET'][target]:
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
    flux_list = [x for x in pl1.mous['FLUX']] if 'FLUX' in pl1.mous else []
    for flux in flux_list:
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
            diff_dict_c = {**diff_dict['MOUS'], **diff_dict['STAGE'], **diff_dict['FLUX'], **diff_dict['TARGET']}
            # clean up
            for key in list(diff_dict_c.keys()):
                if 'task_time' in key or 'result_time' in key:
                    del diff_dict_c[key]
                if 'total_time' in key and ignore_time:
                    del diff_dict_c[key]
            __convdiff2csv__(diff_dict_c, csvfile, comment=None)
        else:
            comm = {'MOUS': 'Mous level properties', 'STAGE': 'Pipeline Stage',
                    'FLUX': 'Flux measurements per spw for calibrator', 'TARGET': 'Imaging characteristics for target'}
            if selection is None:
                selection = diff_dict.keys()
            for item in selection:
                if item in ['STAGE']:
                    subs = ['qa_score']
                    if not ignore_time:
                        subs.append('total_time')
                elif item in ['FLUX', 'TARGET']:
                    subs = list(set([x.split(':')[0] for x in diff_dict[item]]))
                else:
                    subs = ['']
                for sub in subs:
                    __convdiff2csv__(diff_dict[item], csvfile, sub=sub, comment=comm[item] + ':' + sub)
    return diff_dict


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


def __plot_timecomp__(diff, plot_timefile, mode='task_time', pldir1='pl1', pldir2='pl2'):
    stages = [x for x in diff[0]['STAGE'].keys() if mode in x]
    stagenames = [':'.join(x.split(':')[0:2]) for x in diff[0]['STAGE'].keys() if mode in x]
    n_stages = len(stages)
    n_pages = int(np.ceil(n_stages / 12))
    with PdfPages(plot_timefile) as pdf:
        idx = 0
        ds = []
        for page in range(n_pages):
            fig, axs = plt.subplots(3, 4, figsize=(10, 8))
            plt.subplots_adjust(left=0.08, bottom=0.08, right=0.98, top=0.96, wspace=0.2, hspace=0.25)
            fig.text(0.52, 0.02, pldir1 + ' Time (s)', ha='center')
            fig.text(0.02, 0.52, pldir2 + ' Time (s)', rotation=90, va='center')
            for ax in axs.reshape(-1):
                c_stage = stages[idx]
                c_diff = [x['STAGE'][c_stage] for x in diff if c_stage in x['STAGE'].keys()]
                x, y = [x['PL1'] for x in c_diff], [y['PL2'] for y in c_diff]
                maxv, minv = np.max(x + y), np.min(x + y)
                ax.plot(x, y, 'o', color='steelblue')
                ax.plot([minv, maxv], [minv, maxv], ':', color='black')
                ax.set_yscale('log')
                ax.set_xscale('log')
                ax.set_title(stagenames[idx], fontsize=10)
                idx += 1
                ds.append(([ty / tx for tx, ty in zip(x, y)],
                           [ty / tx for tx, ty in zip(x, y) if np.abs(tx - ty) > 60],
                           np.median(x)))
            pdf.savefig()
            plt.close()
        for page in range(n_pages):
            fig, ax = plt.subplots(1, 1, figsize=(16, 7))
            plt.subplots_adjust(left=0.06, right=0.98, bottom=0.20, top=0.96)
            ax.violinplot([x[0] for x in ds[int(page * 12): int((page + 1) * 12)]], showmedians=True, side='low')
            ax.violinplot([x[1] if x[1] != [] else [1] for x in ds[int(page * 12): int((page + 1) * 12)]],
                          showmedians=True, side='high')
            ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc='steelblue'), plt.Rectangle((0, 0), 1, 1, fc='orange')],
                      labels=['All data', 'Data where difference is >60s'], loc='upper right')
            ax.axhline(1, ls='--', color='black')
            ax.set_xticks([y + 1 for y in range(12)], labels=stagenames[int(page * 12): int((page + 1) * 12)],
                          rotation=60, ha='right')
            ax.set_ylabel('Ratio of time {0} / {1}'.format(pldir2.split('/')[-1], pldir1.split('/')[-1]))
            # ax.set_title('Violin plot per task for {}'.format(time))
            ax.set_ylim(0, 4)
            pdf.savefig()
            plt.close()
    return ds
