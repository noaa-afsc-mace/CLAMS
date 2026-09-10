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
.. module:: editPersonDlg

    :synopsis: UI to edit personnel table in database, can 
        add and edit records

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Melina Shak <melina.shak@noaa.gov>
"""

#  imports
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_EditMeasurement
from .baseEditDlg import BaseEditDlg

class editMeasurement(BaseEditDlg, ui_EditMeasurement.Ui_EditMeasurement):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        self.measurementTypes = []
        self.devices = []
        self.modules = ['Catch', 'Specimen', 'TrawlEvent']

        sql = f"SELECT measurement_type from {self.schema}.measurement_types order by measurement_types"
        query = self.db.dbQuery(sql)
        for measurement, in query:
            self.measurementTypes.append(measurement)
        self.measurementCB.addItems(self.measurementTypes)
        
        sql = f"SELECT device_id, device_name from {self.schema}.devices order by device_id"
        query = self.db.dbQuery(sql)
        for deviceId, device_name, in query:
            self.devices.append(deviceId)
            self.deviceCB.addItem(device_name + '- ' + deviceId)
        
        self.moduleCB.addItems(self.modules)

        # Wire the buttons to the Base logic
        self.setup_base()
    
    def setCurrWorkstation(self, id):
        self.workstationId = id

    # Populate fields, if creating a new record then fields will be blank
    # otherwise populate fields with existing user edited
    def setUp(self, measurement):
        if measurement:
            self.workstationId = measurement[0]
            self.origMeasurement = measurement[1]
            self.origDevice = measurement[2]
            self.origModule = measurement[3]

            self.measurementCB.setCurrentIndex(self.measurementTypes.index(measurement[1]))
            self.deviceCB.setCurrentIndex(self.devices.index(measurement[2]))
            self.moduleCB.setCurrentIndex(self.modules.index(measurement[3]))
        else:
            self.measurementCB.setCurrentIndex(-1)
            self.deviceCB.setCurrentIndex(-1)
            self.moduleCB.setCurrentIndex(-1)

    def getData(self):
        self.currMeasurement = self.measurementCB.currentText()
        currDevice = self.deviceCB.currentText()
        self.currDevice = int(currDevice.split(' ')[1]) if currDevice else 0
        self.currModule = self.moduleCB.currentText()
    
    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.measurement_setup (workstation_id, measurement_type, device_id, gui_module) "
                f"VALUES ({self.workstationId}, '{self.currMeasurement}', '{self.currDevice}', '{self.currModule}')")
        self.db.dbExec(sql)
    
    def update(self):
        if 'Update' in self.editBtn.text():
            sql = (f"UPDATE {self.schema}.measurement_setup SET measurement_type='{self.currMeasurement}', "
                   f"device_id={self.currDevice}, gui_module='{self.currModule}' "
                   f"WHERE measurement_type='{self.origMeasurement}' AND device_id={self.origDevice} AND "
                   f"gui_module='{self.origModule}' AND workstation_id={self.workstationId}")
        self.db.dbExec(sql)

