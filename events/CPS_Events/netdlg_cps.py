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
.. module:: netdlg_cps

    :synopsis: netdlg_cps is a dialog that collects net mensuration details during a FEAT event
    :createdby: Alicia Billings <alicia.billings@noaa.gov>

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
from PyQt6.QtWidgets import *
from ui import ui_NetDlg_CPS
import numpad

class NetDlgCPS(QDialog, ui_NetDlg_CPS.Ui_netDlg):

    def __init__(self, parent=None):
        super(NetDlgCPS, self).__init__(parent)
        self.setupUi(self)
        self.settings = parent.settings
        self.db = parent.db
        self.activeEvent = parent.activeEvent
        self.survey = parent.survey
        self.schema = parent.schema
        self.ship = parent.ship
        self.reloaded = parent.reloaded
        self.cur_time = parent.cur_time
        self.net_btn = parent.net_btn
        self.edit_flag = False

        self.buttons = {self.pb_door_spread: 'DoorSpread',
                        self.pb_fr: 'Footrope'}
        
        self.numpad = numpad.NumPad(self)
        numpadDeviceId = 3

        # holds door spread and foot rope depth value
        self.values = {}

        #  set up signals
        for btn in self.buttons:
            btn.clicked.connect(self.get_value)
            btn.setText('')
        self.cancelBtn.clicked.connect(self.doneClicked)
        self.saveButton.clicked.connect(self.add_record)
    
    def setTime(self, time):
        self.cur_time = time

    def reload_data(self, cur_time=None):
        """
        populates with existing data. This is used when
        an event is reloaded and the dialog state has to be updated from the db.
        """
        self.pb_door_spread.setText('')
        self.pb_fr.setText('')
        self.values = {}
        # get the current time, if sent
        if cur_time:
            self.cur_time = cur_time

            sql = ("SELECT measurement_type, measurement_value FROM " + self.schema + ".EVENT_STREAM_DATA WHERE" +
                " SHIP=" + self.ship + 
                " and survey=" + self.survey +
                " and event_id=" + self.activeEvent +
                " and time_stamp=" + self.db.createTimeStamp(self.cur_time) + 
                " and measurement_type in ('DoorSpread', 'Footrope')")
            query = self.db.dbQuery(sql)
            for val in query:
                if val[0] == 'DoorSpread':
                    self.pb_door_spread.setText(val[1] if val[1] else None)
                else:
                    self.pb_fr.setText(val[1] if val[1] else None)

    def edit_data(self):
        """
        sets the text of the buttons depending on the row selected and sets the edit flag
        :return:
        """

    def get_value(self):
        """
        set up a numpad for the button pressed
        :return:
        """
        cur_btn = self.sender()
        measurementType = self.buttons[cur_btn]
        self.numpad.msgLabel.setText("Enter value")
        if not self.numpad.exec():
            return

        val = self.numpad.value
        if val:
            self.values[measurementType] = self.numpad.value
            cur_btn.setText(self.numpad.value)

    def add_record(self):
        """
        adds a total record to the database or updates if it is flagged for editing
        :return:
        """
        for key in self.values:
            if self.values[key]:
                sql = ("SELECT * FROM " + self.schema + ".event_stream_data WHERE" + 
                       " event_id=" + self.activeEvent + 
                       " AND measurement_type='" + key + 
                       "' AND time_stamp=" + self.db.createTimeStamp(self.cur_time))
                query = self.db.dbQuery(sql)
                val = query.first()
                if val[0] != None and len(val) > 0:
                    sql = ("UPDATE " + self.schema + ".event_stream_data" + 
                           " SET measurement_value=" + self.values[key] +
                           " WHERE event_id=" + self.activeEvent + 
                           " AND measurement_type='" + key +
                           "' AND time_stamp=" + self.db.createTimeStamp(self.cur_time))
                    self.db.dbExec(sql)
                else:
                    # Enter data into event_stream_data table
                    sql = ("INSERT INTO " + self.schema + ".event_stream_data (ship,survey, " +
                                            "event_id, device_id, time_stamp, measurement_type, measurement_value) " +
                                            "VALUES (" + self.ship + ", " + self.survey + ", " + self.activeEvent +
                                            ", 3, " + self.db.createTimeStamp(self.cur_time) +
                                            ", '" + key + "', '" + self.values[key] +"')")
                    self.db.dbExec(sql)
        self.close()

    def doneClicked(self):
        """
        resets the button text, clears the selection, and closes the dialog
        :return:
        """
        self.close()

    def closeEvent(self, event=None):
        self.accept()
