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
.. module:: FEATLuckDlg

    :synopsis: Special dialog for project collecting samples (liver/gonad) for RNA

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
|
| NOTE: cannot test this until it is called with parent values
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon
from ui import ui_FEATLuckDlg
import messagedlg
from collections import OrderedDict
import functions as fun


class FEATLuckDlg(QDialog, ui_FEATLuckDlg.Ui_Dialog):
    def __init__(self, parent=None):
        super(FEATLuckDlg, self).__init__(parent)
        self.setupUi(self)

        self.message = messagedlg.MessageDlg(self)

        self.result = OrderedDict()
        self.survey = parent.survey
        self.ship = parent.ship
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.activeHaul
        self.active_sample = parent.activeSample
        self.settings = parent.settings
        self.edit_flag = parent.editFieldFlag
        self.specimen_key = parent.specimenKey
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.oto_present = False
        self.oto_last = 0
        self.ip = parent.ip
        self.port = parent.port
        self.printer_connected = parent.printer_connected
        self.printer = parent.printer
        self.message = parent.message
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.db = parent.db
        self.schema = parent.schema

        # set check boxes to checked
        self.cb_nad.setChecked(True)
        self.cb_liver.setChecked(True)

        #  connect signals
        self.pb_take_liver.clicked.connect(self.taken)
        self.pb_take_gonad.clicked.connect(self.taken)
        self.cb_nad.stateChanged.connect(self.get_rna)
        self.cb_liver.stateChanged.connect(self.get_rna)
        self.pb_done.clicked.connect(self.fin)
        self.pb_cancel.clicked.connect(self.close)

    def setup(self, parent):
        # check for otolith
        self.specimen_key = parent.specimenKey
        self.oto()
        if not self.oto_present:
            # send up dialog to tell them they need to enter an otolith number first
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "You must enter an otolith vial number FIRST before collecting gonad information. "
                                    "Please either scan or enter a vial number.", 'info')
            self.message.exec_()
            return

        self.edit_flag = parent.editFieldFlag
        if self.edit_flag:
            # load all diet samples for that measurement
            self.load_measures()

        # set the sample number label
        # get the last five of the otolith
        sql = "SELECT measurement_value FROM " + self.schema + ".Measurements WHERE ship=" + self.ship + " AND survey=" + self.survey + \
              " AND event_id=" + self.active_event + " AND sample_id=" + self.active_sample + \
              " AND specimen_id=" + self.specimen_key + " AND measurement_type = 'barcode'"
        query = self.db.dbQuery(sql)
        if query.first():
            last_five = query.value(0).toString()[-5:]
            self.l_samp_num.setText("Use Sample Number: " + str(last_five))
        else:
            self.l_samp_num.setText("Need to enter an otolith first!!!")

    def oto(self):
        """
        checks if there is an otolith barcode in the measurements and returns if not
        :return:
        """
        if self.specimen_key is not None:
            exist_sql = "SELECT measurement_value FROM " + self.schema + ".Measurements WHERE ship=" + self.ship + \
                        " AND survey=" + self.survey + " AND event_id=" + self.active_event + \
                        " AND sample_id=" + self.active_sample + " AND specimen_id=" + self.specimen_key + \
                        " AND measurement_type = 'barcode'"
            exist_query = self.db.dbQuery(exist_sql)
            if exist_query.first():
                self.oto_last = exist_query.value(0).toString()[-5:]
                self.oto_present = True

    def load_measures(self):
        """
        loads the measurements from the database
        :return:
        """
        measures_to_load = ['liver_rna', 'gonad_rna', 'liver_taken']
        for measure in measures_to_load:
            query_txt = "SELECT measurement_value FROM " + self.schema + ".Measurements WHERE measurement_type = '%s' " \
                        "AND specimen_id = %s" % (measure, self.specimen_key)
            query = self.db.dbQuery(query_txt)
            if query.first():
                value = query.value(0).toString()
                if measure == 'liver_taken':
                    self.l_cur_code.setText(str(value))
                elif measure == 'gonad_rna':
                    if value == "Y":
                        self.cb_nad.setChecked(True)
                    else:
                        self.cb_nad.setChecked(False)
                elif measure == 'liver_rna':
                    if value == "Y":
                        self.cb_liver.setChecked(True)
                    else:
                        self.cb_liver.setChecked(False)
            else:
                if measure == 'liver_taken':
                    self.l_cur_code.setText("None")
                elif measure == 'gonad_rna':
                    self.cb_nad.setChecked(False)
                elif measure == 'liver_rna':
                    self.cb_liver.setChecked(False)

    def taken(self):
        """
        sends up a dialog to print the label with a barcode
        sets the liver_taken measurement to the barcode number if liver
        and the gonad_taken measurement to the barcode number if gonad
        :return:
        """
        sender = self.sender().objectName()
        if 'liver' in sender:
            print_label = GetLabel(self, 'liver')
        else:
            print_label = GetLabel(self, 'gonad')
        if print_label.result() == 1:
            if 'liver' in sender:
                self.result["liver_taken"] = str(print_label.code)
            else:
                self.result["gonad_taken"] = str(print_label.code)
            self.l_cur_code.setText(str(print_label.code))

    def get_rna(self):
        """
        checks to see the state of both of the rna check boxes and sets appropriate dict values
        :return:
        """
        if self.cb_nad.isChecked():
            self.result['gonad_rna'] = "Y"
        if self.cb_liver.isChecked():
            self.result['liver_rna'] = "Y"

    def fin(self):
        """
        sets all of the variables into the result dict and accepts to return
        :return:
        """
        # get appropriate values
        nad = False
        liver = False
        barcode = self.l_cur_code.text()
        if self.cb_nad.isChecked():
            nad = True
        if self.cb_liver.isChecked():
            liver = True

        if barcode != "None":
            self.result['liver_taken'] = barcode
            self.result['gonad_taken'] = barcode
        if nad:
            self.result["gonad_rna"] = "Y"
        else:
            self.result["gonad_rna"] = "N"
        if liver:
            self.result['liver_rna'] = "Y"
        else:
            self.result['liver_rna'] = "N"

        if barcode != "None" and nad and liver:
            self.result['luck_meas'] = "Complete"
        elif barcode == "None" and not nad and not liver:
            self.result['luck_meas'] = "None"
        else:
            self.result['luck_meas'] = "Partial"

        self.accept()

    def closeEvent(self, event):
        self.result = (False, '')
        self.reject()


class GetLabel(QDialog):
    def __init__(self, parent=None, project=None):
        super(QDialog, self).__init__(parent)
        self.project = project
        self.survey = parent.survey
        self.ship = parent.ship
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.active_event
        self.active_sample = parent.active_sample
        self.specimen_key = parent.specimen_key
        self.code = ""
        self.settings = parent.settings
        self.ip = parent.ip
        self.port = parent.port
        self.printer_connected = parent.printer_connected
        self.printer = parent.printer
        self.message = parent.message
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.oto_last = parent.oto_last

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
        # get length and weight for the specimen
        length, weight = fun.get_len_wt(self.specimen_key)
        # create the barcode
        self.code = str(str(self.survey) + str(self.ship) + str(self.active_event)
                        + str(self.oto_last))

        # set the project
        if self.project == 'liver':
            project = "Liver"
        else:
            project = "Gonad"

        if self.printer is not None:
            if self.printer_connected:
                # test again, just to be sure
                if self.printer.printer_status():
                    self.printer.print_label(project, self.activeSpcName, self.activeSpcCode, self.active_event,
                                             self.code, self.specimen_key, str(length), str(weight))
                else:
                    self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                            "Printer not responding, please use a paper label",
                                            'info')
                    self.message.exec_()
            else:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                        "Printer not responding, please use a paper label",
                                        'info')
                self.message.exec_()
        else:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "No printer is configured for this station, please use a paper label",
                                    'info')
            self.message.exec_()
        self.accept()

    def closeEvent(self, QCloseEvent):
        self.reject()
