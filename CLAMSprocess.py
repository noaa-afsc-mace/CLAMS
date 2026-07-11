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
.. module:: CLAMSProcess

    :synopsis: CLAMSProcess is the main catch processing form and is
               displayed after a user selects a catch event to process.
               It is the entry point to the other catch processing
               modules (Haul, Catch, Length, and Specimen)

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
from PyQt6 import QtSql  
from PyQt6.QtMultimedia import QSoundEffect
import Clamsbase2Functions
from ui import ui_CLAMSProcess
import devices
import CLAMShaul
import CLAMScatch
import CLAMSspecimen
import CLAMSlength
import CLAMSSpeciesFix
from acquisition.SensorMonitor import SensorMonitor
import messagedlg
import listseldialog
import codendstatusdlg
import CPS.catchHome as catchHomeSWFSC


class CLAMSProcess(QDialog, ui_CLAMSProcess.Ui_clamsProcess):

    def __init__(self, parent=None):
        #  set up the GUI
        super(CLAMSProcess, self).__init__(parent)
        self.setupUi(self)

        # initialize variables
        self.reloadFlag=False
        self.db=parent.db
        self.survey=parent.survey
        self.ship=parent.ship
        self.activeHaul=parent.activeEvent
        self.settings=parent.settings
        self.workStation=parent.workStation
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.schema = parent.schema
        self.testing=parent.testing
        self.partitions=[]
        self.activePartition=None
        self.methotFlag=False
        self.sensorsClosed = False
        self.sensorsStopping = False

        #  set up some colors
        self.blue = QPalette()
        self.blue.setColor(QPalette.ColorRole.ButtonText,QColor(0, 0, 255))
        self.black = QPalette()
        self.black.setColor(QPalette.ColorRole.ButtonText,QColor(0, 0, 0))

        # hide fix species and edit codend button for SWFSC mode
        if self.settings['OrganizationName'] == 'SWFSC':
            self.fixSpeciesBtn.hide()
            self.editCodendStateBtn.hide()

        # set up button colors
        self.haulBtn.setPalette(self.black)
        self.catchBtn.setPalette(self.black)
        self.lengthBtn.setPalette(self.black)
        self.specBtn.setPalette(self.black)
        self.swfscCatchBtn.setPalette(self.black)

        #  Set up the signals and slots
        self.partitionBox.activated[int].connect(self.getPartition)
        self.haulBtn.clicked.connect(self.getHaul)
        self.catchBtn.clicked.connect(self.getCatch)
        self.swfscCatchBtn.clicked.connect(self.getCatchSWFSC)
        self.specBtn.clicked.connect(self.getSpecimen)
        self.lengthBtn.clicked.connect(self.getLength)
        self.fixSpeciesBtn.clicked.connect(self.goFixSpecies)
        self.editCodendStateBtn.clicked.connect(self.editCodendState)
        self.doneBtn.clicked.connect(self.close)

        # SETUP THE TABLE VIEW ---
        self.catchModel = QtSql.QSqlQueryModel()
        self.catchView.setModel(self.catchModel)
        self.catchView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.catchView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.catchView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.catchView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)        # -----------------------------------------------
        self.catchView.horizontalHeader().setStyleSheet("QHeaderView::section { font-size: 12pt; font-weight: bold; }")

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'ProcessForm')
        size = self.appSettings.value('winsize', QSize(950,656))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  set the event number
        self.haulLabel.setText(self.activeHaul)

        # added by AB to account for different length types
        # get all lengths from measurement_types
        self.length_types = []
        sql_l = f"SELECT measurement_type from {self.schema}.MEASUREMENT_TYPES WHERE is_length=1"
        query_l = self.db.dbQuery(sql_l)
        for lt, in query_l:
            self.length_types.append(lt)

        # get the scientist - first get the list of active scientists
        self.sciList=[]
        sql = ("SELECT scientist FROM " + self.schema + ".personnel WHERE active=1"
                " ORDER BY scientist")
        query = self.db.dbQuery(sql)
        for scientist, in query:
            self.sciList.append(scientist)
        #  instantiate the list dialog with the sci names
        self.listDialog = listseldialog.ListSelDialog(self.sciList, parent=self)
        self.listDialog.label.setText('Identify yourself, please.')
        #  and finally present the dialog - force the selection
        needScientist = True
        while needScientist:
            if self.listDialog.exec():
                if (self.listDialog.itemList.currentRow() < 0):
                    #  no name selected
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                            "Please select your name, or a suitable substitute if yours" +
                            " cannot be found.", 'info')
                    self.message.exec()
                else:
                    #  name selected
                    needScientist = False
                    self.scientist = self.listDialog.itemList.currentItem().text()
        #  parse the first name
        p = self.scientist.split(' ')
        self.firstName = p[0]

        #  setup reoccurring dialogs
        self.message = messagedlg.MessageDlg(self)
        self.codendstate = codendstatusdlg.CodendStatusDlg(self.firstName, self)

        #  update this workstation's status to "Open". We also update the
        #  current_event value
        sql = ("UPDATE " + self.schema + ". workstations SET status='open', current_event=" +
                self.activeHaul + " WHERE workstation_ID=" +
                self.workStation)
        self.db.dbExec(sql)

        #  Set the visibility of the action buttons based on the actions specified for this station
        self.haulBtn.hide()
        self.catchBtn.hide()
        self.swfscCatchBtn.hide()
        self.lengthBtn.hide()
        self.specBtn.hide()
        if 'haul' in parent.modules:
            self.haulBtn.show()
        if 'catch' in parent.modules:
            self.catchBtn.show()
        if 'length' in parent.modules:
            self.lengthBtn.show()
        if 'specimen' in parent.modules:
            self.specBtn.show()
        if 'catchswfsc' in parent.modules:
            self.swfscCatchBtn.show()
        self.haulBtn.setEnabled(True)

        #  check if we're reloading data and enable buttons if so
        sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE event_id=" + self.activeHaul +
                " AND ship=" + self.ship + " AND survey=" + self.survey +
                " AND event_parameter='PartitionWeightType'")
        query = self.db.dbQuery(sql)
        if query.first():
            #  at least one partition has a weight type assigned so we've been
            #  here before. Enable the catch button
            self.reloadFlag = True
            self.catchBtn.setEnabled(True)

            #  now check to see if there are any existing samples
            sql = ('SELECT sample_id FROM ' + self.schema + '.samples WHERE event_id=' + self.activeHaul +
                    ' AND ship=' + self.ship + ' AND survey=' + self.survey)
            query = self.db.dbQuery(sql)
            if query.first():
                #  yes, there is at least one sample so we will enable the length
                #  and specimen buttons too.
                self.lengthBtn.setEnabled(True)
                self.specBtn.setEnabled(True)

        #  set up the serial devices attached to this workstation
        self.setupDevices()

        # enable entry of non-codend partition data before trawl codend is on deck
        self.catchBtn.setEnabled(True)

        #  set up the partitions business
        self.setupAllPartitions()

        # set up catch view 
        self.updateCatchView()

    def setupAllPartitions(self):
        '''
        setupPartitions populates the partition drop down menu with the
        appropriate partition options
        '''

        self.partitions=[]
        self.partitionBox.clear()
        #  get the possible partitions for this gear
        sql = ("SELECT GEAR_PARTITIONS.PARTITION, EVENTS.GEAR FROM " + self.schema + ".GEAR_OPTIONS, " + 
               self.schema + ".GEAR_PARTITIONS, " + 
               self.schema + ".EVENTS WHERE" +
                " (GEAR_PARTITIONS.PARTITION = GEAR_OPTIONS.PARTITION) and (GEAR_OPTIONS.GEAR = EVENTS.GEAR)" +
                " and ((EVENTS.SHIP = " + self.ship + " ) AND (EVENTS.SURVEY = " + self.survey + ") AND" +
                " (EVENTS.EVENT_ID = " + self.activeHaul + ") AND (GEAR_PARTITIONS.PARTITION_TYPE = 'Catch'))" +
                "  ORDER BY GEAR_PARTITIONS.PARTITION ASC")
        query = self.db.dbQuery(sql)

        #  loop thru partitions and populate partition dropdown
        for partition, gear in query:
            self.partitionBox.addItem(partition)
            self.partitions.append(partition)

        #  check to make sure we found something to process for this event
        if (len(self.partitions) == 0):
            #  no partitions? - must have the wrong event
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", I am unable to find any catch partitions " +\
                    "to process. Did you select the correct event?", 'info')
            self.message.exec()
            return

        #  set (or unset) the default value in the partition drop down
        if len(self.partitions) > 1:
            #  if there is more than one option - clear the current selection to force the
            #  user to select a partition
            self.partitionBox.setCurrentIndex(-1)
        else:
            #  if there is only one option, select it
            self.partitionBox.setCurrentIndex(0)
            self.partitionBox.setEnabled(False)
            self.activePartition = self.partitions[0]


    def getPartition(self):

        #  set the active partition so the selected partition
        self.activePartition = self.partitionBox.currentText()

        #  check if the codend status has been set
        sql = (f"SELECT * FROM {self.schema}.event_data WHERE ship={self.ship} AND survey={self.survey} "
               f"AND event_id={self.activeHaul} AND partition='{self.activePartition}' "
               f"AND event_parameter = 'CodendStatus'")
        query = self.db.dbQuery(sql)
        first_row = query.first()
        if not first_row or all(item is None for item in first_row):
            # value has not been recorded for this partition - display the status dialog
            self.codendstate.exec()
            codendstatus = self.codendstate.state_value
            #  and insert the status into event_data
            sql = (f"INSERT INTO {self.schema}.event_data (ship, survey, event_id, partition, "
                   f"event_parameter, parameter_value) VALUES({self.ship}, {self.survey}, {self.activeHaul}, "
                   f"'{self.activePartition}' ,'CodendStatus','{codendstatus}')")
            self.db.dbExec(sql)


    def setupDevices(self):
        '''
        setupDevices creates an instance of SensorMonitor and configures it accordingly.
        SensorMonitor is the CLAMS sensor data acquisition class which oversees all sensor
        acquisition. It creates threads for each configured device and handles the polling
        and parsing of data received from the devices.


        '''
        #  Set up sensors - first create an instance of SensorMonitor
        #  which will handle all the details of receiving and parsing
        #  data from our devices/sensors.
        self.sensorMonitor = SensorMonitor.SensorMonitor()

        #  connect the SensorsStopped signal which tells us when all
        #  sensorMonitor's acquisition threads have stopped so we make
        #  sure we don't exit before all threads have stopped.
        self.sensorMonitor.SensorsStopped.connect(self.devicesClosed)

        #  connect the SensorError signal to inform the user of any
        #  sensor errors. Errors will be emitted asyncronously.
        self.sensorMonitor.SensorError.connect(self.sensorError)

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
                messageText = ("Error initializing device ::: " + str(e) +
                        '. This device will be disabled.' )
                QMessageBox.warning(self, "WARNING", "<font size = 13>" + messageText)
                continue

            #  only set up network and serial devices
            if self.deviceData[deviceName]['interface'] in ['network', 'serial']:
                # added 6/9/26 - remove network printer from monitor since it is throwing an error
                if self.deviceData[deviceName]['interface'] != 'network' and deviceName != 'Label_Printer':
                    #  then add this device to the sensor monitor
                    self.sensorMonitor.addDevice(deviceName, deviceParams['port'], deviceParams['baud'],
                            deviceParams['parseType'], deviceParams['parseExp'], deviceParams['parseIndex'],
                            deviceParams['commandPrompt'])

            #  store the sound effect object for each device with an associated sound
            if 'soundFile' in deviceParams['soundFile']:
                if deviceParams['soundFile']:
                    #  see if the file has an extension
                    hasExt = deviceParams['soundFile'].split('.')
                    if len(hasExt) > 1:
                        soundFile = self.settings['SoundsDir'] + deviceParams['soundFile']
                    else:
                        soundFile = self.settings['SoundsDir'] + deviceParams['soundFile'] + '.wav'
                    soundEffect = QSoundEffect()
                    soundEffect.setSource(QUrl.fromLocalFile(soundFile))
                    self.deviceData[deviceName]['soundeffect'] = soundEffect
                else:
                    self.deviceData[deviceName]['soundeffect'] = None
            else:
                self.deviceData[deviceName]['soundeffect'] = None

        #  now that all devices are added - start monitoring them. This will cause
        #  SensorMonitor to open serial or network ports and in the case of serial
        #  ports start polling. SensorMonitor will buffer data until full messages
        #  are received. Those messages are optionally parsed and then SensorMonitor
        #  emits a signal with the parsed data.
        self.sensorMonitor.startMonitoring()

        #  If there are any errors opening ports, SensorMonitor will emit the
        #  SensorError signal for each device with an issue


    @pyqtSlot(str, object)
    def sensorError(self, deviceName, obj):

        #  There was an issue with a device display a warning dialog
        QMessageBox.warning(self, "Sensor/Device Error", "<font size = 14>" +
                obj.errText + " This device will be not be enabled.")


    def editCodendState(self):

        #  make sure there is an active partition
        if self.activePartition is None:
            #  no partition selected - issue error
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", you need to select a partition for" +
                    " this haul first!", 'info')
            self.message.exec()
            return

        #  get the existing codend status
        sql = (f"SELECT parameter_value FROM {self.schema}.event_data WHERE ship={self.ship} AND survey={self.survey} "
               f"AND event_id={self.activeHaul} AND partition='{self.activePartition}' "
               f"AND event_parameter = 'CodendStatus'")
        query = self.db.dbQuery(sql)
        currentCodendState, = query.first()

        #  if there is a current state, set that button on the dialog and display.
        #  if there is no current status, we ignore this button press (don't do anything)
        if currentCodendState:
            for btn in self.codendstate.btns:
                if btn.text() == currentCodendState:
                    btn.setChecked(True)
            #  now display the codendstate dialog
            self.codendstate.exec()

            #  update the state based on the dialog selection
            newStatus = self.codendstate.state_value
            if newStatus != currentCodendState:
                #  and update the database entry
                sql = ("UPDATE " + self.schema + ".event_data SET parameter_value='" + newStatus +
                        "' WHERE ship = " + self.ship + " and survey = " +
                        self.survey + " and event_id = " + self.activeHaul +
                        " and partition = '" +  self.activePartition +
                        "' AND event_parameter = 'CodendStatus'")
                self.db.dbExec(sql)


    def getHaul(self):
        '''getHaul opens up the Haul form.
        '''

        #  set the button blue to indicate the active form
        self.haulBtn.setPalette(self.blue)

        #  display the haul selection dialog
        haulWindow = CLAMShaul.CLAMSHaul(self)
        haulWindow.exec()

        #  set the button back to black
        self.haulBtn.setPalette(self.black)


    def getCatch(self):
        '''getCatch opens up the Catch form.
        '''

        #  make sure there is an active partition
        if (self.activePartition == None):
            #  no partition selected - issue error
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", you need to select a partition for" +
                    " this haul first!", 'info')
            self.message.exec()
            return

        #  set the catch button blue to indicate the current form
        self.catchBtn.setPalette(self.blue)

        #  show the catch form
        catchWindow = CLAMScatch.CLAMSCatch(self)
        catchWindow.exec()

        #  set the button color back now that the form is closed
        self.catchBtn.setPalette(self.black)

        #  now check to see if we should enable the length and specimen buttons
        sql = ('SELECT sample_id FROM ' + self.schema + '.samples WHERE event_id=' + self.activeHaul +
                ' AND ship=' + self.ship + ' AND survey=' + self.survey)
        query = self.db.dbQuery(sql)
        if query.first():
            #  yes, there is at least one sample so we will enable the length
            #  and specimen buttons.
            self.lengthBtn.setEnabled(True)
            self.specBtn.setEnabled(True)

        self.updateCatchView()

    def getCatchSWFSC(self):
        #  show the catch form
        catchWindow = catchHomeSWFSC.catchHome(self)
        catchWindow.exec()

        #  set the button color back now that the form is closed
        self.catchBtn.setPalette(self.black)

        self.updateCatchView()

    def updateCatchView(self):
        '''
        updateCatchView queries all columns from v_catch_view for the current 
        event and updates the catchView QTableView on the GUI.
        '''
        # Ensure the database is open
        if not self.db.db.isOpen():
            self.db.dbOpen()

        # UPDATED: Match the column names exactly as they appear in v_catch_view (cruise, haul)
        # Note: I added single quotes around {self.ship} assuming it is a string like 'RL'. 
        # If self.ship is actually a numeric ID in Python, you may need to remove the ship filter here.
        sql = (f"SELECT * FROM {self.schema}.v_catch_view "
               f"WHERE cruise = {self.survey} "
               f"AND haul = {self.activeHaul}")
        
        # Execute the query and bind it to the model
        self.catchModel.setQuery(sql, self.db.db)
        
        # --- HIDE SPECIFIC COLUMNS ---
        # Loop through all the columns in the model
        for col in range(self.catchModel.columnCount()):
            # Get the name of the column
            col_name = self.catchModel.headerData(col, Qt.Orientation.Horizontal)
            
            # If the column name is in our list of columns to hide, hide it!
            if col_name in ['cruise', 'ship', 'haul']:
                self.catchView.setColumnHidden(col, True)

        # DEBUGGING: If the table is still empty, this will print the exact SQL error to your terminal
        if self.catchModel.lastError().isValid():
            print("SQL Error in catchView:", self.catchModel.lastError().text())
            print("Attempted Query:", sql)
        
        # Resize columns to fit contents and scroll to the latest entry
        self.catchView.resizeColumnsToContents()
        self.catchView.scrollToBottom()
    # --------------------------------
    def getLength(self):
        '''getLength opens up the Length form.
        '''

        #  make sure there is an active partition
        if (self.activePartition == None):
            #  no partition selected - issue error
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", you need to select a partition for" +
                    " this haul first!", 'info')
            self.message.exec()
            return

        #  set the length button blue to indicate the current form
        self.lengthBtn.setPalette(self.blue)

        #  show the length form
        lengthWindow = CLAMSlength.CLAMSLength(self)
        lengthWindow.exec()

        #  set the button color back now that the form is closed
        self.lengthBtn.setPalette(self.black)


    def getSpecimen(self):
        '''getLength opens up the Length form.
        '''

        #  make sure there is an active partition
        if (self.activePartition == None):
            #  no partition selected - issue error
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", you need to select a partition for" +
                    " this haul first!", 'info')
            self.message.exec()
            return

        #  set the specimen button blue to indicate the current form
        self.specBtn.setPalette(self.blue)

        #  show the specimen form
        specimenWindow = CLAMSspecimen.CLAMSSpecimen(self)
        specimenWindow.exec()

        #  set the button color back now that the form is closed
        self.specBtn.setPalette(self.black)


    def goFixSpecies(self):
        '''goFixSpecies opens up the SpeciesFix form. this form can be
        used for bulk correction of species and/or sex assignments when users
        forget to change one of these parameters and then measures a bunch
        of fish. Correcting this directly in the database is difficult
        due to various parent child relationships. This form handles all of
        that making corrections quick and easy.
        '''

        #  make sure there is an active partition
        if (self.activePartition == None):
            #  no partition selected - issue error
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1], "Sorry " +
                    self.firstName + ", you need to select a partition for" +
                    " this haul first!", 'info')
            self.message.exec()
            return

        #  display the SpeciesFix dialog
        spcFixWindow = CLAMSSpeciesFix.CLAMSSpeciesFix(self)
        spcFixWindow.exec()


    def closeEvent(self, event=None):
        '''closeEvent is called when the form is closed.

        When the last workstation is closed for an event we runs some checks
        on the data to make sure there aren't any major issues.

        We also update the CATCH_SUMMARY table. Currently we update it when
        any station closes. This approach was used when there was a hole in
        the "last workstation" logic where in certain cases a last workstation
        wouldn't know it is the last workstation and would fail to update the
        table. That logic has been fixed by adding the "current_event" column
        to the workstations table so in theory we can now only update
        CATCH_SUMMARY when the last workstation closes but I'm leaving it as-is
        for now.
        '''

        #  only exit when all sensors have closed
        if self.sensorsClosed:
            #  all sensors closed. store the application size and position
            self.appSettings.setValue('winposition', self.pos())
            self.appSettings.setValue('winsize', self.size())

            #  and accept to close
            event.accept()

        elif self.sensorsStopping == False:

            #  set the status for this workstation to closed
            sql = ("UPDATE " + self.schema + ".workstations SET status='closed', " +
                    "current_event=0 WHERE workstation_ID=" + self.workStation)
            self.db.dbExec(sql)

            #  check if we're the last station working on this event to close
            sql = ("SELECT workstation_id FROM " + self.schema + ".workstations WHERE status='open' AND " +
                    "current_event=" + self.activeHaul)
            query = self.db.dbQuery(sql)

            if not query.first():
                #  we ARE the last station working on this event. We'll do some checks on the
                #  data compute some summary data that is inserted into the database

                #  check "normal" trawls, don't check methots and skip when testing flag is set
                if not self.methotFlag and not self.testing:
                    #  do some basic checks on the data we just collected to make sure
                    #  we didn't miss anything big.
                    self.sampleValidation1()

                    if self.returnFlag:
                        #  user chose to fix the problem so we don't exit
                        event.ignore()
                        return

                # populate the total partition weights into the event_data table
                self.totalHaulWeight()

                # this is the last station to close - reset the active haul
                sql = ("UPDATE " + self.schema + ".application_configuration SET parameter_value = 0" +
                        " WHERE parameter = 'ActiveHaul'")
                self.db.dbExec(sql)

            #  update the CATCH_SUMMARY table for this event - we'll update it every time
            #  a station exits to ensure that it is fully up-to-date
            ok, error_txt = self.updateCatchSummary()
            if not ok:
                #  let the user know there was a problem
                self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                        error_txt, 'info')
                self.message.exec()

            #  tell SensorMonitor to shut down. SensorMonitor will signal after
            #  all threads have stopped. We set the sensorsStopping attribute so
            #  we know that this is an intentional shutdown
            self.sensorsStopping = True
            self.sensorMonitor.stopMonitoring()

            #  lastly ignore this event for now and wait for
            #  our sensors to close
            event.ignore()


    def devicesClosed(self):
        '''devicesClosed is called when the SensorMonitor emits the
        SensorsStopped signal which lets us know all acquisition
        threads have stopped. Once they are stopped we can close the
        form without error. (Qt gets angry when threads are destroyed
        while running.) Set sensorsClosed to True and call close()
        again.
        '''

        #  we check if this is an intentional shutdown and if so, close
        #  the form. This method will also be called if every sensor
        #  fails to start when the form is initializing and we *don't*
        #  want to close the form in that case.
        if self.sensorsStopping:
            #  set sensorsClosed to True and call close() again
            self.sensorsClosed = True
            self.close()



    def totalHaulWeight(self):
        '''totalHaulWeight updates the HAUL_DATA PartitionWeight parameter for each partition
        that has a PartitionWeightType of "not_subsampled". This is done by summing up the
        weights of all baskets, which is how you compute the total catch weight when you
        don't subsample.
        '''
        #  loop thru the partitions and add up baskets for any partition that is not subsampled.
        for partition in self.partitions:

            #  check if this partition is not_subsampled
            sql = ("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                    " AND partition='" + partition +"' AND event_parameter='PartitionWeightType'")
            query = self.db.dbQuery(sql)
            weightType, = query.first()

            if weightType.lower() in ["not_subsampled", "not subsampled"]:
                #  this partition is not subsampled, add up all of the basket weights
                total_weight = 0

                #  get the sample parent ID
                sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                        " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                        " AND partition='" + partition + "' AND sample_type='WholeHaul'")
                query = self.db.dbQuery(sql)
                parent_id, = query.first()
                parent_id = int(parent_id)

                #  get the sample IDs associated with this parent
                sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                        " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                        " AND parent_sample=" + str(parent_id))
                sampleQuery, = self.db.dbQuery(sql)

                #  loop thru those samples and add up the baskets
                for sample_id in sampleQuery:
                    #  get the weight of all baskets of this sample id
                    sql = ("SELECT weight FROM " + self.schema + ".baskets WHERE ship=" + self.ship +
                            " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                            " AND sample_id=" + sample_id)
                    query = self.db.dbQuery(sql)
                    for weight, in query:
                        try:
                            #  convert the string weight to float and append to
                            total_weight += float(weight)
                        except:
                            #  error converting basket weight to float - ignore this basket
                            pass

                #  update the partition weight in EVENT_DATA
                sql = ("UPDATE " + self.schema + ".event_data set parameter_value=" + str(round(total_weight,3)) +
                        " WHERE ship=" + self.ship + " AND survey=" + self.survey +
                        " AND event_id=" + self.activeHaul + " AND partition='" +
                        partition + "' AND event_parameter='PartitionWeight'")


    def updateCatchSummary(self):
        '''
        updateCatchSummary updates the catch_summary table with data from this event. Data in catch_summary
        are generated outside the database and loaded into the table. These data need to be updated
        whenever the underlying data change. This method does this.

        '''

        event_id = self.activeHaul

        #  set the initial return state
        ok = True
        error_msg = ''

        try:

            #  create an instance of clamsbase functions
            clamsFunctions = Clamsbase2Functions.Clamsbase2Functions(self.db, self.ship,
                    self.survey)

            #  start a transaction to ensure that any other clients closed while this
            #  code is running are blocked until this transaction completes.
            self.db.startTransaction()

            #  delete existing data for this event
            sql = ("DELETE FROM " + self.schema + ".catch_summary WHERE ship=" + self.ship + " AND survey=" + self.survey +
                    " AND event_id=" + event_id)
            self.db.dbExec(sql)

            #  find all the unique species samples
            sql = ("SELECT sample_id, parent_sample, partition, species_code, subcategory FROM " + self.schema + ".samples " +
                    "WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND event_id=" + event_id +
                    " AND sample_type='Species'")
            sampleQuery = self.db.dbQuery(sql)

            for sample_id, parent_sample, partition, species_code, subcategory in sampleQuery:
                #  call the computeCatchSummary method of clamsFunctions to, er compute the
                #  catch summary data.
                [status, vals]=clamsFunctions.computeCatchSummary(event_id, partition, species_code, subcategory)

                #  check if we successfully computed the summary data
                if status:
                    #  since status is OK, discard the empty error strings that can be returned in
                    #  vals. vals[0] is a list containing the following data:
                    #    vals = [sample id, species code, subcategory, sample id, WeightInHaul,SampledWeight,
                    #            NumberInHaul,SampledNumer,FrequencyExpansion,InMix,WholeHauled]
                    vals = vals[0]

                    #  get species name
                    sql = ("SELECT scientific_name, common_name FROM " + self.schema + ".species WHERE species_code=" + species_code)
                    sppQuery = self.db.dbQuery(sql)
                    sci_name, common_name = sppQuery.first()

                    #  then insert results into catch summary table
                    sql = ("INSERT INTO " + self.schema + ".catch_summary (ship,survey,event_id,partition,sample_id,parent_sample," +
                            "scientific_name,species_code,common_name,subcategory,weight_in_haul,sampled_weight," +
                            "number_in_haul,sampled_number,frequency_expansion,in_mix,whole_hauled) VALUES(" +
                            self.ship + "," + self.survey + "," + event_id + ",'" + partition + "'," + sample_id + "," +
                            parent_sample + ",'" + sci_name + "'," + species_code + ",'" + common_name +
                            "','" + subcategory + "'," + str(vals[4]) + "," + str(vals[5]) + "," +
                            str(vals[6]) + ","+str(vals[7]) + "," + str(vals[8]) + "," + str(vals[9]) +
                            "," + str(vals[10]) + ")")
                    self.db.dbExec(sql)
                else:
                    #  check to make sure there is an actionable error - computeCatchSummary can return false if there
                    #  is a sample with no measurements which we silently ignore here as it isn't necessarily an error
                    if (len(vals) > 0):
                        error_msg = ("Error computing catch summary data for event " +
                                event_id + ". Error text:" + vals[2]  + vals[1])
                        ok = False

                        #  rollback on error
                        self.db.rollback()

                        break

            #  update is complete - commit
            self.db.commit()

        except Exception as e:
            #  there was some issue updating the catch summary
            error_msg = ("Unknown error computing catch summary data for event " +
                    event_id + ". Error:" + str(e))
            ok = False

            #  rollback on error
            self.db.rollback()

        return (ok, error_msg)


    def sampleValidation1(self):
        '''
        sampleValidation1 performs some basic checks to make sure there aren't any obvious
        errors made during sampling.
        '''

        self.returnFlag = False

        #  loop thru the partitions doing common validations on the catch
        for partition in self.partitions:
            # loop though samples in this partition
            sql = ("SELECT species.common_name, samples.sample_id, samples.species_code, samples.subcategory" +
                    " FROM " + self.schema + ".species, samples WHERE species.species_code = samples.species_code" +
                    " AND samples.event_id=" + self.activeHaul + " AND samples.ship=" + self.ship +
                    " AND samples.survey=" + self.survey + " AND samples.partition='" +
                    partition + "' and samples.sample_type = 'Species'")
            sampleQuery = self.db.dbQuery(sql)

            #  loop thru the sampes
            for species, key, code, subcat in sampleQuery:

                # validation #1 - check for species samples without weights
                sql = ("SELECT * FROM " + self.schema + ".baskets WHERE sample_id=" + key+" AND event_id=" +
                        self.activeHaul + " AND ship=" + self.ship +
                        " AND survey=" + self.survey)
                query = self.db.dbQuery(sql)

                if not query.first():
                    # this sample has no basket weights
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                            "You haven't weighed any baskets for " + species + " in the " +
                            partition + ". Do you want to return to sampling?", 'choice')
                    if self.message.exec():
                        #  return to sampling to fix problem
                        self.returnFlag = True
                        return
                    else:
                        #  user decided to delete the sample that doesn't have a weight
                        sql = ("DELETE FROM " + self.schema + ".samples WHERE samples.sample_id = " + key+
                                " AND samples.event_id=" + self.activeHaul +
                                " AND samples.ship=" + self.ship +
                                " AND samples.survey=" + self.survey)
                        self.db.dbExec(sql)


                # validation #2 - are there samples of type measure lacking specimen (or length) data

                #  get the total basket weight for this sample
                sql = ("SELECT sum(weight) FROM " + self.schema + ".baskets WHERE basket_type = 'Measure'" +
                        " AND sample_id=" + key+" AND event_id=" +
                        self.activeHaul + " AND ship=" + self.ship +
                        " AND survey=" + self.survey)
                query = self.db.dbQuery(sql)
                basketWeight, = query.first()
                basketWeight = float(basketWeight)

                #  make sure we have at least one basket with a weight for this sample
                if basketWeight != 0:
                    # there are "measure" baskets - check if there are specimen
                    sql = ("SELECT specimen_id FROM " + self.schema + ".specimen WHERE sample_id = " + key+
                            " AND event_id=" + self.activeHaul + " AND ship=" +
                            self.ship + " AND survey=" + self.survey)
                    query = self.db.dbQuery(sql)

                    if query.first():
                        #  There are also specimen.

                        #  validation #3 - verify that there is an appropriate sample weight for
                        #  the number of specimen. First the get length/weight regression params
                        #  if available for this species
                        sql = ("SELECT parameter_value FROM " + self.schema + ".species_data WHERE species_code="+
                                code + " AND subcategory='" + subcategory + "' AND lower(" +
                                "species_parameter)='a_param'")
                        query = self.db.dbQuery(sql)
                        aParm, = query.first()
                        if aParm:
                            try:
                                self.aParm=float(aParm)
                            except:
                                self.aParm=None
                        else:
                            self.aParm=None
                        sql = ("SELECT parameter_value FROM " + self.schema + ".species_data WHERE species_code="+
                                code + " AND subcategory='" + subcategory +
                                "' AND lower(species_parameter)='b_param'")
                        query = self.db.dbQuery(sql)
                        bParm, = query.first()
                        if bParm:
                            try:
                                self.bParm=float(bParm)
                            except:
                                self.bParm=None
                        else:
                            self.bParm=None

                        #  if we have length/weight parameters for this species we'll compute
                        #  a theoretical weight
                        if self.aParm and self.bParm:
                            #  get the lengths
                            sql = ("SELECT measurement_value FROM  " + self.schema + ".measurements WHERE " +
                                    "sample_id=" + key + "  AND event_id=" + self.activeHaul +
                                    " AND ship=" + self.ship +" AND survey=" + self.survey+
                                    " AND LOWER(measurement_type) LIKE '%length%'")
                            query = self.db.dbQuery(sql)

                            #  sum up the theoretical weights for the sampled lengths
                            calcWeight = 0
                            for length, in query:
                                try:
                                    length = float(length)
                                    calcWeight += (length ** self.aParm) * self.bParm
                                except:
                                    #  skip over bad data
                                    pass

                            #  if there are no measured fish we have to move on
                            if calcWeight==0:
                                continue

                            #  Compare the sample weight and the theoretical weight
                            deviation = (calcWeight - basketWeight) / calcWeight

                            #  check that the two weights are within the allowed threshold
                            if abs(deviation) > float(self.settings['SubSampleCheckThreshold']):
                                # The sample deviates too much from the theoretical weight
                                self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                        "The weight of the measured sample is " +
                                        str(round(1+deviation, 0)) + "% different from the estimated " +
                                        "weight for " + species + " in the " + partition +
                                        " using length weight regression of measured fish. You might " +
                                        "have misclassified a Basket." + " Do you want to return to "
                                        "the sampling?", 'choice')
                                if self.message.exec():
                                    #  return to fix the problem
                                    self.returnFlag = True
                                    return
                                else:
                                    #  Ignore the problem - insert into override table
                                    self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                            "OK. This exception has been logged in the overrides table.", 'info')
                                    self.message.exec()

                                    #  insert into overrides table
                                    overrideDesc = ("'Bad subsample weight. Total sampled weight=" +
                                            str(round(basketWeight,2)) + " Theoretical weight=" +
                                            str(round(calcWeight,2)) + "'")
                                    sql = ("INSERT INTO " + self.schema + ".overrides (ship,survey,event_id,record_id,table_name," +
                                            "scientist,description) VALUES (" + self.ship + ", " + self.survey +
                                            "," + self.activeHaul + "," + key + ",'baskets','" +
                                            self.scientist + "'," + overrideDesc + ")")
                                    self.db.dbExec(sql)

                                    self.returnFlag = False

                    else:
                        # Huh, there are baskets with no specimen
                        self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                "You have some basket weights of type 'Measure' for " + species +
                                " in the " + partition + " but no measurements!  Are you able " +
                                "to live with yourself?", 'choice')
                        if not self.message.exec():
                            self.returnFlag=True
                            return


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        '''
        checkWindowLocation accepts a window position (QPoint) and size (QSize)
        and returns a potentially new position and size if the window is currently
        positioned off the screen.

        This function uses QScreen.availableVirtualGeometry() which returns the full
        available desktop space *not* including taskbar. For all single and "typical"
        multi-monitor setups this should work reasonably well. But for multi-monitor
        setups where the monitors may be different resolutions, have different
        orientations or different scaling factors, the app may still fall partially
        or totally offscreen. A more thorough check gets complicated, so hopefully
        those cases are very rare.

        If the user is holding the <shift> key while this method is run, the
        application will be forced to the primary monitor.
        '''

        #  create a QRect that represents the app window
        appRect = QRect(position, size)

        #  check for the shift key which we use to force a move to the primary screem
        resetPosition = QGuiApplication.queryKeyboardModifiers() == Qt.KeyboardModifier.ShiftModifier
        if resetPosition:
            position = QPoint(padding[0], padding[0])

        #  get a reference to the primary system screen - If the app is off the screen, we
        #  will restore it to the primary screen
        primaryScreen = QGuiApplication.primaryScreen()

        #  assume the new and old positions are the same
        newPosition = position
        newSize = size

        #  Get the desktop geometry. We'll use availableVirtualGeometry to get the full
        #  desktop rect but note that if the monitors are different resolutions or have
        #  different scaling, some parts of this rect can still be offscreen.
        screenGeometry = primaryScreen.availableVirtualGeometry()

        #  if the app is partially or totally off screen or we're force resetting
        if resetPosition or not screenGeometry.contains(appRect):

            #  check if the upper left corner of the window is off the left side of the screen
            if position.x() < screenGeometry.x():
                newPosition.setX(screenGeometry.x() + padding[0])
            #  check if the upper right is off the right side of the screen
            if position.x() + size.width() >= screenGeometry.width():
                p = screenGeometry.width() - size.width() - padding[0]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setX(p)
            #  check if the top of the window is off the top/bottom of the screen
            if position.y() < screenGeometry.y():
                newPosition.setY(screenGeometry.y() + padding[0])
            if position.y() + size.height() >= screenGeometry.height():
                p = screenGeometry.height() - size.height() - padding[1]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setY(p)

            #  now make sure the lower right (resize handle) is on the screen
            if (newPosition.x() + newSize.width()) > screenGeometry.width():
                newSize.setWidth(screenGeometry.width() - newPosition.x() - padding[0])
            if (newPosition.y() + newSize.height()) > screenGeometry.height():
                newSize.setHeight(screenGeometry.height() - newPosition.y() - padding[1])

        return [newPosition, newSize]
