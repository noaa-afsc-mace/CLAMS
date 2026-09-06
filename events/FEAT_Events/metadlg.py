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

from PyQt6.QtWidgets import *
from ui import ui_MetaDlg
import numpad
import keypad
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
        self.event_entered = parent.event_entered
        self.msg_shown = parent.msg_shown

        self.message = messagedlg.MessageDlg(self)

        # hide the MMED label and checkbox if not requires
        try:
            if self.settings['MMED'] == 'False':
                self.l_mmed.hide()
                self.ckb_mmed.hide()
        except:
            pass

        # this is all hard-coded for now todo: should use DB for this later
        self.required_params = ['Transect', 'TrawlScientist', 'Gear']

        self.pbs = {'Transect': [self.pb_transect, 'ed', 'np'],
                    'TargetDepth': [self.pb_td, 'ed', 'np'],
                    'TDLatitude': [self.pb_tdlat, 'ed', 'kp'],
                    'TDLongitude': [self.pb_tdlon, 'ed', 'kp'],
                    'WindSpd': [self.pb_wind_spd, 'ed', 'np'],
                    'WindDir': [self.pb_wind_dir, 'ed', 'np'],
                    'SwellHeight': [self.pb_swell_h, 'ed', 'np'],
                    'WindWaves': [self.pb_wind_waves, 'ed', 'np']}
        self.cbs = {'TrawlScientist': [self.cb_sci, 'ed'],
                    'Gear': [self.cb_gear, 'ed'],
                    'TomWeights': [self.cb_toms, 'ga'],
                    'NetNumber': [self.cb_netnums, 'ga'],
                    'HeadropeSBE': [self.cb_head_sbe, 'ga'],
                    'FootropeSBE': [self.cb_foot_sbe, 'ga'],
                    'CameraSBE': [self.cb_cam_sbe, 'ga'],
                    'CameraType': [self.cb_cam_type, 'ga'],
                    'CameraView': [self.cb_cam_view, 'ga'],}

        # load dropdown boxes
        self.load_dropdowns()

        # set up numpad ane keypad
        self.numpad = numpad.NumPad(self)
        self.keypad = keypad.KeyPad('', self)

        # deal with it if it is a reload of data
        if self.reloaded:
            self.event_entered = True
            self.reload_data()

        # set signals and slots
        for param, btn in self.pbs.items():
            btn[0].clicked.connect(self.enter_data)
        self.pb_save.clicked.connect(self.save)
        self.pb_cancel.clicked.connect(self.cancel)

        # send up a reminder message
        if not self.msg_shown:
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "Don't forget to turn off the EAL and reset recording depth!", 'warning')
            self.message.show()
            self.msg_shown = True

    def reload_data(self):
        """
        populates the widgets with data loaded from the database
        :return: none
        """
        # refill any buttons
        for param, pb_lst in self.pbs.items():
            pb, table, np = pb_lst
            # see if it exists
            exists = self.check_if_exists(param, table)
            # set text if so
            if exists != 0:
                pb.setText(exists)
        # refill any drop downs
        for param, cb_lst in self.cbs.items():
            cb, table = cb_lst
            # see if it exists
            exists = self.check_if_exists(param, table)
            # set text if so
            if exists != 0:
                cb.setCurrentText(exists)

    def load_dropdowns(self):
        """
        loads the dropdowns from the gear_accessory_option table
        todo: hard-coded for now, but should be updated when a fix is available
        :return:
        """
        # list of scientists for the fisher
        sci_sql = "SELECT scientist FROM " + self.schema + ".personnel WHERE active=1 AND uuid='F'"
        sci_query = self.db.dbQuery(sci_sql)
        for sci, in sci_query:
            self.cb_sci.addItem(sci)
            self.cb_sci.setCurrentIndex(-1)

        # list of gear
        gear_sql = "SELECT gear FROM " + self.schema + ".gear WHERE active=1"
        gear_query = self.db.dbQuery(gear_sql)
        for gear, in gear_query:
            self.cb_gear.addItem(gear)
            self.cb_gear.setCurrentIndex(-1)

        # TODO: update this from db 2025 offseason
        # list of tom weights
        tom_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory_options "
                   "WHERE gear_accessory = 'TomWeights' AND active = 1")
        tom_query = self.db.dbQuery(tom_sql)
        for tom, in tom_query:
            self.cb_toms.addItem(tom)
            self.cb_toms.setCurrentIndex(-1)

        # list of net numbers
        net_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory_options "
                   "WHERE gear_accessory='NetNumber' AND active = 1")
        net_query = self.db.dbQuery(net_sql)
        for net, in net_query:
            self.cb_netnums.addItem(net)
            self.cb_netnums.setCurrentIndex(-1)

        # SBE lists
        sbe_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory_options "
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
        cam_t_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory_options "
                     "WHERE gear_accessory = 'CameraType' AND active = 1")
        cam_v_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory_options "
                     "WHERE gear_accessory = 'CameraView' AND active = 1")
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
        btn_name = self.sender().objectName()
        # get the dialog to send up (numpad or keypad)
        np_name = ''
        for txt, lst in self.pbs.items():
            btn, table, np = lst
            if btn_name == btn.objectName():
                np_name = np

        if np_name == 'np':
            self.numpad.msgLabel.setText("Enter value")
            if not self.numpad.exec():
                return
            val = self.numpad.value
        else:
            if not self.keypad.exec():
                return
            val = self.keypad.dispEdit.toPlainText()
        # save value as text of button
        self.sender().setText(val)

    def write_haul_record(self):
        """
        writes the initial records into the events table;
        todo: default for event type is used, but could be taken from db at some point
        default for performance_code is 0
        :return:
        """
        #  write record to events table
        sql = ("INSERT INTO " + self.schema + ".events (ship, survey, event_id, gear, event_type, " +
                "performance_code, scientist, comments) VALUES (" + self.ship + "," + self.survey + "," +
               str(self.activeEvent) + ",'" + self.gear + "', 8, 0, '" + self.scientist + "', '')")
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
                p_meas = self.pbs[r][0].text()
            except KeyError:
                p_meas = self.cbs[r][0].currentText()
            if p_meas == '':
                required = True
        if required:
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "You need to add all of the required parameters before you can continue!",
                                    'info')
            if self.message.exec():
                self.reload_data()
                # this is the only way I could find that would stop the meta dialog from being closed when this
                # dialog was closed - fix if there is a better way
                return 'stub'
        else:
            # deal with checkboxes
            # uphill checkbox #
            up_exists = self.check_if_exists('Uphill', 'ed')
            if up_exists == 0:
                if self.ckb_uphill.isChecked():
                    up_sql = (f"INSERT INTO {self.schema}.event_data (ship, survey, event_id, partition, "
                              f"event_parameter, parameter_value) "
                              f"VALUES ({self.ship}, {self.survey}, {self.activeEvent}, 'MainTrawl', 'Uphill', 'Y')")
                    self.db.dbExec(up_sql)
            else:
                if not self.ckb_uphill.isChecked():
                    del_sql = (f"DELETE FROM {self.schema}.event_data WHERE ship={self.ship} "
                               f"AND survey={self.survey} AND event_id={self.activeEvent} "
                               f"AND partition='MainTrawl' AND event_parameter='Uphill'")
                    self.db.dbExec(del_sql)

            # mmed checkbox #
            mmed_exists = self.check_if_exists('MMED', 'ed')
            if mmed_exists == 0:
                if self.ckb_mmed.isChecked():
                    mmed_sql = (f"INSERT INTO {self.schema}.event_data (ship, survey, event_id, partition, "
                                f"event_parameter, parameter_value) "
                                f"VALUES ({self.ship}, {self.survey}, {self.activeEvent}, 'MainTrawl', 'MMED', 'Y')")
                    self.db.dbExec(mmed_sql)
            else:
                if not self.ckb_mmed.isChecked():
                    del_mmed_sql = (f"DELETE FROM {self.schema}.event_data WHERE ship={self.ship} "
                                    f"AND survey={self.survey} AND event_id={self.activeEvent} "
                                    f"AND partition='MainTrawl' AND event_parameter='MMED'")
                    self.db.dbExec(del_mmed_sql)

            # iterate over all buttons and dropdowns
            for param, pb_lst in self.pbs.items():
                pb, table, np = pb_lst
                # check if it already exists in the table
                exists = self.check_if_exists(param, table)
                # if the entry doesn't exist and the text is not blank, enter a new row
                if exists == 0 and pb.text() != '':
                    if table == 'ed':
                        le_sql = ("INSERT INTO " + self.schema +
                                  ".event_data (ship, survey, event_id, partition, event_parameter, "
                                  "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                                  + str(self.activeEvent) + ", 'MainTrawl', '" + param + "', '" + pb.text() + "')")
                    else:
                        le_sql = ("INSERT INTO " + self.schema +
                                  ".gear_accessory (ship, survey, event_id, gear_accessory, gear_accessory_option) "
                                  "VALUES (" + self.ship + ", " + self.survey + ", "
                                  + str(self.activeEvent) + ", '" + param + "', '" + pb.text() + "')")
                    self.db.dbQuery(le_sql)
                # if the entry exists and the text is not blank, update with the new text
                elif exists != 0 and pb.text() != '':
                    if table == 'ed':
                        le_sql = ("UPDATE " + self.schema +
                                  ".event_data SET parameter_value = '" + pb.text() + "' WHERE ship=" + self.ship +
                                  " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                                  " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    else:
                        le_sql = ("UPDATE " + self.schema +
                                  ".gear_accessory SET gear_accessory_option = '" + pb.text()
                                  + "' WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND gear_accessory='" + param + "'")
                    self.db.dbQuery(le_sql)
                # if the entry exists and the text is blank, delete the row
                elif exists != 0 and pb.text() == '':
                    if table == 'ed':
                        le_sql = ("DELETE FROM " + self.schema +
                                  ".event_data WHERE ship=" + self.ship +
                                  " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                                  " AND partition='MainTrawl' AND event_parameter='" + param + "'")
                    else:
                        le_sql = ("DELETE FROM " + self.schema +
                                  ".gear_accessory WHERE ship=" + self.ship +
                                  " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                                  " AND gear_accessory='" + pb.text() + "'")
                    self.db.dbQuery(le_sql)
            for param, cb_lst in self.cbs.items():
                cb, table = cb_lst
                # check if it already exists
                exists = self.check_if_exists(param, table)
                # if it is for the trawl scientist or the gear, update the EVENTS table as well
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
                    if table == 'ed':
                        cb_sql = ("INSERT INTO " + self.schema +
                                  ".event_data (ship, survey, event_id, partition, event_parameter, "
                                  "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                                  + str(self.activeEvent) + ", 'MainTrawl', '" + param + "', '"
                                  + cb.currentText() + "')")
                    else:
                        cb_sql = ("INSERT INTO " + self.schema +
                                  ".gear_accessory (ship, survey, event_id, gear_accessory, gear_accessory_option) "
                                  "VALUES (" + self.ship + ", " + self.survey + ", " + str(self.activeEvent)
                                  + ", '" + param + "', '" + cb.currentText() + "')")
                    self.db.dbQuery(cb_sql)
                # if it exists and the text is not blank, update the row
                elif exists != 0 and cb.currentText() != '':
                    if table == 'ed':
                        cb_sql = ("UPDATE " + self.schema +
                                  ".event_data SET parameter_value = '" + cb.currentText() + "' WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND partition='MainTrawl' AND event_parameter='"
                                  + param + "'")
                    else:
                        cb_sql = ("UPDATE " + self.schema +
                                  ".gear_accessory SET gear_accessory_option = '" + cb.currentText() + "' WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND gear_accessory='" + param + "'")
                    self.db.dbQuery(cb_sql)
                # if it exists and the text is blank, delete the row
                elif exists != 0 and cb.currentText() == '':
                    if table == 'ed':
                        cb_sql = ("DELETE FROM " + self.schema +
                                  ".event_data WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND partition='MainTrawl' AND event_parameter='"
                                  + param + "'")
                    else:
                        cb_sql = ("DELETE FROM " + self.schema + ".gear_accessory WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND gear_accessory='" + param + "'")
                    self.db.dbQuery(cb_sql)
        self.accept()

    def check_if_exists(self, event_parameter, table):
        """
        checks if the entry exists in the database
        :param event_parameter: the parameter to check
        :param table: the table to query
        :return: the value of the parameter if exists and 0 if not
        """
        if table == 'ed':
            exists_sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship=" + self.ship +
                          " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                          " AND partition='MainTrawl' AND event_parameter='" + event_parameter + "'")
        else:
            exists_sql = ("SELECT gear_accessory_option FROM " + self.schema + ".gear_accessory WHERE ship="
                          + self.ship + " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                          " AND gear_accessory='" + event_parameter + "'")
        exists_query = self.db.dbQuery(exists_sql)
        exists, = exists_query.first()
        if exists:
            return exists
        else:
            return 0

    def cancel(self):
        """
        if the cancel button is pressed, reject the dialog to close
        :return:
        """
        self.reject()

    def closeEvent(self, event=None):
        self.accept()
