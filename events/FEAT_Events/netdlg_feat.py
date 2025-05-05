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
.. module:: netdlg_feat

    :synopsis: netdlg_feat is a dialog that collects net mensuration details during a FEAT event
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
from ui import ui_NetDlg_FEAT
import numpad
import keypad


class NetDlgFEAT(QDialog, ui_NetDlg_FEAT.Ui_netDlg):

    def __init__(self, parent=None):
        super(NetDlgFEAT, self).__init__(parent)
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

        self.buttons = {self.pb_nh: 'num',
                        self.pb_nw: 'num',
                        self.pb_hd: 'num',
                        self.pb_wo: 'num',
                        self.pb_com: 'key'}
        self.measurements = ['NetVerticalOpening', 'NetHorizontalOpening', 'HeadRopeDepth',
                             'TrawlWireOut', 'EventComments']
        self.timeDlg = parent.timeDlg
        self.set_time = None
        self.edit_flag = False
        self.doneEditing = False
        
        self.numpad = numpad.NumPad(self)
        self.defTime = QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss.zzz')

        #  set up signals
        for btn in self.buttons:
            btn.clicked.connect(self.get_value)
            btn.setText('')
        self.okBtn.clicked.connect(self.doneClicked)
        self.addRecordBtn.clicked.connect(self.add_record)
        self.netTable.itemSelectionChanged.connect(self.edit_data)
        
        if self.reloaded:
            self.reload_data()
            sql = ("SELECT to_char(min(time_stamp), 'MMDDYYYY HH24:MI:SS.FF3') " +
                    "FROM " + self.schema + ".event_stream_data WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeEvent)
            query = self.db.dbQuery(sql)
            timeStamp, = query.first()
            self.minTime = QDateTime().fromString(timeStamp, 'MMddyyyy hh:mm:ss.zzz')
            sql = ("SELECT to_char(max(time_stamp), 'MMDDYYYY HH24:MI:SS.FF3') FROM " +
                    self.schema + ".event_stream_data WHERE ship=" + self.ship + " AND survey=" +
                    self.survey + " AND event_id=" + self.activeEvent)
            query = self.db.dbQuery(sql)
            timeStamp, = query.first()
            self.maxTime = QDateTime().fromString(timeStamp, 'MMddyyyy hh:mm:ss.zzz')

    def reload_data(self, btn=None, cur_time=None):
        """
        populates the table with any existing data. This is used when
        an event is reloaded and the dialog state has to be updated from the db.
        """
        # remove any newline characters from the btn text and set the self.net_btn variable
        if btn:
            btn = btn.replace('\n', ' ')
            self.net_btn = btn

            # clear the button texts
            self.pb_nh.setText('')
            self.pb_nw.setText('')
            self.pb_hd.setText('')
            self.pb_wo.setText('')
            self.pb_com.setText('')

            # if the button is the net dimensions button, do not allow to add a new record since we associate any
            # net dimension entries with an event (TD, HB, COM, etc)
            if 'net' in self.net_btn.lower():
                self.pb_nh.setEnabled(False)
                self.pb_nw.setEnabled(False)
                self.pb_hd.setEnabled(False)
                self.pb_wo.setEnabled(False)
                self.pb_com.setEnabled(False)
                self.addRecordBtn.setEnabled(False)
            else:
                self.pb_nh.setEnabled(True)
                self.pb_nw.setEnabled(True)
                self.pb_hd.setEnabled(True)
                self.pb_wo.setEnabled(True)
                self.pb_com.setEnabled(True)
                self.addRecordBtn.setEnabled(True)

        # get the current time, if sent
        if cur_time:
            self.cur_time = cur_time

        # get times of existing measurements
        self.netTable.clearContents()
        self.netTable.setRowCount(0)
        meas_str = ', '.join("'{0}'".format(m) for m in self.measurements)

        sql = ("SELECT to_char(time_stamp,'MMDDYYYY HH24:MI:SS.FF3') FROM " +
                self.schema + ".event_stream_data WHERE ship=" + self.ship + " AND survey=" +
                self.survey + " AND event_id=" + self.activeEvent + " AND measurement_type " +
                "IN (" + meas_str + ") GROUP BY time_stamp ORDER BY time_stamp ASC")
        query = self.db.dbQuery(sql)

        # for each time, insert the associated data in the table widget
        row = 0
        for timestamp, in query:
            # get event name
            ev_sql = ("SELECT event_parameter FROM " + self.schema
                      + ".event_data WHERE parameter_value='" + timestamp + "'")
            ev_query = self.db.dbQuery(ev_sql)
            ev_type, = ev_query.first()
            self.netTable.insertRow(self.netTable.rowCount())
            self.netTable.setItem(row, 0, QTableWidgetItem(ev_type))
            for i in range(len(self.measurements)):
                sql = ("SELECT measurement_value FROM " + self.schema + ".event_stream_data WHERE ship=" +
                        self.ship + " AND survey=" + self.survey + " AND event_id=" +
                        self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                        "' AND time_stamp=to_timestamp('" + timestamp + "')")
                dataQuery = self.db.dbQuery(sql)
                val, = dataQuery.first()
                if val:
                    self.netTable.setItem(row, i+1, QTableWidgetItem(val))
                else:
                    self.netTable.setItem(row, i+1, QTableWidgetItem(''))

            if timestamp == self.cur_time:
                # find the row that matches the button
                for row in range(self.netTable.rowCount()):
                    item = self.netTable.item(row, 0).text()
                    if item == self.net_btn:
                        self.netTable.selectRow(row)
            else:
                self.edit_flag = False
                self.addRecordBtn.setText('Add\nRecord')
            row += 1
        self.netTable.resizeColumnsToContents()
        self.netTable.scrollToBottom()

    def edit_data(self):
        """
        sets the text of the buttons depending on the row selected and sets the edit flag
        :return:
        """

        if self.doneEditing:
            self.doneEditing = False
            return
        # set the text of the buttons to the entered text and enable the button
        for i in range(len(self.measurements)):
            if self.netTable.item(self.netTable.currentRow(), i+1):
                list(self.buttons)[i].setText(self.netTable.item(self.netTable.currentRow(), i+1).text())
                list(self.buttons)[i].setEnabled(True)
        self.edit_flag = True
        self.addRecordBtn.setText('Update \nRecord')
        # enable the update button
        self.addRecordBtn.setEnabled(True)

    def get_value(self):
        """
        set up either a numpad or a keypad for the button pressed
        :return:
        """

        cur_btn = self.sender()
        cur_popup = self.buttons[cur_btn]
        if cur_popup == 'num':
            self.numpad.msgLabel.setText("Enter value")
            if not self.numpad.exec():
                return
            cur_btn.setText(self.numpad.value)
        else:
            cur_txt = cur_btn.text()
            keyDlg = keypad.KeyPad(cur_txt, self)
            if not keyDlg.exec():
                return
            if keyDlg.okFlag:
                text = keyDlg.dispEdit.toPlainText()
                cur_btn.setText(text)

    def add_record(self):
        """
        adds a total record to the database or updates if it is flagged for editing
        :return:
        """
        # update record
        if self.edit_flag:
            for i in range(len(self.measurements)):
                cur_btn = list(self.buttons.keys())[i]
                if cur_btn.text() != '':
                    # get the trawl event type for the selected row
                    ev_type = self.netTable.item(self.netTable.currentRow(), 0).text()
                    # get the timestamp for the event type
                    ev_sql = ("SELECT parameter_value "
                              "FROM " + self.schema + ".event_data WHERE ship=" + self.ship + " AND survey="
                              + self.survey + " AND event_id=" + self.activeEvent +
                              " AND event_parameter='" + ev_type + "'")
                    ev_query = self.db.dbQuery(ev_sql)
                    self.cur_time, = ev_query.first()
                    stream_sql = ("SELECT event_id FROM " + self.schema + ".event_stream_data WHERE ship=" +
                                  self.ship + " AND survey=" + self.survey + " AND event_id=" +
                                  self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                                  "' AND time_stamp=to_timestamp('" + self.cur_time + "','MMDDYYYY HH24:MI:SS.FF3')")
                    stream_query = self.db.dbQuery(stream_sql)
                    ev, = stream_query.first()
                    if not ev:
                        #  this is a new measurement, insert it
                        sql = ("INSERT INTO " + self.schema + ".event_stream_data (ship,survey, " +
                                "event_id, device_id, time_stamp, measurement_type, measurement_value) " +
                                "VALUES (" + self.ship + ", " + self.survey + ", " + self.activeEvent +
                                ", 0, to_timestamp('" + self.cur_time + "', 'MMDDYYYY HH24:MI:SS.FF3'), '"
                               + self.measurements[i] + "', '" + cur_btn.text()+"')")
                        self.db.dbExec(sql)
                    else:
                        #  measurement exists, update the value
                        sql = ("UPDATE " + self.schema + ".event_stream_data SET measurement_value='" +
                                cur_btn.text() + "' WHERE ship=" + self.ship + " AND survey=" +
                                self.survey + " AND event_id=" + self.activeEvent +
                                " AND measurement_type='" + self.measurements[i] +
                                "' AND time_stamp=to_timestamp('" + self.cur_time + "','MMDDYYYY HH24:MI:SS.FF3')")
                        self.db.dbExec(sql)
                else:
                    sql = ("DELETE FROM " + self.schema + ".event_stream_data WHERE ship=" +
                            self.ship + " AND survey=" + self.survey + " AND event_id=" +
                            self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                            "' AND time_stamp=to_timestamp('" + self.cur_time + "','MMDDYYYY HH24:MI:SS.FF3')")
                    self.db.dbExec(sql)

            self.edit_flag = False
            self.addRecordBtn.setText('Add \nRecord')
            self.doneEditing = True
            self.netTable.clearSelection()
        # new record
        else:
            i = 0
            for btn in self.buttons.keys():
                if not btn.text() == '':
                    sql = ("INSERT INTO " + self.schema + ".event_stream_data " +
                           "(ship, survey, event_id, device_id, time_stamp, measurement_type, measurement_value) "
                           "VALUES (" + self.ship + ", " + self.survey + ", " + self.activeEvent +
                           ", 0 , to_timestamp('" + self.cur_time + "', 'MMDDYYYY HH24:MI:SS.FF3'), '"
                           + self.measurements[i] + "', '" + btn.text() + "')")
                    print(sql)
                    self.db.dbExec(sql)
                i += 1
        self.reload_data()

    def doneClicked(self):
        """
        resets the button text, clears the selection, and closes the dialog
        :return:
        """
        self.addRecordBtn.setText('Add\nRecord')
        self.netTable.clearSelection()
        self.close()

    def closeEvent(self, event=None):
        self.accept()
