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
import importlib
from events import *
import eventseldlg
from ui import ui_EventLauncher


class EventLauncher(QDialog, ui_EventLauncher.Ui_EventLauncher):
    def __init__(self, parent):
        #  call the superclass inits and create the UI
        super(EventLauncher, self).__init__(parent)
        self.setupUi(self)

        #  store our reference to our database connection
        self.db = parent.db
        self.ship = parent.ship
        self.survey = parent.survey
        self.parent = parent
        # added by AB
        self.settings = parent.settings
        self.schema = parent.schema

        #  connect the cancel button signal
        self.pbCancel.clicked.connect(self.cancelClicked)

        #  create a list of button references ordered from top to bottom
        self.eventButtons = [self.pbEvent1, self.pbEvent2, self.pbEvent3, self.pbEvent4,
                             self.pbEvent5, self.pbEvent6, self.pbEvent7, self.pbEvent8]

        #  and connect their signals and initially hide all of them
        for button in self.eventButtons:
            button.clicked.connect(self.eventButtonClicked)
            button.hide()

        #  First extract the events from the application_events table and update the buttons
        #  Also build a dict of events and their package, module, and entry class names
        # 4/3/25 updated to get only ACTIVE
        nEvents = 0
        self.eventInfo = {}
        # sql = ("SELECT event_name, event_package, event_module, event_class, active FROM " +
        #        self.parent.schema + ".application_events ORDER BY event_name")
        sql = ("SELECT event_name, event_package, event_module, event_class, active FROM " +
               self.parent.schema + ".application_events WHERE active=1 ORDER BY event_name")
        eventQuery = self.db.dbQuery(sql)

        #  loop through the events and set the button text and other bits
        for event_name, event_package, event_module, event_class, active in eventQuery:
            self.eventButtons[nEvents].setText(event_name)
            if active.lower() in ['1', 'y']:
                self.eventButtons[nEvents].setEnabled(True)
                self.eventButtons[nEvents].show()
            else:
                self.eventButtons[nEvents].setEnabled(False)
            self.eventInfo[event_name] = [event_package, event_module, event_class]
            nEvents += 1

    def eventButtonClicked(self):
        event_name = QObject.sender(self).text()

        #  get the event details
        eventDetails = self.eventInfo[event_name]
        if 'nwfsc' in self.settings['OrganizationName'].lower():
            moduleName = 'events.' + eventDetails[0] + '.' + eventDetails[1]
            module = importlib.import_module(moduleName)
            module.FEATTrawlEvent(self.parent).exec()
        else:
            if 'trawl' in event_name.lower():
                #  create an instance of the event selection dialog showing
                #  only catch events
                eventSelectDialog = eventseldlg.EventSelDlg(self, catchOnly=True)
            else:
                #  create an instance of the event selection dialog
                eventSelectDialog = eventseldlg.EventSelDlg(self)

            #  display the event select dialog
            eventSelectDialog.exec()

            #  check if a event number was selected - exit if not
            if eventSelectDialog.activeEvent is None:
                return

            #  import the selected event form module
            moduleName = 'events.' + eventDetails[0] + '.' + eventDetails[1]
            module = importlib.import_module(moduleName)

            #  hide this dialog
            self.hide()

            #  and use the handle to instantiate and start the configured event form
            module.Event(eventSelectDialog.activeEvent, self.parent)

        #  close this dialog
        self.accept()

    def cancelClicked(self):
        self.reject()

    def closeEvent(self):
        self.reject()
