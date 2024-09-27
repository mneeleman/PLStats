import xml.etree.ElementTree as ElT


def load_aquareport(arfile):
    ar = ElT.parse(open(arfile)).getroot()
    mous = {}
    get_projectinfo(ar, mous)

    return mous


def get_projectinfo(ar, mous):
    ps = ar.find('ProjectStructure')
    mous['proposal_code'] = {'value': list(ar.iter('ProposalCode'))[0].text}
    mous['pipeline_recipe'] = {'value': list(ar.iter('ProcessingProcedure'))[0].text}
    mous['project_id'] = {'value': list(ar.iter('OusEntityId'))[0].text}
    mous['mous_uid'] = {'value': list(ar.iter('OusStatusEntityId'))[0].text}
    mous['total_time'] = {'value': list(ar.iter('ProcessingTime'))[0].text}
    mous['casa_version'] = {'value': list(ar.iter('CasaVersion'))[0].text}
    mous['pipeline_version'] = {'value': list(ar.iter('PipelineVersion'))[0].text}
