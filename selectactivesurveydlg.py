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
.. module:: SelectActiveSurveyDlg

    :synopsis: SelectActiveSurveyDlg is presented when the user
               clicks on "Set Active Survey" in the administration
               dialog. It is used to change active survey and it
               calls database procedures to reset sequences for
               the survey.


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
from ui import ui_SelectActiveSurveyDlg


class SelectActiveSurveyDlg(QDialog, ui_SelectActiveSurveyDlg.Ui_selectactivesurveydlg):

    def __init__(self, db, parent=None):
        super(SelectActiveSurveyDlg, self).__init__(parent)
        self.setupUi(self)

        self.db = db
        self.schema = parent.schema

        #  get the list of ships from the database
        sql = ("SELECT ship, name FROM " + self.schema + ".ships")
        query = self.db.dbQuery(sql)
        self.vesselData = [[],[]]
        for ship, name in query:
            self.vesselData[0].append(ship)
            self.vesselData[1].append(name)

        #  populate the GUI fields
        self.ship.clear()
        self.ship.addItems(self.vesselData[1])
        self.ship.setCurrentIndex(-1)

        #  set up signals
        self.ship.activated[int].connect(self.getSurveys)
        self.okBtn.clicked.connect(self.okClicked)
        self.cancelBtn.clicked.connect(self.cancelClicked)

        #  desensitize survey combo
        self.survey.setEnabled(False)

        #  show the dialog
        self.show()


    def getSurveys(self):

        #  get the ship number of the currently selected ship and populate survey list
        shipIndex = self.ship.currentIndex()
        self.shipNumber = self.vesselData[0][shipIndex]

        #  get the list of surveys and their ships in descending order
        sql = ("SELECT survey FROM " + self.schema + ".surveys WHERE ship=" + self.shipNumber +
                " ORDER BY start_date DESC")
        query = self.db.dbQuery(sql)
        self.surveyData = []
        for survey, in query:
            self.surveyData.append(survey)

        self.survey.clear()
        self.survey.addItems(self.surveyData)
        self.survey.setCurrentIndex(-1)

        #  sensitize survey combo
        self.survey.setEnabled(True)


    def okClicked(self):

        #  ensure that a survey has been selected
        selectedIndex = self.survey.currentIndex()
        if (selectedIndex < 0):
            QMessageBox.critical(self, "ERROR", "<font size = 12>Please select a" +
                    "survey or select Cancel.")
            return

        #  make sure that all stations are closed
        sql = ("SELECT hostname FROM " + self.schema + ".workstations WHERE lower(status)='open' and active=1")
        query = self.db.dbQuery(sql)
        openHosts, = query.first()

        if openHosts:
            #  one or more CLAMS workstations are open - do not update active ship/survey
            QMessageBox.critical(self, "ERROR", "<font size = 12>One or more CLAMS workstations " +
                    "are open. The active survey cannot be changed when workstations are open.")

        else:
            #  all stations are closed - update the active ship and survey in the application_configuration table

            #  do this as a transaction so we can easily clean up if there are issues.
            self.db.startTransaction()

            try:
                #  update the ActiveSurvey setting
                sql = ("UPDATE " + self.schema + ".application_configuration SET PARAMETER_VALUE = '" +
                        self.surveyData[selectedIndex] + "' WHERE PARAMETER='ActiveSurvey'")
                self.db.dbExec(sql)

                #  update the ActiveShip setting
                sql = ("UPDATE " + self.schema + ".application_configuration SET PARAMETER_VALUE = " +
                        self.shipNumber + " WHERE PARAMETER='ActiveShip'")
                self.db.dbExec(sql)

                #  zero out the active haul
                sql = ("UPDATE " + self.schema + ".application_configuration SET PARAMETER_VALUE ='0' " +
                              " WHERE PARAMETER='ActiveEvent'")
                self.db.dbExec(sql)

                #  reset the sequences for the new ship/survey combo. This sets the sequence values
                #  to whatever is appropriate for this ship/survey.
                sql = ("CALL " + self.schema + ".reset_sequence_by_survey('" + self.schema + ".baskets'::text, 'basket_id'::text," +
                        self.shipNumber + "::bigint," + self.surveyData[selectedIndex] + "::bigint)")
                self.db.dbExec(sql)

                sql = ("CALL " + self.schema + ".reset_sequence_by_survey('" + self.schema + ".samples'::text, 'sample_id'::text," +
                        self.shipNumber + "::bigint," + self.surveyData[selectedIndex] + "::bigint)")
                self.db.dbExec(sql)

                sql = ("CALL " + self.schema + ".reset_sequence_by_survey('" + self.schema + ".specimen'::text, 'specimen_id'::text," +
                        self.shipNumber + "::bigint," + self.surveyData[selectedIndex] + "::bigint)")
                self.db.dbExec(sql)

                #  reset the protected spp event ID sequence - new in 2019
                sql = ("CALL " + self.schema + ".reset_sequence_by_survey('" + self.schema + ".protected_spp_events'::text, 'event_id'::text," +
                        self.shipNumber + "::bigint," + self.surveyData[selectedIndex] + "::bigint)")
                self.db.dbExec(sql)

                self.db.commit()

            except Exception as e:
                #  there was an error updating the data
                self.db.rollback()
                QMessageBox.critical(self, "ERROR", "<font size = 12>Unable to set the active " +
                        "survey. " + str(e))

        # close the dialog
        self.accept()


    def cancelClicked(self):
        self.reject()


    def closeEvent(self, event=None):
        self.reject()


if __name__ == "__main__":

    import sys
    app = QApplication(sys.argv)

    db = QtSql.QSqlDatabase.addDatabase("QODBC")
    db.setDatabaseName('macebase_shop-64')
    db.setUserName('clamsbase2')
    db.setPassword('pollock')
    db.open()

    form = SelectActiveSurveyDlg(db)
    app.exec()
