import os
import sys
import glob

from astropy.io.fits.util import first

from plstats import PLStats
from comparestats import create_diff_dict
from copy import deepcopy as dc
import numpy as np
from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qtagg import FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure
import json


class ApplicationWindow(QtWidgets.QWidget):

    def __init__(self, input1, uid_names=None):
        # overall image parameters of gui window
        super().__init__()
        self.left = 20
        self.top = 50
        self.width = 1500
        self.height = 1000
        # defining the data
        self.input1 = input1.strip()
        self.statslist = []
        self.newstatslist = []
        if self.input1[-4:] == 'json':
            print('Assuming this is a JSON diff file')
            self.load_json()
        else:
            print('Assuming this is a directory with pipeline-stats and pipeline_suppl-stats files')
            self.load_cf(uid_names=uid_names)
        # create the headers from the first stats file
        self.mousheaders = self.get_keywords(level='MOUS', ignore=['EB', 'SPW', 'TARGET', 'FLUX', 'STAGE'])
        self.ebheaders = self.get_keywords(level='EB')
        self.spwheaders = self.get_keywords(level='SPW')
        self.targetheaders = self.get_keywords(level='TARGET')
        self.imageheaders = self.get_keywords(level='IMAGE')
        self.mousheadsel = []
        self.ebheadsel = []
        self.spwheadsel = []
        self.targetheadsel = []
        self.imageheadsel = []
        # create the GUI layout
        self.table = QtWidgets.QGroupBox('Table of data')
        self.nrows_label = QtWidgets.QLabel(self)
        self.resetbutton = QtWidgets.QPushButton('Reset table', self)
        self.message = QtWidgets.QLabel(self)
        self.expandcell = QtWidgets.QLabel(self)
        self.tableview = QtWidgets.QTableView()
        self.columntabs = QtWidgets.QTabWidget()
        self.dataselect = QtWidgets.QGroupBox('Select data')
        self.criterion1 = QtWidgets.QLineEdit()
        self.criterion2 = QtWidgets.QComboBox()
        self.criterion3 = QtWidgets.QLineEdit()
        self.criterion4 = QtWidgets.QLabel(self)
        self.dataselectbutton = QtWidgets.QPushButton('Apply Criterion', self)
        self.mousselect = QtWidgets.QGroupBox('MOUS level columns')
        self.ebselect = QtWidgets.QGroupBox('EB level columns')
        self.spwselect = QtWidgets.QGroupBox('SPW level columns')
        self.targetselect = QtWidgets.QGroupBox('TARGET level columns')
        self.imageselect = QtWidgets.QGroupBox('IMAGE level columns')
        self.mousselectlist = QtWidgets.QListWidget()
        self.mousselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.ebselectlist = QtWidgets.QListWidget()
        self.ebselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.spwselectlist = QtWidgets.QListWidget()
        self.spwselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.targetselectlist = QtWidgets.QListWidget()
        self.targetselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.imageselectlist = QtWidgets.QListWidget()
        self.imageselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.init_ui()
        self.new_window = []
        # populate the table to its initial state
        self.model = QtGui.QStandardItemModel(0, 0)
        self.reset_data()

    def init_ui(self):
        self.setWindowTitle(self.input1)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.get_table_layout()
        self.get_columnselect_layout()
        self.get_dataselect_layout()
        main_layout = QtWidgets.QGridLayout()
        main_layout.addWidget(self.table, 0, 0, 2, 2)
        main_layout.addWidget(self.columntabs, 0, 2, 1, 1)
        main_layout.addWidget(self.dataselect, 1, 2, 1, 1)
        main_layout.setColumnStretch(0, 10)
        main_layout.setRowStretch(0, 8)
        self.setLayout(main_layout)

    def get_dataselect_layout(self):
        self.criterion1.setPlaceholderText("Enter parameter name")
        self.criterion2.addItems(['==', '!=', '>=', '<=', 'contains'])
        self.criterion3.setPlaceholderText("Enter value")
        # self.dataselectbutton.clicked.connect(self.apply_criterion)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.criterion1)
        layout.addWidget(self.criterion2)
        layout.addWidget(self.criterion3)
        layout.addWidget(self.criterion4)
        layout.addWidget(self.dataselectbutton)
        self.dataselect.setLayout(layout)

    def get_columnselect_layout(self):
        self.columntabs.addTab(self.mousselect, "MOUS Level")
        self.columntabs.addTab(self.ebselect, "EB Level")
        self.columntabs.addTab(self.spwselect, "SPW Level")
        self.columntabs.addTab(self.targetselect, "TARGET Level")
        self.columntabs.addTab(self.imageselect, "IMAGE Level")
        zipped = zip([self.mousselect, self.ebselect, self.spwselect, self.targetselect, self.imageselect],
                     [self.mousselectlist, self.ebselectlist, self.spwselectlist, self.targetselectlist,
                      self.imageselectlist],
                     [self.mousselectbutton, self.ebselectbutton, self.spwselectbutton, self.targetselectbutton,
                      self.imageselectbutton],
                     [self.mousheaders, self.ebheaders, self.spwheaders, self.targetheaders, self.imageheaders])
        for select, selectlist, selectbutton, headers in zipped:
            selectlist.addItems(headers)
            selectlist.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            selectbutton.clicked.connect(self.update_table)
            layout = QtWidgets.QGridLayout()
            layout.addWidget(selectlist, 0, 0, 8, 1)
            layout.addWidget(selectbutton, 8, 0, 1, 1)
            select.setLayout(layout)

    def get_table_layout(self):
        self.resetbutton.clicked.connect(self.reset_data)
        self.tableview.clicked.connect(self.on_cell_clicked)
        self.message.setText('Table is showing show per MOUS entries')
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.tableview, 0, 0, 15, 15)
        layout.addWidget(self.nrows_label, 15, 0, 1, 1)
        layout.addWidget(self.resetbutton, 15, 1, 1, 1)
        layout.addWidget(self.message, 15, 2, 1, 1)
        layout.addWidget(self.expandcell, 16, 0, 1, 3)
        self.table.setLayout(layout)

    def update_table(self):
        if ((len(self.ebselectlist.selectedItems()) > 0 and len(self.spwselectlist.selectedItems()) > 0) or
                (len(self.ebselectlist.selectedItems()) > 0 and len(self.targetselectlist.selectedItems()) > 0) or
                (len(self.spwselectlist.selectedItems()) > 0 and len(self.targetselectlist.selectedItems()) > 0)):
            self.message.setText('Cannot select columns from EB, SPW and IMAGE level at the same time')
            return
        self.mousheadsel = [x.text() for x in self.mousselectlist.selectedItems()]
        if len(self.ebselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per EB entries')
            self.ebheadsel = [x.text() for x in self.ebselectlist.selectedItems()]
            self.update_perxtable('EB', 'n_EB', self.ebheadsel, 'eb_list')
        elif len(self.spwselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per SPW entries')
            self.spwheadsel = [x.text() for x in self.spwselectlist.selectedItems()]
            self.update_perxtable('SPW', 'n_spw', self.spwheadsel, 'spw_list')
        elif len(self.targetselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per TARGET entries')
            self.targetheadsel = [x.text() for x in self.targetselectlist.selectedItems()]
            self.update_perxtable('TARGET', 'n_target', self.targetheadsel, 'target_list')
        elif len(self.imageselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per IMAGE entries')
            self.imageheadsel = [x.text() for x in self.imageselectlist.selectedItems()]
            self.update_imagetable()
        else:
            self.message.setText('Table is showing per MOUS entries')
            self.update_moustable()

    def update_perxtable(self, xval, n_x, n_xheadsel, x_list):
        raise NotImplementedError('need to implement this')

    def update_imagetable(self):
        rowlength = 0
        for x in self.newstatslist:
            n_targets = len(list(x['TARGET'].keys())) - 1
            first_target = list([y for y in x['TARGET'].keys() if y != 'CF'])[0]
            n_sciencespw = len(list(x['TARGET'][first_target]['SPW'].keys()))
            rowlength += n_targets * n_sciencespw
        columnlength = len(self.imageheadsel) + len(self.mousheadsel) + 3
        firstmousdict = self.newstatslist[0]['MOUS']
        headers = ['mous_uid (str)', 'TARGET (str)', 'SPW (str)']
        header2 = ([x + ' (' + str(type(firstmousdict[x]['PL1']['value']))[8:-2] + ')' for x in self.mousheadsel] +
                   [x + ' (bool)' for x in self.imageheadsel])
        headers.extend(header2)
        self.model = QtGui.QStandardItemModel(rowlength, columnlength)
        self.model.setHorizontalHeaderLabels(headers)
        self.nrows_label.setText('Number of rows: {}'.format(rowlength))
        rownumber = 0
        for diff_strct in self.newstatslist:
            for target in diff_strct['TARGET']:
                for spw in diff_strct['TARGET'][target]['SPW']:
                    __set_data__(self.model, diff_strct['MOUS']['mous_uid']['PL1']['value'], rownumber, 0)
                    __set_data__(self.model, target, rownumber, 1)
                    __set_data__(self.model, spw, rownumber, 2)
                    for idx1, z1 in enumerate(self.mousheadsel):
                        if z1 == 'manual_flags':
                            __set_data__(self.model, str(diff_strct['MOUS'][z1]['PL2']['value']), rownumber, idx1 + 3)
                        else:
                            __set_data__(self.model, str(diff_strct['MOUS'][z1]['PL1']['value']), rownumber, idx1 + 3)
                    for idx2, z2 in enumerate(self.imageheadsel):
                        cf_value = (np.any(diff_strct['TARGET'][target]['SPW'][spw][z2]['CF']['value'])
                                    if diff_strct['TARGET'][target]['SPW'][spw][z2]['CF']['value'] != [] else '')
                        __set_data__(self.model, str(cf_value), rownumber, len(self.mousheadsel) + idx2 + 3)
                    rownumber += 1
        self.update_tableview()

    def update_tableview(self):
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(self.model)
        self.tableview.setModel(proxy)
        self.tableview.resizeColumnsToContents()
        self.tableview.horizontalHeader().setStretchLastSection(True)
        for x in range(self.model.columnCount()):
            if self.tableview.columnWidth(x) > 300:
                self.tableview.setColumnWidth(x, 300)
        self.tableview.setSortingEnabled(True)

    def reset_data(self):
        self.newstatslist = dc(self.statslist)
        self.mousheadsel = []
        self.ebheadsel = []
        self.spwheadsel = []
        self.targetheadsel = []
        self.mousselectlist.reset()
        for i in range(self.mousselectlist.count()):
            item = self.mousselectlist.item(i)
            if item.text() in ['manual_flags']:
                item.setSelected(True)
        self.ebselectlist.reset()
        self.spwselectlist.reset()
        self.targetselectlist.reset()
        self.imageselectlist.selectAll()
        self.update_table()

    def on_cell_clicked(self, index):
        row = index.row()
        column = index.column()
        mous_uid = self.model.itemFromIndex(self.model.index(row, 0)).text()
        target = self.model.itemFromIndex(self.model.index(row, 1)).text()
        spw = self.model.itemFromIndex(self.model.index(row, 2)).text()
        image = self.model.horizontalHeaderItem(column).text().split(' ')[0]
        manual_flags = ''
        for c in range(self.model.columnCount()):
            if 'manual_flags' in self.model.horizontalHeaderItem(c).text():
                manual_flags = self.model.itemFromIndex(self.model.index(row, c)).text()
                break
        self.expandcell.setText(self.model.itemFromIndex(self.model.index(row, column)).text())
        if ('rms' in image) or ('max' in image) or ('snr' in image):
            diff_dict = [x for x in self.newstatslist if x['MOUS']['mous_uid']['PL1']['value'] == mous_uid][0]
            diff_strct = diff_dict['TARGET'][target]['SPW'][spw][image]
            self.new_window = PlotWindow(diff_strct, image, manual_flags)
            self.new_window.show()

    def load_cf(self, uid_names=None):
        if type(uid_names) == str:
            uid_names = [uid_names]
        if uid_names is None:
            uid_names = np.unique([x.split('___')[-1].split('-')[0] + '-'
                                   for x in glob.glob(self.input1 + '/pipeline_stats*')])
        for uid_name in uid_names:
            print(uid_name)
            pl1 = PLStats.from_uidname(uid_name, searchdir=self.input1, index=0)
            pl2 = PLStats.from_uidname(uid_name, searchdir=self.input1, index=-1)
            diff = create_diff_dict(pl1, pl2)
            self.statslist.append(diff)
        if len(self.statslist) == 0:
            raise IOError('No json stat files found in: {}'.format(self.input1))
        self.newstatslist = dc(self.statslist)
        print('Done loading the diff structure')

    def load_json(self):
        with open(self.input1, 'r') as file:
            self.statslist = json.load(file)
            self.newstatslist = dc(self.statslist)

    def get_keywords(self, level, ignore=None):
        if level == 'IMAGE':
            first_target = list([x for x in self.statslist[0]['TARGET'].keys() if x != 'CF'])[0]
            print(first_target)
            first_spw = list(self.statslist[0]['TARGET'][first_target]['SPW'].keys())[0]
            keywords = list(self.statslist[0]['TARGET'][first_target]['SPW'][first_spw].keys())
        else:
            keywords = list(self.statslist[0][level].keys())
        if ignore:
            if type(ignore) == list:
                for x in ignore:
                    if x in keywords:
                        keywords.pop(keywords.index(x))
            else:
                if ignore in keywords:
                    keywords.pop(keywords.index(ignore))
        return keywords

def __set_data__(model, obj, row, col):
    newitem = QtGui.QStandardItem()
    if type(obj) == str:
        newitem.setData(obj, QtCore.Qt.DisplayRole)
    elif type(obj) == dict:
        if 'value' in obj.keys():
            newitem.setData(str(obj['value']), QtCore.Qt.DisplayRole)
        else:
            newitem.setData(str(obj), QtCore.Qt.DisplayRole)
    else:
        raise IOError('{}-type is not defined in __set_data__'.format(type(obj)))
    model.setItem(row, col, newitem)

class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self, diff_strct, image, manual_flags):
        super().__init__()
        self.setWindowTitle("image")
        self.setGeometry(50, 200, 1000, 1000)
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.canvas = FigureCanvas(Figure(figsize=(5, 5)))
        self.axes = self.canvas.figure.subplots(2, 1, sharex=True)
        self.axes[0].set_title(manual_flags)
        self.axes[0].plot(diff_strct['PL1']['value'], '-o', color='steelblue', label='PL1')
        self.axes[0].plot(diff_strct['PL2']['value'], '-o', color='orange', label='PL2')
        self.axes[0].set_ylabel(image)
        self.axes[0].legend()
        self.axes[1].set_ylabel('Percentage Difference')
        self.axes[1].set_xlabel('Channel')
        self.axes[1].plot(np.array(diff_strct['pdiff']['value']) * 100, '-o', color='maroon')
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.


def main():
    qapp = QtWidgets.QApplication(['1'])
    if len(sys.argv) == 1:
        print('comparestatsgui: taking current directory as input')
        appw = ApplicationWindow(os.getcwd())
    elif len(sys.argv) == 2:
        appw = ApplicationWindow(sys.argv[1])
    elif len(sys.argv) == 3:
        appw = ApplicationWindow(sys.argv[1], dir_type=sys.argv[2])
    elif len(sys.argv) == 4:
        appw = ApplicationWindow(sys.argv[1], dir_type=sys.argv[2], uid_names=sys.argv[3])
    else:
        raise IOError('Not a valid number or arguments')
    appw.show()
    sys.exit(qapp.exec())

if __name__ == '__main__':
    main()
