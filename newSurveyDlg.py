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
.. module:: newSurveyDlg

    :synopsis: newSurveyDlg is presented when the user clicks on
               "Create Survey" in the administration dialog. It
               is used to create new surveys in the CLAMS database.


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
from ui import ui_NewSurveyDlg


class newSurveyDlg(QDialog, ui_NewSurveyDlg.Ui_newSurveyDlg):
    def __init__(self, db,  parent=None):
        super(newSurveyDlg, self).__init__(parent)
        self.setupUi(self)

        #  set up the GUI
        self.surveyNumEdit.setInputMask("999990")
        self.startDateEdit.setDate(QDate.currentDate())
        self.startDateEdit.setCalendarPopup(True)
        self.endDateEdit.setDate(QDate.currentDate())
        self.endDateEdit.setCalendarPopup(True)

        self.createBtn.clicked.connect(self.createSurvey)
        self.cancelBtn.clicked.connect(self.cancelClicked)

        self.db=db
        self.schema = parent.schema
        self.shipNumbers = []

        #  populate the combo boxes

        #  get the list of ships from the database
        sql = ("SELECT ship, name FROM " + self.schema + ".ships WHERE active=1")
        query = self.db.dbQuery(sql)
        for ship, name in query:
            self.shipNumbers.append(ship)
            self.cbShip.addItem(name)

        #  get the list of personnel from the database
        sql = ("SELECT scientist FROM " + self.schema + ".personnel")
        query = self.db.dbQuery(sql)
        for sciFi, in query:
            self.cbChiefSci.addItem(sciFi)

        #  get the list of sea areas from the database
        sql = ("SELECT iho_sea_area FROM " + self.schema + ".survey_sea_areas")
        query = self.db.dbQuery(sql)
        for iho_sea_area, in query:
            self.cbSeaArea.addItem(iho_sea_area)

        #  get the list of regions from the database
        sql = ("SELECT region FROM " + self.schema + ".survey_regions")
        query = self.db.dbQuery(sql)
        for region, in query:
            self.cbRegion.addItem(region)

        #  get the list of regions from the database
        sql = ("SELECT port FROM " + self.schema + ".survey_ports WHERE active=1")
        query = self.db.dbQuery(sql)
        for port, in query:
            self.cbStartPort.addItem(port)
            self.cbEndPort.addItem(port)


    def createSurvey(self):

        #  make sure the dates are sane
        if (self.endDateEdit.date() < self.startDateEdit.date()):
            QMessageBox.critical(self, "ERROR", "<font size = 12> " +
                    "The start date is later than the end date. Please fix.")
            return

        #  scrub quotes from our free form strings
        abstract = self.abstractEdit.toPlainText().replace("'",'"')
        surveyName = self.surveyNameEdit.text().replace("'",'"')

        #  extract some of our params
        ship = self.shipNumbers[self.cbShip.currentIndex()]
        surveyNumber = self.surveyNumEdit.text()
        startDate = QDate(self.startDateEdit.date())
        endDate = QDate(self.endDateEdit.date())

        # check that survey doesn't exist
        sql = ("SELECT survey FROM " + self.schema + ".surveys WHERE ship=" + ship+ " AND survey=" +
                surveyNumber)
        query = self.db.dbQuery(sql)
        survey, = query.first()
        if survey:
            QMessageBox.critical(self, 'Error', "Error creating survey. " +
                    "Survey already exists in the database.")
            return

        #  insert the new survey
        try:
            sql = ("INSERT INTO " + self.schema + ".surveys (survey,ship,name,chief_scientist,start_date,end_date," +
                    "start_port,end_port,sea_area,abstract,region) VALUES ("+ surveyNumber + "," +
                    ship + ",'" + surveyName + "','" + self.cbChiefSci.currentText() + "',TO_DATE('" +
                    startDate.toString('MM/dd/yyyy')+"','MM/DD/YYYY')," + "TO_DATE('" +
                    endDate.toString('MM/dd/yyyy') + "','MM/DD/YYYY'),'" + self.cbStartPort.currentText() +
                    "','" + self.cbEndPort.currentText() + "','" + self.cbSeaArea.currentText() +
                    "','" + abstract+ "','" + self.cbRegion.currentText() + "')")
            self.db.dbExec(sql)

        except exception as e:
            #  there was a problem creating the survey
            QMessageBox.critical(self, 'Error', 'Error creating survey. ' + str(e))
            return


        #  success!
        QMessageBox.information(self, 'Success', "Survey created successfully. " +
                "Remember to set it as the active survey if that is your intention.")
        self.accept()


    def cancelClicked(self):
        self.reject()


    def closeEvent(self, event=None):
        self.reject()



