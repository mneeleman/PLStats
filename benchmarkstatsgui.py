import os
import sys
import glob
from benchmarkstats import BenchMarkStats
from copy import deepcopy as dc
import numpy as np
from matplotlib.backends.qt_compat import QtWidgets, QtCore, QtGui


class ApplicationWindow(QtWidgets.QWidget):

    def __init__(self, directory):
        # overall image parameters of gui window
        super().__init__()
        self.left = 20
        self.top = 50
        self.width = 1500
        self.height = 1000
        # defining the data
        self.directory = directory
        self.benchmarkstats = BenchMarkStats(directory)
        self.newstatslist = []
        self.statslist = []
        self.reset_benchmarkstats = dc(self.benchmarkstats)
        self.mousheaders = self.benchmarkstats.get_keywords(ignore=['EB', 'SPW', 'TARGET'])
        self.ebheaders = self.benchmarkstats.get_keywords(level='EB')
        self.spwheaders = self.benchmarkstats.get_keywords(level='SPW')
        self.targetheaders = self.benchmarkstats.get_keywords(level='TARGET')
        self.mousheadsel = []
        self.ebheadsel = []
        self.spwheadsel = []
        self.targetheadsel = []
        # create the GUI layout
        self.table = QtWidgets.QGroupBox('Table of data')
        self.nrows_label = QtWidgets.QLabel(self)
        self.resetbutton = QtWidgets.QPushButton('Reset table', self)
        self.message = QtWidgets.QLabel(self)
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
        self.mousselectlist = QtWidgets.QListWidget()
        self.mousselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.spwselectlist = QtWidgets.QListWidget()
        self.spwselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.targetselectlist = QtWidgets.QListWidget()
        self.targetselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.ebselectlist = QtWidgets.QListWidget()
        self.ebselectbutton = QtWidgets.QPushButton('Apply Selection', self)
        self.init_ui()
        # populate the table to its initial state
        self.reset_data()

    def init_ui(self):
        self.setWindowTitle(self.directory)
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
        self.dataselectbutton.clicked.connect(self.apply_criterion)
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
        zipped = zip([self.mousselect, self.ebselect, self.spwselect, self.targetselect],
                     [self.mousselectlist, self.ebselectlist, self.spwselectlist, self.targetselectlist],
                     [self.mousselectbutton, self.ebselectbutton, self.spwselectbutton, self.targetselectbutton],
                     [self.mousheaders, self.ebheaders, self.spwheaders, self.targetheaders])
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
        self.message.setText('Table is showing show per MOUS entries')
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.tableview, 0, 0, 3, 3)
        layout.addWidget(self.nrows_label, 3, 0, 1, 1)
        layout.addWidget(self.resetbutton, 3, 1, 1, 1)
        layout.addWidget(self.message, 3, 2, 1, 1)
        self.table.setLayout(layout)

    def update_table(self):
        if ((len(self.ebselectlist.selectedItems()) > 0 and len(self.spwselectlist.selectedItems()) > 0) or
                (len(self.ebselectlist.selectedItems()) > 0 and len(self.targetselectlist.selectedItems()) > 0) or
                (len(self.spwselectlist.selectedItems()) > 0 and len(self.targetselectlist.selectedItems()) > 0)):
            self.message.setText('Cannot select columns from EB, SPW and IMAGE level at the same time')
            return
        self.mousheadsel = [x.text() for x in self.mousselectlist.selectedItems()]
        self.tweak_mousheadsel()
        if len(self.ebselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per EB entries')
            self.ebheadsel = [x.text() for x in self.ebselectlist.selectedItems()]
            self.update_perxtable('EB', self.ebheadsel)
        elif len(self.spwselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per SPW entries')
            self.spwheadsel = [x.text() for x in self.spwselectlist.selectedItems()]
            self.update_perxtable('SPW', self.spwheadsel)
        elif len(self.targetselectlist.selectedItems()) > 0:
            self.message.setText('Table is showing per TARGET entries')
            self.targetheadsel = [x.text() for x in self.targetselectlist.selectedItems()]
            self.update_perxtable('TARGET', self.targetheadsel)
        else:
            self.message.setText('Table is showing per MOUS entries')
            self.update_moustable()

    def update_moustable(self):
        self.nrows_label.setText('Number of rows: {}'.format(len(self.benchmarkstats.mouslist)))
        if len(self.benchmarkstats.mouslist) == 0:
            model = QtGui.QStandardItemModel()
        else:
            model = QtGui.QStandardItemModel(len(self.benchmarkstats.mouslist), len(self.mousheadsel))
            column_labels = []
            for idx1, x in enumerate(self.mousheadsel):
                values = self.benchmarkstats.get_values(x, value_only=True, return_list=True)
                column_labels.append(str(x) + ' (' + str(type(values[0]))[8:-2] + ')')
                for idx2, value in enumerate(values):
                    newitem = QtGui.QStandardItem()
                    newitem.setData(str(value), QtCore.Qt.DisplayRole)
                    model.setItem(idx2, idx1, newitem)
            model.setHorizontalHeaderLabels(column_labels)
        self.update_tableview(model)

    def update_perxtable(self, xval, n_xheadsel):
        rowlength = len(self.benchmarkstats.get_values(xval, return_list=True, flatten=True))
        self.nrows_label.setText('Number of rows: {}'.format(rowlength))
        columnlength = len(n_xheadsel) + len(self.mousheadsel) + 1
        model = QtGui.QStandardItemModel(rowlength, columnlength)
        column_labels = ['mous_uid (str)', xval + '(str)']
        values = self.benchmarkstats.get_values(n_xheadsel[0], flatten=True)
        for idx2, value in enumerate(values):
            newitem = QtGui.QStandardItem()
            newitem.setData(value.split('|')[0], QtCore.Qt.DisplayRole)
            model.setItem(idx2, 0, newitem)
            newitem = QtGui.QStandardItem()
            newitem.setData(value.split('|')[2], QtCore.Qt.DisplayRole)
            model.setItem(idx2, 1, newitem)
        for idx1, mouskey in enumerate(self.mousheadsel):
            values = self.benchmarkstats.get_values(mouskey, value_only=True, return_list=True, repeat=xval)
            column_labels.append(str(mouskey) + ' (' + str(type(values[0]))[8:-2] + ')')
            for idx2, value in enumerate(values):
                newitem = QtGui.QStandardItem()
                newitem.setData(str(value), QtCore.Qt.DisplayRole)
                model.setItem(idx2, idx1 + 2, newitem)
        for idx1, xkey in enumerate(n_xheadsel):
            values = self.benchmarkstats.get_values(xkey, level=xval, value_only=True, flatten=True, return_list=True)
            column_labels.append(str(xkey) + ' (' + str(type(values[0]))[8:-2] + ')')
            for idx2, value in enumerate(values):
                newitem = QtGui.QStandardItem()
                newitem.setData(str(value), QtCore.Qt.DisplayRole)
                model.setItem(idx2, idx1 + len(self.mousheadsel) + 2, newitem)
        model.setHorizontalHeaderLabels(column_labels)
        self.update_tableview(model)

    def update_tableview(self, model):
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(model)
        self.tableview.setModel(proxy)
        self.tableview.resizeColumnsToContents()
        self.tableview.horizontalHeader().setStretchLastSection(True)
        self.tableview.setSortingEnabled(True)

    def apply_criterion(self):
        if self.criterion1.text() in self.mousheaders:
            self.criterion4.setText('found header in MOUS')
            self.apply_mouscriterion()
        elif self.criterion1.text() in self.ebheaders:
            self.criterion4.setText('found header in EB')
            self.apply_xciterion('EB', 'n_EB', 'eb_list')
        elif self.criterion1.text() in self.spwheaders:
            self.criterion4.setText('found header in SPW')
            self.apply_xciterion('SPW', 'n_spw', 'spw_list')
        elif self.criterion1.text() in self.targetheaders:
            self.criterion4.setText('found header in TARGET')
            self.apply_xciterion('TARGET', 'n_target', 'target_list')
        else:
            self.criterion4.setText('{} Not a valid parameter name'.format(self.criterion1.text()))
            self.criterion1.setText('')

    def apply_mouscriterion(self):
        try:
            crit = type(self.newstatslist[0].mous[self.criterion1.text()]['value'])(self.criterion3.text())
        except ValueError:
            self.criterion4.setText('Inconsistent type for {}'.format(self.criterion1))
            return
        criterion = {'==': [x for x in self.newstatslist if x.mous[self.criterion1.text()]['value'] == crit],
                     '!=': [x for x in self.newstatslist if x.mous[self.criterion1.text()]['value'] != crit],
                     '>=': [x for x in self.newstatslist if x.mous[self.criterion1.text()]['value'] >= crit],
                     '<=': [x for x in self.newstatslist if x.mous[self.criterion1.text()]['value'] <= crit],
                     'contains': [x for x in self.newstatslist
                                  if self.criterion3.text() in str(x.mous[self.criterion1.text()]['value'])]}
        self.newstatslist = criterion[self.criterion2.currentText()]
        self.update_table()

    def apply_xciterion(self, xval, n_x, x_list):
        try:
            row = self.newstatslist[0].mous
            crit = type(row[xval][row[x_list]['value'][0]][self.criterion1.text()]['value'])(self.criterion3.text())
        except ValueError:
            self.criterion4.setText('Inconsistent type for {}'.format(self.criterion1))
            return
        projects = [x for x in self.newstatslist]
        for x in projects:
            tlist = []
            for y in x.mous[x_list]['value']:
                criterion = {'==': x.mous[xval][y][self.criterion1.text()]['value'] == crit,
                             '!=': x.mous[xval][y][self.criterion1.text()]['value'] != crit,
                             '>=': x.mous[xval][y][self.criterion1.text()]['value'] >= crit,
                             '<=': x.mous[xval][y][self.criterion1.text()]['value'] <= crit,
                             'contains': self.criterion3.text() in str(x.mous[xval][y]
                                                                       [self.criterion1.text()]['value'])}
                if not criterion[self.criterion2.currentText()]:
                    del x.mous[xval][y]
                    x.mous[n_x]['value'] -= 1
                else:
                    tlist.append(y)
            x.mous[x_list]['value'] = tlist
            if x.mous[n_x]['value'] <= 0:
                self.newstatslist.remove(x)
        self.update_table()

    def reset_data(self):
        self.benchmarkstats = self.reset_benchmarkstats
        self.mousheadsel = []
        self.ebheadsel = []
        self.spwheadsel = []
        self.targetheadsel = []
        self.mousselectlist.selectAll()
        self.ebselectlist.reset()
        self.spwselectlist.reset()
        self.targetselectlist.reset()
        self.update_table()

    def tweak_mousheadsel(self):
        if 'mous_uid' in self.mousheadsel:
            self.mousheadsel.insert(0, self.mousheadsel.pop(self.mousheadsel.index('mous_uid')))
        if 'proposal_code' in self.mousheadsel:
            self.mousheadsel.insert(0, self.mousheadsel.pop(self.mousheadsel.index('proposal_code')))


def main():
    if len(sys.argv) == 1:
        print('cfgui: taking current directory as input')
        qapp = QtWidgets.QApplication(['1'])
        appw = ApplicationWindow(os.getcwd())
    else:
        qapp = QtWidgets.QApplication(['1'])
        appw = ApplicationWindow(sys.argv[1])
    appw.show()
    sys.exit(qapp.exec())


if __name__ == '__main__':
    main()
