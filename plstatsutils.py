# code to read in the json stats files and provide basic manipulation
import json


class StatsObject:
    def __init__(self, jsonfile):
        self.file = jsonfile
        tempjson = json.load(open(jsonfile, 'r'))
        self.header = tempjson['header']
        self.name = jsonfile.split('/')[-3].split('_')[0]
        mouslist = [x for x in list(tempjson.keys()) if 'uid' in x]
        if len(mouslist) != 1:
            raise ValueError('There should be a unique MOUS in each json file, but found: {}'.format(mouslist))
        self.data = tempjson[mouslist[0]]
        self.data['eb_list'] = {'value': list(self.get_keywords(level='EB'))}
        self.data['spw_list'] = {'value': list(self.get_keywords(level='SPW'))}

    def get_keywords(self, level='MOUS', sublevel='', ignore=None):
        if level == 'MOUS':
            keywords = list(self.data.keys())
        elif sublevel == '':
            keywords = list(self.data[level].keys())
        else:
            keywords = list(self.data[level][sublevel].keys())
        if ignore:
            if type(ignore) == list:
                for x in ignore:
                    keywords.pop(keywords.index(x))
            else:
                keywords.pop(keywords.index(ignore))
        return keywords
