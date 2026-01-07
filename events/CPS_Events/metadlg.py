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
from PyQt6.QtCore import *
from ui import ui_CPSMetaDlg
import numpad
import keypad
import messagedlg
from enum import Enum

class MetadataFields(Enum):
    Collection = 'Collection'
    Operator = 'Operator'
    State = 'State'
    Country = 'Country'
    Gear = 'Gear'
    FishingMode = 'FishingMode'
    ArcedTow = 'ArcedTow'
    SeaCondition = 'SeaCondition'
    Clouds = 'Clouds'
    DownswellTow = 'DownswellTow'

class GearTypeFields(Enum):
    HeadropeTDR = 'HeadropeTDR'
    FootropeTDR = 'FootropeTDR'
    Pingers = 'Pingers'

class MetaDlg(QDialog, ui_CPSMetaDlg.Ui_metaDlg):

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

        self.message = messagedlg.MessageDlg(self)

        # this is all hard-coded for now todo: should use DB for this later
        self.required_params = [MetadataFields.Collection.value, MetadataFields.Operator.value]

        # load dropdown boxes
        self.load_dropdowns()

        self.pbs = {MetadataFields.Collection.value: [self.pb_collection, 'ed', 'np']}
        self.cbs = {MetadataFields.Operator.value: [self.cb_operator, 'ed'],
                    MetadataFields.State.value: [self.cb_state, 'ed'],
                    MetadataFields.Country.value: [self.cb_country, 'ed'],
                    MetadataFields.Gear.value: [self.cb_gear, 'ed'],
                    MetadataFields.FishingMode.value: [self.cb_fishing_mode, 'ed'],
                    MetadataFields.ArcedTow.value: [self.cb_arced_tow, 'ed'],
                    MetadataFields.SeaCondition.value: [self.cb_sea_cond, 'ed'],
                    MetadataFields.Clouds.value: [self.cb_clouds, 'ed']}
        self.tf = {MetadataFields.DownswellTow.value: [self.tf_downswell_tow, 'ed'],
                    GearTypeFields.HeadropeTDR.value: [self.tf_headrope, 'ga'],
                    GearTypeFields.FootropeTDR.value: [self.tf_footrope, 'ga'],
                    GearTypeFields.Pingers.value: [self.tf_pingers, 'ga']}
        
        # set up numpad ane keypad
        self.numpad = numpad.NumPad(self)
        self.keypad = keypad.KeyPad('', self)
        
        # set signals and slots
        for param, btn in self.pbs.items():
            btn[0].clicked.connect(self.enter_data)
        self.pb_save.clicked.connect(self.save)
        self.pb_cancel.clicked.connect(self.cancel)

    def reload_data(self):
        """
        populates the widgets with data loaded from the database
        :return: none
        """
        startingEventNum = 4790
        # refill any buttons
        for param, pb_lst in self.pbs.items():
            pb, table, np = pb_lst
            # see if it exists
            exists = self.check_if_exists(param, table)
            # set text if so
            if exists != 0:
                pb.setText(exists)
            # init collection number to 4791 + event num
            elif param == MetadataFields.Collection.value:
                currEvent = startingEventNum + int(self.activeEvent)
                pb.setText(str(currEvent))
        # refill any drop downs
        for param, cb_lst in self.cbs.items():
            cb, table = cb_lst
            # see if it exists
            exists = self.check_if_exists(param, table)
            # set text if so
            if exists != 0:
                cb.setCurrentText(exists)
        # refill any tf
        for param, tf_lst in self.tf.items():
            tf, table = tf_lst
            # get current value of check state
            exists = self.check_if_exists(param, table)
            state = Qt.CheckState.Checked if exists == 'Yes' else Qt.CheckState.Unchecked
            tf.setCheckState(state)

    def load_dropdowns(self):
        """
        loads the dropdowns from the gear_accessory_option table
        todo: hard-coded for now, but should be updated when a fix is available
        :return:
        """
        # Overall lookups
        # List of scientists for the fisher
        sci_sql = "SELECT scientist FROM " + self.schema + ".personnel WHERE active=1 ORDER BY scientist"
        sci_query = self.db.dbQuery(sci_sql)
        for sci, in sci_query:
            self.cb_operator.addItem(sci)
            self.cb_operator.setCurrentIndex(-1)
        
        # Init combo boxes to empty value
        self.cb_state.setCurrentIndex(-1)
        self.cb_country.setCurrentIndex(-1)
        self.cb_arced_tow.setCurrentIndex(-1)
        self.cb_sea_cond.setCurrentIndex(-1)
        self.cb_clouds.setCurrentIndex(-1)

        # Gear tab
        # List of gear
        gear_sql = "SELECT gear FROM " + self.schema + ".gear WHERE active=1"
        gear_query = self.db.dbQuery(gear_sql)
        for gear, in gear_query:
            self.cb_gear.addItem(gear)
            # Default to MFT 
            self.cb_gear.setCurrentIndex(0)

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

        if txt != MetadataFields.Collection.value:
            return
        elif np_name == 'np':
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
        :return:
        """
        sql = ("SELECT * FROM " + self.schema + ".events where ship=" + self.ship + 
               ' and survey=' + self.survey + ' and event_id= ' + str(self.activeEvent))
        exists_query = self.db.dbQuery(sql)
        exists = exists_query.first()

        # get good performance code
        sql = ("SELECT performance_code FROM " + self.schema + ".event_performance where description='Good performance'")
        performanceCode, = self.db.dbQuery(sql).first()
        if not exists[0]:
            # Write record to events table
            # SW will only use event type 17 (Standard surface tow), so hardcoding it here.
            if self.cb_operator.currentText():
                sql = ("INSERT INTO " + self.schema + ".events (ship, survey, event_id, gear, event_type, " +
                        "performance_code, scientist, comments) VALUES (" + self.ship + "," + self.survey + "," +
                    str(self.activeEvent) + ",'" + self.gear + "', 17," + performanceCode + ",'" + self.cb_operator.currentText() + "', '')")
                self.db.dbExec(sql)
                # set the flag to true that the event was entered
                self.event_entered = True
                return

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
            for param, tf_lst in self.tf.items():
                tf, table = tf_lst
                # check if it already exists
                exists = self.check_if_exists(param, table)
                paramVal = 'Yes' if tf.checkState() == Qt.CheckState.Checked else 'No'
                # if it is for the trawl scientist or the gear, update the EVENTS table as well
                # if it doesn't exist and the text is not blank, add a new row
                if exists == 0:
                    if table == 'ed':
                        tf_sql = ("INSERT INTO " + self.schema +
                                  ".event_data (ship, survey, event_id, partition, event_parameter, "
                                  "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                                  + str(self.activeEvent) + ", 'MainTrawl', '" + param + "', '"
                                  + paramVal + "')")
                    else:
                        tf_sql = ("INSERT INTO " + self.schema +
                                  ".gear_accessory (ship, survey, event_id, gear_accessory, gear_accessory_option) "
                                  "VALUES (" + self.ship + ", " + self.survey + ", " + str(self.activeEvent)
                                  + ", '" + param + "', '" + paramVal + "')")
                    self.db.dbQuery(tf_sql)
                # if it exists and the text is not blank, update the row
                elif exists != 0:
                    if table == 'ed':
                        tf_sql = ("UPDATE " + self.schema +
                                  ".event_data SET parameter_value = '" + paramVal + "' WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND partition='MainTrawl' AND event_parameter='"
                                  + param + "'")
                    else:
                        tf_sql = ("UPDATE " + self.schema +
                                  ".gear_accessory SET gear_accessory_option = '" + paramVal + "' WHERE ship="
                                  + self.ship + " AND survey=" + self.survey + " AND event_id="
                                  + str(self.activeEvent) + " AND gear_accessory='" + param + "'")
                    self.db.dbQuery(tf_sql)
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
