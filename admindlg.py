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
.. module:: AdminDlg

    :synopsis: AdminDlg displays administration dialog and is
               displayed when the "Administration" button is
               clicked in the main application window.

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
"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_AdminDlg
import newSurveyDlg
import selectactivesurveydlg
import setup.setupDlg as setupDlg

class AdminDlg(QDialog, ui_AdminDlg.Ui_admindlg):

    def __init__(self, db, parent=None):
        super(AdminDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.settings = parent.settings

        #  set up signals
        self.createSurveyBtn.clicked.connect(self.createClicked)
        self.selectSurveyBtn.clicked.connect(self.selectClicked)
        self.setUpBtn.clicked.connect(self.setupClicked)
        self.doneBtn.clicked.connect(self.doneClicked)

    def createClicked(self):
        """
          create a new survey.
        """
        self.hide()
        dialog = newSurveyDlg.newSurveyDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()


    def selectClicked(self):
        """
          Select the active survey.
        """
        self.hide()
        dialog = selectactivesurveydlg.SelectActiveSurveyDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()

    def setupClicked(self):
        """
          Configure application settings.
        """
        dialog = setupDlg.setupDlg(self.db, parent=self)
        ok = dialog.exec()

        if ok:
            self.accept()
        else:
            self.show()


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

    form = AdminDlg(db)
    app.exec()
