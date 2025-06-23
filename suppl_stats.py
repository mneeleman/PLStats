import glob
import numpy as np
import os
from astropy.io import fits
import json


def benchmark_make_suppl_statfile(bmdir, outdir='./'):
    """
    simple wrapper program to get the supplemental stats file for a whole directory (e.g., benchmark run).
    :param bmdir: main directory that contains the individual pl_runs
    :param outdir: direcoty that contains the output files
    :return: None
    """
    projects = list(np.unique([x.split('/')[-2] for x in sorted(glob.glob(bmdir + '/*.*/'))]))
    for pldir in projects:
        print('{0}: {1} of {2}'.format(pldir, projects.index(pldir) + 1, len(projects)))
        make_suppl_statfile(bmdir + '/' + pldir, jsonfile=outdir + '/' + pldir + '-suppl_stats.json')


def make_suppl_statfile(pldir, jsonfile=None, return_mous=False):
    """
    creates a supplemental stats file in JSON form with additional information that is not prenst in the
    current stats file
    :param pldir: String pointing to the pipeline run (not the working directory)
    :param jsonfile: String of the json file that is created. If not set, will use the last part of the pldir string
    :param return_mous: if set, it will return the dictionary in addition to writing it to file
    :return: dictionary of the supplemental stats (optional)
    """
    mous = {'EB': {}, 'TARGET': {}}
    scrape_flagfiles(mous, pldir)
    im_list, image_path = __get_imagelist__(pldir)
    for image in im_list:
        get_imagestats(mous, image_path + image)
    if jsonfile is None:
        plrun_name = pldir.split('/')[-1]
        jsonfile = plrun_name + '-suppl_stats.json'
    with open(jsonfile, 'w') as fp:
        json.dump(mous, fp)
    if return_mous:
        return mous


def scrape_flagfiles(mous, pldir):
    flag_files = glob.glob('{}/working/*.flagtemplate.txt'.format(pldir))
    if not flag_files:
        print('__scrape_flagfiles__: no flagging files in working directory')
        return
    for ff in flag_files:
        eb = ff.split('/')[-1].split('.')[0] + '.ms'
        if eb not in mous['EB']:
            mous['EB'][eb] = {}
        if 'flagdata_manual_flags' not in mous['EB'][eb]:
            mous['EB'][eb]['flagdata_manual_flags'] = \
                {'value': [line.strip() for line in open(ff) if not line.strip().startswith('#')]}
        else:
            mous['EB'][eb]['flagdata_manual_flags']['value'].extend([line.strip() for line in open(ff)
                                                                     if not line.strip().startswith('#')])


def get_imagestats(mous, image):
    usefits = True if image[-4:] == 'fits' else False
    header, im, im_pbcor, im_pb, im_mask = __load_images__(image, use_fits=usefits)
    header.remove('HISTORY', remove_all=True)
    if header['OBJECT'] not in mous['TARGET']:
        mous['TARGET'][header['OBJECT']] = {}
    im_rms, im_mad = __get_rms__(im, im_pb, im_mask)
    im_max = __get_max__(im)
    if header['SPW'] not in mous['TARGET'][header['OBJECT']]:
        mous['TARGET'][header['OBJECT']][header['SPW']] = {}
    t_im = mous['TARGET'][header['OBJECT']][header['SPW']]
    t_im['makeimages_science_' + header['SPECMODE'] + '_bmaj'] = {'value': header['BMAJ'] * 3600}
    t_im['makeimages_science_' + header['SPECMODE'] + '_bmin'] = {'value': header['BMIN'] * 3600}
    t_im['makeimages_science_' + header['SPECMODE'] + '_bpa'] = {'value': header['BPA']}
    t_im['makeimages_science_' + header['SPECMODE'] + '_rms'] = {'value': im_rms}
    t_im['makeimages_science_' + header['SPECMODE'] + '_mad'] = {'value': im_mad}
    t_im['makeimages_science_' + header['SPECMODE'] + '_max'] = {'value': im_max}


def __load_images__(image, use_fits=True):
    if use_fits:
        hdu = fits.open(image)
        header = hdu[0].header
        im_pbcor = np.squeeze(hdu[0].data)
        if '.tt0' in image:
            ext = '.tt0'
        else:
            ext = ''
        im_pb = np.squeeze(fits.open(image.replace(ext + '.pbcor', '.pb' + ext))[0].data)
        if os.path.exists(image.replace(ext + '.pbcor', 'mask')):
            im_mask = np.squeeze(fits.open(image.replace(ext + '.pbcor', '.mask'))[0].data).astype(bool)
        else:
            im_mask = np.zeros_like(im_pbcor).astype(bool)
        im = im_pbcor * im_pb
    else:
        raise NotImplementedError('Need to implement image load from .image files to bypass the use of fits')
    return header, im, im_pbcor, im_pb, im_mask


def __get_imagelist__(pldir):
    imlist = glob.glob(pldir + '/S*/G*/M*/products/*_sci*.pbcor.fits')
    if not imlist:
        print('__get_imagelist__: no images in {}'.format(pldir + '/S*/G*/M*/products/*_sci*.pbcor.fits'))
        image_list = []
    else:
        image_list = [x.split('/')[-1] for x in imlist if 'tt1.pbcor.fits' not in x]
    return image_list, '/'.join(imlist[0].split('/')[:-1]) + '/'


def __scrape_flagfiles__(pldir):
    flag_files = glob.glob('{}/working/*.flagtemplate.txt'.format(pldir))
    if not flag_files:
        print('__scrape_flagfiles__: no flagging files in working directory')
    strct = {}
    for ff in flag_files:
        eb = ff.split('/')[-1].split('.')[0] + '.ms'
        if eb not in strct:
            strct[eb] = [line.strip() for line in open(ff) if not line.strip().startswith('#')]
        else:
            strct[eb].extend([line.strip() for line in open(ff) if not line.strip().startswith('#')])
    return strct


def __get_rms__(im, im_pb, im_mask):
    if im.ndim == 2:
        pb_limit = __get_pblimit__(im_pb)
        im_pbmaskcomp = np.where((~im_mask) & (im_pb < pb_limit), im, np.nan)
        im_rms = [np.sqrt(np.nanmean(np.square(im_pbmaskcomp))).astype(np.float64)]
        im_mad = [np.nanmedian(np.abs(im_pbmaskcomp - np.nanmedian(im_pbmaskcomp))).astype(np.float64)]
    else:
        im_rms, temp_rmsidx, im_mad = [], [], []
        for channel in np.arange(im.shape[-3]):
            pb_limit = __get_pblimit__(im_pb[channel, :])
            im_pbmaskcomp = np.where(~im_mask[channel, :] & (im_pb[channel, :] < pb_limit), im[channel, :], np.nan)
            im_rms.append(np.sqrt(np.nanmean(np.square(im_pbmaskcomp))).astype(np.float64))
            im_mad.append(np.nanmedian(np.abs(im_pbmaskcomp - np.nanmedian(im_pbmaskcomp))).astype(np.float64))
    return im_rms, im_mad


def __get_max__(im):
    if im.ndim == 2:
        im_max = [np.nanmax(im).astype(np.float64)]
    else:
        im_max, temp_maxidx = [], []
        for channel in np.arange(im.shape[-3]):
            im_max.append(np.nanmax(im[channel, :]).astype(np.float64))
    return im_max


def __get_pblimit__(im_pb):
    if np.min(im_pb) > 1.1 * 0.3:
        pb_limit = 1.1 * np.min(im_pb)
    else:
        pb_limit = 0.33
    return pb_limit
