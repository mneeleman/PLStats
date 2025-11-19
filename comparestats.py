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
    else:
        return []


def compare_plstats(pl1, pl2, csvfile=None, stagemap=None, selection=None, diff_only=False, limit=1E-5,
                    compact=False, ignore_time=False):
    """ Creates a diff dictionary with the differences between the parameters. The parameters that are checked are
    (partly) hard-coded into this function. The result can also create a csv file of the output (if set).

    :param pl1: The first PLStats object
    :param pl2: The second PLStats object that will be compared to the first
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
    diff_dict = create_diff_dict(pl1, pl2, do_mous=True, do_stage=True, do_flux=True, do_target=True, limit=limit,
                                 diff_only=diff_only, stagemap=stagemap)
    # output
    if csvfile is not None:
        if compact:
            diff_dict_c = {**diff_dict['MOUS'], **diff_dict['STAGE'], **diff_dict['FLUX'], **diff_dict['TARGET']}
            if selection is None:
                selection = list(diff_dict_c.keys())
            # clean up
            for key in selection:
                if ('task_time' in key) or ('result_time' in key):
                    del diff_dict_c[key]
                if ('total_time' in key) and ignore_time:
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


def create_diff_dict(pl1, pl2, do_mous=True, do_eb=True, do_stage=True, do_target=True, do_cube=True, do_mfs=True,
                     do_cont=True, do_flux=True, diff_only=False, limit=1E-5, stagemap=None):
    """
    Code to create the difference structure.

    This is the main strcuture for the comparison codes. It is modular, so it can compare only sections
    of the pipeline structure by setting the appropriate keywords. This is done for speed, because any parameter that
    is not present in both pipelines will be ignored and not compared.
    """
    diff_dict = {'MOUS': {}, 'EB': {}, 'STAGE': {}, 'TARGET': {}, 'FLUX': {}, 'SPW': {}}
    # get MOUS level parameters
    if do_mous:
        pcl = __get_parameter_comparison_list__(pl1, level='MOUS')
        if 'proposal_code' in pcl:
            pcl.sort()
            pcl.remove('proposal_code')
            pcl.insert(0, 'proposal_code')
        for key in pcl:
            if key not in pl2.get_keywords('MOUS'):
                print('key: {} not present in pl2'.format(key))
            if 'value' not in pl1.mous[key]:
                print('value not present in key: {}'.format(key))
                continue
            val1 = pl1.mous[key]['value'] if key in pl1.mous.keys() else '---'
            val2 = pl2.mous[key]['value'] if key in pl2.mous.keys() else '---'
            __add2diff__(diff_dict, ['MOUS', key], val1, val2, limit, diff_only=diff_only)
    # per eb keywords
    if do_eb:
        for eb in pl1.mous['EB']:
            pcl_eb = pl1.mous['EB'][eb].keys()
            for key in pcl_eb:
                val1 = pl1.mous['EB'][eb][key]['value'] if key in pl1.mous['EB'][eb].keys() else '---'
                val2 = pl2.mous['EB'][eb][key]['value'] if key in pl2.mous['EB'][eb].keys() else '---'
                __add2diff__(diff_dict, ['EB', eb, key], val1, val2, limit, diff_only=diff_only,
                             less_than=False)
    # get stage info (QA scores and timing)
    if do_stage:
        if stagemap is None:
            stagemap = __get_stagemap__(pl1, pl2)
        for stage in stagemap:
            for k in ['qa_score', 'task_time', 'result_time', 'total_time']:
                key = stage[0] + ':' + pl1.mous['STAGE'][stage[0]]['stage_name']['value'] + ':' + k
                if k in pl1.mous['STAGE'][stage[0]] and k in pl2.mous['STAGE'][stage[1]]:
                    val1 = pl1.mous['STAGE'][stage[0]][k]['value']
                    val1 = float(val1) if val1 != 'None' else -1.
                    val2 = pl2.mous['STAGE'][stage[1]][k]['value']
                    val2 = float(val2) if val2 != 'None' else -1.
                    __add2diff__(diff_dict, ['STAGE', key], val1, val2, limit, diff_only=diff_only)
    # get sensitivity info
    if do_target:
        target_list = [x for x in pl1.mous['TARGET']] if 'TARGET' in pl1.mous else []
        for target in target_list:
            if target not in pl2.mous['TARGET']:
                continue
            diff_dict['TARGET'][target] = {'SPW': {}}
            # code to read in the aquareport sensitivties, should eventually be removed or integrated with below code
            # this wil actually likely crash with current structure.
            #if 'SPW' in pl1.mous['TARGET'][target] and 'SPW' in pl2.mous['TARGET'][target]:
            #    for spw in pl1.mous['TARGET'][target]['SPW']:
            #        if spw in ['n_images']:
            #            continue
            #        for k in pl1.mous['TARGET'][target]['SPW'][spw]:
            #            if k not in pl2.mous['TARGET'][target]['SPW'][spw]:
            #                continue
            #            new_k_name = ':'.join(k.split('_')[2:])
            #            key = target + ':' + spw + ':' + new_k_name
            #            val1 = float(pl1.mous['TARGET'][target]['SPW'][spw][k]['value'])
            #            val2 = float(pl2.mous['TARGET'][target]['SPW'][spw][k]['value'])
            #            __add2diff__(diff_dict, ['TARGET', key], val1, val2, limit, diff_only=diff_only)
            for spw in pl1.mous['TARGET'][target]:
                if 'value' in pl1.mous['TARGET'][target][spw].keys() or spw == 'SPW':
                    continue
                if spw not in pl2.mous['TARGET'][target]:
                    continue
                diff_dict['TARGET'][target]['SPW'][spw] = __image_strct__()
                if do_mfs:
                    __add_imstats__(pl1, pl2, target, spw, 'mfs', diff_dict)
                    __add_imstats__(pl1, pl2, target, spw, 'mfs_selfcal', diff_dict)
                if do_cube:
                    __add_imstats__(pl1, pl2, target, spw, 'cube', diff_dict)
                    __add_imstats__(pl1, pl2, target, spw, 'cube_selfcal', diff_dict)
                if do_cont:
                    __add_imstats__(pl1, pl2, target, spw, 'cont', diff_dict)
                    __add_imstats__(pl1, pl2, target, spw, 'cont_selfcal', diff_dict)
                # the following is broken
                # cf = np.any(np.concatenate([diff_dict['TARGET'][target]['SPW'][spw][x]['CF']['value']
                #                             for x in diff_dict['TARGET'][target]['SPW'][spw] if x != 'CF']))
                # diff_dict['TARGET'][target]['SPW'][spw]['CF'] = {'value': bool(cf)}
            # cf = [diff_dict['TARGET'][target]['SPW'][x]['CF']['value']
            #       for x in diff_dict['TARGET'][target]['SPW']]
            # diff_dict['TARGET'][target]['CF'] = {'value': bool(np.any(cf))}
    # get flux info
    if do_flux:
        flux_list = [x for x in pl1.mous['FLUX']] if ('FLUX' in pl1.mous) and ('FLUX' in pl2.mous) else []
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
                    __add2diff__(diff_dict, ['FLUX', key], val1, val2, limit, diff_only=diff_only)
    return diff_dict


def __get_parameter_comparison_list__(pl, **kwargs):
    pcl = pl.get_keywords(**kwargs)
    [pcl.pop(pcl.index(x)) for x in ['EB', 'SPW', 'TARGET', 'STAGE', 'spw_list', 'eb_list', 'target_list', 'FLUX']
     if x in pcl]
    return pcl


def __get_stagemap__(pl1, pl2):
    if 'STAGE' not in pl1.mous or 'STAGE' not in pl2.mous:
        return []
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


def __add_imstats__(pl1, pl2, target, spw, imtype, diff_dict, limit=None, diff_only=False):
    if limit is None:
        limit = [-1E-3, 5E-2, 5E-2]
    rms1 = (pl1.mous['TARGET'][target][spw]['makeimages_science_' + imtype + '_rms']['value']
            if 'makeimages_science_' + imtype + '_rms' in pl1.mous['TARGET'][target][spw] else '---')
    rms2 = (pl2.mous['TARGET'][target][spw]['makeimages_science_' + imtype + '_rms']['value']
            if 'makeimages_science_' + imtype + '_rms' in pl2.mous['TARGET'][target][spw] else '---')
    max1 = (pl1.mous['TARGET'][target][spw]['makeimages_science_' + imtype + '_max']['value']
            if 'makeimages_science_' + imtype + '_max' in pl1.mous['TARGET'][target][spw] else '---')
    max2 = (pl2.mous['TARGET'][target][spw]['makeimages_science_' + imtype + '_max']['value']
            if 'makeimages_science_' + imtype + '_max' in pl2.mous['TARGET'][target][spw] else '---')
    __add2diff__(diff_dict, ['TARGET', target, 'SPW', spw, imtype + '_rms'], rms1, rms2, limit[0],
                 diff_only=diff_only, less_than=True)
    __add2diff__(diff_dict, ['TARGET', target, 'SPW', spw, imtype + '_max'], max1, max2, limit[1],
                 diff_only=diff_only, less_than=False)
    if rms1 != '---' and max1 != '---' and rms2 != '---' and max2 != '---':
        sn1 = [x / y for x, y in zip(max1, rms1)]
        sn2 = [x / y for x, y in zip(max2, rms2)]
        __add2diff__(diff_dict, ['TARGET', target, 'SPW', spw, imtype + '_snr'], sn1, sn2, limit[2],
                     diff_only=diff_only, less_than=False)
        # adjust the SNR and MAX 'CF' based on the S/N > 10 criteria
        sncut = [True if x > 10 else False for x in sn1]
        diff_dict['TARGET'][target]['SPW'][spw][imtype + '_max']['CF']['value'] = list(
            np.logical_and(diff_dict['TARGET'][target]['SPW'][spw][imtype + '_max']['CF']['value'], sncut))
        diff_dict['TARGET'][target]['SPW'][spw][imtype + '_snr']['CF']['value'] = list(
            np.logical_and(diff_dict['TARGET'][target]['SPW'][spw][imtype + '_snr']['CF']['value'], sncut))


def __calc_diff__(val1, val2):
    if type(val1) == str and type(val2) == str:
        diff = val1 + ' -- ' + val2 if val1 != val2 else '---'
    elif type(val1) == float and type(val2) == float:
        diff = val2 - val1
    elif type(val1) == int and type(val2) == int:
        diff = int(val2 - val1)
    elif type(val1) == list and type(val2) == list:
        if val1 == [] and val2 == []:
            diff = '---'
        else:
            if len(val1) != len(val2):
                diff = 'Lists are different'
            else:
                diff = []
                for v1, v2 in zip(val1, val2):
                    diff.append(__calc_diff__(v1, v2))
    else:
        # print('unknown type for comparison, will not calculate difference.')
        # print('Types are: {} and {}'.format(type(val1), type(val2)))
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
        if val1 == [] and val2 == []:
            pdiff = '---'
        else:
            if len(val1) != len(val2):
                pdiff = 'Lists are different'
            else:
                pdiff = []
                for v1, v2 in zip(val1, val2):
                    pdiff.append(__calc_diff__(v1, v2))
    else:
        # print('unknown type for comparison, will not calculate percentage difference.')
        # print('Types are: {} and {}'.format(type(val1), type(val2)))
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


def __add2diff__(diff_dict, keys, val1, val2, limit, diff_only=False, ignore_str=True, less_than=True):
    if val1 == '---' and val2 == '---':
        return
    diff, pdiff = __calc_diff__(val1, val2), __calc_pdiff__(val1, val2)
    diff_strct = diff_dict
    for key in keys:
        if key == keys[-1]:
            diff_strct[key] = {'PL1': {'value': val1}, 'PL2': {'value': val2}, 'diff': {'value': diff},
                               'pdiff': {'value': pdiff}, 'CF': {'value': False}}
        else:
            if key not in diff_strct:
                diff_strct[key] = {}
            else:
                diff_strct = diff_strct[key]
    # Here do the comparison
    if type(diff) == str:
        if diff == '---':
            if diff_only and 'proposal_code' not in keys:
                return
        else:
            if not ignore_str:
                diff_strct[keys[-1]]['CF'] = {'value': True}
    elif type(diff) == float or type(diff) == int:
        if (pdiff > limit and less_than) or (pdiff < limit and not less_than):
            if diff_only:
                return
        else:
            diff_strct[keys[-1]]['CF'] = {'value': True}
    elif type(diff) == list:
        if type(diff[0]) == str:
            if not ignore_str:
                cf_list = [False if x == '---' else True for x in pdiff]
            else:
                cf_list = [False for _x in pdiff]
        else:
            if less_than:
                cf_list = [False if x > limit else True for x in pdiff]
            else:
                cf_list = [False if x < limit else True for x in pdiff]
        if diff_only:
            return
        else:
            diff_strct[keys[-1]]['CF'] = {'value': cf_list}


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

def __image_strct__():
    image_strct = {'mfs_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'mfs_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'mfs_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'mfs_selfcal_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'mfs_selfcal_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'mfs_selfcal_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                               'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_selfcal_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_selfcal_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cube_selfcal_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_selfcal_rms': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_selfcal_max': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}},
                   'cont_selfcal_snr': {'PL1': {'value': ['---']}, 'PL2': {'value': '---'}, 'diff': {'value': '---'},
                                        'pdiff': {'value': ['---']}, 'CF': {'value': []}}}
    return image_strct

# pl1 = PLStats.from_uidname('X3827_Xce-', searchdir='/stor/naasc/sciops/comm/mneelema/CF/Data/PLStats/QACF_20250909',
# index=0)
# pl2 = PLStats.from_uidname('X3827_Xce-', searchdir='/stor/naasc/sciops/comm/mneelema/CF/Data/PLStats/QACF_20250909',
# index=-1)
