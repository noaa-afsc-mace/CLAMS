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
.. module:: EventSelDlg

    :synopsis: EventSelDlg presents the event selection dialog.
               It will show only events that retain catch when used
               to start processing catch and all events when used
               to start/edit a new event.

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
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
from ui import ui_EventSelDlg

class EventSelDlg(QDialog, ui_EventSelDlg.Ui_eventselDlg):

    def __init__(self, parent, catchOnly=True):
        '''
        set catchOnly to False to show all events and True to only
        show events that retain catch.
        '''

        #  call the superclass inits and create the UI
        super(EventSelDlg, self).__init__(parent)
        self.setupUi(self)

        #  set some attributes
        self.activeEvent = None
        self.db = parent.db
        self.ship=parent.ship
        self.survey=parent.survey
        self.eventTable.setRowCount(0)
        self.settings = parent.settings
        self.schema = parent.schema

        #  set up the table
        self.eventTable.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.eventTable.verticalHeader().setVisible(False)
        self.eventTable.scrollToBottom()

        #  connect signals and slots
        self.newEventBtn.clicked.connect(self.getNewEvent)
        self.cancelBtn.clicked.connect(self.goExit)
        self.okBtn.clicked.connect(self.goOn)
        self.eventTable.itemSelectionChanged.connect(self.getPrevEvent)

        #  query out the events that used gear that can retain catch and add to
        #  the table.
        if catchOnly:
            sql = ("SELECT a.performance_code, a.event_id, a.gear FROM (SELECT performance_code, event_id, gear, " +
                    "ship, survey FROM " + self.schema + ".events) a JOIN (SELECT gear, gear_type " +
                    "FROM " + self.schema + ".gear) b ON a.gear = b.gear JOIN (SELECT gear_type, " +
                    "retains_catch from  " + self.schema + ".gear_types) c ON b.gear_type = c.gear_type " +
                    "WHERE a.ship = " + parent.ship + " AND a.survey= " + parent.survey +
                    " AND c.retains_catch > 0  ORDER BY event_id ASC")
        else:
            sql = ("SELECT a.performance_code, a.event_id, a.gear FROM (SELECT performance_code, event_id, gear, " +
                    "ship, survey FROM " + self.schema + ".events) a JOIN (SELECT gear, gear_type " +
                    "FROM " + self.schema + ".gear) b ON a.gear = b.gear WHERE a.ship = " + parent.ship +
                    " AND a.survey= " + parent.survey + " ORDER BY event_id ASC")
        eventQuery = self.db.dbQuery(sql)

        #  loop through the events
        rowCount = 0
        for perf_code, event_id, gear in eventQuery:
            #  add the event number
            self.eventTable.insertRow(rowCount)
            self.eventTable.setItem(rowCount, 0, QTableWidgetItem(event_id))

            if catchOnly:
                #  check if the event is "closed" defined by having a HB time
                sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE event_parameter IN ('Haulback', 'HB')" +
                       " AND event_id=" + event_id + " AND ship=" + parent.ship +
                       " AND survey=" + parent.survey)
                query = self.db.dbQuery(sql)
                hbTime, = query.first()
                # AB added to show which are aborted tows
                if int(perf_code) < 0 and int(perf_code) != -99:
                    hbTime = 'Aborted Operation'
                if hbTime:
                    #  event is closed - insert the gear in black text
                    self.eventTable.setItem(rowCount, 1, QTableWidgetItem(gear))
                    self.eventTable.setItem(rowCount, 2, QTableWidgetItem(hbTime))
                else:
                    #  event is not closed - insert the gear text with a pink background
                    item = QTableWidgetItem(gear)
                    brush = QBrush(QColor(250, 200, 200))
                    brush.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(brush)
                    self.eventTable.setItem(rowCount, 1, item)

            else:
                #  For non catch events, "closed" is harder to define. We'll say if EQ, Timestamp,
                #  or Released exist in the event_data table we'll call the event closed.
                sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE (event_parameter='EQ'" +
                        " OR event_parameter = 'TimeStamp' OR event_parameter = 'Released') "
                        " AND event_id=" + event_id + " AND ship=" + parent.ship +
                        " AND survey=" + parent.survey)
                query = self.db.dbQuery(sql)
                evTime, = query.first()

                if evTime:
                    #  event is closed - insert the gear in black text
                    self.eventTable.setItem(rowCount, 1, QTableWidgetItem(gear))
                    self.eventTable.setItem(rowCount, 2, QTableWidgetItem(evTime))
                else:
                    #  event is not closed - insert the gear text with a pink background
                    item = QTableWidgetItem(evTime)
                    brush = QBrush(QColor(250, 200, 200))
                    brush.setStyle(Qt.BrushStyle.SolidPattern)
                    item.setBackground(brush)
                    self.eventTable.setItem(rowCount, 1, item)

            #  increment the row counter
            rowCount += 1

        #  resize the columns and scroll to the bottom to show the most recent events
        self.eventTable.resizeColumnsToContents()
        self.eventTable.scrollToBottom()
        self.eventTable.setRowCount(rowCount)

        #  stuff I tried to get the scrollbar to appear but seems to have no effect
        self.eventTable.verticalScrollBar().setSingleStep(1)
        self.eventTable.verticalScrollBar().setPageStep(10)
        self.eventTable.verticalScrollBar().setVisible(True)
        self.eventTable.verticalScrollBar().setMinimumWidth(50)


    def getNewEvent(self):
        '''getNewEvent sets the active event to the max event ID + 1

        '''
        #  get the last event ID
        sql = ("SELECT MAX(event_id) FROM " + self.schema + ".events WHERE survey ="+
                self.survey + " and ship= " + self.ship)
        query = self.db.dbQuery(sql)
        lastEvent, = query.first()
        if lastEvent is None:
            lastEvent = 0
        else:
            lastEvent = int(lastEvent)

        #  set the active event to the max + 1
        self.activeEvent = str(lastEvent + 1)

        #  not sure why this is inserted into the table here?
        self.eventTable.insertRow(self.eventTable.rowCount())
        self.eventTable.setItem(self.eventTable.rowCount()-1, 0,
                QTableWidgetItem(self.activeEvent))

        #  set the reloaded state to false since this is a new event
        self.reloaded = False

        #  close the dialog
        self.accept()


    def getPrevEvent(self):
        '''getPrevEvent sets the active event to the one selected in
        the table.
        '''

        #  get the event ID from the table and set the reloaded state
        self.activeEvent = self.eventTable.item(self.eventTable.currentRow(),
                0).text()
        self.reloaded = True


    def goOn(self):
        self.accept()


    def goExit(self):
        self.reject()

