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
from ui import ui_EditDeviceConfig
from .baseEditDlg import BaseEditDlg

class editDeviceConfig(BaseEditDlg, ui_EditDeviceConfig.Ui_EditDeviceConfig):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        self.deviceParams = []

        sql = f"SELECT device_parameter from {self.schema}.device_parameters order by device_parameter"
        query = self.db.dbQuery(sql)
        for param, in query:
            self.deviceParams.append(param)
        self.deviceParamsCB.addItems(self.deviceParams)

        # Wire the buttons to the Base logic
        self.setup_base()

    # Populate fields, if creating a new record then fields will be blank
    # otherwise populate fields with existing user edited
    def setUp(self, device):
        if device:
            self.deviceIdLabel.setText(str(device[0]))
            self.deviceParamsCB.setCurrentIndex(self.deviceParams.index(device[1]))
            self.paramValLabel.setText(device[2])
        else:
            self.deviceIdLabel.setText(str(self.deviceId))
            self.deviceParamsCB.setCurrentIndex(-1)
            self.paramValLabel.setText('')

        if ('Update' in self.editBtn.text()):
            self.deviceParamsCB.setDisabled(True)
        else:
            self.deviceParamsCB.setDisabled(False)
    
    def validate_fields(self):
        if 'Add' in self.editBtn.text():
            existingParams = []
            currParam = self.deviceParamsCB.currentText()

            if currParam == '':
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    f"Device parameter empty, please select parameter before saving. ", 'info')
                self.message.exec()
                return False

            sql = f"SELECT device_parameter from {self.schema}.device_configuration where device_id={self.deviceId}"
            query = self.db.dbQuery(sql)
            for param, in query:
                existingParams.append(param)
            
            if currParam in existingParams:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    f"Device parameter {currParam} already exists for deviceId: {self.deviceId}. "
                                    f"Please select a different device parameter before updating.", 'info')
                self.message.exec()
                return False
            else:
                return True
        else:
            return True

    # --- Implement the Hooks ---
    def setDeviceId(self, id):
        self.deviceId = id

    def getData(self):
        self.deviceIdVal = self.deviceIdLabel.text()
        self.deviceParam = self.deviceParamsCB.currentText()
        self.currParamVal = self.paramValLabel.text()
    
    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.device_configuration (device_id, device_parameter, parameter_value) "
                f"VALUES ({self.deviceIdVal}, '{self.deviceParam}', '{self.currParamVal}')")
        self.db.dbExec(sql)
    
    def update(self):
        if 'Update' in self.editBtn.text():
            sql = (f"UPDATE {self.schema}.device_configuration SET "
                   f"device_parameter='{self.deviceParam}', parameter_value='{self.currParamVal}' "
                   f"WHERE device_id={self.deviceIdVal} AND device_parameter='{self.deviceParam}' ")
        self.db.dbExec(sql)

