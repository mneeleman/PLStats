import glob
import numpy as np
import os
from astropy.io import fits
import json
try:
    a = ia.open()
    a.done()
except NameError:
    from casatools import image as ia


def benchmark_make_suppl_statfile(bmdir, outdir='./', overwrite=False):
    """
    simple wrapper program to get the supplemental stats file for a whole directory (e.g., benchmark run).
    :param bmdir: main directory that contains the individual pl_runs
    :param outdir: direcoty that contains the output files
    :param overwrite: if set, it will overwrite the existing outputfile
    :return: None
    """
    projects = list(np.unique([x.split('/')[-2] for x in sorted(glob.glob(bmdir + '/*.*/'))]))
    for pldir in projects:
        print('{0}: {1} of {2}'.format(pldir, projects.index(pldir) + 1, len(projects)))
        make_suppl_statfile(bmdir + '/' + pldir, overwrite=overwrite, outdir=outdir)


def make_suppl_statfile(workingdir, return_mous=False, overwrite=False, outdir=None, use_product_folder=False):
    """
    creates a supplemental stats file in JSON form with additional information that is not prenst in the
    current stats file
    :param workingdir: String pointing to the working directory
    :param return_mous: if set, it will return the dictionary in addition to writing it to file
    :param overwrite: if set, it will overwrite the existing outputfile
    :param outdir: The directory to put the output into. The default is the current (working directory)
    :param use_product_folder: if set, will use the fits files in the product foler instead of the .image files
    :return: dictionary of the supplemental stats (optional)
    """
    # define the naming of the suppl. stats file. This is done first, to see if the file exists, and if so,
    # the function does not need to be run.
    workingdir = workingdir + '/' if workingdir[-1] != '/' else workingdir
    outdir = workingdir if outdir is None else outdir
    outdir = outdir + '/' if outdir[-1] != '/' else outdir
    try:  # will try to create a more meaningful name, if this fails, will default to non-descriptive name
        mousname = glob.glob(workingdir + '/pipeline_stats_*.json')[0].split('/')[-1][15:-5]
        timestamp = glob.glob(workingdir + '/pipeline-*T*.timetracker.json')[-1].split('/')[-1].split('.')[0][9:]
        jsonfile = 'pipeline-suppl_stats-' + mousname + '-' + timestamp + '.json'
    except NameError:
        jsonfile = 'pipeline-suppl_stats.json'
    if os.path.exists(outdir + jsonfile) and overwrite is False:
        print('make_suppl_statfile: file: {} already exists will not overwrite it'.format(outdir + jsonfile))
        return
    # create the dictionary
    mous = {'EB': {}, 'TARGET': {}}
    scrape_flagfiles(mous, workingdir)
    im_list, image_path = __get_imagelist__(workingdir, use_product_folder=use_product_folder)
    for image in im_list:
        get_imagestats(mous, image_path + image)
    # output the file and optionally return the dictionary
    with open(outdir + jsonfile, 'w') as fp:
        json.dump(mous, fp)
    if return_mous:
        return mous


def scrape_flagfiles(mous, workingdir):
    flag_files = glob.glob('{}*.flagtemplate.txt'.format(workingdir))
    if not flag_files:
        print('__scrape_flagfiles__: no flagging files in working directory: {}'.format(workingdir))
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
    header, im, im_pbcor, im_pb, im_mask = __load_images__(image)
    if header['OBJECT'].rstrip() not in mous['TARGET']:
        mous['TARGET'][header['OBJECT']] = {}
    im_rms, im_mad = __get_rms__(im, im_pb, im_mask)
    im_max = __get_max__(im)
    if header['SPW'].rstrip() not in mous['TARGET'][header['OBJECT']]:
        mous['TARGET'][header['OBJECT']][header['SPW']] = {}
    t_im = mous['TARGET'][header['OBJECT']][header['SPW']]
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_bmaj'] = {'value': header['BMAJ'] * 3600}
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_bmin'] = {'value': header['BMIN'] * 3600}
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_bpa'] = {'value': header['BPA']}
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_rms'] = {'value': im_rms}
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_mad'] = {'value': im_mad}
    t_im['makeimages_science_' + header['SPECMODE'].rstrip() + '_max'] = {'value': im_max}


def __load_images__(image):
    if image[-5:] == '.fits':
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
        casa_im = ia().newimagefromfile(image)
        header = casa_im.fitsheader()
        im = np.squeeze(casa_im.getchunk())
        casa_im.done()
        casa_im = ia().newimagefromfile(image + '.pbcor')
        im_pbcor = np.squeeze(casa_im.getchunk())
        casa_im.done()
        casa_im = ia().newimagefromfile(image.replace('image', 'pb'))
        im_pb = np.squeeze(casa_im.getchunk())
        casa_im.done()
        if os.path.exists(image.replace('image', 'mask')):
            casa_im = ia().newimagefromfile(image.replace('image', 'mask'))
            im_mask = np.squeeze(casa_im.getchunk()).astype(bool)
            casa_im.done()
        else:
            im_mask = np.zeros_like(im).astype(bool)
    return header, im, im_pbcor, im_pb, im_mask


def __get_imagelist__(workingdir, use_product_folder=False):
    if use_product_folder:
        imlist = glob.glob(workingdir + '../products/*_sci*.pbcor.fits')
        if not imlist:
            print('__get_imagelist__: no images in {}'.format(workingdir + '../products/*_sci*.pbcor.fits'))
            image_list = []
            return image_list, ''
        else:
            image_list = [x.split('/')[-1] for x in imlist if 'tt1.pbcor.fits' not in x]
            return image_list, '/'.join(imlist[0].split('/')[:-1]) + '/'
    else:
        imlist = glob.glob(workingdir + '*_sci*.image')
        image_list = [x.split('/')[-1] for x in imlist]
        return image_list, workingdir


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
