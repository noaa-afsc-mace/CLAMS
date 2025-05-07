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
.. module:: FEATTrawlEvent

    :synopsis: This will allow for the user to enter the trawl (event)
               number directly, bypassing the need for a trawl form. It
               is intended to phase this out by 2026. Written by Alicia
               Billings <alicia.billings@noaa.gov>

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
|       Alicia Billings <alicia.billings@noaa.gov>
"""

#  import
from PyQt6.QtWidgets import *
from ui import ui_FEATTrawlEvent
from ui import ui_FEATEventNum
from ui import ui_FEATEventParams
import numpad
import messagedlg
from datetime import datetime as dt


class FEATTrawlEvent(QDialog, ui_FEATTrawlEvent.Ui_Dialog):
    def __init__(self, parent=None):
        """
        The CLAMS Trawl event dialog initialization method. Gets basic information
        and sets up the haul selection form for FEAT
        """
        #  call superclass init methods and GUI form setup method
        super(FEATTrawlEvent, self).__init__(parent)
        self.setupUi(self)

        #  copy some properties from our parent
        self.db = parent.db
        self.schema = parent.schema
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.workStation = parent.workStation
        self.testing = parent.testing

        # todo: get the current event out of the database
        self.activeEvent = 0
        #  setup reoccurring dialogs
        self.numpad = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)

        # set choose event to disabled
        self.pb_choose.setEnabled(False)
        self.pb_edit.setEnabled(False)

        # set up other variables
        self.gear = ""
        self.event_type = ""
        self.sci = ""
        self.active_partition = ""
        self.active = False
        self.check_active()

        # set slots
        self.lw_events.currentTextChanged.connect(self.check_events)
        self.pb_choose.clicked.connect(self.choose_event)
        self.pb_add.clicked.connect(self.add_event)
        self.pb_cancel.clicked.connect(self.reject)
        self.cb_active.clicked.connect(self.check_active)
        self.pb_edit.clicked.connect(self.edit_event_num)

    def set_cur_event(self):
        """
        fills the event table and sets the current event text
        :return:
        """
        # set current event
        if self.activeEvent != '0':
            self.l_current.setText("Current Event: " + str(self.activeEvent))
        else:
            self.l_current.setText("Current Event: NONE")

        # get the events and performance out of the database
        if not self.active:
            event_sql = ("SELECT event_id, performance_code FROM " + self.schema + ".events WHERE survey="
                         + self.survey + " AND ship=" + self.ship + " ORDER BY event_id")
        else:
            event_sql = ("SELECT event_id, performance_code FROM " + self.schema + ".events WHERE survey="
                         + self.survey + " AND ship=" + self.ship + " AND performance_code != 0 ORDER BY event_id")
        event_query = self.db.dbQuery(event_sql)
        # clear the events from the list
        self.lw_events.clear()

        for cur_ev, perf in event_query:
            if self.activeEvent == cur_ev:
                lst_item = QListWidgetItem(cur_ev + "\tCurrent")
            elif perf == '0':
                lst_item = QListWidgetItem(cur_ev + "\tClosed")
            else:
                # check if already has data
                sample_sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE event_id=" + cur_ev)
                samp_query = self.db.dbQuery(sample_sql)
                query_size = 0
                for samp in samp_query:
                    query_size += 1
                if query_size > 0:
                    lst_item = QListWidgetItem(cur_ev + "\tStarted")
                else:
                    lst_item = QListWidgetItem(cur_ev + "\tEmpty")
            self.lw_events.addItem(lst_item)
            if self.activeEvent == cur_ev:
                self.lw_events.setCurrentItem(lst_item)
                self.pb_choose.setEnabled(True)
                # check to see if samples exist
                sample_sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE event_id=" + cur_ev)
                samp_query = self.db.dbQuery(sample_sql)
                if samp_query.first():
                    self.pb_edit.setEnabled(False)
                else:
                    self.pb_edit.setEnabled(True)

    def check_events(self):
        """
        checks to enable the edit number button if there are no samples associated with the
        event and enables the choose button
        :return:
        """
        try:
            if self.lw_events.currentItem().text().contains("Empty"):
                self.pb_edit.setEnabled(True)
            elif self.lw_events.currentItem().text().contains("Current"):
                # check to see if samples exist
                temp_event = self.lw_events.currentItem().text().split("\t")[0]
                query = self.db.dbQuery("SELECT * FROM Samples WHERE event_id = " + str(temp_event))
                if query.first():
                    self.pb_edit.setEnabled(False)
                else:
                    self.pb_edit.setEnabled(True)
            else:
                self.pb_edit.setEnabled(False)
        except:
            self.pb_edit.setEnabled(False)
        self.pb_choose.setEnabled(True)

    def choose_event(self):
        """
        sets the currently selected event from the list as the tow to use and updates the application_configuration
        and the events table
        :return:
        """
        temp_event = self.lw_events.currentItem().text().split("\t")
        self.activeEvent = temp_event[0]
        update_ac_sql = ("UPDATE " + self.schema + ".application_configuration SET parameter_value='"
                         + str(self.activeEvent) + " WHERE parameter='ActiveEvent'")
        self.db.dbQuery(update_ac_sql)
        update_ev_sql = ("UPDATE " + self.schema + ".events SET performance_code=-99 WHERE event_id="
                         + self.activeEvent)
        self.db.dbQuery(update_ev_sql)
        self.accept()

    def add_event(self):
        """
        adds an event to the database without associated data to get CLAMS going - NC data will be added later
        :return:
        """
        new_event = AddEvent(self.numpad)
        if new_event.result() == 1:
            self.activeEvent = new_event.activeEvent
            other_params = AddParams(self)
            self.gear = other_params.gear
            self.event_type = other_params.event_type
            self.sci = other_params.sci
            cont = 0

            # check if event already exists in database for this gear and survey
            dup_sql = ("SELECT event_id FROM " + self.schema + ".events WHERE survey=" + self.survey + " AND ship="
                       + self.ship + " AND event_id=" + self.activeEvent + " AND gear='" + self.gear + "'")
            dup_query = self.db.dbQuery(dup_sql)
            pres, = dup_query.first()
            if not pres:
                cont = 1
                values = "(" + self.ship + "," + self.survey + "," + self.activeEvent + ",'" + self.gear + "'," \
                         + self.event_type + ",-99,'" + self.sci + "','')"
                insert_sql = ("INSERT INTO " + self.schema + ".events (ship, survey, event_id, gear, event_type, "
                                                             "performance_code, scientist, comments) VALUES " + values)
                self.db.dbQuery(insert_sql)

                # insert into the event_data table

                # get the current date
                cur_date = int(dt.strftime(dt.now(), "%Y%m%d"))

                # enter the date of the event (EventOverallDate)
                date_values = "(" + self.ship + "," + self.survey + "," \
                              + self.activeEvent + ",'Codend','EventOverallDate'," + str(cur_date) + ")"
                date_sql = ("INSERT INTO " + self.schema + ".event_data (Ship, Survey, Event_Id, Partition, "
                                                           "Event_Parameter, Parameter_Value) VALUES %s" % date_values)
                self.db.dbQuery(date_sql)

                # enter the trawl scientist
                sci_vals = "(" + self.ship + "," + self.survey + "," \
                           + self.activeEvent + ",'Codend','TrawlScientist','" + self.sci + "')"
                sci_sql = ("INSERT INTO " + self.schema + ".event_data (Ship, Survey, Event_Id, Partition, "
                                                          "Event_Parameter, Parameter_Value) VALUES %s" % sci_vals)
                self.db.dbQuery(sci_sql)

                # set the current event in the application_configuration table
                update_sql = ("UPDATE " + self.schema + ".application_configuration SET parameter_value='"
                              + self.activeEvent + "' WHERE parameter = 'ActiveEvent'")
                self.db.dbQuery(update_sql)
                self.set_cur_event()
            else:
                cont = 0
                msg = "That event already exists in the database"
                self.message.setMessage(self.errorIcons[0], self.errorSounds[0], msg)
                self.message.show()
                print("duplicate entry")
            if cont == 1:
                self.accept()

    def check_active(self):
        """
        checks the shown events
        :return:
        """
        if self.cb_active.isChecked():
            # show only active events
            self.active = True
        else:
            # show all events
            self.active = False
        self.set_cur_event()

    def edit_event_num(self):
        """
        edits the event number if there are no samples associated with the event
        :return:
        """
        # pull event number out of list item
        temp_event = self.lw_events.currentItem().text().split("\t")[0]
        # check again to make sure there are no samples for the event number
        query = self.db.dbQuery("SELECT * FROM Samples WHERE event_id = " + str(temp_event))
        if query.first():
            # if there are samples, send up msg
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                    "There are samples associated with this event "
                                    "number, so it cannot be changed. Please write "
                                    "down the issue in the lab notebook.")
        else:
            # if no samples
            # send up numpad to get new number
            self.numpad.msgLabel.setText("Enter the new event number")
            if not self.numpad.exec():
                return
            value = self.numpad.value
            # check that number isn't in the database
            query_2 = self.db.dbQuery("SELECT * FROM Events WHERE event_id = " + str(value))
            if query_2.first():
                # if there is an event, send up msg
                self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "That event is already in the "
                                                                                 "database, please choose another")
                self.message.exec()
            else:
                # if not update the event_data table
                try:
                    self.db.dbQuery("ALTER TABLE Event_Data disable constraint EVENTS_EVENT_DATA_FK")
                    self.db.dbQuery("UPDATE Event_Data SET event_id = " + str(value) + " WHERE event_id = "
                                    + str(temp_event))
                    self.db.dbQuery("ALTER TABLE Event_Data enable constraint EVENTS_EVENT_DATA_FK")
                    # update the event table
                    try:
                        self.db.dbQuery("UPDATE Events SET event_id = " + str(value) + " WHERE event_id = "
                                        + str(temp_event))
                        # update the application_configuration table
                        try:
                            self.db.dbQuery("UPDATE Application_Configuration SET parameter_value = " + str(value) +
                                            "WHERE parameter = 'ActiveEvent'")
                            self.activeEvent = value
                            self.set_cur_event()
                        except:
                            self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                                    "Could not update Active Event with the new event id")
                            self.message.exec()
                    except:
                        self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Could not update Events "
                                                                                         "table with the new event id")
                        self.message.exec()
                except:
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Could not update Event_Data "
                                                                                     "table with the new event id")
                    self.message.exec()


class AddEvent(QDialog, ui_FEATEventNum.Ui_Dialog):
    def __init__(self, numpad):
        """
        allows user to add an event
        """
        super(AddEvent, self).__init__()
        self.setupUi(self)

        self.numpad = numpad
        self.activeEvent = ''

        # set slots
        self.pb_ok.clicked.connect(self.add_event)
        self.pb_cancel.clicked.connect(self.reject)
        self.pb_num.clicked.connect(self.set_event)

        self.exec()

    def set_event(self):
        """
        sets the event by calling the numpad and changing the text of the button
        :return:
        """
        self.numpad.msgLabel.setText("Enter event num")
        if not self.numpad.exec():
            return
        self.pb_num.setText(self.numpad.value)

    def add_event(self):
        """
        sets the activeEvent and accepts to send back to enter into database
        :return:
        """
        self.activeEvent = str(self.pb_num.text())
        self.accept()


class AddParams(QDialog, ui_FEATEventParams.Ui_Dialog):
    def __init__(self, parent):
        """
        allows user to add an event
        """
        # TODO: take trawl scientist out of add event
        #  call superclass init methods and GUI form setup method
        super(AddParams, self).__init__()
        self.setupUi(self)

        # set up variables
        self.db = parent.db
        self.gear = ""
        self.event_type = ""
        self.sci = "Check NC"

        # fill combo boxes
        self.fill_combos()

        # hide the trawl scientist
        # self.label_3.hide()
        # self.cb_sci.hide()

        # set slots
        self.pb_ok.clicked.connect(self.add_params)
        self.pb_cancel.clicked.connect(self.reject)

        self.exec()

    def fill_combos(self):
        """
        fills the combo boxes for the parameters (gear, event type, and scientist
        :return:
        """
        # get gear list
        gear_sql = "SELECT gear FROM GEAR WHERE active=1"
        gear_query = self.db.dbQuery(gear_sql)
        for gear, in gear_query:
            self.cb_gear.addItem(gear)

        # get event_types
        e_sql = "SELECT description FROM EVENT_TYPES"
        e_query = self.db.dbQuery(e_sql)
        for description, in e_query:
            self.cb_event_type.addItem(description)

        # get scientists
        scis = self.db.dbQuery("SELECT scientist FROM PERSONNEL WHERE active=1")
        for sci, in scis:
            self.cb_sci.addItem(sci)

    def add_params(self):
        """
        adds the parameters to the self and accepts to close the dialog
        :return:
        """
        self.gear = self.cb_gear.currentText()
        self.sci = self.cb_sci.currentText()
        desc = self.cb_event_type.currentText()
        # get event_type_id
        ev_sql = ("SELECT event_type FROM EVENT_TYPES where description = '" + desc + "'")
        ev_query = self.db.dbQuery(ev_sql)
        self.event_type, = ev_query.first()
        self.accept()
