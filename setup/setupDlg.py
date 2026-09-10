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
.. module:: setupDlg

    :synopsis: Shows all personnel records from the personnel table

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
from ui import ui_SetupDlg
import setup.table.personnelDlg as personnelDlg
import setup.table.workstationDlg as workstationDlg
import setup.table.devicesDlg as devicesDlg
import setup.table.speciesDlg as speciesDlg

class setupDlg(QDialog, ui_SetupDlg.Ui_SetupDlg):

    def __init__(self, db, parent=None):
        super(setupDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.settings=parent.settings

        #  set up signals
        self.editPersonBtn.clicked.connect(self.editPersonClicked)
        self.editWorkstationBtn.clicked.connect(self.editWorkstationClicked)
        self.editDevicesBtn.clicked.connect(self.devicesClicked)
        self.editSpeciesBtn.clicked.connect(self.editSpeciesClicked)
        self.doneBtn.clicked.connect(self.doneClicked)

    def editPersonClicked(self):
        """
          open personnel dialog
        """
        dialog = personnelDlg.personnelDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()
        
    def editWorkstationClicked(self):
        """
          open workstation dialog
        """
        dialog = workstationDlg.workstationDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()
    
    def devicesClicked(self):
        """
          open workstation dialog
        """
        dialog = devicesDlg.devicesDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()
    
    def editSpeciesClicked(self):
        """
          open species dialog
        """
        dialog = speciesDlg.speciesDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()

    def doneClicked(self):
        self.reject()
