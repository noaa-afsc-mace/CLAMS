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
.. module:: sampletypeseldlg

    :synopsis: Dialog to present sample types for selection when adding
               a sample to the catch.

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
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from ui import ui_SampleTypeSelDlg


class sampletypeseldlg(QDialog, ui_SampleTypeSelDlg.Ui_SampleTypeSelDlg):
    def __init__(self,  parent=None):
        super(sampletypeseldlg, self).__init__(parent)
        self.setupUi(self)

        self.db = parent.db
        self.activeHaul = parent.activeHaul
        self.schema = parent.schema

        sql = (f"SELECT count(*) from {self.schema}.samples where sample_type='WholeHaul' " 
               f"and event_id={self.activeHaul}")
        results = self.db.dbQuery(sql)
        count, = results.first()

        if (int(count) > 0):
            self.noExtrapBtn.setEnabled(True)
        else:
            self.noExtrapBtn.setEnabled(False)
        
        # variable declarations
        self.result = (False, '')

        self.speciesBtn.clicked.connect(self.getType)
        self.presentBtn.clicked.connect(self.getType)
        self.noExtrapBtn.clicked.connect(self.getType)

    def getType(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        self.result = (True, self.sender().text())
        self.accept()


    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


