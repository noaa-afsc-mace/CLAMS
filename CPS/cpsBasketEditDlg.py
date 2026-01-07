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
.. module:: cpsbasketeditdlg

    :synopsis: cpsbasketeditdlg presents a dialog to edit a single basket.
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
from ui import ui_BasketEditDlg
import numpad


class CPSBasketEditDlg(QDialog, ui_BasketEditDlg.Ui_basketeditDlg):
    def __init__(self, header,  items,  parent=None):
        super(CPSBasketEditDlg, self).__init__(parent)
        self.setupUi(self)

        self.keep = None
        self.transDevice = None
        self.okFlag = False

        self.validList = parent.validList
        self.typeDlg = parent.typeDlg
        self.sensorMonitor = parent.sensorMonitor
        self.devices = parent.devices
        self.sounds = parent.sounds
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.deviceData = parent.deviceData
        self.headerFont = QFont("Arial Black", 14, -1, False)

        # set up edit basket table
        self.editBasket.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.editBasket.setColumnCount(len(header))
        self.editBasket.setRowCount(1)
        self.editBasket.verticalHeader().setVisible(False)
        self.editBasket.horizontalHeader().setStretchLastSection(True)
        for i in range(len(header)):
            headerItem = QTableWidgetItem(header[i])
            headerItem.setFont(self.headerFont)
            self.editBasket.setHorizontalHeaderItem(i, headerItem)

            #  set up the values cells
            self.setColumnValue(i, items[i])
        self.editBasket.resizeColumnsToContents()

        self.weight = items[1]
        self.basketType = items[2]
        self.numpad = numpad.NumPad(self)

        # signal/slot connections
        self.editBasket.itemSelectionChanged.connect(self.getEdit)
        self.okBtn.clicked.connect(self.getOK)
        self.cancelBtn.clicked.connect(self.getCancel)
        #self.sensorMonitor.SensorDataReceived.connect(self.getAuto)


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
        self.editBasket.setItem(0, col, tableItem)


    def getEdit(self):
        """
        brings up a number pad (if selected weight or count edits) or a way to choose basket type
        changes the text in the table to be saved
        :return: none
        """
        col = self.editBasket.currentColumn()

        #  column 0 is the basket ID which is uneditable

        if col == 1:
            # selected weight - show the numpad to get the new weight

            self.numpad.msgLabel.setText("Enter the New Weight (kg)")
            if not self.numpad.exec():
                #  user hit cancel
                return

            #  numpad forces the user to enter a valid number, but
            #  they can enter nothing so we need to make sure a number
            #  was entered.
            if self.numpad.value != '':
                #  number entered, update thtable
                self.weight = self.numpad.value
                self.setColumnValue(col, self.weight)

        elif col == 2:
            # selected basket type

            #  store the old type and count
            oldType = self.basketType

            #  show the sample type selection dialog
            self.typeDlg.exec()
            self.basketType = self.typeDlg.basketType

            #  check if it has changed
            if oldType.lower() != self.basketType.lower():
                #  type has changed, update the table
                self.setColumnValue(col, self.basketType)


        self.editBasket.resizeColumnsToContents()


    def getAuto(self, device, val):
        """
        gets information from the device that sent an entry (should be only scale here)
        :param device: device that sent the entry
        :param val: value that is sent
        :return: none
        """


        #  check if this is a device we're interested in, if not, ignore this data.
        #  first check if there are any catch measurements
        #if 'catch' not in self.deviceData[device_name]['measurements']:
        #    return

        #  then make sure this is a basket_weight measurement which is the only
        #  measurement that Catch cares about
        #if 'basket_weight' not in self.deviceData[device_name]['measurements']['catch']:
        #    return

        self.weight = val
        self.setColumnValue(1, self.weight)
        self.editBasket.resizeColumnsToContents()

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
