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
.. module:: CLAMSmain

    :synopsis: CLAMSmain presents the main CLAMS application window.
    It is the entry point for the CLAMS catch processing application.

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

import sys
import os
import functools
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QSoundEffect
import messagedlg
import numpad
import CLAMSprocess
import admindlg
import connectdlg
#import utilitiesdlg
import processdlg
import EventLauncher
import dbConnection
from ui import ui_CLAMSMain


class CLAMSMain(QMainWindow, ui_CLAMSMain.Ui_clamsMain):

    def __init__(self, dataSource, user, password, settings, parent=None):
        #  initialize the superclasses
        super().__init__(parent)

        #  set up the UI
        self.setupUi(self)

        #  define version
        self.version = "V3.0"
        self.titleTextColor = 'rgb(255,255,255)'
        self.testing = False

        #  set database credentials
        self.db = None
        self.schema = user
        self.dbName = dataSource
        self.dbUser = user
        self.dbPassword = password
        self.settings = settings

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'MainWindow')
        size = self.appSettings.value('winsize', QSize(1000,650))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  connect signals
        self.trawlEventBtn.clicked.connect(self.logEvent)
        self.procBtn.clicked.connect(self.processHaul)
        self.utilitiesBtn.clicked.connect(self.utilities)
        self.adminBtn.clicked.connect(self.administration)
        self.exitBtn.clicked.connect(self.close)

        #  set the base directory path - this is the full path to this application
        self.baseDir = functools.reduce(lambda l,r: l + os.path.sep + r,
                os.path.dirname(os.path.realpath(__file__)).split(os.path.sep))
        #  set the window icon
        try:
            self.setWindowIcon(QIcon(self.baseDir + os.sep + 'icons/giant_clam.png'))
        except:
            pass

        #  set the version, survey and ship in the main window
        labelSheet = 'QLabel{color: ' + self.titleTextColor + ';}\n'
        self.titleLabel.setStyleSheet(labelSheet)
        self.subtitleLabel.setStyleSheet(labelSheet)
        self.shipLabel.setStyleSheet(labelSheet)
        self.surveyLabel.setStyleSheet(labelSheet)
        self.schemaLabel.setStyleSheet(labelSheet)
        self.titleLabel.setText("CLAMS " + self.version )
        self.subtitleLabel.setText("Catch Logger for Acoustic Midwater Surveys")

        #  create a single-shot timer that runs the application initialization code
        #  this allows the application to complete the main window init method before
        #  the rest of the initialization code runs.
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.applicationInit)
        initTimer.start(0)


    def applicationInit(self):
        """
        applicationInit creates a connection to the CLAMS database and sets up the
        CLAMS application depending on how the workstation running the application
        is configured.
        """

        #  In order to make scrolling easier for users using a touchscreen with gloves, CLAMS
        #  sets the width of the scroll bar about double the standard width. This can be
        #  altered by setting GUI-ScrollBar-Width in the .ini file
        width = str(self.settings['GUI-ScrollBar-Width'])
        appStyleSheet = 'QScrollBar:vertical{width: ' + width + 'px;}\n'
        self.setStyleSheet(appStyleSheet)

        #  try to load the background image.
        try:
            #  the background image is based on the app version number
            imFile = (self.settings['ImageDir'] + '/backgrounds/' +
                    os.sep + homeScreenImg + ".png")
            imFile = os.path.normpath(imFile)

            #  the image URL must use forward slashes
            imFile = imFile.replace(os.sep, '/')

            #  set the background of the central widget
            appStyleSheet = ("#centralwidget {border-image:url(" + imFile + ");\n" +
                "border-repeat: no-repeat;\n border-position: center;}")

        except:
            #  skip the background image if there is a problem
            pass
        self.centralWidget().setStyleSheet(appStyleSheet)

        #  clean up and check our paths if any fail, try to fallback to local folders
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

        #  load error dialog icons
        if not QDir().exists(self.settings['IconDir']):
            QMessageBox.critical(self, "ERROR", "<font size = 12>Icon directory not found. ")
            self.errorIcons = []
        else:
            dialogImage = QImage(self.settings['IconDir'] + "squidworth.jpg")
            errorIcon = QPixmap.fromImage(dialogImage)
            dialogImage = QImage(self.settings['IconDir'] + "spongebob.jpg")
            msgIcon = QPixmap.fromImage(dialogImage)
            dialogImage = QImage(self.settings['IconDir'] + "patrick.jpg")
            overIcon = QPixmap.fromImage(dialogImage)
            dialogImage = QImage(self.settings['IconDir'] + "sandy.jpg")
            okIcon = QPixmap.fromImage(dialogImage)
            self.errorIcons = [errorIcon,  msgIcon,  overIcon, okIcon]

        #  load base sound effects (device sounds are handled elsewhere)
        self.errorSounds = []
        self.startSound = None
        self.printSound = None
        if not QDir().exists(self.settings['SoundsDir']):
            QMessageBox.warning(self, "ERROR", "<font size = 12>Sound directory not found. " +
                    "CLAMS will operate with generic sounds.")
        else:
            #  these 4 sounds are used to indicate errors, information, questions and ???
            errorSoundFiles = ['Error.wav', 'Ding.wav', 'Exclamation.wav', 'Notify.wav']
            for sound in errorSoundFiles:
                soundEffect = QSoundEffect()
                soundEffect.setSource(QUrl.fromLocalFile(self.settings['SoundsDir'] + sound))
                self.errorSounds.append(soundEffect)

            #  load the "opening" sound (I think this was an easter egg at some point) and the
            #  sound made when sending something to the label printer
            soundEffect = QSoundEffect()
            soundEffect.setSource(QUrl.fromLocalFile(self.settings['SoundsDir'] + 'opening.wav'))
            self.startSound = soundEffect
            soundEffect = QSoundEffect()
            soundEffect.setSource(QUrl.fromLocalFile(self.settings['SoundsDir'] + 'KARATE.wav'))
            self.printSound = soundEffect

        #  create instances of some of our common dialogs
        self.message = messagedlg.MessageDlg(self)
        self.numDialog = numpad.NumPad(self)

        #  setup local SQL logger - CLAMS creates a local text file that contains all of the SQL transactions
        #  First, normalize the path and make sure we have a trailing separator
        self.settings['LoggingDir'] = os.path.normpath(self.settings['LoggingDir'])
        if (self.settings['LoggingDir'][-1] != '/') or (self.settings['LoggingDir'][-1] != '\\'):
            self.settings['LoggingDir'] = self.settings['LoggingDir'] + os.sep

        #  check if the logging directory exists
        if not QDir().exists(self.settings['LoggingDir']):
            reply = QMessageBox.question(self, "ERROR", "<font size = 12>SQL logging directory not found. " +
                    "Do you want to create it?", QMessageBox.StandardButton.Yes,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                QDir().mkdir(self.settings['LoggingDir'])
            else:
                QMessageBox.critical(self, "ERROR", "<font size = 12>Sorry, CLAMS cannot operate without a " +
                        "SQL logging directory. Goodbye!")
                self.close()
                return

        #  After doing some basic setup, we'll continue by connecting to the database
        #  using a timer. This allows the app to draw the initial GUI window before
        #  (possibly) presenting the login dialog and logging into the database.
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.connectToDatabase)
        initTimer.start(0)


    def connectToDatabase(self):
        '''connectToDatabase is called during application startup to
        possibly gather creds and then connect to the database and finish
        setting up the main window.
        '''

        #  determine if we're connecting to an Oracle, postgres, or "other"
        #  database. Since the Oracle driver does not ship compiled with
        #  Qt, we use ODBC for Oracle. Postgres uses the Qt "native" postgres
        #  driver. Other uses ODBC.
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

        #  if we're missing any credentials, get them from the user
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
                driver=driver)

        #  and try to connect
        try:
            self.db.dbOpen()
        except Exception as err:
            #  display the error dialog then close the application
            QMessageBox.critical(self, "Database Login Error", "<font size = 12> Unable " +
                    "to connect to the database.  Does the clams.ini file exist? Are the " +
                    "values in it correct? Error text:" + str(err))
            self.close()
            return

        #  determine our hostname and query database for workstation number
        computerName = os.getenv("COMPUTERNAME")
        sql = ("SELECT workstation_id FROM " + self.schema +
                ".workstations WHERE hostname ='" + computerName + "'")
        query = self.db.dbQuery(sql)
        self.workStation, = query.first()

        if self.workStation is None:
            QMessageBox.critical(self, "ERROR", "<font size = 12> Unable to find this " +
                    "computer name (" + computerName + ") in the workstations table. " +
                    "This workstation must be added to and configured in the database " +
                    "before you can run CLAMS on it.")
            self.close()
            return

        #  close station if the application didn't cleanly exit during the last run
        sql = ("SELECT status FROM " + self.schema + ".workstations WHERE workstation_id =" +
                self.workStation)
        query = self.db.dbQuery(sql)
        status, = query.first()
        if status.lower() == 'open':
            #  the workstation is marked as open so we set it closed
            sql = ("UPDATE " + self.schema + ".workstations SET status='closed' " +
                    "WHERE workstation_ID=" + self.workStation)
            self.db.dbExec(sql)

        #  read in general application settings
        sql = ("SELECT parameter, parameter_value FROM " + self.schema +
                ".application_configuration ")
        query = self.db.dbQuery(sql)
        for parameter, parameter_value in query:
            self.settings.update({parameter:parameter_value})

        # check for a valid Active Survey and Ship
        if 'ActiveSurvey' not in self.settings:
            #  no "ActiveSurvey" parameter exists in application_configuration
            QMessageBox.critical(self, "ERROR", "<font size = 12>ActiveSurvey parameter not found in " +
                    "application_configuration table. Please contact your CLAMS administrator " +
                    "to get this issue resolved.")
            self.close()
            return

        #  read in workstation specific settings
        sql = ("SELECT parameter, parameter_value FROM " + self.schema +
                ".workstation_configuration WHERE workstation_ID = " +
                self.workStation)
        query = self.db.dbQuery(sql)
        #  only update missing keys so we don't overwrite any keys from the .ini
        for parameter, parameter_value in query:
            if parameter not in self.settings:
                self.settings.update({parameter:parameter_value})

        #  query the db for the active survey and update the ship/survey state variables and the GUI
        self.setActiveSurvey()

        #  generate the log file name
        loggerFilename = ('CLAMS_' + QDateTime.currentDateTime().toString('MMddyyyy_hhmmss') +
                '_SQL_Backup.log')

        #  and enable dbConnection logging
        self.db.enableLogging(self.settings['LoggingDir'] + loggerFilename)

        #  Enable only the appropriate actions for this workstation
        try:
            actions = str(self.settings['MainActions'] )
            actions = actions.split(',')
            self.trawlEventBtn.setEnabled(False)
            self.procBtn.setEnabled(False)
            self.adminBtn.setEnabled(False)
            self.utilitiesBtn.setEnabled(False)

            for i in actions:
                if (i.strip().lower() == 'trawl event'):
                    self.trawlEventBtn.setEnabled(True)
                if (i.strip().lower() == 'enter catch'):
                    self.procBtn.setEnabled(True)
                if (i.strip().lower() == 'administration'):
                    self.adminBtn.setEnabled(True)
                if (i.strip().lower() == 'utilities'):
                    self.utilitiesBtn.setEnabled(True)
        except:
            QMessageBox.critical(self, "ERROR", "<font size = 12>Error configuring workstation. " +
                                 "Unable to find this workstation's main actions.")
            self.close()
            return


    def setActiveSurvey(self):
        '''
            setActiveSurvey queries the database for the active ship and survey then
            updates some attributes and the main CLAMS window with the new survey info.
        '''

        #  get the active ship and survey
        sql = ("SELECT parameter_value FROM " + self.schema + ".application_configuration WHERE " +
                "parameter='ActiveSurvey'")
        query = self.db.dbQuery(sql)
        self.survey, = query.first()
        self.settings['ActiveSurvey'] = self.survey
        sql = ("SELECT parameter_value FROM " + self.schema + ".application_configuration WHERE " +
                "parameter='ActiveShip'")
        query = self.db.dbQuery(sql)
        self.ship, = query.first()
        self.settings['ActiveShip'] = self.ship

        #  update the ship name in the GUI
        sql = "SELECT name FROM " + self.schema + ".ships WHERE ship=" + self.ship
        query = self.db.dbQuery(sql)
        self.shipName, = query.first()
        self.surveyLabel.setText("Survey: " + self.survey)
        self.shipLabel.setText("Ship: " + self.shipName)
        self.schemaLabel.setText("Schema: " + self.schema)


    def logEvent(self):
        """
          logEvent displays the event launcher so the user can select the
          type of event to start.
        """

        #  create an instance of the even launcher dialog and run it
        eventLauncher = EventLauncher.EventLauncher(self)
        eventLauncher.exec()


    def processHaul(self):
        """
          processHaul is the entry point for all biological processing.

          CLAMS assumes that stations with the haul module enabled will coordinate catch
          processing and so these stations will be presented with the event selection
          dialog when they press the process haul button. The event selected is then set as
          the active event. Other stations will not see the event selection dialog. When
          CLAMSprocess is started on these stations, the active event will be queried from
          the db and used.

          IMPORTANT NOTE: CLAMS only queries the active event when the process button is
          pressed. If the haul station starts processing a new event while other stations are
          finishing up the previous event, THE OTHER STATIONS MUST CLOSE THE PROCESS MODULE
          WHEN THEY ARE FINISHED WITH THE PREVIOUS EVENT. If they don't, they will not pick
          up the new active event ID and data from the new event will be entered into the
          previous one.
        """

        #  build a list of the CLAMS modules allowed to run on this workstation
        module_string = self.settings['Modules'].lower()
        module_bits = module_string.split(',')
        self.modules = []
        for module in module_bits:
            self.modules.append(module.strip())

        #  check is this station is a event entry station
        if not 'haul' in self.modules:
            #  not a event entry station, get active event from the
            #  application_configuration table
            sql = ("SELECT parameter_value FROM " + self.schema +
                    ".application_configuration WHERE parameter='ActiveEvent'")
            query = self.db.dbQuery(sql)
            self.activeEvent, = query.first()
            if self.activeEvent == '0':
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                        "There is currently no active event. Please select an event to" +
                        " process from an event processing station.", 'info')
                self.message.exec()
                return

        else:
            # This is a event processing station - first check if we allow the event to
            # be changed when any other stations are open.
            if 'AllowEventChangeWhileProcessing' not in self.settings:
                #  one or more CLAMS workstations are open - do not update active ship/survey
                QMessageBox.warning(self, "Warning", "<font size = 12>The 'AllowEventChangeWhileProcessing' " +
                        "parameter is missing from the Application_Configuration table. The default value " +
                        "of 'False' will be assumed.")
                self.settings['AllowEventChangeWhileProcessing'] = 'False'

            if self.settings['AllowEventChangeWhileProcessing'].lower() == 'false':
                #  we do not allow a change when other stations are open so check if any are
                stationOpen = False
                sql = "SELECT status FROM " + self.schema + ".workstations"
                query = self.db.dbQuery(sql)
                for status, in query:
                    if status.lower() == 'open':
                        stationOpen = True
                        break
                if stationOpen:
                    #  one or more CLAMS workstations are open - do not update active ship/survey
                    QMessageBox.critical(self, "ERROR", "<font size = 12>One or more CLAMS workstations "+
                            "are open. The active event cannot be changed when workstations are open. " +
                            "Please close them.")
                    return

            #  get the active event from the database
            sql = ("SELECT parameter_value FROM " + self.schema +
                    ".application_configuration WHERE parameter='ActiveEvent'")
            query = self.db.dbQuery(sql)
            event, = query.first()

            #  get the time the active event came on deck
            sql = ("SELECT parameter_value FROM " + self.schema +
                    ".event_data WHERE event_parameter='Haulback' AND event_id="+
                    event + "AND ship="+self.ship+" AND survey="+self.survey)
            query = self.db.dbQuery(sql)
            eventTime, = query.first()
            if eventTime is None:
                eventTime = ''

            #  present the event selection dialog
            dlg = processdlg.ProcessDlg(event, eventTime, parent=self)
            if dlg.exec():
                event = dlg.activeEvent

                #  check if this event has catch to process

                #  get the gear for the active event
                sql = ("SELECT gear FROM " + self.schema + ".events WHERE ship="+self.ship+
                        " AND survey="+self.survey + " AND event_id=" + event)
                query = self.db.dbQuery(sql)
                gear, = query.first()

                #  determine gear type
                sql = "SELECT gear_type FROM gear WHERE gear='" + gear + "'"
                query = self.db.dbQuery(sql)
                gearType, = query.first()

                #  and finally check if this gear retains catch
                sql = ("SELECT retains_catch FROM " + self.schema +
                        ".gear_types WHERE gear_type='" + gearType + "'")
                query = self.db.dbQuery(sql)
                retainsCatch, = query.first()

                if not retainsCatch:
                    #  this gear does not have a catch to process, why are we here?
                    QMessageBox.information(self, "Kipaumbele!", "<font size=14>The gear deployed for the " +
                            "event you have selected does not retain catch. Therefore we have nothing to " +
                            "do here. Did you select the correct event?")
                    return

                #  event can have catch - proceed
                self.activeEvent = event

                #  update the active event in the database
                sql = ("UPDATE application_configuration SET parameter_value=" + self.activeEvent +
                        " WHERE parameter='ActiveEvent'")
                self.db.dbExec(sql)
            else:
                return

        #  create the CLAMSProcess window and display it
        procWindow = CLAMSprocess.CLAMSProcess(self)
        procWindow.exec()


    def utilities(self):
        '''
            Display the utilities dialog.
        '''
        #dialog = utilitiesdlg.UtilitiesDlg(self)
        #dialog.exec()
        pass


    def administration(self):
        '''
            Display the administration dialog.
        '''
        dialog = admindlg.AdminDlg(self.db, self)
        dialog.exec()
        self.setActiveSurvey()


    def closeEvent(self, event=None):
        """
        Clean up when the CLAMS main window is closed.
        """
        #  close our connection to the database
        if self.db:
            self.db.dbClose()

        #  store the application size and position
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())


    def checkPath(self, thisPath, default):
        """
        checkPath cleans up a path and ensures that it has a trailing separator
        and then checks that it exists.
        """

        #  set the default path
        defaultPath =  '.' + os.sep + default + os.sep

        if thisPath is not None:
            #  path provided - normalize the path
            thisPath = os.path.normpath(str(thisPath))

            #  make sure there is a trailing slash
            if (thisPath[-1] != '/') or (thisPath[-1] != '\\'):
                thisPath = thisPath + os.sep
        else:
            thisPath = defaultPath

        #  check for the existence of one of our paths
        if not QDir().exists(thisPath):
            if not QDir().exists(defaultPath):
                return (thisPath, False)
            else:
                return (defaultPath, True)
        else:
            return (thisPath, True)



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


if __name__ == "__main__":

    #  see if the ini file path was passed in
    if (len(sys.argv) > 1):
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
    homeScreenImg = initSettings.value('HomeScreenImg', '')

    #  extract the application paths and settings
    settings = {}
    settings['LoggingDir'] = initSettings.value('LoggingDir', './sql_logs')
    settings['ImageDir'] = initSettings.value('ImageDir', './images')
    settings['SoundsDir'] = initSettings.value('SoundsDir', './sounds')
    settings['IconDir'] = initSettings.value('IconDir', './icons')
    settings['Database'] = initSettings.value('Database', 'Oracle')
    settings['GUI-ScrollBar-Width'] = initSettings.value('GUI-ScrollBar-Width', 40)

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  create an instance of the CLAMS main form
    form = CLAMSMain(dataSource, user, password, settings)

    #  show it
    form.show()

    #  and start the application...
    app.exec()
