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
.. module:: metadlg

    :synopsis: metadlg is a dialog that collects the metadata information for an event used by the NWFSC;
                created by Alicia Billings <alicia.billings@noaa.gov>

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
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
from ui import ui_MetaDlg
import numpad
import messagedlg


class MetaDlg(QDialog, ui_MetaDlg.Ui_metaDlg):

    def __init__(self, parent=None):
        super(MetaDlg, self).__init__(parent)
        self.setupUi(self)
        self.settings = parent.settings
        self.db = parent.db
        self.activeEvent = parent.activeEvent
        self.survey = parent.survey
        self.schema = parent.schema
        self.ship = parent.ship
        self.reloaded = parent.reloaded
        self.timeDlg = parent.timeDlg
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.gear = parent.gear
        self.scientist = parent.scientist
        self.event_entered = False

        self.message = messagedlg.MessageDlg(self)

        self.required_params = ['Transect', 'TrawlScientist', 'Gear']

        self.pbs = {'Transect': self.pb_transect,
                    'TargetDepth': self.pb_td,
                    'TDLatitude': self.pb_tdlat,
                    'TDLongitude': self.pb_tdlon,
                    'WindSpd': self.pb_wind_spd,
                    'WindDir': self.pb_wind_dir,
                    'SwellHeight': self.pb_swell_h,
                    'WindWaves': self.pb_wind_waves}
        self.cbs = {'TrawlScientist': self.cb_sci,
                    'Gear': self.cb_gear,
                    'TomWeights': self.cb_toms,
                    'HeadropeSBE': self.cb_head_sbe,
                    'FootropeSBE': self.cb_foot_sbe,
                    'CameraSBE': self.cb_cam_sbe,
                    'CameraType': self.cb_cam_type,
                    'CameraView': self.cb_cam_view}

        # load dropdown boxes
        self.load_dropdowns()

        # set up numpad
        self.numpad = numpad.NumPad(self)

        # deal with it if it is a reload of data
        if self.reloaded:
            self.event_entered = True
            self.reload_data()

        # set signals and slots
        for param, btn in self.pbs.items():
            btn.clicked.connect(self.enter_data)
        self.pb_save.clicked.connect(self.save)
        self.pb_cancel.clicked.connect(self.cancel)

    def reload_data(self):
        """
        populates the widgets with entered data
        :return: none
        """
        # refill any buttons
        for param, pb in self.pbs.items():
            # see if it exists
            exists = self.check_if_exists(param)
            # set text if so
            if exists != 0:
                pb.setText(exists)
        # refill any drop downs
        for param, cb in self.cbs.items():
            # see if it exists
            exists = self.check_if_exists(param)
            # set text if so
            if exists != 0:
                cb.setCurrentText(exists)

    def load_dropdowns(self):
        """

        :return:
        """
        # list of scientists for the fisher
        sci_sql = "SELECT scientist FROM personnel WHERE active=1"
        sci_query = self.db.dbQuery(sci_sql)
        for sci, in sci_query:
            self.cb_sci.addItem(sci)
            self.cb_sci.setCurrentIndex(-1)

        # list of gear
        gear_sql = "SELECT gear FROM gear WHERE active=1"
        gear_query = self.db.dbQuery(gear_sql)
        for gear, in gear_query:
            self.cb_gear.addItem(gear)
            self.cb_gear.setCurrentIndex(-1)

        # list of tom weights
        tom_sql = ("SELECT gear_accessory_option FROM gear_accessory_options "
                   "WHERE gear_accessory = 'Tom_weights' AND active = 1")
        tom_query = self.db.dbQuery(tom_sql)
        for tom, in tom_query:
            self.cb_toms.addItem(tom)
            self.cb_toms.setCurrentIndex(-1)

        # SBE lists
        sbe_sql = ("SELECT gear_accessory_option FROM gear_accessory_options "
                   "WHERE gear_accessory = 'SBE_serial' AND active = 1")
        sbe_query = self.db.dbQuery(sbe_sql)
        for sbe, in sbe_query:
            # add to headrope
            self.cb_head_sbe.addItem(sbe)
            self.cb_head_sbe.setCurrentIndex(-1)
            # add to footrope
            self.cb_foot_sbe.addItem(sbe)
            self.cb_foot_sbe.setCurrentIndex(-1)
            # add to camera
            self.cb_cam_sbe.addItem(sbe)
            self.cb_cam_sbe.setCurrentIndex(-1)

        # camera type and view
        cam_t_sql = ("SELECT gear_accessory_option FROM gear_accessory_options "
                     "WHERE gear_accessory = 'Cam_type' AND active = 1")
        cam_v_sql = ("SELECT gear_accessory_option FROM gear_accessory_options "
                     "WHERE gear_accessory = 'Cam_view' AND active = 1")
        cam_t_query = self.db.dbQuery(cam_t_sql)
        cam_v_query = self.db.dbQuery(cam_v_sql)
        for c_type, in cam_t_query:
            self.cb_cam_type.addItem(c_type)
            self.cb_cam_type.setCurrentIndex(-1)
        for c_view, in cam_v_query:
            self.cb_cam_view.addItem(c_view)
            self.cb_cam_view.setCurrentIndex(-1)

    def enter_data(self):
        """
        allows user to enter the value using a number pad and saves that value as the button text
        :return: none
        """
        # send up numpad
        self.numpad.msgLabel.setText("Enter value")
        if not self.numpad.exec():
            return
        # save value as text of button
        self.sender().setText(self.numpad.value)

    def write_haul_record(self):
        """
        writes the initial records into the events table
        :return:
        """
        #  write record to events table
        sql = ("INSERT INTO " + self.schema + ".events (ship, survey, event_id, gear, event_type, " +
                "performance_code, scientist, comments) VALUES (" + self.ship + "," + self.survey + "," +
               str(self.activeEvent) + ",'" + self.gear + "', 0, 0, '" + self.scientist + "', '')")
        self.db.dbExec(sql)
        # set the flag to true that the event was entered
        self.event_entered = True

    def save(self):
        """
        this will write a record for the event, checks if record is already entered and updates if it does or creates
        if it doesn't, updates event record with gear and scientist after it is entered
        :return: none
        """
        # if the event has not already been entered, enter it
        if not self.event_entered:
            self.write_haul_record()

        # check if all required entries are entered
        required = False
        for r in self.required_params:
            try:
                p_meas = self.pbs[r].text()
            except:
                p_meas = self.cbs[r].currentText()
            if p_meas == '':
                required = True
        if required:
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "You need to add all of the required parameters before you can continue!",
                                    'info')
            self.message.exec()
            # todo: dont close the metadata window after ok
        else:
            # iterate over all buttons and dropdowns
            for param, pb in self.pbs.items():
                # check if it already exists in EVENT_DATA
                exists = self.check_if_exists(param)
                # if the entry doesn't exist and the text is not blank, enter a new row
                if exists == 0 and pb.text() != '':
                    le_sql = ("INSERT INTO " + self.schema +
                              ".event_data (ship, survey, event_id, partition, event_parameter, "
                              "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                              + str(self.activeEvent) + ", 'MainTrawl', '" + param + "', '" + pb.text() + "')")
                    self.db.dbQuery(le_sql)
                # if the entry exists and the text is not blank, update with the new text
                elif exists != 0 and pb.text() != '':
                    le_sql = ("UPDATE " + self.schema +
                              ".event_data SET parameter_value = '" + pb.text() + "' WHERE ship=" + self.ship +
                              " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                              " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    self.db.dbQuery(le_sql)
                # if the entry exists and the text is blank, delete the row
                elif exists != 0 and pb.text() == '':
                    le_sql = ("DELETE FROM " + self.schema +
                              ".event_data WHERE ship=" + self.ship +
                              " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                              " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    self.db.dbQuery(le_sql)
            for param, cb in self.cbs.items():
                # check if it already exists in EVENT_DATA
                exists = self.check_if_exists(param)
                # if it is for the trawl scientist or the gear, update the EVENTS table
                if param == 'TrawlScientist':
                    update_sci_sql = ("UPDATE " + self.schema +
                                      ".events SET scientist='" + cb.currentText() + "' WHERE ship="
                                      + self.ship + " AND survey=" + self.survey +
                                      " AND event_id=" + str(self.activeEvent))
                    self.db.dbQuery(update_sci_sql)
                elif param == 'Gear':
                    update_gear_sql = ("UPDATE " + self.schema +
                                       ".events SET gear='" + cb.currentText() + "' WHERE ship="
                                       + self.ship + " AND survey=" + self.survey +
                                       " AND event_id=" + str(self.activeEvent))
                    self.db.dbQuery(update_gear_sql)
                # if it doesn't exist and the text is not blank, add a new row
                if exists == 0 and cb.currentText() != '':
                    cb_sql = ("INSERT INTO " + self.schema +
                              ".event_data (ship, survey, event_id, partition, event_parameter, "
                              "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                              + str(self.activeEvent) + ", 'MainTrawl', '" + param + "', '" + cb.currentText() + "')")
                    self.db.dbQuery(cb_sql)
                # if it exists and the text is not blank, update the row
                elif exists != 0 and cb.currentText() != '':
                    cb_sql = ("UPDATE " + self.schema +
                              ".event_data SET parameter_value = '" + cb.currentText() + "' WHERE ship="
                              + self.ship + " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                              " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    self.db.dbQuery(cb_sql)
                # if it exists and the text is blank, delete the row
                elif exists != 0 and cb.currentText() == '':
                    cb_sql = ("DELETE FROM " + self.schema +
                              ".event_data WHERE ship="
                              + self.ship + " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                              " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    self.db.dbQuery(cb_sql)
        self.accept()

    def check_if_exists(self, event_parameter):
        """
        checks if the entry exists in the database
        :param event_parameter: the parameter to check
        :return: the value of the parameter if exists and 0 if not
        """
        exists_sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship=" + self.ship +
                      " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                      " AND partition='MainTrawl' AND event_parameter='" + event_parameter + "'")
        exists_query = self.db.dbQuery(exists_sql)
        exists, = exists_query.first()
        if exists:
            return exists
        else:
            return 0

    def cancel(self):
        self.close()

    def closeEvent(self, event=None):
        self.accept()
