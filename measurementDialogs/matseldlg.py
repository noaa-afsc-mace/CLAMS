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
.. module:: MatSelDlg

    :synopsis: Dialog to choose maturity

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
| Updated February 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
"""

from PyQt6.QtWidgets import *
from ui import ui_MatSelDlg
import matguide


class MatSelDlg(QDialog, ui_MatSelDlg.Ui_matselDlg):

    def __init__(self,  parent=None):
        super(MatSelDlg, self).__init__(parent)
        self.setupUi(self)
        self.db = parent.db
        self.schema = parent.schema
        self.settings = parent.settings
        self.speciesName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.activeSpcSubcat = parent.activeSpcSubcat

        # variable declarations
        self.result = ()
        self.buttons = [self.mat1Btn, self.mat2Btn, self.mat3Btn, self.mat4Btn, self.mat5Btn,
                self.mat6Btn, self.mat7Btn, self.mat8Btn]
        # used for NWFSC
        self.oto_present = True

        # get the current sex value from the parent if available
        self.sex = None
        if hasattr(parent, 'measureType') and hasattr(parent, 'values') and 'sex' in parent.measureType:
            self.sex = parent.values[parent.measureType.index('sex')]

        # get maturity stage names
        mat_stage_sql = "SELECT parameter_value FROM " + self.schema + ".species_data " \
                        "WHERE lower(species_parameter)='maturity_table' AND species_code=" + self.activeSpcCode
        query = self.db.dbQuery(mat_stage_sql)
        mat_stage_query, = query.first()
        if not mat_stage_query:
            return

        mat_desc_sql = "SELECT md.button_text, md.description_text_male " \
                       "FROM  " + self.schema + ".maturity_description md JOIN  " + self.schema + ".maturity_tables mt " \
                       "ON (mt.maturity_table = md.maturity_table) WHERE " \
                       "(mt.maturity_table = " + mat_stage_query + ") ORDER BY md.maturity_key"
        query = self.db.dbQuery(mat_desc_sql)
        maturityBtnText = []
        maleApplicable = []

        for button_text, description_text_male in query:
            maturityBtnText.append(button_text)
            maleApplicable.append(bool(description_text_male))

        # signal/slot connections
        self.guideBtn.clicked.connect(self.getGuide)
        for idx, btn in enumerate(self.buttons):
            btn.clicked.connect(self.getMat)
            try:
                btn.setText(maturityBtnText[idx])
                # disable maturity stages that have no male description when sex is male
                if (self.sex is not None and self.sex.lower() == 'male' and
                        not maleApplicable[idx]):
                    btn.setText(' - ')
                    btn.setEnabled(False)
            except:
                btn.setText(' - ')
                btn.setEnabled(False)


    def setup(self, parent):
        pass


    def getMat(self):
        self.result = (True, self.sender().text())
        self.accept()


    def getGuide(self):
        matGuide = matguide.MatGuide(self)
        matGuide.exec()


    def closeEvent(self, event):

        self.result = (False, '')
        self.reject()
