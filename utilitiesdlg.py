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
    :module:: UtilitiesDlg

    :synopsis: UtilitiesDlgvis launched when someone clicks the ""Utilities""
               button on the main screen.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
        Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6 import QtSql
from PyQt6.QtWidgets import QDialog, QApplication
#import devicesetupdlg
import Ichthysetupdlg
from ui import ui_UtilitiesDlg

class UtilitiesDlg(QDialog, ui_UtilitiesDlg.Ui_utilitiesdlg):

    def __init__(self, parent=None):
        super(UtilitiesDlg, self).__init__(parent)
        self.setupUi(self)

        self.db=parent.db
        self.ship=parent.ship
        self.survey=parent.survey
        self.settings=parent.settings
        self.workStation=parent.workStation
        self.schema=parent.schema

        #  set up signals
        self.setupBtn.clicked.connect(self.setupDevices)
        self.IchthystickBtn.clicked.connect(self.setupIcthystick)
        self.doneBtn.clicked.connect(self.doneClicked)

        self.setupBtn.setEnabled(False)

        self.show()



    def setupDevices(self):
        '''setupDevices is commented out since the old PyQt4 version was out of date and
        not updated for PyQt6. This should be completely re-written as part of a larger
        collection of setup and configuration forms

        '''
        #dlg = devicesetupdlg.DeviceSetupDlg(self)
        #dlg.exec()


    def setupIcthystick(self):
        dlg = Ichthysetupdlg.Ichthysetupdlg(db=self.db, workstation=self.workStation, parent=self)
        dlg.exec()


    def doneClicked(self):
        self.reject()


    def closeEvent(self, event=None):
        self.reject()



if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)

    db = QtSql.QSqlDatabase.addDatabase("QODBC")
    db.setDatabaseName('mbdev')
    db.setUserName('mbdev')
    db.setPassword('pollock')
    db.schema = 'mbdev'
    db.open()

    form = UtilitiesDlg()
    app.exec()
