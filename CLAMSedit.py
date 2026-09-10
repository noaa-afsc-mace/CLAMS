
#  add the UI files directory to the python path
import sys
import os

#  import packages
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6 import QtSql
from ui import ui_CLAMSEdit
import eventseldlg

class CLAMSEdit(QDialog, ui_CLAMSEdit.Ui_clamsEdit):

    def __init__(self, parent=None):
        #  initialize the superclasses
        super(CLAMSEdit, self).__init__(parent)
        self.setupUi(self)
        self.db=parent.db
        self.schema = parent.schema
        self.dataModel=QtSql.QSqlRelationalTableModel(self.dataView)
        #self.dataModel.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        #self.dataView.setSelectionMode(QAbstractItemView.SingleSelection)
        #self.dataView.setSelectionBehavior(QAbstractItemView.SelectRows)

        # some other data
        self.ship=parent.parent().ship
        self.survey=parent.parent().survey

        # get tables
        self.setupTables=['APPLICATION_CONFIGURATION','WORKSTATION_CONFIGURATION', 'PROTOCOL_DEFINITIONS',
                          'PROTOCOL_MAP', 'GEAR_OPTIONS','MEASUREMENT_SETUP', 'VALIDATIONS', 'CONDITIONALS',
                          'APPLICATION_EVENTS']
        self.setupTables.sort()
        self.lookupTables=[ 'GEAR_ACCESSORY_OPTIONS','GEAR_ACCESSORY_TYPES', 'GEAR_TYPES',  'EVENT_PARAMETERS',
                     'EVENT_PERFORMANCE', 'EVENT_TYPES', 'HAUL_WEIGHT_TYPES', 'DEVICE', 'MATURITY_DESCRIPTION',
                     'MATURITY_TABLES', 'MEASUREMENT_TYPES', 'PERSONNEL', 'SAMPLE_TYPES', 'SPECIES', 'SPECIMEN_PROTOCOL',
                     'WORKSTATIONS', 'GEAR_PARTITIONS', 'GEAR_TYPES', 'GEAR_PARTITION_TYPES', 'DEVICE_INTERFACES',
                     'GEAR', 'BASKET_TYPES', 'DEVICE_PARAMETERS','DEVICE_CONFIGURATION', 'VALIDATION_DEFINITIONS',
                     'CONDITIONAL_DEFINITIONS', 'SAMPLING_METHODS', 'SURVEY_PORTS', 'SURVEY_REGIONS','SURVEY_SEA_AREAS']
        self.lookupTables.sort()
        self.dataTables=['SHIP','SURVEY','EVENTS', 'EVENT_DATA', 'EVENT_STREAM_DATA','GEAR_ACCESSORY', 'SAMPLES', 'SAMPLE_DATA','BASKETS',
                          'SPECIMEN', 'MEASUREMENTS', 'OVERRIDE']
        self.dataTables.sort()
        self.tableTypes=['Setup', 'Lookup', 'Data']
        self.tableTypeBox.addItems(self.tableTypes)
        self.tableTypeBox.setCurrentIndex(-1)

        self.newRow=None
        self.editRow=None
        self.deleteRow=None
        # set up button colors
        self.red=QPalette()
        #self.red.setColor(QPalette.button,QColor(230,0, 0))
        #self.red.setColor(QPalette.buttonText,QColor(230, 0, 0))
        self.green=QPalette()
        #self.green.setColor(QPalette.button,QColor(0, 230, 0))
        #self.green.setColor(QPalette.buttonText,QColor(0, 230, 0))

        self.commitBtn.setPalette(self.green)

        self.insertBtn.clicked.connect(self.goInsert)

        self.insertBtn.clicked.connect(self.goInsert)
        self.commitBtn.clicked.connect(self.goCommit)
        self.cancelBtn.clicked.connect(self.goCancel)
        self.filterBtn.clicked.connect(self.getFilter)
        self.deleteBtn.clicked.connect(self.goDelete)
        self.clearHaulBtn.clicked.connect(self.clearHaul)
        #self.connect(self.tableTypeBox, SIGNAL("activated(int)"), self.chooseTables)
        #self.connect(self.dataModel, SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.commitColor)

        # for right now...
        #self.loadBtn.setEnabled(True)


    def runSql(self):
        try:
            query=QtSql.QSqlQuery(str(self.textEdit.toPlainText()))
            if not query.isValid():
                QMessageBox.warning(self, "ERROR", "<font size = 14> Query is no good!</font>")
        except:
            QMessageBox.warning(self, "ERROR", "<font size = 14> Query is no good!</font>")


    def chooseTables(self):
        self.tableBox.clear()
        if self.tableTypeBox.currentText()=='Setup':
            for i in self.setupTables:
                self.tableBox.addItem(i)
        elif self.tableTypeBox.currentText()=='Lookup':
            for i in self.lookupTables:
                self.tableBox.addItem(i)
        elif self.tableTypeBox.currentText()=='Data':
            for i in self.dataTables:
                self.tableBox.addItem(i)

        self.tableBox.setCurrentIndex(-1)
        #self.tableBox, SIGNAL("activated(int)"), self.showTable)


    def showTable(self):
        if self.tableBox.currentText()=='EVENT_PERFORMANCE':
            QMessageBox.warning(self, "ERROR", "<font size = 14> I can't show that table!")
            return
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.dataModel.setTable(self.tableBox.currentText())
        self.dataModel.setSort(0, Qt.AscendingOrder)
        self.dataModel.select()
        if self.tableBox.currentText()=='PROTOCOL_DEFINITIONS':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("SPECIMEN_PROTOCOL", "PROTOCOL_NAME", "PROTOCOL_NAME"))
            self.dataModel.setRelation(1, QtSql.QSqlRelation("measurement_types", "measurement_type", "measurement_type"))
        elif self.tableBox.currentText()=='MEASUREMENT_SETUP':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("WORKSTATION", "workstation_ID", "workstation_ID"))
            self.dataModel.setRelation(1, QtSql.QSqlRelation("measurement_types", "measurement_type", "measurement_type"))
            self.dataModel.setRelation(2, QtSql.QSqlRelation("device", "device_id", "device_name"))
            self.dataModel.setRelation(3, QtSql.QSqlRelation("device_interfaces", "device_interface", "device_interface"))
        elif self.tableBox.currentText()=='PROTOCOL_MAP':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("SPECIMEN_PROTOCOL", "PROTOCOL_NAME", "PROTOCOL_NAME"))
        elif self.tableBox.currentText()=='VALIDATIONS':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("VALIDATION_DEFINITIONS", "VALIDATION", "VALIDATION"))
            self.dataModel.setRelation(1, QtSql.QSqlRelation("SPECIMEN_PROTOCOL", "PROTOCOL_NAME", "PROTOCOL_NAME"))
            self.dataModel.setRelation(2, QtSql.QSqlRelation("measurement_types", "measurement_type", "measurement_type"))
        elif self.tableBox.currentText()=='CONDITIONALS':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("CONDITIONAL_DEFINITIONS", "CONDITIONAL", "CONDITIONAL"))
            self.dataModel.setRelation(1, QtSql.QSqlRelation("SPECIMEN_PROTOCOL", "PROTOCOL_NAME", "PROTOCOL_NAME"))
        elif self.tableBox.currentText()=='DEVICE_CONFIGURATION':
            self.dataModel.setRelation(0, QtSql.QSqlRelation("DEVICE", "DEVICE_ID", "DEVICE_NAME"))
            self.dataModel.setRelation(1, QtSql.QSqlRelation("DEVICE_PARAMETERS", "DEVICE_PARAMETER", "DEVICE_PARAMETER"))
        self.dataView.setModel(self.dataModel)
        self.dataView.setItemDelegate(QtSql.QSqlRelationalDelegate(self.dataView))
        self.dataView.show()
        self.dataView.resizeColumnsToContents()
        # filter combobox
        self.fieldBox.clear()
        for i in range(self.dataModel.columnCount(QModelIndex())):
            header=self.dataModel.headerData(i, Qt.Horizontal)
            self.fieldBox.addItem(header.toString())

        QApplication.restoreOverrideCursor()


    def getFilter(self):
        if self.valueEdit.text()=='':
            return
        self.dataModel.setFilter(self.fieldBox.currentText()+'='+self.valueEdit.text())


    def goInsert(self):
        self.newRow=self.dataModel.rowCount()
        self.dataModel.insertRow(self.newRow)
        self.dataView.scrollToBottom()
        self.insertBtn.setEnabled(False)
        self.commitBtn.setPalette(self.red)


    def goCommit(self):

        if self.dataModel.submitAll():
            self.deleteBtn.setEnabled(True)
            self.insertBtn.setEnabled(True)
            self.commitBtn.setPalette(self.green)
        else:
            print(self.dataModel.lastError())


    def goCancel(self):
        self.showTable()
        self.commitBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)
        self.insertBtn.setEnabled(True)
        self.commitBtn.setPalette(self.green)


    def goDelete(self):
        ind=self.dataView.currentIndex()
        if self.dataModel.removeRow(ind.row()):
            self.deleteBtn.setEnabled(False)
            self.commitBtn.setPalette(self.red)
        else:
            print(self.dataModel.lastError())


    def commitColor(self):
        self.commitBtn.setPalette(self.red)


    def clearHaul(self):
        query=QtSql.QSqlQuery("SELECT EVENT_ID, PARAMETER_VALUE FROM " + self.schema + ".EVENT_DATA  WHERE ship = "+self.ship+ " AND survey="+self.survey+" AND EVENT_PARAMETER = 'EQ' "  )
        Hauls=[]
        EQTimes=[]
        while query.next():
            Hauls.append(query.value(0).toString())
            EQTimes.append(query.value(1).toString())

        hlDialog = eventseldlg.eventseldlg(self)
        hlDialog.okBtn.setText('Delete Haul')
        hlDialog.newHaulBtn.hide()
        if hlDialog.exec_():
            self.activeHaul = hlDialog.activeHaul
        else:
            return

        reply = QMessageBox.question(self, 'Warning!',"<font size = 14> This will delete all data for haul "+self.activeHaul+" from database, are you sure you want to do this? </font>", QMessageBox.Yes, QMessageBox.No)
        if reply==QMessageBox.No: # open the file, go to the end
            return


        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".measurements WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".specimen WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".basket WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".sample_data WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".sample WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_stream_data WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".gear_accessory WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)
        QtSql.QSqlQuery("DELETE FROM " + self.schema + ".events WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id ="+self.activeHaul)





    def closeEvent(self, event=None):
        """
          Clean up when the CLAMS main window is closed.
        """
        pass






