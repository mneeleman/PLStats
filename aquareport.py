import xml.etree.ElementTree as ElT


def load_aquareport(arfile):
    ar = ElT.parse(open(arfile)).getroot()
    mous = {}
    get_projectinfo(ar, mous)
    
    return mous


def get_projectinfo(ar, mous):
    ps = ar.find('ProjectStructure')
    mous['proposal_code'] = list(ar.iter('ProposalCode'))[0].text
    mous['pipeline_recipe'] = list(ar.iter('ProcessingProcedure'))[0].text
    mous['project_uid'] = list(ar.iter('OusEntityId'))[0].text
    mous['mous_uid'] = list(ar.iter('OusStatusEntityId'))[0].text
    mous['total_time'] = list(ar.iter('ProcessingTime'))[0].text
    mous['casa_version'] = list(ar.iter('CasaVersion'))[0].text
    mous['pipeline_version'] = list(ar.iter('PipelineVersion'))[0].text
