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
.. module:: FEATGonadDlg

    :synopsis: Special dialog for entering gonad collection data

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
| Created by:
|       Alicia Billings - alicia.billings@noaa.gov
|       date: April 2019
| Updated January 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
| Updated June 2026 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - update queries
| NOTE: cannot test this until it is called with parent values
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon
from ui import ui_FEATGonadDlg
import numpad
import messagedlg
from collections import OrderedDict


class FEATGonadDlg(QDialog, ui_FEATGonadDlg.Ui_Dialog):
    def __init__(self, parent=None):
        super(FEATGonadDlg, self).__init__(parent)
        self.setupUi(self)

        self.message = messagedlg.MessageDlg(self)

        self.result = OrderedDict()
        self.survey = parent.survey
        self.ship = parent.ship
        self.schema = parent.schema
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.activeHaul
        self.active_sample = parent.activeSample
        self.lengthTypeBox = parent.lengthTypeBox
        self.settings = parent.settings
        self.edit_flag = parent.editFieldFlag
        self.specimen_key = parent.specimenKey
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.oto_present = False
        self.printer = parent.printer
        self.db = parent.db
        self.schema = parent.schema
        # disable buttons
        self.pb_done.setEnabled(False)

        #  connect signals
        self.pb_take_nad.clicked.connect(self.taken)
        self.pb_nad_wt.clicked.connect(self.get_wt)
        self.pb_done.clicked.connect(self.fin)
        self.pb_cancel.clicked.connect(self.close)

    def setup(self, parent):
        # check for otolith
        self.specimen_key = parent.specimenKey
        self.edit_flag = parent.editFieldFlag
        self.oto_present = self.oto()
        if not self.oto_present:
            # send up dialog to tell them they need to enter an otolith number first
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "You must enter an otolith vial number FIRST before collecting gonad information. "
                                    "Please either scan or enter a vial number.", 'info')
            self.message.exec()
            return
        if self.edit_flag:
            # load all diet samples for that measurement
            self.load_measures()

    def oto(self):
        """
        checks if there is an otolith barcode in the measurements and returns if not
        :return:
        """
        rtn = False
        if self.specimen_key is not None:
            exist_sql = (f"SELECT * FROM {self.schema}.measurements WHERE ship={self.ship} AND survey={self.survey} "
                         f"AND event_id={self.active_event} AND sample_id={self.active_sample} "
                         f"AND specimen_id={self.specimen_key} AND measurement_type='barcode'")
            exist_query = self.db.dbQuery(exist_sql)
            if exist_query.first():
                rtn = True

        return rtn

    def load_measures(self):
        """
        loads the measurements from the database
        :return:
        """
        measures_to_load = ['gonad_collect', 'gonad_weight']
        for measure in measures_to_load:
            query_txt = (f"SELECT measurement_value FROM {self.schema}.measurements "
                         f"WHERE measurement_type = '{measure}' AND specimen_id = {self.specimen_key}")
            query = self.db.dbQuery(query_txt)
            if query.first():
                value = query.first()[0]
                if measure == 'gonad_collect':
                    self.l_cur_code.setText(str(value))
                    self.pb_take_nad.setText("Reprint label")
                elif measure == 'gonad_weight':
                    self.pb_nad_wt.setText(str(value))
            else:
                if measure == 'gonad_collect':
                    self.l_cur_code.setText("None")
                elif measure == 'gonad_weight':
                    self.pb_nad_wt.setText("Gonad Weight")

    def taken(self):
        """
        sets the gonad_collection measurement to 'Collected'
        sends up a dialog to print the label with a barcode
        sets the gonad_collect measurement to the barcode number
        :return:
        """
        print_label = GetLabel(self)
        if print_label.result() == 1:
            self.result["gonad_collection"] = "Collected"
            self.result["gonad_collect"] = str(print_label.code)
            self.l_cur_code.setText(str(print_label.code))
            self.pb_done.setEnabled(True)

    def get_wt(self):
        """
        opens a number pad and takes the weight, sets the button text to the weight, and sets the gonad_weight
        :return:
        """
        rst = numpad.NumPad()
        rst.exec()
        self.pb_nad_wt.setText(rst.value)
        self.result['gonad_weight'] = rst.value

    def fin(self):
        """
        sets all of the variables into the result dict and accepts to return
        :return:
        """
        # get values out of the buttons just to be sure
        barcode = self.l_cur_code.text()
        weight = self.pb_nad_wt.text()

        if barcode != "None":
            self.result['gonad_collect'] = barcode
            self.result['gonad_collection'] = "Collected"
        else:
            self.result['gonad_collection'] = "Not collected"
            self.result['gonad_collect'] = "Not collected"
        if weight != "Gonad Weight":
            self.result["gonad_weight"] = weight
        self.accept()

    def closeEvent(self, event):
        self.result = (False, "")
        self.reject()


class GetLabel(QDialog):
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent)
        self.survey = parent.survey
        self.ship = parent.ship
        self.schema = parent.schema
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.active_event
        self.active_sample = parent.active_sample
        self.specimen_key = parent.specimen_key
        self.lengthTypeBox = parent.lengthTypeBox
        self.code = ""
        self.settings = parent.settings
        self.printer = parent.printer
        self.message = parent.message
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.db = parent.db

        # create the popup
        title = "Print Label"
        win_icon = QIcon()
        win_icon.addFile(self.settings['IconDir'] + "/giant_clam.ico")

        self.setWindowTitle(title)
        self.setFixedWidth(350)
        self.setFixedHeight(100)
        self.setWindowIcon(win_icon)

        print_btn = QPushButton()
        print_btn.setStyleSheet("color: rgb(0, 0, 127); font: 14pt 'Arial Black';")
        print_btn.setText("Print Label")
        print_btn.clicked.connect(self.create_label)

        overall_layout = QVBoxLayout()
        overall_layout.addWidget(print_btn)

        self.setLayout(overall_layout)

        self.exec()

    def create_label(self):
        """
        creates the small popup to prompt user to print the label
        :return:
        """
        # create the barcode
        self.code = str(self.survey) + str(self.ship) + str(self.active_event).zfill(3) + str(self.specimen_key)
        # set the project
        project = "Gonad Collection"

        if self.printer is not None:
            lengthType = str(self.lengthTypeBox.currentText())
            lw_sql = (f"SELECT {lengthType}, organism_weight FROM {self.schema}.v_specimen_measurements "
                      f"WHERE survey={self.survey} AND ship={self.ship} AND event_id={self.active_event} "
                      f"AND specimen_id={self.specimen_key}")
            lw_query = self.db.dbQuery(lw_sql)
            length, weight = lw_query.first()
            self.printer.print_label(project, self.activeSpcName, self.activeSpcCode, self.active_event,
                                     self.code, self.specimen_key, length, weight, self.settings['OrganizationName'])

        else:
            # otherwise, prompt to fill out a label
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "No printer is configured for this station, please use a paper label with "
                                    "specimen number " + self.oto_last,
                                    'info')
            self.message.exec()

        self.accept()

    def closeEvent(self, QCloseEvent):
        self.reject()
