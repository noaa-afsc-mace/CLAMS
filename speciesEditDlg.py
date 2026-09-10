# coding=utf-8

#     National Oceanic and Atmospheric Administration (NOAA)
#     Alaskan Fisheries Science Center (AFSC)
#     Resource Assessment and Conservation Engineering (RACE)
#     Midwater Assessment and Conservation Engineering (MACE)

#  THIS SOFTWARE AND ITS DOCUMENTATION ARE CONSIDERED TO BE IN THE PUBLIC DOMAIN
#  AND THUS ARE AVAILABLE FOR UNRESTRICTED PUBLIC USE. THEY ARE FURNISHED "AS
#  IS."  THE AUTHORS, THE UNITED STATES GOVERNMENT, ITS INSTRUMENTALITIES,
#  OFFICERS, EMPLOYEES, AND AGENTS MAKE NO WARRANTY, EXPRESS OR IMPLIED,
#  AS TO THE USEFULNESS OF THE SOFTWARE AND DOCUMENTATION FOR ANY PURPOSE.
#  THEY ASSUME NO RESPONSIBILITY (1) FOR THE USE OF THE SOFTWARE AND
#  DOCUMENTATION; OR (2) TO PROVIDE TECHNICAL SUPPORT TO USERS.

"""
.. module:: basketeditdlg

    :synopsis: basketeditdlg presents a dialog to edit a single basket.
               It is presented when a user selects a basket from the
               baskets table in the Catch module and then clicks the
               "edit" button.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
|       Alicia Billings <alicia.billings@noaa.gov>
"""

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sampletypeseldlg
from ui import ui_SpeciesEditDlg
import CPS.cpsAddCatchSpcDlg as cpsAddCatchSpcDlg


class SpeciesEditDlg(QDialog, ui_SpeciesEditDlg.Ui_speciesEditDlg):

    def __init__(self, header,  items,  parent=None):
        super(SpeciesEditDlg, self).__init__(parent)
        self.setupUi(self)

        #self.keep = None
        #self.transDevice = None
        self.okFlag = False
        self.db = parent.db
        self.activeHaul = parent.activeHaul
        self.schema = parent.schema

        self.devices = parent.devices
        self.sounds = parent.sounds
        self.deviceData = parent.deviceData
        self.headerFont = QFont("Arial Black", 14, -1, False)

        # set up edit basket table
        self.editSpecies.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.editSpecies.setColumnCount(len(header))
        self.editSpecies.setRowCount(1)
        self.editSpecies.verticalHeader().setVisible(False)
        self.editSpecies.horizontalHeader().setStretchLastSection(True)

        del items[2]

        for i in range(len(header)):
            headerItem = QTableWidgetItem(header[i])
            headerItem.setFont(self.headerFont)
            self.editSpecies.setHorizontalHeaderItem(i, headerItem)

            #  set up the values cells
            self.setColumnValue(i, items[i])
        self.editSpecies.resizeColumnsToContents()

        self.activeSpeciesName = items[1]
        self.type = items[2]

        self.activeSpcCode = ''

        # signal/slot connections
        self.editSpecies.clicked.connect(self.getEdit)
        self.okBtn.clicked.connect(self.getOK)
        self.cancelBtn.clicked.connect(self.getCancel)

        self.spcDlg = cpsAddCatchSpcDlg.cpsAddCatchSpcDlg('Edit', parent)


    def setColumnValue(self, col, value):

        #  set up the values cells -
        tableItem = QTableWidgetItem(value)
        tableItem.setFont(self.headerFont)
        if col == 0:
            #  the first cell (basket id) is not editble
            tableItem.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            #  the other cells are selectable
            tableItem.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.editSpecies.setItem(0, col, tableItem)

    def updateSpecies(self):
        spcName = self.spcDlg.activeSpcName
        self.setColumnValue(1, spcName)

    def getEdit(self):
        """
        brings up a number pad (if selected weight or count edits) or a way to choose basket type
        changes the text in the table to be saved
        :return: none
        """
        col = self.editSpecies.currentColumn()

        #  column 0 is the species ID which is uneditable

        if col == 1:
            #  show the add species dialog
            self.spcDlg.exec()

            if self.spcDlg and not self.spcDlg.okFlag:
            #  user cancelled action
                return
            
            if (self.spcDlg and self.spcDlg.activeSpcCode and self.spcDlg.activeSpcName):
                self.activeSpcCode = self.spcDlg.activeSpcCode
                self.activeSpeciesName = self.spcDlg.activeSpcName
                self.nameType = self.spcDlg.nameType
                self.setColumnValue(1, self.activeSpeciesName)

        elif col == 2:
            # selected count
            currentCount = self.editSpecies.currentItem().text()
            self.SampTypeDlg = sampletypeseldlg.sampletypeseldlg(self)
            self.SampTypeDlg.exec()

            if self.SampTypeDlg.result[1]:
                self.type = self.SampTypeDlg.result[1]
                print('type ' + self.type)
                self.setColumnValue(2, self.type)

        self.editSpecies.resizeColumnsToContents()


    def getAuto(self, device, val):
        """
        gets information from the device that sent an entry (should be only scale here)
        :param device: device that sent the entry
        :param val: value that is sent
        :return: none
        """


        #  check if this is a device we're interested in, if not, ignore this data.
        #  first check if there are any catch measurements
        if 'catch' not in self.deviceData[device_name]['measurements']:
            return

        #  then make sure this is a basket_weight measurement which is the only
        #  measurement that Catch cares about
        if 'basket_weight' not in self.deviceData[device_name]['measurements']['catch']:
            return

        self.weight = val
        self.setColumnValue(1, self.weight)
        self.editSpecies.resizeColumnsToContents()

        #  play the device sound
        self.sounds[self.devices.index(device)].play()


    def getOK(self):
        """
        sets the okFlag to true and closes the dialog
        :return: none
        """
        self.okFlag = True
        self.done(1)


    def getCancel(self):
        """
        sets the okFlag to false and closes the dialog
        :return: none
        """
        self.okFlag = False
        self.done(1)
