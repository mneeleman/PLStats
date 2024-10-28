import xml.etree.ElementTree as ElT
import json


def load_aquareport(arfile, timefile=None):
    ar = ElT.parse(open(arfile)).getroot()
    mous = {}
    get_projectinfo(ar, mous)
    get_stageinfo(ar, mous, timefile=timefile)
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
        timeinfo = load_timefile(timefile)
        for key in timeinfo['results']:
            if key not in stageinfo:
                stageinfo[key] = {'stage_name': {'value': 'unknown'}, 'qascore': {'value': None}}
            stageinfo[key]['task_time'] = {'value': timeinfo['tasks'][key]['seconds'], 'unit': 'second'}
            stageinfo[key]['result_time'] = {'value': timeinfo['results'][key]['seconds'], 'unit': 'second'}
            stageinfo[key]['total_time'] = {'value': timeinfo['total'][key]['seconds'], 'unit': 'second'}
    mous['STAGE'] = stageinfo
    return stageinfo


def load_timefile(timefile):
    return json.load(open(timefile, 'r'))
