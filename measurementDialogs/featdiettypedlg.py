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
.. module:: FEATDietTypeDlg

    :synopsis: Special dialog for entering diet collection data - collection and contents

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
|        Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - cleaning up queries
|
| NOTE: cannot test this until it is called with parent values
"""


from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QImage, QPixmap
from ui import ui_FEATDietTypeDlg
from ui import ui_FEATDietSpDlg
import numpad
import messagedlg
from collections import OrderedDict
from sys import argv


class FEATDietTypeDlg(QDialog, ui_FEATDietTypeDlg.Ui_Dialog):
    def __init__(self, parent=None):
        super(FEATDietTypeDlg, self).__init__(parent)
        self.setupUi(self)

        self.message = messagedlg.MessageDlg(self)

        self.result = OrderedDict()
        self.survey = parent.survey
        self.ship = parent.ship
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.activeHaul
        self.active_sample = parent.activeSample
        self.lengthTypeBox = parent.lengthTypeBox
        self.settings = parent.settings
        self.edit_flag = parent.editFieldFlag
        self.specimen_key = parent.specimenKey
        self.schema = parent.schema
        self.errorIcons = parent.errorIcons
        self.errorSounds = parent.errorSounds
        self.settings = parent.settings
        self.printer = parent.printer
        self.db = parent.db
        self.schema = parent.schema
        self.called_enable = self.settings['DietCalledEnable']
        #self.settings = {}

        self.oto_present = False
        self.oto_last = 0
        self.tot_collect = 5
        self.tot_called = 5
        self.collected = ""
        self.called = ""

        if self.called_enable:
            if self.called_enable == 'True':
                self.called_enable = True
            else:
                self.called_enable = False

        # hide the species code buttons
        self.pb_code_1.hide()
        self.pb_code_2.hide()
        self.pb_code_3.hide()

        # disable buttons
        self.pb_sp_2.setEnabled(False)
        self.pb_vol_2.setEnabled(False)
        self.pb_sp_3.setEnabled(False)
        self.pb_vol_3.setEnabled(False)
        self.pb_done.setEnabled(False)

        # set the called table enabled/disabled
        self.tw_stom_type.setTabEnabled(1, self.called_enable)

        #  connect signals
        self.pb_taken.clicked.connect(self.taken)
        self.pb_not_taken.clicked.connect(lambda: self.not_taken('collect'))
        self.pb_not_taken_2.clicked.connect(lambda: self.not_taken('content'))
        self.pb_overall.clicked.connect(self.overall)
        self.pb_sp_1.clicked.connect(self.set_species)
        self.pb_sp_2.clicked.connect(self.set_species)
        self.pb_sp_3.clicked.connect(self.set_species)
        self.pb_vol_1.clicked.connect(self.set_volume)
        self.pb_vol_2.clicked.connect(self.set_volume)
        self.pb_vol_3.clicked.connect(self.set_volume)
        self.pb_done.clicked.connect(self.fin)
        self.pb_cancel.clicked.connect(self.close)

    def setup(self, parent):
        """
        called when the dialog is actually executed
        :param parent: calling class
        :return:
        """
        # reset button text
        self.reset_btn_txt()

        # get the edit flag
        self.edit_flag = parent.editFieldFlag

        # check for otolith
        self.specimen_key = parent.specimenKey
        self.oto()
        if not self.oto_present:
            # send up dialog to tell them they need to enter an otolith number first
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "You must enter an otolith vial number FIRST before collecting diet information. "
                                    "Please either scan or enter a vial number.", 'info')
            self.message.exec()
            return

        # if it is an edit, allow everything - there may be an instance where we end up with more stomach than
        # the protocol dictates, but it shouldn't happen very often
        if not self.edit_flag:
            # check collected and called numbers
            # get total already collected and called
            collection_sql = (f"SELECT COUNT(*) FROM {self.schema}.measurements WHERE event_id = {self.active_event} "
                              f"AND measurement_type = 'stomach_collect' "
                              f"AND measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
            collection_query = self.db.dbQuery(collection_sql)

            self.collected = int(collection_query.first()[0])
            if self.collected >= self.tot_collect:
                self.tw_stom_type.setTabEnabled(0, False)

            # get total already collected and called
            called_sql = (f"SELECT COUNT(*) FROM {self.schema}.measurements WHERE event_id = {self.active_event} "
                          f"AND measurement_type = 'stom_cont_1' AND "
                          f"measurement_value NOT IN ('Blown', 'Nicked', 'Regurg', 'Unknown')")
            called_query = self.db.dbQuery(called_sql)
            self.called = int(called_query.first()[0])
            if self.called >= self.tot_called:
                self.tw_stom_type.setTabEnabled(1, False)

        else:
            self.specimen_key = parent.specimenKey
            # load all diet samples for that measurement
            self.load_measures()

    def reset_btn_txt(self):
        """
        resets the button texts to the default
        :return:
        """
        # reset the current barcode
        self.l_cur_code.setText("None")

        # reset the taken button
        self.pb_taken.setText("Taken")

        # reset the can't take button
        self.pb_not_taken_2.setText("Can't take contents")

        # reset the overall weight button
        self.pb_overall.setText("Overall Weight")
        # reset species buttons
        self.pb_sp_1.setText("Species 1")
        self.pb_sp_2.setText("Species 2")
        self.pb_sp_3.setText("Species 3")

        # reset volume buttons
        self.pb_vol_1.setText("Vol 1")
        self.pb_vol_2.setText("Vol 2")
        self.pb_vol_3.setText("Vol 3")

        # reset species code hidden buttons
        self.pb_code_1.setText("species_code")
        self.pb_code_2.setText("species_code")
        self.pb_code_3.setText("species_code")

    def oto(self):
        """
        checks if there is an otolith barcode in the measurements and returns if not
        :return:
        """
        self.oto_present = False
        if self.specimen_key is not None:
            exist_sql = (f"SELECT measurement_value FROM {self.schema}.measurements WHERE ship={self.ship} "
                         f"AND survey={self.survey} AND event_id={self.active_event} "
                         f"AND sample_id={self.active_sample} AND specimen_id={self.specimen_key} "
                         f"AND measurement_type = 'barcode'")
            exist_query = self.db.dbQuery(exist_sql)
            if exist_query.first():
                self.oto_last = exist_query.first()[0]
                self.oto_present = True

    def load_measures(self):
        """
        loads the measurements from the database
        :return:
        """
        # reset the button texts
        self.reset_btn_txt()
        # enable the done button
        self.pb_done.setEnabled(True)
        measures_to_load = ['stomach_collect', 'stom_cont_1', 'stom_cont_2', 'stom_cont_3',
                            'stom_vol_1', 'stom_vol_2', 'stom_vol_3', 'stom_overall_wt']
        for measure in measures_to_load:
            query_txt = (f"SELECT measurement_value FROM {self.schema}.measurements "
                         f"WHERE measurement_type = '{measure}' AND specimen_id = {self.specimen_key}")
            query = self.db.dbQuery(query_txt)
            if query.first():
                value = query.first()[0]
                if measure == 'stomach_collect':
                    self.l_cur_code.setText(str(value))
                    if str(value) not in ['Blown', 'Regurg', 'Nicked', 'Unknown']:
                        self.pb_taken.setText("Reprint label")
                elif measure == 'stom_cont_1' and self.called_enable:
                    if value not in ['Blown', 'Regurg', 'Nicked', 'Unknown']:
                        self.pb_not_taken_2.setText("Can't take contents")
                        self.pb_code_1.setText(str(value))
                        self.pb_sp_1.setText(self.get_sp(value))
                    else:
                        self.pb_not_taken_2.setText(str(value))
                        self.pb_code_1.setText("species_code")
                        self.pb_sp_1.setText("Species 1")
                elif measure == 'stom_cont_2' and self.called_enable:
                    self.pb_code_2.setText(str(value))
                    self.pb_sp_3.setText(self.get_sp(value))
                elif measure == 'stom_cont_3' and self.called_enable:
                    self.pb_code_3.setText(str(value))
                    self.pb_sp_3.setText(self.get_sp(value))
                elif measure == 'stom_vol_1' and self.called_enable:
                    self.pb_vol_1.setText(str(value))
                elif measure == 'stom_vol_2' and self.called_enable:
                    self.pb_vol_2.setText(str(value))
                elif measure == 'stom_vol_3' and self.called_enable:
                    self.pb_vol_3.setText(str(value))
                elif measure == 'stom_overallwt':
                    self.pb_overall.setText(str(value))
            else:
                if measure == 'stomach_collect':
                    self.l_cur_code.setText("None")
                elif measure == 'stom_cont_1':
                    self.pb_sp_1.setText("Species 1")
                    self.pb_code_1.setText("species_code")
                elif measure == 'stom_cont_2':
                    self.pb_sp_2.setText("Species 2")
                    self.pb_code_2.setText("species_code")
                elif measure == 'stom_cont_3':
                    self.pb_sp_3.setText("Species 3")
                    self.pb_code_3.setText("species_code")
                elif measure == 'stom_vol_1':
                    self.pb_vol_1.setText("Vol 1")
                elif measure == 'stom_vol_2':
                    self.pb_vol_2.setText("Vol 2")
                elif measure == 'stom_vol_3':
                    self.pb_vol_3.setText("Vol 3")
                elif measure == 'stom_overallwt':
                    self.pb_overall.setText("Overall Weight")

    def get_sp(self, sp_code):
        """
        returns the species name for the code
        :return: species name - scientific
        """
        query_txt = f"SELECT scientific_name FROM {self.schema}.species WHERE species_code = {sp_code}"
        query = self.db.dbQuery(query_txt)
        query.first()
        return query.first()[0]

    def taken(self):
        """
        sets the diet_collection measurement to 'Collected'
        sends up a dialog to print the label with a barcode
        sets the stomach_collect measurement to the barcode number
        :return:
        """
        # if self.printer is not None:
        self.pb_done.setEnabled(True)
        print_label = GetLabel(self)
        if print_label.result() == 1:
            self.result["diet_collection"] = "Collected"
            self.result["stomach_collect"] = str(print_label.code)
            self.accept()

    def not_taken(self, location):
        """
        sends up a dialog to ask why it wasn't taken
        sets the diet_collection measurement to the reason
        sets the stomach_collect measurement to the reason if it is a collection
        or the stom_cont_1 measurement to the reason if contents
        :return: none
        """
        reasons = GetReasons(location, self.settings)
        self.result = {}
        if reasons.result() == 1:
            self.pb_done.setEnabled(True)
            if location == "collect":
                self.result["diet_collection"] = "Not collected"
                self.result["stomach_collect"] = reasons.reason
            else:
                if reasons.reason == 'Empty':
                    self.result['diet_collection'] = 'Contents'
                    self.result['stom_cont_1'] = reasons.reason
                else:
                    self.result["diet_collection"] = "No contents"
                    self.result["stom_cont_1"] = reasons.reason

            self.accept()

    def overall(self):
        """
        sends up a number pad to get the overall weight of the bolus
        sets the stom_overall_wt measurement to the value
        :return:
        """
        rst = numpad.NumPad()
        rst.exec()
        self.pb_overall.setText(rst.value)
        self.result['stom_overall_wt'] = rst.value

    def set_species(self):
        """
        popup with the list of available species for stomach contents
        :return:
        """
        cur_btn = self.sender()
        btn_num = cur_btn.objectName()[-1]
        cur_sp = GetStomachSpecies(self.settings, self.db)
        if cur_sp.result() == 1:
            self.pb_done.setEnabled(True)
            cur_btn.setText(cur_sp.species[1])
            if btn_num == '1':
                self.pb_code_1.setText(cur_sp.species[0])
                self.result['stom_cont_1'] = cur_sp.species[1]
                self.pb_sp_2.setEnabled(True)
                self.pb_vol_2.setEnabled(True)
                self.pb_done.setEnabled(True)
            elif btn_num == '2':
                self.pb_code_2.setText(cur_sp.species[0])
                self.result['stom_cont_2'] = cur_sp.species[1]
                self.pb_sp_3.setEnabled(True)
                self.pb_vol_3.setEnabled(True)
                self.pb_done.setEnabled(True)
            elif btn_num == '3':
                self.pb_code_3.setText(cur_sp.species[0])
                self.result['stom_cont_3'] = cur_sp.species[1]
                self.pb_done.setEnabled(True)

    def set_volume(self):
        """
        sends up the number pad, sets the button name to the value, and sets the result dict
        :return:
        """
        rst = numpad.NumPad()
        rst.exec()
        btn_num = self.sender().objectName()[-1]
        self.pb_done.setEnabled(True)
        if btn_num == '1':
            self.pb_vol_1.setText(rst.value)
            self.result['stom_vol_1'] = rst.value
            self.pb_done.setEnabled(True)
        elif btn_num == '2':
            self.pb_vol_2.setText(rst.value)
            self.result['stom_vol_2'] = rst.value
            self.pb_done.setEnabled(True)
        elif btn_num == '3':
            self.pb_vol_3.setText(rst.value)
            self.result['stom_vol_3'] = rst.value
            self.pb_done.setEnabled(True)

    def fin(self):
        """
        sets all of the variables into the result dict and accepts to return
        :return:
        """
        if self.tw_stom_type.currentIndex() == 1:
            self.result['diet_collection'] = ""
            # get values out of the buttons just to be sure
            overall_wt = self.pb_overall.text()
            sp_1 = self.pb_code_1.text()
            sp_2 = self.pb_code_2.text()
            sp_3 = self.pb_code_3.text()
            vol_1 = self.pb_vol_1.text()
            vol_2 = self.pb_vol_2.text()
            vol_3 = self.pb_vol_3.text()

            if overall_wt != "Overall Weight":
                self.result['stom_overall_wt'] = overall_wt
                self.result['diet_collection'] = "Contents"
            if sp_1 != "species_code":
                self.result['diet_collection'] = "Contents"
                self.result["stom_cont_1"] = sp_1
                if vol_1 != 'Vol 1':
                    self.result["stom_vol_1"] = vol_1
            if sp_2 != "species_code":
                self.result['diet_collection'] = "Contents"
                self.result["stom_cont_2"] = sp_2
                if vol_2 != 'Vol 2':
                    self.result["stom_vol_2"] = vol_2
            if sp_3 != "species_code":
                self.result['diet_collection'] = "Contents"
                self.result["stom_cont_3"] = sp_3
                if vol_3 != 'Vol 3':
                    self.result["stom_vol_3"] = vol_3
        else:
            if self.l_cur_code != 'None':
                self.result['diet_collection'] = "Collected"
                self.result['stomach_collect'] = str(self.l_cur_code.text())
        self.accept()

    def closeEvent(self, event):
        self.result = (False, '')
        self.reject()


class GetLabel(QDialog):
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent)
        self.survey = parent.survey
        self.ship = parent.ship
        self.db = parent.db
        self.schema = parent.schema
        self.activeSpcName = parent.activeSpcName
        self.activeSpcCode = parent.activeSpcCode
        self.active_event = parent.active_event
        self.specimen_key = parent.specimen_key
        self.lengthTypeBox = parent.lengthTypeBox
        self.code = ""
        self.settings = parent.settings
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
        # create the barcode number
        self.code = str(self.survey) + str(self.ship) + str(self.active_event).zfill(3) + str(self.specimen_key)
        # set the project
        project = "Stomach"
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

        # print sound
        # if self.printSound:
        #    self.printSound.play()
        self.accept()

    def closeEvent(self, QCloseEvent):
        self.reject()


class GetReasons(QDialog):
    def __init__(self, location, settings):
        super(QDialog, self).__init__()
        self.reason = ""
        self.settings = settings

        # create the popup
        title = "Why not?"
        win_icon = QIcon()
        win_icon.addFile(self.settings['IconDir'] + "/giant_clam.ico")

        self.setWindowTitle(title)
        self.setFixedWidth(350)
        self.setFixedHeight(300)
        self.setWindowIcon(win_icon)

        self.overall_layout = QVBoxLayout()

        reason_label = QLabel()
        reason_label.setStyleSheet("color: rgb(0, 0, 127); font: 12pt 'Arial Black';")
        if location == 'collect':
            reason_label.setText("Why can't you take the stomach?")
            reasons = ["Blown", "Regurg", "Nicked", "Unknown"]
        else:
            reason_label.setText("Why can't you get the contents?")
            reasons = ["Blown", "Regurg", "Nicked", "Unknown", "Empty"]
        self.overall_layout.addWidget(reason_label)

        for r in reasons:
            btn = QPushButton()
            btn.setObjectName(r)
            btn.setStyleSheet("color: rgb(0, 0, 127); font: 14pt 'Arial Black';")
            btn.setText(r)
            btn.clicked.connect(self.set_reason)
            self.overall_layout.addWidget(btn)

        # create finished and cancel buttons
        btn_box = QHBoxLayout()
        self.reason_done = QPushButton()
        self.reason_done.setStyleSheet("color: rgb(0, 0, 127); font: 12pt 'Arial Black';")
        self.reason_done.setText("Done")
        self.reason_done.clicked.connect(self.fin)
        self.reason_done.setEnabled(False)
        reason_cancel = QPushButton()
        reason_cancel.setStyleSheet("color: rgb(0, 0, 127); font: 14pt 'Arial Black';")
        reason_cancel.setText("Cancel")
        reason_cancel.clicked.connect(self.close)
        btn_box.addWidget(reason_cancel)
        btn_box.addWidget(self.reason_done)

        self.overall_layout.addLayout(btn_box)

        self.setLayout(self.overall_layout)

        self.exec()

    def set_reason(self, r):
        """
        sets the reason
        :param r: button text
        :return:
        """
        # reset all stylesheets
        widgets = (self.overall_layout.itemAt(i) for i in range(self.overall_layout.count()))
        for w in widgets:
            if isinstance(w.widget(), QPushButton):
                w.widget().setStyleSheet("color: rgb(0, 0, 127); font: 12pt 'Arial Black'")
        sending_btn = self.sender()
        sending_btn.setStyleSheet("color: red; font: 16pt 'Arial Black'")
        self.reason = sending_btn.text()
        self.reason_done.setEnabled(True)

    def fin(self):
        """
        closes the popup with accept
        :return:
        """
        self.accept()

    def closeEvent(self, QCloseEvent):
        self.reject()


class GetStomachSpecies(QDialog, ui_FEATDietSpDlg.Ui_Dialog):
    def __init__(self, settings, db):
        super(GetStomachSpecies, self).__init__()
        self.setupUi(self)
        self.chars = ''
        self.updatingDigit = False
        self.species = []
        self.settings = settings
        self.db = db

        #  put the keyboard buttons into a list to easily reference them
        self.digitBtns = [self.A_Btn, self.B_Btn, self.C_Btn, self.D_Btn, self.E_Btn, self.F_Btn,
                          self.G_Btn, self.H_Btn, self.I_Btn, self.J_Btn, self.K_Btn, self.L_Btn,
                          self.M_Btn, self.N_Btn, self.O_Btn, self.P_Btn, self.Q_Btn, self.R_Btn,
                          self.S_Btn, self.T_Btn, self.U_Btn, self.V_Btn, self.W_Btn, self.X_Btn,
                          self.Y_Btn, self.Z_Btn]

        #  connect signals
        for btn in self.digitBtns:
            btn.clicked.connect(self.get_digit)
        self.backBtn.clicked.connect(self.clear_one_char)
        self.clearBtn.clicked.connect(self.clear_all_char)
        self.lw_com.itemClicked.connect(self.get_sel_sp)
        self.lw_sci.itemClicked.connect(self.get_sel_sp)
        self.doneBtn.clicked.connect(self.go_exit)
        self.pb_cancel.clicked.connect(self.close)
        self.doneBtn.setEnabled(False)
        self.r_com.toggled.connect(self.clear_all_char)
        self.r_full.toggled.connect(self.clear_all_char)

        self.get_list()

        self.exec()

    def get_digit(self):
        """
        gets the text from the pressed button and adds it to chars
        sets the line edit to the full chars
        clears both lists and updates
        :return:
        """
        self.updatingDigit = True
        self.chars = self.chars + self.sender().text()
        self.le_species.setText(self.chars)

        self.lw_com.clear()
        self.lw_sci.clear()

        self.get_list()
        self.updatingDigit = False

    def get_list(self):
        """
        gets names that contain the chars from both sci and common names
        :return:
        """
        if self.r_com.isChecked():
            # if chars are empty, return full list of species in Species_Data that are stomach_species
            if self.chars == '':
                com_query = (f"SELECT species.common_name FROM {self.schema}.species WHERE species_code IN "
                                f"(SELECT species_code FROM {self.schema}.species_data "
                                f"WHERE species_parameter = 'stomach_species' AND parameter_value = 1) "
                             f"ORDER BY species.common_name")
                sci_query = (f"SELECT species.scientific_name FROM {self.schema}.species WHERE species_code IN "
                                f"(SELECT species_code FROM {self.schema}.species_data "
                                f"WHERE species_parameter = 'stomach_species' AND parameter_value = 1) "
                             f"ORDER BY species.scientific_name")
            else:
                com_query = (f"SELECT species.common_name FROM {self.schema}.species WHERE species_code IN "
                                f"(SELECT species_code FROM {self.schema}.species_data "
                                f"WHERE species_parameter = 'stomach_species' AND parameter_value = 1) "
                             f"AND upper(species.common_name) "
                             f"LIKE upper('%{self.chars}%') ORDER BY species.common_name")
                sci_query = (f"SELECT species.scientific_name FROM {self.schema}.species WHERE species_code IN "
                                f"(SELECT species_code FROM {self.schema}.species_data "
                                f"WHERE species_parameter = 'stomach_species' AND parameter_value = 1) "
                             f"AND upper(species.scientific_name) ('%{self.chars}%') ORDER BY species.scientific_name")
        else:
            if self.chars == '':
                com_query = (f"SELECT species.common_name FROM {self.schema}.species WHERE species_code != -1 "
                             f"ORDER BY species.common_name")
                sci_query = (f"SELECT species.scientific_name FROM {self.schema}.species WHERE species_code != -1 "
                             f"ORDER BY species.scientific_name")
            else:
                com_query = (f"SELECT species.common_name FROM {self.schema}.species WHERE species_code != -1 "
                             f"AND upper(species.common_name) LIKE upper('%{self.chars}%') "
                             f"ORDER BY species.common_name")
                sci_query = (f"SELECT species.scientific_name FROM {self.schema}.species WHERE species_code != -1 "
                             f"AND upper(species.scientific_name) LIKE upper('%{self.chars}%') "
                             f"ORDER BY species.scientific_name")
        query = self.db.dbQuery(com_query)
        trunc = []
        while query.next():
            trunc.append(query.first()[0])
        self.lw_com.addItems(trunc)

        query = self.db.dbQuery(sci_query)
        trunc1 = []
        while query.next():
            trunc1.append(query.first()[0])
        self.lw_sci.addItems(trunc1)

        if len(trunc) < 2 and self.nameTab.currentIndex == 0:
            self.lw_com.setCurrentRow(1)
        elif len(trunc1) < 2 and self.nameTab.currentIndex == 1:
            self.lw_sci.setCurrentRow(1)

        self.picLabel.clear()

    def clear_one_char(self):
        """
        takes the last character out of the chars and reloads the list
        :return:
        """
        self.chars = self.chars[:-1]
        self.le_species.setText(self.chars)
        self.lw_com.clear()
        self.lw_sci.clear()
        self.get_list()

    def clear_all_char(self):
        """
        clears all of the characters
        :return:
        """
        if not self.updatingDigit:
            self.chars = ''
            self.spcLabel.setText('')
            self.picLabel.clear()
            self.le_species.setText(self.chars)
            self.lw_com.clear()
            self.lw_sci.clear()
            self.get_list()

    def get_sel_sp(self):
        """
        get the species that is selected in the list and get the code
        set up the label and load an image, if available
        :return:
        """
        list_origin = self.sender()
        active_name = list_origin.currentItem().text()
        if self.nameTab.currentIndex() == 0:
            sql = f"SELECT species_code FROM {self.schema}.species WHERE common_name='{active_name}'"
            query = self.db.dbQuery(sql)
        else:
            sql = f"SELECT species_code FROM {self.schema}.species WHERE scientific_name='{active_name}'"
            query = self.db.dbQuery(sql)
        query.first()
        sp_code = query.first()[0]
        img_name = sp_code

        # load label
        self.spcLabel.setText(active_name)

        # set image
        pic = QImage()
        if img_name:
            if pic.load(self.settings['ImageDir'] + '\\fishPics\\' + img_name + ".jpg"):
                pic = pic.scaled(self.picLabel.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.AspectRatioMode.SmoothTransformation)
                self.picLabel.setPixmap(QPixmap.fromImage(pic))
            else:
                pic.load(self.settings['ImageDir'] + '\\fishPics\\no_img.png')
                pic = pic.scaled(self.picLabel.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.AspectRatioMode.SmoothTransformation)
                self.picLabel.setPixmap(QPixmap.fromImage(pic))
        self.doneBtn.setEnabled(True)
        self.species = [sp_code, active_name]

    def go_exit(self):
        """
        saves the chosen species and closes dlg with accept
        :return:
        """
        self.accept()

    def closeEvent(self, QCloseEvent):
        """
        closes with reject
        :param QCloseEvent:
        :return:
        """
        self.reject()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = FEATDietTypeDlg()
    form.show()
    #  and start the application...
    app.exec()
"""