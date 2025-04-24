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
.. module:: netdlg

    :synopsis: netdlg is a dialog that collects net opening dimensions,
               headrope depth and wire out and is used during the trawl event
               to periodically collect this info between EQ and Haulback.

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
from ui import ui_NetDlg
import numpad

class NetDlg(QDialog, ui_NetDlg.Ui_netDlg):

    def __init__(self, parent=None):
        super(NetDlg, self).__init__(parent)
        self.setupUi(self)
        self.settings = parent.settings
        self.db = parent.db
        self.activeEvent = parent.activeEvent
        self.survey = parent.survey
        self.schema = parent.schema
        self.ship = parent.ship
        self.defTime = QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss.zzz')
        self.reloaded = parent.reloaded
        self.buttons = [self.btn1,self.btn2,self.btn3,self.btn4]
        self.measurements = ['NetVerticalOpening', 'NetHorizontalOpening',
                'HeadRopeDepth','TrawlWireOut']
        self.timeDlg = parent.timeDlg
        self.setTime = None
        self.editFlag = False
        self.doneEditing = False
        self.numpad = numpad.NumPad(self)

        #  set up signals
        for btn in self.buttons:
            btn.clicked.connect(self.getValue)
            btn.setText('')

        self.okBtn.clicked.connect(self.doneClicked)
        self.addRecordBtn.clicked.connect(self.addRecord)
        self.deleteBtn.clicked.connect(self.deleteRecord)
        self.netTable.itemSelectionChanged.connect(self.editData)

        if self.reloaded:
            self.reloadData()
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


    def reloadData(self):
        '''
        reloadData populates the table with any existing data. This is used when
        an event is reloaded and the dialog state has to be updated from the db.
        '''
        # get times of existing measurements
        self.netTable.clearContents()
        self.netTable.setRowCount(0)
        sql = ("SELECT to_char(time_stamp,'MMDDYYYY HH24:MI:SS.FF3') FROM " +
                self.schema + ".event_stream_data WHERE ship=" + self.ship + " AND survey=" +
                self.survey + " AND event_id=" + self.activeEvent + " AND measurement_type " +
                "IN('NetVerticalOpening','NetHorizontalOpening','HeadRopeDepth'," +
                "'TrawlWireOut') GROUP BY time_stamp ORDER BY time_stamp ASC")
        print(sql)
        query = self.db.dbQuery(sql)

        #  for each time, insert the associated data in the table widget
        row=0
        for timestamp, in query:
            self.netTable.insertRow(self.netTable.rowCount())
            self.netTable.setItem(row, 0, QTableWidgetItem(timestamp))
            for i in range(len(self.measurements)):
                sql = ("SELECT measurement_value FROM " + self.schema + ".event_stream_data WHERE ship=" +
                        self.ship + " AND survey=" + self.survey + " AND event_id=" +
                        self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                        "' AND time_stamp=to_timestamp('" + timestamp + "','MMDDYYYY HH24:MI:SS.FF3')")
                print(sql)
                dataQuery = self.db.dbQuery(sql)
                val, = dataQuery.first()
                if val:
                    self.netTable.setItem(row, i+1,QTableWidgetItem(val))
                else:
                    self.netTable.setItem(row, i+1,QTableWidgetItem(''))
            row += 1

        self.netTable.resizeColumnsToContents()
        self.netTable.scrollToBottom()


    def editData(self):

        if self.doneEditing:
            self.doneEditing=False
            return
        for i in range(4):
            if self.netTable.item(self.netTable.currentRow(), i+1):
                self.buttons[i].setText(self.netTable.item(self.netTable.currentRow(), i+1).text())
        self.editFlag=True
        self.addRecordBtn.setText('Update \nRecord')


    def deleteRecord(self):
        if self.netTable.currentRow() > -1:
            delTime = self.netTable.item(self.netTable.currentRow(),0).text()
            sql = ("DELETE FROM " + self.schema + ".event_stream_data WHERE measurement_type IN" +
                    "('NetVerticalOpening','NetHorizontalOpening','HeadRopeDepth','TrawlWireOut') " +
                    "AND time_stamp=to_timestamp('" + delTime + "', 'MMDDYYYY HH24:MI:SS.FF3')")
            self.db.dbExec(sql)
            self.reloadData()
            self.addRecordBtn.setText('Add \nRecord')
            self.editFlag=False


    def getValue(self):
        self.numpad.msgLabel.setText("Enter value")
        if not self.numpad.exec():
            return
        ind = self.buttons.index(self.sender())
        self.buttons[ind].setText(self.numpad.value)


    def addRecord(self):

        # update record
        if self.editFlag:
            for i in range(len(self.measurements)):
                if not self.buttons[i].text() == '':
                    sql = ("SELECT event_id FROM " + self.schema + ".event_stream_data WHERE ship=" +
                            self.ship + " AND survey=" + self.survey + " AND event_id=" +
                            self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                            "' AND time_stamp=to_timestamp('" +
                            self.netTable.item(self.netTable.currentRow(), 0).text() +
                            "','MMDDYYYY HH24:MI:SS.FF3')")
                    query = self.db.dbQuery(sql)
                    if not query.first():
                        #  this is a new measurement, insert it
                        sql = ("INSERT INTO " + self.schema + ".event_stream_data (ship,survey," +
                                "event_id,device_id,time_stamp,measurement_type,measurement_value) " +
                                "VALUES (" + self.ship + "," + self.survey + "," + self.activeEvent +
                                ",0,to_timestamp('" + self.netTable.item(self.netTable.currentRow(), 0).text() +
                                "','MMDDYYYY HH24:MI:SS.FF3'),'" + self.measurements[i] + "','" +
                                self.buttons[i].text()+"')")
                        self.db.dbExec(sql)
                    else:
                        #  measurement exists, update the value
                        sql = ("UPDATE " + self.schema + ".event_stream_data SET measurement_value='" +
                                self.buttons[i].text() + "' WHERE ship=" + self.ship + " AND survey=" +
                                self.survey + " AND event_id=" + self.activeEvent +
                                " AND measurement_type='" + self.measurements[i] +
                                "' AND time_stamp=to_timestamp('" +
                                self.netTable.item(self.netTable.currentRow(), 0).text() +
                                "','MMDDYYYY HH24:MI:SS.FF3')")
                        self.db.dbExec(sql)
                else:
                    sql = ("DELETE FROM " + self.schema + ".event_stream_data WHERE ship=" +
                            self.ship + " AND survey=" + self.survey + " AND event_id=" +
                            self.activeEvent + " AND measurement_type='" + self.measurements[i] +
                            "' AND time_stamp=to_timestamp('" +
                            self.netTable.item(self.netTable.currentRow(), 0).text() +
                            "','MMDDYYYY HH24:MI:SS.FF3')")
                    self.db.dbExec(sql)

            self.editFlag=False
            self.addRecordBtn.setText('Add \nRecord')
            self.doneEditing=True
            self.netTable.clearSelection()

        else:# new record

            if self.reloaded:
                self.timeDlg.setTime(self.defTime)
                if self.timeDlg.exec():
                    if self.timeDlg.qTime<self.minTime or self.timeDlg.qTime>self.maxTime:
                        QMessageBox.critical(self, "ERROR", "<font size = 12> This time " +
                                "is not valid for this event_id.")
                        return
                    self.setTime = self.timeDlg.time

                else:
                    QMessageBox.critical(self, "ERROR", "<font size = 12> Must... Have... Time...")
                    return
            else:
                if self.setTime == None:
                    self.setTime = QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss.zzz')
            for i in range(4):
                if not self.buttons[i].text() == '':
                    sql = ("INSERT INTO " + self.schema + ".event_stream_data " +
                            "(ship,survey,event_id,device_id,time_stamp,measurement_type," +
                            "measurement_value) VALUES (" + self.ship + "," + self.survey +
                            "," + self.activeEvent + ",0,to_timestamp('" + self.setTime +
                            "','MMDDYYYY HH24:MI:SS.FF3'),'" + self.measurements[i] + "','" +
                            self.buttons[i].text()+"')")
                    print(sql)
                    self.db.dbExec(sql)

        self.setTime=None
        self.reloadData()

    def doneClicked(self):
        self.close()

    def closeEvent(self, event=None):
        self.accept()


