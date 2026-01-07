#!/usr/bin/env python
"""
CLAMSCatchSummaryLoader is a simple application that queries the underlying CLAMS
data tables, creates summary information, and then populates the catch summary table.

This is normally handled by the CLAMS application but if any of the data tables are
edited outside of CLAMS, the catch_summary table will not be updated to reflect those
edits. This program can be used to force the updating of the catch_summary table.

It generally cannot hurt to run this program and doing so will ensure that the
catch_summary table is up to date.
"""

#  import dependent modules
import sys
import os
import functools
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import connectdlg
import dbConnection
import Clamsbase2Functions
from ui import ui_CatchSummaryLoader


class CLAMSCatchSummaryLoader(QMainWindow, ui_CatchSummaryLoader.Ui_MainWindow):

    def __init__(self, dataSource, user, password, settings, parent=None):
        super(CLAMSCatchSummaryLoader, self).__init__(parent)
        self.setupUi(self)

        #  Initialize variables and define constants
        self.initializing = True
        self.db = None
        self.schema = user
        self.dbName = dataSource
        self.dbUser = user
        self.dbPassword = password
        self.settings = settings

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'CLAMSCatchSummaryLoader')
        size = self.appSettings.value('winsize', QSize(420,190))
        position = self.appSettings.value('winposition', QPoint(10,10))
        self.lastship = self.appSettings.value('lastship', '')
        self.lastsurvey  = self.appSettings.value('lastsurvey', '')

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  add the COM port settings display in the status bar
        self.schemaLabel = QLabel('')
        self.statusbar.addPermanentWidget(self.schemaLabel)
        self.schemaLabel.setText('User: Not Connected')

        #  connect this GUI's button signals
        self.pbUpdateSurvey.clicked.connect(self.updateSurvey)
        self.pbUpdateEvent.clicked.connect(self.updateEvent)
        self.cbShip.currentTextChanged.connect(self.refreshSurveys)
        self.cbSurvey.currentTextChanged.connect(self.refreshEvents)

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
        self.db.bioSchema = self.schema

        try:
            self.db.dbOpen()
        except Exception as err:
            QMessageBox.critical(self,"ERROR", "Unable to connect to the database. " + err.error)
            self.close()
            return

        #  update the schema name on the GUI
        self.schemaLabel.setText('User: ' + self.schema)

        #  set the initializing flag
        self.initializing = True

        #  clear the combobox
        self.cbShip.clear()

        #  populate the ship combo box
        sql = "SELECT ship FROM " + self.schema + ".ships"
        query = self.db.dbQuery(sql)
        for ship, in query:
            self.cbShip.addItem(ship)

        #  unset the initializing flag
        self.initializing = False

        #  unset the selection in our combobox to ensure that the next line fires an event
        self.cbShip.setCurrentIndex(-1)

        #  set to the last selected ship - otherwise to -1
        self.cbShip.setCurrentIndex(self.cbShip.findText(self.lastship,
                Qt.MatchFlag.MatchExactly))


    def refreshSurveys(self, ship):

        #  make sure we don't execute when adding the first item to the combobox
        #  or when the combobox index is set to -1
        if (ship == '' or self.initializing):
            return

        #  set the initializing flag
        self.initializing = True

        # store the ship
        self.ship = ship
        self.appSettings.setValue('lastship', ship)

        #  clear the combobox
        self.cbSurvey.clear()

        #  populate the surveys combo box
        sql = ("SELECT survey FROM " + self.schema + ".surveys WHERE ship=" + ship +
                " AND ship <> 999 AND survey < 205000 AND survey > 190000 ORDER BY survey DESC")
        query = self.db.dbQuery(sql)
        for survey, in query:
            self.cbSurvey.addItem(survey)

        #  unset the initializing flag
        self.initializing = False

        #  unset the selection in our combobox to ensure that the next line fires an event
        self.cbSurvey.setCurrentIndex(-1)

        #  set to the last selected survey - otherwise to -1
        self.cbSurvey.setCurrentIndex(self.cbSurvey.findText(self.lastsurvey,
                Qt.MatchFlag.MatchExactly))

        #  enable the GUI elements
        self.cbSurvey.setEnabled(True)
        self.pbUpdateSurvey.setEnabled(True)


    def refreshEvents(self, survey):

        #  make sure we don't execute when adding the first item to the combobox
        #  or when the combobox index is set to -1
        if (survey == '' or self.initializing):
            return

        # store the survey
        self.survey = survey
        self.appSettings.setValue('lastsurvey', survey)

        #  clear the combobox
        self.cbEvent.clear()

        #  populate the events combo box
        sql = ("SELECT event_id FROM " + self.schema + ".events WHERE ship=" + self.ship + " AND " +
                "survey=" + self.survey + " ORDER BY event_id DESC")
        query = self.db.dbQuery(sql)
        for event, in query:
            self.cbEvent.addItem(event)

        #  enable the GUI elements
        self.cbEvent.setEnabled(True)
        self.pbUpdateEvent.setEnabled(True)


    def updateSurvey(self):
        '''
        updateSurvey updates catch summary and histogram data for all events in
        the currently selected survey
        '''
        success = True
        events = [self.cbEvent.itemText(i) for i in range(self.cbEvent.count())]
        for event_id in events:
            #  update catch summary and histogram table for this event
            ok = self.updateCatchSummaryTable(self.ship, self.survey, event_id)
            if (not ok):
                success = False

        if (success):
            QMessageBox.information(self, 'Success', "Catch summary data updated for all events in survey " +
                    self.survey)
        else:
            QMessageBox.warning(self, 'Uh oh.', "Error updating catch summary data for one or more " +
                    "events in survey " + self.survey)


    def updateEvent(self):
        '''
        updateEvent updates catch summary and histogram data for the currently selected event
        '''

        event_id = self.cbEvent.currentText()
        if (event_id == ''):
            return

        #  update catch summary and histogram table for this event
        ok = self.updateCatchSummaryTable(self.ship, self.survey, event_id)

        if (ok):
            QMessageBox.information(self, 'Success', "Catch summary data updated for event " + event_id)
        else:
            QMessageBox.warning(self, 'Huh.', "Error updating catch summary data for event " + event_id)



    def updateCatchSummaryTable(self, ship, survey, event_id):
        '''
        updateCatchSummaryTable updates the catch summary data for the specified
        ship, survey, and event
        '''

        #  set the initial return state
        ok = True

        #  create an instance of clamsbase functions
        clamsFunctions = Clamsbase2Functions.Clamsbase2Functions(self.db, ship, survey)

        self.statusBar().showMessage("Updating Catch Summary for Event " + event_id);

        #  delete existing data for this event
        sql = ("DELETE FROM " + self.schema + ".catch_summary WHERE ship=" + ship + " AND survey=" + survey +
                " AND event_id=" + event_id)
        self.db.dbExec(sql)

        #  find all the unique species samples
        sql = ("SELECT sample_id, parent_sample, partition, species_code, subcategory FROM " + self.schema + ".samples " +
                "WHERE ship=" + ship + " AND survey=" + survey + " AND event_id=" + event_id +
                " AND sample_type='Species'")
        sampleQuery = self.db.dbQuery(sql)
        for sample_id, parent_sample, partition, species_code, subcategory in sampleQuery:
            #[sample id, species code, subcategory, sample id, WeightInHaul,SampledWeight,NumberInHaul,SampledNumer,FrequencyExpansion,InMix,WholeHauled]
            [status, vals]=clamsFunctions.computeCatchSummary(event_id, partition, species_code, subcategory)


            #  check if we successfully computed the summary data
            if status:
                vals = vals[0]
                #  yes - get species name
                sql = ("SELECT scientific_name, common_name FROM " + self.schema + ".species WHERE species_code=" + species_code)
                sppQuery = self.db.dbQuery(sql)
                sci_name, common_name = sppQuery.first()

                #  then insert results into catch summary table
                sql = ("INSERT INTO " + self.schema + ".catch_summary (ship,survey,event_id,partition,sample_id,parent_sample," +
                        "scientific_name,species_code,common_name,subcategory,weight_in_haul,sampled_weight," +
                        "number_in_haul,sampled_number,frequency_expansion,in_mix,whole_hauled) VALUES(" +
                        ship + "," + survey + "," + event_id + ",'" + partition + "'," + sample_id + "," +
                        parent_sample + ",'" + sci_name + "'," + species_code + ",'" + common_name +
                        "','" + subcategory + "'," + str(vals[4]) + "," + str(vals[5]) + "," +
                        str(vals[6]) + ","+str(vals[7]) + "," + str(vals[8]) + "," + str(vals[9]) +
                        "," + str(vals[10]) + ")")
                self.db.dbExec(sql)
            else:
                #  check to make sure there is an actionable error - computeCatchSummary can return false if there
                #  is a sample with no measurements which we silently ignore here as it isn't necessarily an error
                if (len(vals) > 0):
                    QMessageBox.warning(self, 'Attention!', "Error computing catch summary data for event " +
                            event_id + ". Error text:" + vals[2]  + vals[1])
                    ok = False
                    break


        #  clear the statusbar
        self.statusBar().clearMessage()

        #  ugly hack to force the UI to update
        QApplication.processEvents();

        return ok


    def closeEvent(self, event=None):

        if self.db:
            self.db.dbClose()
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())



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

    #  extract the application paths and settings
    settings = {}
    settings['Database'] = initSettings.value('Database', 'Oracle')

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  create an instance of the CLAMS main form
    form = CLAMSCatchSummaryLoader(dataSource, user, password, settings)

    #  show it
    form.show()

    #  and start the application...
    app.exec()


