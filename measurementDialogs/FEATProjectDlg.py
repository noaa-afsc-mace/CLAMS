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
.. module:: FEATProjectDlg

    :synopsis: Special dialog to select a project to collect a whole fish, enter into the database, and print label

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
| Updated February 2025 by:
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
import numpad
import messagedlg
from ui import ui_YesNoDlg


class FEATProjectDlg(QDialog):
    def __init__(self, parent=None):
        super(FEATProjectDlg, self).__init__(parent)
        self.db = parent.db
        self.activeSpcCode = parent.activeSpcCode
        self.activeSpcName = parent.activeSpcName
        self.activeSampleKey = parent.activeSampleKey
        self.activeHaul = parent.activeHaul
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.workStation = parent.workStation
        self.survey = parent.survey
        self.ship = parent.ship
        self.schema = parent.schema
        self.activePartition = parent.activePartition
        self.scientist = parent.scientist
        self.protos = parent.speciesProtos

        self.numpad = numpad.NumPad()
        self.message = messagedlg.MessageDlg()

        self.collected_num = 0
        self.project_label = ""
        self.project_name = ""
        self.code = 0

        # todo: at some point it would be nice to be able to read in the legs for a project in case there
        #  are different ones depending on which leg as well as get the samples already taken for each leg

        # set up the window
        title = "Which Project?"
        win_icon = QIcon()
        win_icon.addFile(self.settings['IconDir'] + "/giant_clam.ico")

        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        self.setMinimumHeight(300)
        self.setWindowIcon(win_icon)

        self.overall_layout = QVBoxLayout()

        # add the instruction label
        instruction_label = QLabel()
        instruction_label.setStyleSheet("color: rgb(0, 0, 127); font: 12pt 'Arial Black';")
        instruction_label.setText("Choose project to print label for...")
        self.overall_layout.addWidget(instruction_label)

        # add buttons for the projects if the active species is not the Mix parent
        if self.activeSpcCode not in ['100000', '100001', '100002', '100003', '100004', '100005']:
            if self.protos:
                sp_protos = self.protos[self.activeSpcCode]
                
                # --> NEW: Create a set to track labels we have already made buttons for
                seen_labels = set() 
                
                # get the label and check if there is a specimen_collection for each protocol
                for proto in sp_protos:
                    proto_sql = (f"SELECT label FROM {self.schema}.protocol_definitions WHERE protocol_name='{proto}' "
                                 f"AND measurement_type='group_collection'")
                    proto_query = self.db.dbQuery(proto_sql)
                    label, = proto_query.first()

                    if label and label not in seen_labels:
                        seen_labels.add(label)
                        
                        btn = QPushButton()
                        btn.setStyleSheet("color: rgb(0, 0, 127); font: 30pt 'Calibri';")
                        btn.setText(label)
                        btn.clicked.connect(self.set_project)
                        self.overall_layout.addWidget(btn)
            else:
                instruction_label.setText("No projects for this species")
                btn = QPushButton()
                btn.setStyleSheet("color: rgb(0, 0, 127); font: 30pt 'Calibri';")
                btn.setText("OK")
                btn.clicked.connect(self.reject)
                self.overall_layout.addWidget(btn)
        else:
            instruction_label.setText("No projects for this species")
            btn = QPushButton()
            btn.setStyleSheet("color: rgb(0, 0, 127); font: 30pt 'Calibri';")
            btn.setText("OK")
            btn.clicked.connect(self.reject)
            self.overall_layout.addWidget(btn)

        self.setLayout(self.overall_layout)

        self.exec()

    def set_project(self):
        """
        sets the project, pushes up number pad to enter number of specimens collected, enters the record
        into the database, and closes the dialog with accept
        :return:
        """

        self.project_label = self.sender().text()

        # get the protocol name
        proto_sql = f"SELECT protocol_name FROM {self.schema}.protocol_definitions WHERE label='{self.project_label}'"
        proto_query = self.db.dbQuery(proto_sql)
        self.project_name, = proto_query.first()

        # check if sample already taken
        dup_sql = (f"SELECT parameter_value FROM {self.schema}.sample_data WHERE ship={self.ship} "
                   f"AND survey={self.survey} AND event_id={self.activeHaul} AND sample_id={self.activeSampleKey} "
                   f"AND sample_parameter='sample_collection' AND parameter_value LIKE '{self.project_name}%'")
        dup_query = self.db.dbQuery(dup_sql)
        param_val, = dup_query.first()
        if param_val:
            self.project_name, self.collected_num = param_val.split("-")
            # there is already a sample, so ask if they want to overwrite or reprint a label
            dup_reply = DuplicateOptions(self)
            if dup_reply.result() == 1:
                option = dup_reply.action
                if option == 'overwrite':
                    self.numpad.dispBox.setText(self.collected_num)
                    self.numpad.msgLabel.setText("How many " + self.activeSpcName + " are you collecting?")
                    if not self.numpad.exec():
                        #  user cancelled action
                        return
                    #  get the number from the numpad
                    val = self.numpad.value
                    #  check that we didn't get a 0 value
                    if val == '0':
                        self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                                "You have entered 0 (zero) for the number collected, which is not allowed. "
                                                "Please enter a valid number.", 'info')
                        self.message.exec()
                    else:
                        self.collected_num = val

                    # update the entry
                    update_sql = (f"UPDATE {self.schema}.sample_data SET "
                                  f"parameter_value='{self.project_name}-{self.collected_num}' "
                                  f"WHERE ship={self.ship} AND survey={self.survey} AND event_id={self.activeHaul} "
                                  f"AND sample_id={self.activeSampleKey} AND sample_parameter='sample_collection' "
                                  f"AND parameter_value LIKE '{self.project_name}%'")
                    self.db.dbQuery(update_sql)
            else:
                return
        else:
            # there is no sample entered, so insert it
            self.numpad.msgLabel.setText("How many " + self.activeSpcName + " are you collecting?")
            if not self.numpad.exec():
                #  user canceled action
                return
            #  get the number from the numpad
            val = self.numpad.value
            #  check that we didn't get a 0 value
            if val == '0':
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                        "You have entered 0 (zero) for the number collected, which is not allowed. "
                                        "Please enter a valid number.", 'info')
                self.message.exec()
            else:
                self.collected_num = val

            # enter into sample_data
            insert_vals = (f"({self.ship}, {self.survey}, {self.activeHaul}, {self.activeSampleKey}, "
                           f"'sample_collection', '{self.project_name}-{self.collected_num}')")
            insert_txt = (f"INSERT INTO {self.schema}.sample_data "
                          f"(ship, survey, event_id, sample_id, sample_parameter, parameter_value) "
                          f"VALUES %s" % insert_vals)

            self.db.dbQuery(insert_txt)

        # create barcode
        self.code = str(self.survey) + str(self.ship) + str(self.activeHaul.zfill(3)) + str(self.activeSampleKey) + \
                    str(self.collected_num)

        self.accept()

    def closeEvent(self, event):
        self.reject()


class DuplicateOptions(QDialog, ui_YesNoDlg.Ui_YesNoDlg):
    def __init__(self, parent=None):
        super(DuplicateOptions, self).__init__(parent)
        self.setupUi(self)
        self.action = None

        self.msgLabel.setText("There is already a record for " + parent.project_label)
        self.yesBtn.setText("Overwrite")
        self.noBtn.setText("Reprint")

        self.yesBtn.clicked.connect(self.overwrite)
        self.noBtn.clicked.connect(self.reprint)

        self.exec()

    def overwrite(self):
        """

        :return:
        """
        self.action = 'overwrite'
        self.accept()

    def reprint(self):
        """

        :return:
        """
        self.action = 'reprint'
        self.accept()

    def closeEvent(self, event):
        self.reject()
