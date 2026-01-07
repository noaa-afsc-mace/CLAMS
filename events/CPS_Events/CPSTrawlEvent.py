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
.. module:: CPSTrawlEvent

    :synopsis: CPSTrawlEvent implements the trawl event form used by the
               FEAT group to collect metadata associated with a fishing
               operation. The form and code define the data to be collected
               and how and when it is collected.

               Events that retain catch (such as a trawl event) are the first
               step in collecting data with CLAMS.
    : created by: Alicia Billings <alicia.billings@noaa.gov>

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

# imports
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_CPSTrawlEvent
import devices
import numpad
import keypad
import messagedlg
import timedlg
from events.CPS_Events import netdlg_cps
from events.CPS_Events import metadlg
from events.CPS_Events import abortdlg
from events.CPS_Events import donedlg
from acquisition.SensorMonitor import SensorMonitor
from enum import Enum

class Events(Enum):
    NetInWater = 'Net In Water'
    EQ = 'Equilibrium'
    Haulback = 'Haul Back'
    NetOnDeck = 'Net On Deck'
    EQ10Min = 'EQ 10'
    EQ20Min = 'EQ 20'

# noinspection PyArgumentList,PyCallByClass,PyTypeChecker
class Event(QDialog, ui_CPSTrawlEvent.Ui_CPSTrawlEvent):
    def __init__(self, eventID, parent=None):
        """
        The CLAMS Trawl event dialog initialization method for CPS
        """
        #  call superclass init methods and GUI form setup method
        super(Event, self).__init__(parent)
        self.setupUi(self)

        gearTypeDefault = "MFT"
        self.abortPrefix = 'ABORT COMS: '

        # copy some properties from our parent
        self.db = parent.db
        self.schema = parent.schema
        self.activeEvent = eventID
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.workStation = parent.workStation
        self.testing = parent.testing

        # declare other variables
        self.meta_entered = False
        self.scientist = "Unknown"
        self.gear = gearTypeDefault
        self.displayMeasurements = ['Latitude', 'Longitude']
        self.meta_info = ['Operator', 'Collection', 'FishingMode']
        self.streamEQHBLogInterval = None
        self.streamSlowLogInterval = None
        self.reloaded = False
        self.comment = None
        self.sensorMonitor = None
        self.SCSisActive = False
        self.scsRetries = None
        self.sensorsStopping = None
        self.sensorsClosed = False
        self.deviceData = None
        self.lastSCSWriteTime = {}
        self.recordStream = True
        self.recording = False
        self.dispVector = {}
        self.cur_dt_row = 0
        self.clam_test = None
        self.perfCode = []
        self.btnTimes = {}
        self.cur_btn_txt = ''
        self.cur_time = None
        self.idxs = []
        self.net_btn = None
        self.fishingFlag = False
        self.event_entered = False
        self.current_scs = {}

        # set up the time to display for the timer
        self.niw_time = QTime(0, 0, 0)
        self.td_time = QTime(0, 0, 0)
        self.hb_time = QTime(0, 0, 0)
        self.nod_time = QTime(0, 0, 0)
        self.event_time = QTime(0, 0, 0)
        self.tow_time = QTime(0, 0, 0)

        # setup recurring dialogs
        self.numpad = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)
        self.timeDlg = timedlg.TimeDlg()
        self.timeDlg.enableGetTimeButton(False)
        self.netdlg = netdlg_cps.NetDlgCPS(self)

        # create a status bar to display the status of SCS
        self.statusBar = QStatusBar(self)
        self.statusLayout.addWidget(self.statusBar)

        # declare buttons
        self.buttons = [self.pb_niw, self.pb_eq, self.pb_eq10, self.pb_eq20, self.pb_hb, self.pb_nod]
        self.button_order = []

        self.streamWindowSeconds = 5

        # set the SCS logging rate default values
        self.streamEQHBLogInterval = 2
        self.streamSlowLogInterval = 5
        self.SCSLogInterval = self.streamSlowLogInterval

        # set up color palettes
        self.red = QPalette()
        self.red.setColor(QPalette.ColorRole.ButtonText, QColor(230, 0, 0))
        self.green = QPalette()
        self.green.setColor(QPalette.ColorRole.ButtonText, QColor(0, 230, 0))
        self.yellow = QPalette()
        self.yellow.setColor(QPalette.ColorRole.ButtonText, QColor(180, 180, 0))

        # set up the timers
        self.event_timer = QTimer(self)
        # timer that runs continuously after eq
        self.td_timer = QTimer(self)

        # set slots
        self.pb_metadata.clicked.connect(self.enter_metadata)
        self.pb_abort.clicked.connect(self.abort_operation)
        self.commentBtn.clicked.connect(self.add_comment)
        self.doneBtn.clicked.connect(self.finish_event)
        self.dataTable.itemSelectionChanged.connect(self.edit_dims)
        for b in self.buttons:
            b.clicked.connect(self.set_event)

        # set average values to display
        self.avgLabels = ['AvgSOG', 'AvgHeading', 'AvgWindSpeed', 'AvgBottomDepth18',
                          'AvgSST-TSG45', 'AvgSalinity-TSG45', 'AvgWireout-Block', 'AvgSTW']

        # set up the initialization timer
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.init_trawl_event_dialog)
        initTimer.start(0)

    def init_trawl_event_dialog(self):
        """
        shows the FEAT trawl form - the active event is set in when the event is selected (eventseldlg) and
        is set depending on if the CLAMSTEST variable is True or False in the Application_Configuration table
        :return:
        """
        # sets the haul number to the activeEvent
        self.l_haul.setText(str(self.activeEvent).zfill(3))

        # reloads the netdlg now
        self.netdlg.reload_data()

        #  query out the "slow" and "fast" SCS write rates. We write SCS data to the
        #  event_stream_data table at different rates depending on where we are in
        #  the event. We write faster between TD and HB, and slower before TD
        #  and after HB.
        sql = ("SELECT parameter_value FROM " + self.schema + ".application_configuration " +
                "WHERE parameter='EventStreamEQHBLogInt'")
        query = self.db.dbQuery(sql)
        val, = query.first()
        if val:
            try:
                self.streamEQHBLogInterval = float(val)
            except:
                pass

        sql = ("SELECT parameter_value FROM " + self.schema + ".application_configuration " +
                "WHERE parameter='EventStreamPreEQLogInt'")
        query = self.db.dbQuery(sql)
        val, = query.first()
        if val:
            try:
                self.streamSlowLogInterval = float(val)
            except:
                pass

        # if this is a restart or continuation of an already started event, reload previously collected data
        sql = ("SELECT event_id FROM " + self.schema + ".events WHERE ship=" + self.ship + " AND survey="
               + self.survey + " AND event_id=" + str(self.activeEvent))
        query = self.db.dbQuery(sql)
        event_id, = query.first()
        if event_id:
            # this is a restart so reload any existing data
            self.reloaded = True
            self.reload_data()

        #  Set up sensors - first create an instance of SensorMonitor
        #  which will handle all the details of receiving and parsing
        #  data from our devices/sensors.
        self.sensorMonitor = SensorMonitor.SensorMonitor()

        #  connect the SensorDataReceived signal. This is emitted when
        #  a sensor transmits a full line of data, after the line is
        #  parsed.
        self.sensorMonitor.SensorDataReceived.connect(self.write_stream)
        
        #  connect the SensorsStopped signal which tells us when all
        #  sensorMonitor's acquisition threads have stopped so we make
        #  sure we don't exit before all threads have stopped.
        self.sensorMonitor.SensorsStopped.connect(self.devices_closed)

        #  connect the SensorError signal to inform the user of any
        #  sensor errors. Errors will be emitted asynchronously.
        self.sensorMonitor.SensorError.connect(self.device_error)

        #  get the devices attached to this workstation
        self.deviceData = devices.getDevices(self.db, self.workStation, self.schema)
        
        #  set up each device
        for deviceName in self.deviceData:
            #  try to get the configuration parameters for this device
            #  this will fail if a required parameter is missing.
            try:
                deviceParams = devices.getDeviceParameters(self.db, self.schema, deviceName,
                                                           self.deviceData[deviceName]['id'],
                                                           self.deviceData[deviceName]['interface'])
            except Exception as e:
                self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                        "Error initializing device ::: " + str(e) +
                                        ". This device will be disabled", 'warning')
                continue

            #  only set up network and serial devices
            if self.deviceData[deviceName]['interface'] in ['network', 'serial']:
                #  then add this device to the sensor monitor
                self.sensorMonitor.addDevice(deviceName, deviceParams['port'], deviceParams['baud'],
                                             deviceParams['parseType'], deviceParams['parseExp'],
                                             deviceParams['parseIndex'], deviceParams['commandPrompt'])

            if 'trawlevent' in self.deviceData[deviceName]['measurements']:
                dev_id = self.deviceData[deviceName]['id']
                dev_name = self.deviceData[deviceName]['measurements']['trawlevent'][0]
                self.current_scs[dev_id] = dev_name

            #  set the initial "last write" time for this device
            self.lastSCSWriteTime[deviceName] = QDateTime.currentDateTime()

        self.SCSisActive = True

        #  now that all devices are added - start monitoring them. This will cause
        #  SensorMonitor to open serial or network ports and in the case of serial
        #  ports start polling. SensorMonitor will buffer data until full messages
        #  are received. Those messages are optionally parsed and then SensorMonitor
        #  emits a signal with the parsed data.
        self.sensorMonitor.startMonitoring()
        self.sensorsClosed = False

        #  If there are any errors opening ports, SensorMonitor will emit the
        #  SensorError signal for each device with an issue.

        #  show the window
        self.show()

        # set stub in status bar
        self.statusBar.showMessage('SCS not connected!')

        # deal with buttons
        self.deal_with_buttons()

    def deal_with_buttons(self):
        """
        deals with which buttons are enabled/disabled
        :return:
        """
        self.disable_enable_buttons('disable', self.doneBtn)
        if Events.NetOnDeck.name in self.button_order:
            self.doneBtn.setEnabled(True)
        
        self.disable_enable_buttons('disable', self.pb_abort)

        # disable all event buttons (except com)
        self.disable_enable_buttons('disable', 'events')
        if self.meta_entered:
            # if there are no event buttons that are pressed yet (and therefore in self.button_order),
            if not self.button_order:
                # enable the start mmw button
                self.disable_enable_buttons('enable', self.pb_niw)
            else:
                self.disable_enable_buttons('enable', self.pb_abort)
                activeBtnIdx = self.cur_dt_row
                curIdx = 0
                for button in self.buttons:
                    if curIdx <= activeBtnIdx:
                        self.disable_enable_buttons('enable', self.buttons[curIdx])
                    else:
                        self.disable_enable_buttons('disable', self.buttons[curIdx])
                    curIdx+=1

    def disable_enable_buttons(self, action, btn=None):
        """
        disables/enables buttons depending on passed action; used when the metadata information is
        entered or not
        :param action: the action (disable or enable) to complete
        :param btn: if this is set, it is to apply action to that single button
        :return: none
        """
        if btn == 'events':
            # got through all event buttons, except for COM
            for btn in self.buttons:
                if action == 'disable':
                    btn.setEnabled(False)
                else:
                    btn.setEnabled(True)
        elif btn:
            if action == 'disable':
                btn.setEnabled(False)
            else:
                btn.setEnabled(True)
        else:
            # abort (only disable), done, net dimensions
            if action == 'disable':
                self.pb_abort.setEnabled(False)
                self.doneBtn.setEnabled(False)
                # self.netDimBtn.setEnabled(False)
            else:
                self.doneBtn.setEnabled(True)
                # self.netDimBtn.setEnabled(True)

    def display_time(self, t_type, show_only=False):
        """
        displays the timers
        :return: none
        """
        if t_type == 'overall':
            if not show_only:
                self.event_time = self.event_time.addSecs(1)
            if self.event_time.hour() > 0:
                self.elapseLabel.setText(self.event_time.toString('h:mm:ss'))
            else:
                self.elapseLabel.setText(self.event_time.toString('mm:ss'))
        else:
            if not show_only:
                self.tow_time = self.tow_time.addSecs(1)
            if self.tow_time.hour() > 0:
                self.l_timeTD.setText(self.tow_time.toString('h:mm:ss'))
            else:
                self.l_timeTD.setText(self.tow_time.toString('mm:ss'))

    def reload_data(self):
        """
        populates the form, metadata, and net dimensions with whatever data exists in the database for this event
        """
        # deal with all buttons
        self.deal_with_buttons()
        # check if the metadata to entered
        exists = self.check_for_required_meta()
        if exists == 1:
            self.meta_entered = True
        else:
            self.meta_entered = False
            return

        # enter the fisher, td, tdlat, tdlon
        self.enter_meta_info()

        # populate comments
        sql = ("SELECT comments FROM " + self.schema + ".events WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeEvent)
        query = self.db.dbQuery(sql)
        self.comment = query.first()
        # if there isn't a comment - set it to an empty string.
        if self.comment is None:
            self.comment = ''

        # set up elapsed seconds to populate
        overall_elapsed = 0
        td_elapsed = 0

        # get event types entered by timestamp
        ev_sql = ("SELECT event_parameter, " + self.db.formatTimeStamp("parameter_value") + " AS times "
                  "FROM " + self.schema + ".event_data WHERE ship=" + self.ship + " AND survey=" + self.survey +
                  " AND event_id=" + self.activeEvent + " AND partition='MainTrawl' AND event_parameter IN "
                                                        "('"  + 
                                                        Events.NetInWater.name + "', '" +
                                                        Events.EQ.name + "', '" +
                                                        Events.EQ10Min.name + "', '" +
                                                        Events.EQ20Min.name + "', '" +
                                                        Events.Haulback.name + "', '" +
                                                        Events.NetOnDeck.name +
                                                        "')"
                                                        "ORDER BY times ASC")
        ev_query = self.db.dbQuery(ev_sql)

        # go through each event type entered into database and add to the table
        row = 0
        for ev, ts in ev_query:
            # add to button order list
            self.button_order.append(ev)
            # set the button text
            btn_txt = Events[ev].value

            # get the index in the list to reset the color
            ind = None
            for b in self.buttons:
                if b.text() == btn_txt:
                    ind = self.buttons.index(b)
                    self.idxs.append(ind)

            #  first check for event_data parameters
            sql = ("SELECT event_parameter, parameter_value FROM " + self.schema + ".event_data WHERE ship=" +
                   self.ship + " AND survey=" + self.survey + " AND event_id=" + self.activeEvent +
                   " AND partition='MainTrawl' AND event_parameter='" + ev + "'")
            query = self.db.dbQuery(sql)
            param, val = query.first()

            # if we found something, populate the parameter's row
            if val:
                # update the button's table values
                self.dataTable.setItem(row, 0, QTableWidgetItem(param))
                self.dataTable.setItem(row, 1, QTableWidgetItem(val))
                self.btnTimes[row] = self.db.createTime(val)

                buttonValues = self.get_event_stream_vals(val, self.displayMeasurements)
                self.dataTable.setItem(row, 2, QTableWidgetItem(buttonValues[0]))
                self.dataTable.setItem(row, 3, QTableWidgetItem(buttonValues[1]))
                #self.dataTable.setItem(row, 4, QTableWidgetItem(buttonValues[2]))

                if ind != None:
                    self.buttons[ind].setPalette(self.yellow)

                if param == Events.NetInWater.name:
                    # get elapsed seconds since NIW was pressed
                    self.niw_time = self.btnTimes[row]
                    overall_elapsed = self.btnTimes[row].secsTo(QDateTime().currentDateTime())
                elif param == Events.NetOnDeck.name:
                    # get the time NOD was pressed
                    self.nod_time = self.btnTimes[row]
                elif param == Events.EQ.name:
                    # get elapsed seconds since TD was pressed
                    self.td_time = self.btnTimes[row]
                    td_elapsed = self.btnTimes[row].secsTo(QDateTime().currentDateTime())
                elif param == Events.Haulback.name:
                    # get the time HB was pressed
                    self.hb_time = self.btnTimes[row]
            row += 1
            self.cur_dt_row = row

        #  set timers to display the elapsed time
        if overall_elapsed > 0 and Events.NetOnDeck.name in self.button_order:
            tot_time = self.niw_time.secsTo(self.nod_time)
            self.event_time = self.event_time.addSecs(tot_time)
            self.display_time('overall', True)
        elif Events.NetInWater.name in self.button_order:
            self.event_time = self.event_time.addSecs(overall_elapsed)
            if not self.event_timer.isActive():
                self.event_timer.timeout.connect(lambda: self.display_time('overall'))
                self.event_timer.start(1000)
        # if HB is pressed, get elapsed time
        if td_elapsed > 0 and Events.Haulback.name in self.button_order:
            at_depth_time = self.td_time.secsTo(self.hb_time)
            self.tow_time = self.tow_time.addSecs(at_depth_time)
            self.display_time(Events.EQ.name, True)
        elif Events.EQ.name in self.button_order:
            self.tow_time = self.tow_time.addSecs(td_elapsed)
            if not self.td_timer.isActive():
                self.td_timer.timeout.connect(lambda: self.display_time('td'))
                self.td_timer.start(1000)

        self.dataTable.resizeColumnsToContents()

        if Events.NetOnDeck.name in self.button_order:
            self.recording = False
            self.doneBtn.setEnabled(True)
        else:
            self.recording = True
        # enable the comment box
        self.commentBtn.setEnabled(True)

        #  check if this event has been completed. Completed is defined as having NIW and NOD
        #  data. Once an event is completed, we only allow editing and do not collect stream data.
        if Events.EQ.name not in self.button_order or Events.Haulback.name not in self.button_order:
            #  one of them is not complete - ask if we should consider this a live event
            reply = QMessageBox.question(self, 'Achtung!', "<font size = 14>This haul was not completed. " +
                                         "Is this event still taking place?</font>", QMessageBox.StandardButton.Yes,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                #  determine what SCS logging rate we should use
                if Events.EQ.name not in self.button_order:
                    #  EQ has not been pressed yet
                    self.SCSLogInterval = self.streamSlowLogInterval
                    self.fishingFlag = False
                else:
                    self.SCSLogInterval = self.streamEQHBLogInterval
                    self.fishingFlag = True
                #  set other state variables for a "live" event
                self.recordStream = True
            else:
                #  this is not a live event - treat this as an edit after the fact
                self.recordStream = False
        # check if NIW and NOD have both been pressed; if so, it is completed and can only edit
        if Events.NetInWater.name in self.button_order and Events.NetOnDeck.name in self.button_order:
            QMessageBox.information(self, 'Kipaumbele!', "<font size=14>This haul appears to have been completed. " +
                                    "You can only edit it. New time values must be within the original "
                                    "time span of the event. " +
                                    "No new stream data will be recorded.</font>", QMessageBox.StandardButton.Ok)
        self.doneBtn.setEnabled(True)

    def check_for_required_meta(self):
        """

        :return:
        """
        # check for operator
        fish_sql = ("SELECT scientist FROM " + self.schema + ".events WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent))
        fish_query = self.db.dbQuery(fish_sql)
        sci, = fish_query.first()
        if sci:
            return 1
        else:
            return 0

    def get_event_stream_vals(self, time, parameters):
        """
        queries the event_data_stream table for the specified parameter
        values at the specified time and returns the value closest to the time. If data is not
        available within the defined time window, empty strings are returned.

        ALL VALUES ARE RETURNED AS STRINGS
        """
        #  check that we've been given a list of one or more params
        if len(parameters) == 0 or not isinstance(parameters, list):
            return ''

        #  set up our default return value
        ret_val = [''] * len(parameters)
        dt = [float('inf')] * len(parameters)

        #  convert our time to a QDateTime
        time = self.db.createTime(time)

        #  query the data from haul_stream data table within our window
        inClause = "'" + "','".join(parameters) + "'"
        sql = ("SELECT time_stamp, measurement_type, measurement_value FROM " + self.schema +
                ".event_stream_data WHERE time_stamp between to_timestamp('" +
                time.addSecs(-self.streamWindowSeconds).toString('MMddyyyy hh:mm:ss.zzz') +
                "','MMDDYYYY HH24:MI:SS.FF3') and to_timestamp('" +
                time.addSecs(self.streamWindowSeconds).toString('MMddyyyy hh:mm:ss.zzz') +
                "','MMDDYYYY HH24:MI:SS.FF3') AND measurement_type IN (" + inClause + ")")
        query = self.db.dbQuery(sql)
        #  loop thru the returned values
        for timestamp, meas, value in query:
            try:
                #  get the index into our return array
                i = parameters.index(meas)
                #  calculate the time difference between this row and our specified time
                timeDiff = abs(QDateTime.fromString(timestamp, 'MMddyyyy hh:mm:ss.zzz').secsTo(time))
                #  check if this delta is smaller
                if timeDiff < dt[i]:
                    #  difference is smaller, save this value
                    dt[i] = timeDiff
                    ret_val[i] = value
            except:
                #  this is not the parameter we're looking for
                pass

        return ret_val

    def add_comment(self):
        """

        :return:
        """
        # get any comments already in database
        # and parse them to only display comment before ABORT xxxx
        com_sql = ("SELECT comments FROM " + self.schema + ".events WHERE ship=" + self.ship +
                   " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent))
        com_query = self.db.dbQuery(com_sql)
        comments, = com_query.first()
        parsedComment = comments.split(self.abortPrefix) if comments else ''

        # send up keypad and set space with comments
        if len(parsedComment) > 0:
            keyDialog = keypad.KeyPad(parsedComment[0], self)
        else:
            keyDialog = keypad.KeyPad('', self)
        keyDialog.exec()
        if keyDialog.okFlag:
            text = keyDialog.dispEdit.toPlainText()
            formattedComment = text + " " + self.abortPrefix + parsedComment[1] if len(parsedComment) > 1 else text 
            # update comments in database
            update_sql = ("UPDATE " + self.schema + ".events SET comments ='" + formattedComment + "' WHERE ship=" + self.ship +
                          " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent))
            self.db.dbQuery(update_sql)

    def set_event(self):
        """
        when an event is pressed, it writes to the form and to the database
        :return:
        """
        if not self.recording:
            self.recording = True
        ind = self.buttons.index(self.sender())

        # get the text of the button
        self.cur_btn_txt = self.sender().text()
        paramName = Events(self.cur_btn_txt).name

        self.button_order.append(paramName)

        # save in DB
        # get the current timestamp
        cur_time = self.db.formatTime()

        # Checks whether an entry exists in event_data table
        # if so, update value if not, create new row.
        event_sql = ("SELECT PARAMETER_VALUE FROM " + self.schema + ".event_data where " + 
                     "ship=" + self.ship +
                     " and survey=" + self.survey + 
                     " and event_id=" + self.activeEvent + 
                     " and event_parameter='" + paramName + "'")
        query = self.db.dbQuery(event_sql)
        val = query.first()
        self.cur_time = val[0] if val[0] else cur_time
        if val[0]:
            # Verify user actually wants to update before updating value in database
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                                    'Are you sure you want to update event?', 'choice')
            if self.message.exec():
                event_sql =("UPDATE " + self.schema + 
                        ".event_data set parameter_value='" + self.cur_time + 
                        "' WHERE ship=" + self.ship + 
                        " and survey=" + self.survey + 
                        " and event_id=" + self.activeEvent +
                        " and event_parameter='" + paramName + "'")
                self.db.dbExec(event_sql)
            else:
                return
        else:
            event_sql = ("INSERT INTO " + self.schema +
                     ".event_data (ship, survey, event_id, partition, event_parameter, parameter_value) "
                     "VALUES (" + self.ship + ", " + self.survey + ", " + self.activeEvent + ", 'MainTrawl', '"
                     + paramName + "', '" + self.cur_time + "')")
            event_query = self.db.dbQuery(event_sql)
            if not event_query:
                return

        self.buttons[ind].setPalette(self.green)
        self.dataTable.setItem(ind, 0, QTableWidgetItem(paramName))
        self.dataTable.setItem(ind, 1, QTableWidgetItem(self.cur_time))
        if self.dispVector:
            # iterate through SCS lat, long, and depth an display in table
            for val in self.dispVector:
                self.dataTable.setItem(ind, val + 2, QTableWidgetItem(self.dispVector[val]))
        self.dataTable.resizeColumnsToContents()

        # deal with the timers and buttons
        if Events.EQ.name == paramName:
            if not self.td_timer.isActive():
                self.td_timer.timeout.connect(lambda: self.display_time('td'))
                self.td_timer.start(1000)
            # if TD is pressed, send up net dimensions
            self.net_btn = Events.EQ.name
            self.get_net_dims()
            self.disable_enable_buttons('enable', self.pb_hb)
        elif paramName in (Events.EQ10Min.name, Events.EQ20Min.name):
            self.net_btn = paramName
            self.get_net_dims()
        elif Events.Haulback.name in paramName:
            # stop the timer
            self.td_timer.stop()
            # if HB is pressed, send up net dimensions
            self.net_btn = Events.Haulback.name
            self.get_net_dims()
        elif Events.NetInWater.name in paramName:
            # if NIW is pressed, start recording and enable the abort button
            self.recording = True
            self.disable_enable_buttons('enable', self.pb_abort)
            # set the timer
            if not self.event_timer.isActive():
                self.event_timer.timeout.connect(lambda: self.display_time('overall'))
                self.event_timer.start(1000)
        elif Events.NetOnDeck.name in paramName:
            # if NOD is pressed, enable the done button, turn off the recording of SCS data, and stop overall timer
            self.disable_enable_buttons('enable', self.doneBtn)
            self.recording = False
            self.event_timer.stop()

        # set next button enabled as long as current button is not Net on Deck
        if paramName != Events.NetOnDeck.name:
            self.disable_enable_buttons('enable', self.buttons[ind + 1])

        # move current row ahead one
        self.cur_dt_row += 1

    def write_stream(self, device_name, data):
        """
        write_stream is called when we receive sensor data (from SCS)
        :return:
        """
        # update the status bar that SCS is alive
        if not self.SCSisActive:
            self.SCSisActive = True
        self.statusBar.showMessage('Connected to SCS', 1000)
        self.scsRetries = 0

        # check if we're recording data and return if not
        if not self.recordStream or not self.recording:
            return

        # check if this sensor provides trawl event data
        if 'trawlevent' not in self.deviceData[device_name]['measurements']:
            #  it doesn't - ignore this data
            return

        # get the current time
        datetime = QDateTime.currentDateTime()
        time = self.db.formatTime(datetime)

        # iterate thru the the list of SCS sensor datagrams and write to database
        if self.testing:
            self.dispVector = ['testlat', 'testlon']
        else:
            wroteToDb = False

            # get the measurement type - while devices can be associated with multiple
            # measurements, in this context this doesn't make sense so we will assume
            # the first measurement assigned to this de
            measurement = self.deviceData[device_name]['measurements']['trawlevent'][0]
            # check that we have data for this sensor
            if data is None or data.strip() == '':
                return

            # convert Lat/Lon to decimal degrees
            if measurement.lower() == 'latitude':
                data = self.convertDegToDecimal(data, 'lat')
            if measurement.lower() == 'longitude':
                data = self.convertDegToDecimal(data, 'lon')

            # check if we need to write a fresh value in the database
            elapsedSecs = self.lastSCSWriteTime[device_name].secsTo(datetime)
            if elapsedSecs >= self.SCSLogInterval:
                #  insert into the database
                sql = ("INSERT INTO " + self.schema + ".event_stream_data (ship, survey, " +
                        "event_id, device_id, time_stamp, measurement_type, measurement_value) " +
                        "VALUES (" + self.ship + "," + self.survey + "," + str(self.activeEvent) + "," +
                        self.deviceData[device_name]['id'] + ",'" + time + "','" + measurement +
                        "','" + data + "')")
                self.db.dbExec(sql)
                wroteToDb = True

            if measurement in self.displayMeasurements:
                ind = self.displayMeasurements.index(measurement)
                self.dispVector[ind] = data

            # update the write time if we wrote to the db
            if wroteToDb:
                self.lastSCSWriteTime[device_name] = datetime

    def devices_closed(self):
        """
        called when the SensorMonitor emits the SensorsStopped signal which lets us know all acquisition
        threads have stopped. Once they are stopped we can close the form without error.
        (Qt gets angry when threads are destroyed while running.) Set sensorsClosed to True and call close() again.
        :return:
        """
        #  we check if this is an intentional shutdown and if so, close
        #  the form. This method will also be called if every sensor
        #  fails to start when the form is initializing and we *don't*
        #  want to close the form in that case.
        if self.sensorsStopping:
            #  set sensorsClosed to True and call close() again
            self.sensorsClosed = True
            self.close()

    def finish_event(self):
        """
        popup for entering the performance of the operation and allowing to check/enter comments
        :return:
        """
        # Check all metadata fields have been entered in event_data and gear_accessory tables
        isValid = True
        errorMsg = "Metadata values missing, metadata must be completed before event can be completed."

        metadataFields = [member.value for member in metadlg.MetadataFields]
        formattedMeta = ", ".join([f"'{x}'" for x in metadataFields])
        sql = ("SELECT count(*) FROM " + self.schema + 
                    ".event_data where event_id=" + str(self.activeEvent) + ' and ' +
                    "event_parameter in (" + formattedMeta + ")")
        resuls = self.db.dbQuery(sql)
        count, = resuls.first()

        if int(count) != len(metadlg.MetadataFields):
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0], errorMsg, "error")
            self.message.show()
            isValid = False

        gearFields = [member.value for member in metadlg.GearTypeFields]
        formattedGear = ", ".join([f"'{x}'" for x in gearFields])
        sql = ("SELECT count(*) FROM " + self.schema + 
                    ".gear_accessory where event_id=" + str(self.activeEvent) +
                    " and gear_accessory in (" + formattedGear + ")")
        resuls = self.db.dbQuery(sql)
        count, = resuls.first()

        if int(count) != len(metadlg.GearTypeFields):
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0], errorMsg, "error")
            self.message.show()
            isValid = False

        if Events.NetOnDeck.name in self.button_order and isValid:
            # stop recording
            self.recording = False
            # set up the finish dialog
            done = donedlg.DoneDlg(self)
            # display the dialog
            result = done.exec()

            # if not cancelled, operation is complete
            if result == QDialog.DialogCode.Accepted:
                self.run_scs_avgs()
                self.accept()
   
    def get_net_dims(self):
        """
        called when the user hits EQ, HB. This presents
        a simple dialog for entering door spread and foot rope depth.
        """
        self.net_btn = self.sender().text()
        self.netdlg.setTime(self.cur_time)

        # reload the net dimension values
        self.netdlg.reload_data(self.cur_time)

        # display the dialog
        self.netdlg.exec()

    def edit_dims(self):
        """

        :return:
        """

        # get the timestamp
        curTime = self.dataTable.item(self.dataTable.currentRow(), 1)
        netBtn = self.dataTable.item(self.dataTable.currentRow(), 0)
        # Checking for null values
        self.cur_time = curTime.text() if curTime else ''
        self.net_btn = netBtn.text() if netBtn else ''

        if self.net_btn in [Events.EQ.name, 
                            Events.Haulback.name, 
                            Events.EQ10Min.name, 
                            Events.EQ20Min.name]:
            # display the dialog
            self.netdlg.setTime(self.cur_time)

            # reload the net dimension values
            self.netdlg.reload_data(self.cur_time)

            # display the dialog
            self.netdlg.exec()
            self.dataTable.blockSignals(True)
            self.dataTable.clearSelection()
            self.dataTable.blockSignals(False)

    @pyqtSlot(str, object)
    def device_error(self, deviceID, obj):
        """

        :param deviceID:
        :param obj:
        :return:
        """
        # there was an issue with a device so display a warning dialog
        QMessageBox.warning(self, "Sensor/Device Error", "<font size = 14>" +
                            obj.errText + " This device will be not be enabled (Device id: " + deviceID + ".")

    @staticmethod
    def convertDegToDecimal(deg, pos):
        """

        :param deg:
        :param pos:
        :return:
        """
        try:
            parts = deg.split(',')
            if len(parts) > 1:
                deg = parts[0]
                h = parts[1].strip().lower()
            else:
                deg = parts[0][0:-1]
                h = parts[0][-1].strip().lower()
            if pos == 'lat':
                dec = round(float(deg[0:2]) + float(deg[2:])/60., 4)
            else:
                dec = round(float(deg[0:3]) + float(deg[3:]) / 60., 4)
            if h in ['s', 'w']:
                dec = dec * -1
        except:
            dec = ''

        return str(dec)

    def enter_metadata(self):
        """

        :return:
        """
        # set up the metadata dialog
        meta = metadlg.MetaDlg(self)
        # reload any data
        meta.reload_data()
        # display the dialog
        result = meta.exec()
        if result:
            # check if meta actually entered - this is a double-check since it should be entered if we got this far
            temp = self.check_for_required_meta()
            if temp:
                self.meta_entered = True
                self.enter_meta_info()
                self.event_entered = True
                # deal with buttons
                self.deal_with_buttons()

    def enter_meta_info(self):
        """
        this updates the gui with some information the fisher may want on hand
        :return:
        """
        for p in self.meta_info:
            sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="
                              + self.ship + " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent) +
                              " AND partition='MainTrawl' AND event_parameter='" + p + "'")
            query = self.db.dbQuery(sql)
            val, = query.first()
            if 'operator' in p.lower():
                self.l_fisher.setText(val)
            elif 'col' in p.lower():
                self.l_collection.setText(val)
            elif 'mode' in p.lower():
                self.l_fishingMode.setText(val)

    def abort_operation(self):
        """
        'aborts' the tow and requires performance (reason) and comments
        :return:
        """
        # open dialog only if NIW has already been pressed
        if Events.NetInWater.name in self.button_order:
            # stop recording
            self.recording = False
            # set up the abort dialog
            abort = abortdlg.AbortDlg(self)
            # display the dialog
            result = abort.exec()

            # if not cancelled, operation is complete
            if result == QDialog.DialogCode.Accepted:
                self.accept()

    def run_scs_avgs(self):
        """
        creates averages of the scs stream data and puts it into the event_data table
        """
        # get the time of the TD and HB
        td_time = hb_time = None
        time_sql = ("SELECT event_parameter, parameter_value FROM " + self.schema
                    + ".event_data WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND event_id="
                    + self.activeEvent + " AND event_parameter IN ('EQ', 'Haulback')")

        time_query = self.db.dbQuery(time_sql)
        for param, val in time_query:
            if param.lower() == 'eq':
                td_time = val
            elif param.lower() == 'haulback':
                hb_time = val
        for dev_id, dev_name in self.current_scs.items():
            # do not take averages of locations (latitude, longitude)
            if dev_name.lower() not in ['latitude', 'longitude']:
                if td_time is not None or hb_time is not None:
                    event_param = "Avg" + dev_name
                    # check if the parameter already exists
                    exists_sql = ("SELECT event_parameter FROM " + self.schema +
                                  ".event_data WHERE ship = " + self.ship + " AND survey = " + self.survey +
                                  " AND event_id = " + self.activeEvent + " AND partition = 'MainTrawl' "
                                  "AND event_parameter = '" + event_param + "'")
                    exists_query = self.db.dbQuery(exists_sql)
                    param, = exists_query.first()

                    if not param:
                        # get avg of the data between the TD and the HB times in event_stream_data
                        avg_sql = ("SELECT AVG(CAST(measurement_value as float)) FROM " + self.schema
                                   + ".event_stream_data WHERE measurement_type='" + dev_name
                                   + "' AND time_stamp BETWEEN '" + td_time + "' AND '" + hb_time + "'")
                        try:
                            avg_query = self.db.dbQuery(avg_sql)
                            dev_avg, = avg_query.first()
                            if dev_avg:
                                # insert parameter into event_data
                                insert_sql = ("INSERT INTO " + self.schema +
                                              ".event_data (ship, survey, event_id, partition, event_parameter, "
                                              "parameter_value) VALUES (" + self.ship + ", " + self.survey + ", "
                                              + self.activeEvent + ", 'MainTrawl', '" + event_param + "', '"
                                              + str(dev_avg) + "')")
                                self.db.dbQuery(insert_sql)
                        except:
                            pass
                else:
                    msg = "Missing EQ or HB for this tow, no averages can be calculated"
                    self.message.setMessage(self.errorIcons[0], self.errorSounds[0], msg, 'warning')

