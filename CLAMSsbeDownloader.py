#!/usr/bin/env python
"""
CLAMSsbeDownloader is a replacement for the MACE SBE download program. This is a
further extension of the MACE mini Downloader used in 2015 which has been modified
to work exclusively with CLAMS. It does not offer the option to download to a text
file and requires a connection to CLAMS and active survey, ship, and haul values
must exist in the application_configuration table.

Also note that this application will attempt to get the latitude to use for pressure
to depth conversions from the EQLatitude parameter in the event_data table. If this
parameter doesn't exist for the active event, it will use a default value of 56.

UPDATES Alicia Billings - Sept 2026
 - preparation for using SBE39+ units
 - cleaning up some code and queries
"""

#  imports
import os
import sys
import math
import socket
import functools
import re
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QSoundEffect
from ui import ui_CLAMSsbeDownloader
import connectdlg
import sbeSetLocation
from acquisition.seabird import sbe39
from acquisition.seabird import sbe39plus
from acquisition.seabird import sbeSetInterval
from acquisition.seabird import sbeProgressDialog
from acquisition.SensorMonitor import selectWinPortDialog
import dbConnection


class CLAMSsbeDownloader(QMainWindow, ui_CLAMSsbeDownloader.Ui_sbeDownloader):

    def __init__(self, dataSource, user, password, settings, schema=None, hostname=None, port=None,parent=None):
        super(CLAMSsbeDownloader, self).__init__(parent)
        self.setupUi(self)

        #  Initialize variables and define constants
        self.dataTextBuffer = []
        self.connecting = False
        self.serialNumber = ''
        self.maxDataTextLines = 500
        self.downloadErrors = 0
        self.maxDownloadErrors = 25
        self.db = None
        self.schema = schema
        self.hostname = hostname
        self.port = port
        self.dbName = dataSource
        self.dbUser = user
        self.dbPassword = password
        self.settings = settings
        self.sbe = None
        self.sbeProgress = None

        self.completeSound = None
        self.haulLat = None
        self.workStation = None
        self.device_id = None

        #  when the 'SBEConversionLat' parameter is not set in the application_configuration
        #  table, the value provided there is not a float, or there is no TD latitude to grab, this is the
        #  default value to use - set around the GOA
        self.defaultEQLatitude = 56.0

        #  restore the application state
        #  the default com port should be set in the application_configuration table 'SBEComPort',
        #  but is set to COM4 here if it isn't there
        self.appSettings = QSettings('CLAMS', 'CLAMSsbeDownloader')
        size = self.appSettings.value('winsize', QSize(690,560))
        position = self.appSettings.value('winposition', QPoint(10,10))
        self.comPort  = self.appSettings.value('comport', 'COM4')
        baud  = self.appSettings.value('baud', 9600)
        try:
            self.baud  = int(baud)
        except:
            self.baud  = 9600

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  add the COM port settings display in the status bar
        self.COMSettingsLabel = QLabel('')
        self.statusbar.addPermanentWidget(self.COMSettingsLabel)
        self.COMSettingsLabel.setText('COM Settings: ' + self.comPort + ', ' + str(self.baud))

        #  update the database user label
        self.userLabel.setText(self.dbUser)

        #  create an instance of the set interval dialog
        self.sbeIntervalDlg = sbeSetInterval.sbeSetInterval(parent=self)

        #  connect the dialog's sbeSetInterval signal - emitted when the user clicks o.k.
        #  on the sbeSetInterval dialog
        self.sbeIntervalDlg.sbeSetIntervalSignal.connect(self.intervalSet)

        #  connect this GUI's button signals
        self.actionExit.triggered.connect(self.close)
        self.actionSetInterval.triggered.connect(self.setInterval)
        self.actionSetComPort.triggered.connect(self.configureComPort)
        self.statusButton.clicked.connect(self.getStatus)
        self.downloadButton.clicked.connect(self.startDownload)
        self.doneBtn.clicked.connect(self.close)
        self.connectButton.clicked.connect(self.connectToSBE)
        self.startButton.clicked.connect(self.startLogging)
        self.stopButton.clicked.connect(self.stopLogging)

        #  set up the button states
        self.setGUIButtons(False)

        #  set the base directory path - this is the full path to this application
        self.baseDir = functools.reduce(lambda l,r: l + os.path.sep + r,
                os.path.dirname(os.path.realpath(__file__)).split(os.path.sep))
        #  set the window icon
        try:
            self.setWindowIcon(QIcon(self.baseDir + os.sep + 'icons/giant_clam.png'))
        except:
            pass

        #  start a timer event to connect to the database
        startTimer = QTimer(self)
        startTimer.setSingleShot(True)
        startTimer.timeout.connect(self.startApplication)
        startTimer.start(0)


    def startApplication(self):
        """
        starts the application by connecting to the database for parameters
        and to determine which model of SBE39 is being used
        :return:
        """
        #  determine which database engine is being used from the application_configuration table
        if self.settings['Database'].lower() == 'oracle':
            isOracle = True
            driver = 'QODBC'
        elif self.settings['Database'].lower() == 'postgres':
            #  use the native Qt Postgres driver
            isOracle = False
            driver = 'QPSQL'
        else:
            #  for everything else just use ODBC
            isOracle = False
            driver = 'QODBC'

        #  clean up and check our paths if any fail, try to fall back to local folders
        if 'ImageDir' in self.settings:
            self.settings['ImageDir'], exists = self.checkPath(self.settings['ImageDir'], 'images')
        else:
            self.settings['ImageDir'], exists = self.checkPath(None, 'images')
        if 'IconDir' in self.settings:
            self.settings['IconDir'], exists = self.checkPath(self.settings['IconDir'], 'icons')
        else:
            self.settings['IconDir'], exists = self.checkPath(None, 'icons')
        if 'SoundsDir' in self.settings:
            self.settings['SoundsDir'], exists = self.checkPath(self.settings['SoundsDir'], 'sounds')
        else:
            self.settings['SoundsDir'], exists = self.checkPath(None, 'sounds')

        #  if we're missing any credentials, get them from the user
        # todo: hostname, port, and schema is required for postgres so update this to catch those missing items as well
        if self.dbName == '' or self.dbUser == '' or self.dbPassword == '':
            connectionDialog = connectdlg.ConnectDlg(self.dbName, self.dbUser,
                                                     self.dbPassword, createConnection=False, parent=self)
            ok = connectionDialog.exec()
            if not ok:
                self.close()
                return
            self.dbName = connectionDialog.getSource()
            self.dbUser = connectionDialog.getUsername()
            self.dbPassword = connectionDialog.getPassword()

        #  create an instance of our dbConnection
        self.db = dbConnection.dbConnection(self.dbName, self.dbUser,
                                            self.dbPassword, label=self.schema, isOracle=isOracle,
                                            driver=driver, hostname=self.hostname, port=self.port)
        self.db.bioSchema = self.schema

        try:
            self.db.dbOpen()
        except Exception as err:
            QMessageBox.critical(self,"ERROR", "Unable to connect to the database. " + str(err))
            self.close()
            return

        #  determine our hostname and query database for workstation number
        computerName = socket.gethostname()
        query = self.db.dbQuery("SELECT workstation_id FROM " + self.schema +
                ".workstations WHERE hostname ='" + computerName + "'")
        self.workStation, = query.first()

        if self.workStation is None:
            QMessageBox.critical(self, "ERROR", "<font size = 12> Unable to find this " +
                    "computer name (" + computerName + ") in the workstations table. " +
                    "This workstation must be added to and configured in the database " +
                    "before you can run CLAMS on it.")
            self.close()
            return

        #  read in general application settings from database
        sql = ("SELECT parameter, parameter_value FROM " + self.schema +
                ".application_configuration ")
        query = self.db.dbQuery(sql)
        for parameter, parameter_value in query:
            self.settings.update({parameter: parameter_value})

        if 'SBEConversionLat' in self.settings:
            try:
                self.defaultEQLatitude = float(self.settings['SBEConversionLat'])
            except ValueError:
                pass

        if 'SBEComPort' in self.settings:
            self.comPort = self.settings['SBEComPort']

        sbe_model = self.settings.get('SBEModel', 'SBE39').strip().upper()

        if sbe_model == 'SBE39PLUS':
            self.sbe = sbe39plus.sbe39plus(self.comPort, baud=self.baud)
        else:
            self.sbe = sbe39.sbe39(self.comPort, baud=self.baud)

        #  connect the SBE signals
        self.sbe.SBEStatus.connect(self.sbeStatusUpdate)
        self.sbe.SBEConnected.connect(self.connected)
        self.sbe.SBETimeout.connect(self.sbeTimeout)
        self.sbe.SBEData.connect(self.showSBEData)
        self.sbe.SBEProgress.connect(self.showProgress)
        self.sbe.SBEDownloadComplete.connect(self.downloadComplete)
        self.sbe.SBEDownloadData.connect(self.downloadingData)
        self.sbe.SBEAbort.connect(self.downloadAbort)

        #  create an instance of the SBE progress dialog - this dialog shows download progress
        #  and has an abort button. You pass it the reference to the sbe object and it
        #  handles the signals internally. You just need to show and hide it.
        self.sbeProgress = sbeProgressDialog.sbeProgressDialog(self.sbe, parent=self)

        #  update status bar text with final COM Port
        self.COMSettingsLabel.setText('COM Settings: ' + self.comPort + ', ' + str(self.baud))

        #  load plankton icon
        if not QDir().exists(self.settings['IconDir']):
            QMessageBox.critical(self, "ERROR", "<font size = 12>Icon directory not found. ")
        else:
            icon = QImage(self.settings['IconDir'] + "plankton.png")
            icon = icon.scaledToHeight(self.imgLabel.height(),
                    Qt.TransformationMode.SmoothTransformation)
            self.imgLabel.setPixmap(QPixmap.fromImage(icon.mirrored(horizontal=True,
                    vertical=False)))

        #  load sound effect
        if not QDir().exists(self.settings['SoundsDir']):
            QMessageBox.warning(self, "ERROR", "<font size = 12>Sound directory not found. " +
                    "SBE Downloader will operate without sound.")
        else:
            self.completeSound = QSoundEffect()
            self.completeSound.setSource(QUrl.fromLocalFile(self.settings['SoundsDir'] +
                    'dp_starwars_yahoo.wav'))

        # populate from active ship, survey, and event stuff
        try:
            self.shipLabel.setText(self.settings['ActiveShip'])
            self.surveyLabel.setText(self.settings['ActiveSurvey'])
        except:
            QMessageBox.critical(self,"ERROR", "ActiveEvent and/or ActiveSurvey are not in the " +
                    "application_configuration table. Something is not right. Ask your CLAMS " +
                    "database administrator.")
            self.db.dbClose()
            self.close()
            return

        try:
            event = self.settings['ActiveEvent']
            self.haulLabel.setText(event)
        except:
            QMessageBox.critical(self,"ERROR", "ActiveEvent is missing from the application_configuration " +
                    "table. Something is not right. Ask your CLAMS database administrator.")
            self.db.dbClose()
            self.close()
            return

        #  get the latitude of this event - first we try to get it from the event_data table
        #  the latitude is pulled from when the net is 'fishing', which can be different for different centers
        # todo: maybe use the application_configuration table to set this parameter?
        fishing_parameters = ('EQLatitude', 'TDLatitude')
        query = self.db.dbQuery(f"SELECT parameter_value FROM {self.schema}.event_data "
                                f"WHERE ship={self.settings['ActiveShip']} and survey={self.settings['ActiveSurvey']} "
                                f"and event_id={event} and event_parameter IN {fishing_parameters}")
        eqLatitude, = query.first()
        if eqLatitude is None:
            #  event doesn't have an EQ entry, use default value from settings or hardcoded default
            eqLatitude = self.defaultEQLatitude
        try:
            self.haulLat = float(eqLatitude)
        except:
            self.haulLat = self.defaultEQLatitude


    def configureComPort(self):
        dialog = selectWinPortDialog.selectWinPortDialog(defaultPort=self.comPort,
                                                         defaultBaud=self.baud, parent=self)
        ok = dialog.exec()
        if ok:
            self.comPort = dialog.port
            self.baud = dialog.baud

            if self.sbe:
                self.sbe.setConnectionParams(self.comPort, self.baud)

            # update settings and GUI
            self.appSettings.setValue('comport', self.comPort)
            self.appSettings.setValue('baud', self.baud)
            self.COMSettingsLabel.setText('COM Settings: ' + self.comPort + ', ' + str(self.baud))
            # todo: update default in application_configuration?


    def showProgress(self, device, pctComplete):
        #  this is just here as a stub since we're using the SBE progress dialog to display
        #  progress. If you use the SBE progress dialog you don't need to connect the progress
        #  signal nor implement this function
        pass


    def downloadComplete(self, device, nDownloaded, nDropped):

        #  hide and reset the progress dialog
        self.sbeProgress.hide()
        self.sbeProgress.reset()

        #  reconnect the SBEData signal
        self.sbe.SBEData.connect(self.showSBEData)

        #  report our results
        if nDownloaded > 2:
            # Compute averages to be inserted into the event_data table
            self.computeAverages()

            #  play the download complete sound
            self.completeSound.play()

            #  report success
            QMessageBox.information(self, 'Success', str(nDownloaded) + ' measurements ' +
                    'downloaded successfully.')
        else:
            QMessageBox.critical(self, 'ERROR', str(nDownloaded)+' measurements downloaded. ' +
                    'Try stopping the SBE from recording and THEN press download.')


    def downloadAbort(self):

        #  hide and reset the progress dialog
        self.sbeProgress.hide()
        self.sbeProgress.reset()

        #  reconnect the SBEData signal
        self.sbe.SBEData.connect(self.showSBEData)

        #  show a temporary message on the status bar
        self.statusbar.showMessage('Downloading aborted.', 5000)


    def downloadingData(self, device, line):

        #  build the time string
        mdy = '{:02d}/{:02d}/{:04d}'.format(line[0].month, line[0].day, line[0].year)
        hms = '{:02d}:{:02d}:{:02d}'.format(line[0].hour, line[0].minute, line[0].second +
                int(round(line[0].microsecond/1000000.)))
        time = mdy + " " + hms

        #  calculate depth from pressure
        depth = round(self.pressureToDepth(line[2], self.haulLat), 3)

        #  insert data into database
        sql = (f"INSERT INTO {self.schema}.event_stream_data (ship, survey, event_id, device_id, " +
                f"time_stamp, measurement_type, measurement_value) VALUES ({self.shipLabel.text()}, "
                f"{self.surveyLabel.text()}, {self.haulLabel.text()}, {self.device_id}, "
                f"TO_TIMESTAMP('{time}','MM/DD/YYYY HH24:MI:SS.FF'),'SBETemperature', '{str(line[1])}')")
        self.db.dbExec(sql)
        sql = (f"INSERT INTO {self.schema}.event_stream_data (ship, survey, event_id, device_id, " +
                f"time_stamp, measurement_type, measurement_value) VALUES ({self.shipLabel.text()}, "
                f"{self.surveyLabel.text()}, {self.haulLabel.text()}, {self.device_id}, "
                f"TO_TIMESTAMP('{time}','MM/DD/YYYY HH24:MI:SS.FF'),'SBEDepth','{str(depth)}')")
        self.db.dbExec(sql)


    def connectToSBE(self):

        if not self.sbe.connected:
            #  we're connecting to the SBE - attempt to connect to the SBE
            try:
                self.serialNumber = ''
                self.statusbar.showMessage('Trying to wake SBE...')
                self.connecting = True
                self.sbe.connect()
            except Exception:
                 QMessageBox.critical(self, 'Error', 'Unable to open COM port ' + str(self.comPort))
                 self.statusbar.showMessage('')
        else:
            #  we need to disconnect from the SBE
            self.sbe.disconnect()

            #  update the GUI
            self.setGUIButtons(False)


    def connected(self, device):

        #  show a temporary message on the status bar
        self.statusbar.showMessage('Connected to ' + device, 10000)

        #  get the SBE status
        self.sbe.getStatus()

        #  set up the GUI
        self.setGUIButtons(True)


    def pressureToDepth(self, p, lat):
        """
        calculates depth based on latitude and pressure. From:
        Unesco 1983. Algorithms for computation of fundamental properties of
        seawater, 1983. _Unesco Tech. Pap. in Mar. Sci._, No. 44, 53 pp.
        """

        deg2rad = math.pi / 180.0

        # Eqn 25, p26.  UNESCO 1983.
        c = [9.72659, -2.2512e-5, 2.279e-10, -1.82e-15]
        gam_dash = 2.184e-6

        lat = abs(lat)
        X = math.sin(lat * deg2rad)
        X = X * X

        bot_line = (9.780318 * (1.0 + (5.2788e-3 + 2.36e-5 * X) * X) +
                    gam_dash * 0.5 * p)
        top_line = (((c[3] * p + c[2]) * p + c[1]) * p + c[0]) * p

        return top_line / bot_line


    def sbeStatusUpdate(self, deviceName, status):
        """
        sbeStatusUpdate is called when we receive the results of a status request.
        We only care about the details when we are connecting to the SBE since
        that is when we extract the serial number. Otherwise we don't do anything.
        """
        if self.connecting:
            self.connecting = False
            self.serialNumber = status['serial number']

            # Match both SBE39 and SBE39Plus device models in the DEVICES table
            sql = (f"SELECT device_id FROM {self.schema}.devices WHERE (model LIKE 'SBE39%' OR model LIKE 'SBE 39%') "
                   f"AND serial_number='{self.serialNumber}'")
            query = self.db.dbQuery(sql)
            self.device_id, = query.first()

            if self.device_id is None:
                self.sbe.disconnect()
                self.setGUIButtons(False)
                QMessageBox.critical(self, 'Error',
                                     "Can't find an SBE with serial number " + self.serialNumber +
                                     " in the DEVICES table.\nPlease add this device before downloading.")


    def startLogging(self):
        ok = QMessageBox.question(self, 'Start Logging', 'Reset the sample number to 0 and start logging? \n' +
                'Existing data will be overwritten!', QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if ok == QMessageBox.StandardButton.Ok:
            self.sbe.stop()

            # set the sample number to 0
            self.sbe.setSampleNumber(0)

            #  set the SBE clock
            self.sbe.setRTC()

            # get realtime data
            self.sbe.setTxRealTime(True)

            #  start logging
            self.sbe.startNow()

        #  DO NOT INTERACT WITH THE SBE AFTER STARTING TO LOG BECAUSE
        #  IT WILL CAUSE THE SBE TO TEMPORARILY STOP LOGGING WHILE IT
        #  SITS IN 'COMMAND' MODE. (It will eventually start logging
        #  again after it times out of command mode after 2 or 3
        #  minutes but it's best just to avoid sending any commands
        #  at this point.)


    def stopLogging(self):

        #  stop the SBE logging
        self.sbe.stop()

        #  update the status in the GUI
        self.sbe.getStatus()


    def sbeTimeout(self):

        #  issue an error
        QMessageBox.critical(self, 'Error', 'Unable to connect or lost connection to SBE on ' +
                str(self.comPort))

        #  disconnect the SBE
        self.sbe.disconnect()

        #  update the GUI
        self.setGUIButtons(False)


    def intervalSet(self, interval, rto):
        #  this method is called when the sbeSetInterval signal is received meaning the
        #  user has set a new sampling interval.

        self.sbe.setSamplingInterval(interval)
        self.sbe.setTxRealTime(rto)

        #  update the status in the GUI
        self.sbe.getStatus()


    def setInterval(self):

        #  get the current interval and RealTime Output values
        rtoText = self.sbe.status.get('real-time output', 'not')
        if (rtoText.lower().find('not') > -1) or (rtoText.lower().find('disabled') > -1):
            rto = False
        else:
            rto = True
        interval = int(self.sbe.status.get('sample interval', '0').split()[0])

        #  set the values in the dialog and show
        self.sbeIntervalDlg.setInterval(interval, rto)
        self.sbeIntervalDlg.exec()


    def setGUIButtons(self, state):
        """
        setGUIButtons sets the state of the GUI elements based on the connection
        state. True if we're connected to the SBE and False if not.
        """

        if state:
            self.connectButton.setText('Disconnect')

        else:
            self.connectButton.setText('Connect')

        self.actionSetComPort.setEnabled(not state)
        self.actionSetInterval.setEnabled(state)
        self.statusButton.setEnabled(state)
        self.startButton.setEnabled(state)
        self.stopButton.setEnabled(state)
        self.downloadButton.setEnabled(state)


    def getStatus(self):
        self.sbe.getStatus()


    def startDownload(self):
        """
        startDownload attempts to start the SBE download process. It first checks for
        existing data, asking the user if they want to overwrite if found, and then it
        disconnects the SBEData signal (so we don't flood the console with data strings)
        and then tells the SBE class to download.
        """

        #  create an instance of the set location dialog to get the mounting location
        sbeLocationlDlg = sbeSetLocation.sbeSetLocation(parent=self)
        sbeLocationlDlg.exec()

        #  make sure that the user specified a location
        if sbeLocationlDlg.location is None:
            #  no location specified
            return

        #  set the location
        self.sbeLocation = sbeLocationlDlg.location

        try:
            #  determine if this data has already been downloaded
            sql = (f"SELECT event_parameter FROM {self.schema}.event_data WHERE ship={self.shipLabel.text()}" +
                    f" AND survey={self.surveyLabel.text()} AND event_id={self.haulLabel.text()}" +
                    f" AND event_parameter like '%SBE' AND parameter_value='{self.serialNumber}'")
            mountingLocQuery = self.db.dbQuery(sql)
            mountingLoc, = mountingLocQuery.first()

            if mountingLoc is not None:
                reply = QMessageBox.question(self, 'Warning!',"<font size = 14> You already downloaded SBE " +
                        "data for this haul and SBE device.  Do you want to overwrite? </font>",
                        QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:

                    #  get the parameters names for the previous mounting location
                    avgDepthParam, avgTempParam = self.getAveragesParamNames(mountingLoc)

                    #  now we can clear out old data
                    sql = (f"DELETE FROM {self.schema}.event_stream_data WHERE ship={self.shipLabel.text()} AND survey=" +
                            f"{self.surveyLabel.text()} AND event_id={self.haulLabel.text()} AND device_id=" +
                            f"{self.device_id}")
                    self.db.dbExec(sql)
                    #  and clear out the old average data as well
                    sql = (f"DELETE FROM {self.schema}.event_data WHERE ship={self.shipLabel.text()} AND survey=" +
                            f"{self.surveyLabel.text()} AND event_id={self.haulLabel.text()} AND " +
                            f"event_parameter='{avgDepthParam}'")
                    self.db.dbExec(sql)
                    sql = (f"DELETE FROM {self.schema}.event_data WHERE ship={self.shipLabel.text()} AND survey=" +
                            f"{self.surveyLabel.text()} AND event_id={self.haulLabel.text()} AND " +
                            f"event_parameter='{avgTempParam}'")
                    self.db.dbExec(sql)

                    #  and lastly, clear out the mounting location
                    sql = (f"DELETE FROM {self.schema}.event_data WHERE ship={self.shipLabel.text()} AND survey=" +
                            f"{self.surveyLabel.text()} AND event_id={self.haulLabel.text()} AND " +
                            f"event_parameter like '%SBE' AND parameter_value='{self.serialNumber}'")
                    self.db.dbExec(sql)

                else:
                    #  user chose not to overwrite
                    return

            #  insert the SBE mounting location into haul_data
            self.db.dbQuery(f"INSERT INTO {self.schema}.event_data (ship,  survey, event_id, partition, " +
                f"event_parameter,  parameter_value) VALUES({self.shipLabel.text()}" +
                f",{self.surveyLabel.text()},{self.haulLabel.text()},'Codend','" +
                f"{self.sbeLocation}','{self.serialNumber}')")

            #  show the progress dialog
            self.sbeProgress.show()

            #  disconnect the SBEData signal since displaying the data during
            #  download slows the download down significantly.
            self.sbe.SBEData.disconnect(self.showSBEData)

            #  download all samples for previous logging session - calling download with
            #  no arguments will download all samples from 0 to the current sample.
            #  NOTE THAT YOU MUST UPDATE THE STATUS OF THE DEVICE AFTER IT IS STOPPED TO
            #  MAKE SURE THAT SAMPLE NUMBER IS UP TO DATE.
            self.downloadErrors = 0
            self.sbe.download()

        except Exception as err:
            #  there was an error
            QMessageBox.critical(self, 'Error', 'Error downloading data: ' + str(err))


    def showSBEData(self, name, val, color='black'):
        if val:
            # Check if this is a raw XML string that wasn't pre-formatted
            if val.strip().startswith('<') and val.strip().endswith('>'):
                # Extract XML tag-value pairs: <SampleInterval>3</SampleInterval> -> SampleInterval: 3
                matches = re.findall(r'<([A-Za-z0-9_]+)>\s*([^<]+)\s*</\1>', val)
                if matches:
                    val = " | ".join([f"{k}: {v}" for k, v in matches])
                else:
                    # Remove XML brackets but leave text contents
                    val = re.sub(r'<[^>]+>', ' ', val).strip()

            if val:
                self.dataTextBuffer.append(val)
                if len(self.dataTextBuffer) > self.maxDataTextLines:
                    self.dataTextBuffer.pop(0)
                text = '\n'.join(self.dataTextBuffer)
                self.dataText.setPlainText(text)
                self.dataText.verticalScrollBar().setValue(
                    self.dataText.verticalScrollBar().maximum()
                )


    def closeEvent(self, event=None):

        self.sbe.disconnect()
        if self.db:
            self.db.dbClose()
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())
        self.appSettings.setValue('comport',self.comPort)
        self.appSettings.setValue('baud',self.baud)


    def getAveragesParamNames(self, locationName):
        """
        getAveragesParamNames returns the event_parameters used to store the
        averages computed for the specified SBE mounting location. Since
        there isn't a straightforward way to identify these params in the
        event_parameters table and link them to their mounting location, and
        the fact that we'll only have a handful, we're hard coding them here.

        This method is used both when deleting existing data and inserting
        averages for just downloaded data.
        """

        #  set the event_parameters based on the mountng location
        if locationName == 'HeadropeSBE':
            avgDepthParam = 'AvgSBEHeadRopeDepth'
            avgTempParam = 'AvgSBEHeadRopeTemp'
        elif locationName == 'FootropeSBE':
            avgDepthParam = 'AvgSBEFootRopeDepth'
            avgTempParam = 'AvgSBEFootRopeTemp'
        elif locationName == 'DropTSSBE':
            avgDepthParam = 'AvgSBEDropTSDepth'
            avgTempParam = 'AvgSBEDropTSTemp'
        elif locationName == 'DropcamSBE':
            avgDepthParam = 'AvgSBEDropcamDepth'
            avgTempParam = 'AvgSBEDropcamTemp'
        else:
            #  we don't compute averages for this mounting location
            avgDepthParam = None
            avgTempParam = None

        return avgDepthParam, avgTempParam


    def computeAverages(self):
        """
        computeAverages is called after download to compute the average temp and depth of
        the SBE between EQ and Haulback. These values are then inserted into the EVENT_DATA
        table
        """

        #  7-26-18 - RHT: In addition to tracking the mounting location, I have changed
        #  the event_parameters for the averages so they are specific to the mounting
        #  location. I have omitted computing averages for Camtrawl and "Other" for now.

        #  set the event_parameters based on the mountng location
        avgDepthParam, avgTempParam = self.getAveragesParamNames(self.sbeLocation)
        if avgDepthParam is None:
            #  we don't compute averages for this mounting location
            return

        ship=self.shipLabel.text()
        survey=self.surveyLabel.text()
        haul=self.haulLabel.text()
        p='Codend'
        avgTemp = float('nan')
        avgDepth = float('nan')

        # Find EQ time
        fishing_params = "'EQ', 'TD', 'TargetDepth'"
        query=self.db.dbQuery(f"SELECT parameter_value FROM {self.schema}.event_data WHERE ship={ship} "
                              f"AND survey={survey} AND event_id= {haul} AND partition='{p}' "
                              f"AND event_parameter IN ({fishing_params})")
        eqTime=query.first()

        # Find HB time
        stop_params = "'HB', 'Haulback'"
        query=self.db.dbQuery(f"SELECT parameter_value FROM {self.schema}.event_data WHERE ship={ship} "
                              f"AND survey={survey} AND event_id= {haul} AND partition='{p}' "
                              f"AND event_parameter IN ({stop_params})")
        hbTime=query.first()

        if eqTime and hbTime:
            # Find temperature data between EQ & HB and average
            query=self.db.dbQuery(f"Select measurement_value FROM {self.schema}.event_stream_data WHERE"+
                            f" time_stamp between to_timestamp('{eqTime[0]}','MMDDYYYY HH24:MI:SS.FF3')" +
                            f" and to_timestamp('{hbTime[0]}','MMDDYYYY HH24:MI:SS:FF3') AND " +
                            f" device_id={self.device_id} AND measurement_type='SBETemperature'")

            query_val =query.first()
            if query_val:
                cumVal = 0.
                nVals = 0
                for val, in query:
                    cumVal = cumVal + float(val)
                    nVals = nVals + 1
                if nVals > 0:
                    avgTemp = cumVal / nVals

            # Find depth data between EQ & HB and average
            query=self.db.dbQuery(f"Select measurement_value FROM {self.schema}.event_stream_data WHERE"+
                            f" time_stamp between to_timestamp('{eqTime[0]}','MMDDYYYY HH24:MI:SS.FF3')" +
                            f" and to_timestamp('{hbTime[0]}','MMDDYYYY HH24:MI:SS:FF3') AND " +
                            f" device_id={self.device_id} AND measurement_type='SBEDepth'")

            if query.first():
                cumVal = 0.
                nVals = 0
                for val, in query:
                    cumVal = cumVal + float(val)
                    nVals = nVals + 1
                if nVals > 0:
                    avgDepth = cumVal / nVals

            # Insert averages into event_data table
            if not math.isnan(avgTemp):
                self.db.dbQuery(f"INSERT INTO {self.schema}.event_data (ship, survey, event_id, partition, " +
                        f"event_parameter, parameter_value) VALUES({ship},{survey},{haul},'"+
                        f"{p}','{avgTempParam}',{avgTemp})")

                self.db.dbQuery(f"INSERT INTO {self.schema}.event_data (ship, survey, event_id, partition, " +
                        f"event_parameter, parameter_value) VALUES({ship},{survey},{haul},'"+
                        f"{p}','{avgDepthParam}',{avgDepth})")
        else:
            #  unable to calculate averages
            QMessageBox.warning(self, 'Attention!', "Unable to calculate averages between EQ and " +
                    "Haulback. Either EQ and HB times are not defined for this event or the timespan " +
                    "of the SBE data does not overlap with EQ and Haulback. That would be bad...")


    def checkPath(self, path, default):
        """
        checkPath cleans up a path and ensures that it has a trailing separator
        and then checks that it exists.
        """

        #  set the default path
        defaultPath =  '.' + os.sep + default + os.sep

        if path is not None:
            #  path provided - normalize the path
            path = os.path.normpath(str(path))

            #  make sure there is a trailing slash
            if (path[-1] != '/') or (path[-1] != '\\'):
                path = path + os.sep
        else:
            path = defaultPath

        #  check for the existence of one of our paths
        if not QDir().exists(path):
            if not QDir().exists(defaultPath):
                return (path, False)
            else:
                return (defaultPath, True)
        else:
            return (path, True)


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        """
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
        """

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


if __name__ == "__main__":

    #  see if the ini file path was passed in
    if len(sys.argv) > 1:
        iniFile = sys.argv[1]
        iniFile = os.path.normpath(iniFile)
    else:
        #  no argument provided, use default
        iniFile = 'clams.ini'

    #  create an instance of QSettings to load fundamental CLAMS settings
    initSettings = QSettings(iniFile, QSettings.Format.IniFormat)

    #  extract connection parameters
    dataSource = initSettings.value('ODBC_Data_Source', '')
    user = initSettings.value('User', '')
    password = initSettings.value('Password', '')
    schema = initSettings.value('Schema', '')
    hostname = initSettings.value('Hostname', '')
    port = initSettings.value('Port', None)
    port = int(port, 0) if port else None

    #  extract the application paths and settings
    settings = {}
    settings['LoggingDir'] = initSettings.value('LoggingDir', './sql_logs')
    settings['ImageDir'] = initSettings.value('ImageDir', './images')
    settings['SoundsDir'] = initSettings.value('SoundsDir', './sounds')
    settings['IconDir'] = initSettings.value('IconDir', './icons')
    settings['Database'] = initSettings.value('Database', 'Oracle')
    settings['GUI-ScrollBar-Width'] = initSettings.value('GUI-ScrollBar-Width', 40)
    settings['HomeScreenImg'] = initSettings.value('HomeScreenImg', 'default.jpg')

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  create an instance of the CLAMSsbeDownloader form
    form = CLAMSsbeDownloader(dataSource, user, password, settings, schema, hostname, port)

    #  show it
    form.show()

    #  and start the application...
    app.exec()
