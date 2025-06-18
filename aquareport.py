import xml.etree.ElementTree as ElT
import json


def load_aquareport(arfile, timefile=None):
    ar = ElT.parse(open(arfile)).getroot()
    mous = {}
    get_projectinfo(ar, mous)
    get_stageinfo(ar, mous, timefile=timefile)
    get_sensitivityinfo(ar, mous)
    get_fluxinfo(ar, mous)
    return mous


def get_projectinfo(ar, mous):
    mous['proposal_code'] = {'value': list(ar.iter('ProposalCode'))[0].text}
    mous['pipeline_recipe'] = {'value': list(ar.iter('ProcessingProcedure'))[0].text}
    mous['project_id'] = {'value': list(ar.iter('OusEntityId'))[0].text}
    mous['mous_uid'] = {'value': list(ar.iter('OusStatusEntityId'))[0].text}
    mous['total_time'] = {'value': list(ar.iter('ProcessingTime'))[0].text}
    mous['casa_version'] = {'value': list(ar.iter('CasaVersion'))[0].text}
    mous['pipeline_version'] = {'value': list(ar.iter('PipelineVersion'))[0].text}


def get_stageinfo(ar, mous, timefile=None):
    stageinfo = {}
    for c in list(ar.find('QaPerStage')):
        stageinfo[c.attrib['Number']] = {'stage_name': {'value': c.attrib['Name']},
                                         'qa_score': {'value': c.find('RepresentativeScore').attrib['Score']}}
    if timefile:
        timeinfo = __get_timefile__(timefile)
        for key in timeinfo['results']:
            if key not in stageinfo:
                stageinfo[key] = {'stage_name': {'value': 'unknown'}, 'qa_score': {'value': 'None'}}
            stageinfo[key]['task_time'] = {'value': timeinfo['tasks'][key]['seconds'], 'unit': 'second'}
            stageinfo[key]['result_time'] = {'value': timeinfo['results'][key]['seconds'], 'unit': 'second'}
            stageinfo[key]['total_time'] = {'value': timeinfo['total'][key]['seconds'], 'unit': 'second'}
    mous['STAGE'] = stageinfo


def get_sensitivityinfo(ar, mous):
    mous['TARGET'] = {}
    for sense in ar.iter('Sensitivity'):
        atb = sense.attrib
        if atb['ImageName'] == 'N/A':  # no useful info in these attributes
            continue
        if atb['Field'] not in mous['TARGET']:
            mous['TARGET'][atb['Field']] = {'SPW': {}}
        if atb['MsSpwId'] not in mous['TARGET'][atb['Field']]['SPW']:
            mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']] = {}
        imtype = atb['BwMode']
        caltype = 'REGCAL' if 'REGCAL' in atb['DataType'] else 'SELFCAL'
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_aggbw_' + caltype] =\
            {'value': atb['BandwidthHz'], 'unit': 'Hz'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_bmaj_' + caltype] =\
            {'value': atb['BeamMajArcsec'], 'unit': 'arcsec'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_bmin_' + caltype] =\
            {'value': atb['BeamMinArcsec'], 'unit': 'arcsec'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_bpa_' + caltype] =\
            {'value': atb['BeamPosAngDeg'], 'unit': 'degree'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_rms_' + caltype] =\
            {'value': atb['SensitivityJyPerBeam'], 'unit': 'Jy/bm'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_pbmax_' + caltype] =\
            {'value': atb['PbcorImageMaxJyPerBeam'], 'unit': 'Jy/bm'}
        mous['TARGET'][atb['Field']]['SPW'][atb['MsSpwId']]['makeimages_science_' + imtype + '_pbmin_' + caltype] =\
            {'value': atb['PbcorImageMinJyPerBeam'], 'unit': 'Jy/bm'}


def get_fluxinfo(ar, mous):
    mous['FLUX'] = {}
    for fm in ar.iter('FluxMeasurement'):
        atb = fm.attrib
        if atb['Field'] not in mous['FLUX']:
            mous['FLUX'][atb['Field']] = {'SPW': {}}
        if atb['MsSpwId'] not in mous['FLUX'][atb['Field']]['SPW']:
            mous['FLUX'][atb['Field']]['SPW'][atb['MsSpwId']] = {}
        if atb['Asdm'] not in mous['FLUX'][atb['Field']]['SPW'][atb['MsSpwId']]:
            mous['FLUX'][atb['Field']]['SPW'][atb['MsSpwId']][atb['Asdm']] = {'value': atb['FluxJy'], 'unit': 'Jy',
                                                                              'fitted_value': -1.0}
        else:
            mous['FLUX'][atb['Field']]['SPW'][atb['MsSpwId']][atb['Asdm']]['fitted_value'] = atb['FluxJy']


def __get_timefile__(timefile):
    return json.load(open(timefile, 'r'))
