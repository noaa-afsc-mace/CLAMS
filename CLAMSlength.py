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
.. module:: CLAMSlength

    :synopsis: CLAMSlength presents the CLAMS length form. The length form
               is used to collect length measurements for a selected species
               and sex in a given haul and partition.
               Species will appear in the length form once they have been
               entered from the catch form for the associated haul and partition.
               Length measurements can be auto recorded with a serial connection
               or manually entered with a keypad.  The type of length needs to be specified
               but the default length type for each species will be used first, if available in
               the database.
               Recorded length data for each selected species are presented in the table
               display and a length-frequency plot.
               The length form is launched from the haul form.

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
import os
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6 import QtSql
from PyQt6.QtMultimedia import QSoundEffect
from ui import ui_CLAMSLength
import numpad
import keypad
import messagedlg
import histogramplot
import addspecdlg

class CLAMSLength(QDialog, ui_CLAMSLength.Ui_clamsLength):
    '''CLAMSlength presents the CLAMS length form. The length form is used
    to collect and store lengths in the database for selected species and sex.
    The species available for the haul that have been added from using the catch
    form are displayed.  Once the sex and the length type are select, measurements
    can be either manual or automatic from a serial device.  Measurements are loaded
    to the database and a table and plot view of the length data are shown.
    '''

    def __init__(self, parent=None):
        ''' The CLAMS Length dialog initialization method.  Gets basic information
            and sets up the length form.
        '''

        #  call superclass init methods, GUI form setup method, and set to delete object on close
        super(CLAMSLength, self).__init__(parent)
        self.setupUi(self)

        #  copy some info from parent for convenience
        self.db = parent.db
        self.schema = parent.schema
        self.sensorMonitor = parent.sensorMonitor
        if not self.db.db.isOpen():
            self.db.dbOpen()
        self.workStation = parent.workStation
        self.survey = parent.survey
        self.ship = parent.ship
        self.activeHaul = parent.activeHaul
        self.activePartition = parent.activePartition
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.blue = parent.blue
        self.black = parent.black
        self.scientist = parent.scientist
        self.deviceData = parent.deviceData

        # setup reoccuring dlgs
        self.numDialog = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)
        self.addspec = addspecdlg.addspecedlg(self)

        #  set the event number
        haul_txt = str(self.activeHaul) + " - " + self.activePartition
        self.haulNum.setText(haul_txt)

        # figure out if this is administrative station
        actions = str(self.settings['MainActions'] )
        actions = actions.split(',')
        if 'Administration' in actions:
            self.admin = True
        else:
            self.admin = False

        # initialize variables
        self.activeSpcName = None
        self.comment = ''
        self.value = ''
        self.tempval = ''
        self.valFlag = 1
        self.sex = None
        self.editFlag = False
        self.plotFreshCount = 0
        self.malesPlot = []
        self.femalesPlot = []
        self.unsexPlot = []
        self.selRecord = [None, None, None]
        self.freeze = False
        self.specimenKey = None
        self.sciLabel.setText(self.scientist)
        p = self.scientist.split(' ')
        self.firstName = p[0]

        # set up some table bits
        self.sumTable.horizontalHeader().setVisible(False)
        self.sumTable.setColumnCount(1)

        # set default sampling Method
        sql = "SELECT sampling_method FROM " + self.schema + ".sampling_methods"
        query = self.db.dbQuery(sql)
        for sampling_method,  in query:
            self.samplingMethodBox.addItem(sampling_method)
        self.samplingMethodBox.setCurrentIndex(self.samplingMethodBox.findText('random'))

        # populate species window
        self.updateSpecies()

        # set up tables for data display
        font = QFont('Arial Black', 14, -1, False)
        self.measureView.setFont(font)
        self.measureView.horizontalHeader().setStyleSheet("QHeaderView::section { font-size: 8pt; font-family: 'Arial Black'; }")
        self.measureView.verticalHeader().setStyleSheet("QHeaderView::section { font-size: 8pt; font-family: 'Arial Black'; }")
        self.measureModel = QtSql.QSqlQueryModel() #TODO: change this to a QTableView using QtDesigner, following ~ line of ClamsCatch
        self.measureView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.measureView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.measureView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.measureView.setModel(self.measureModel)
        self.selModel = QItemSelectionModel(self.measureModel, self.measureView)
        self.measureView.setSelectionModel(self.selModel)
        self.measureView.show()

        # set up length frequency plot
        self.lfPlotScene = histogramplot.HistogramPlot(self)
        self.lfPlot.setScene(self.lfPlotScene)
        self.lfPlot.scale(4, 4)
        self.lfPlot.show()

        # set up window position
        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'LengthForm')
        size = self.appSettings.value('winsize', QSize(1000,725))
        position = self.appSettings.value('winposition', QPoint(10,10))

       #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        # connect signals and slots
        self.deleteBtn.clicked.connect(self.goDelete)
        self.doneBtn.clicked.connect(self.close)
        self.speciesList.itemSelectionChanged.connect(self.getSpecies)
        self.maleBtn.clicked.connect(self.getSex)
        self.femaleBtn.clicked.connect(self.getSex)
        self.unsexBtn.clicked.connect(self.getSex)
        self.commentBtn.clicked.connect(self.getComment)
        self.lengthTypeBox.activated[int].connect(self.lengthTypeChanged)
        self.selModel.selectionChanged.connect(self.getMeasureRow)
        # manual length
        self.manualBtn.clicked.connect(self.getManual)
        # auto lengths from serial device
        self.sensorMonitor.SensorDataReceived.connect(self.getAuto)

        # get the sound for the board
        board_sql = ("SELECT device_id FROM " + self.schema + ".measurement_setup WHERE workstation_id = " + self.workStation +
                     " AND gui_module = 'Length'")
        board_query = self.db.dbQuery(board_sql)
        device_id, = board_query.first()
        if device_id:
            sql = ("SELECT parameter_value FROM " + self.schema + ".device_configuration WHERE device_id = " + device_id
                   + " AND device_parameter = 'SoundFile'")
        query1 = self.db.dbQuery(sql)
        sound_file, = query1.first()
        soundEffect = QSoundEffect()

        if sound_file:
            hasExt = sound_file.split('.')
            if len(hasExt) > 1:
                soundFile = (self.settings['SoundsDir'] + sound_file)
            else:
                soundFile = (self.settings['SoundsDir'] + sound_file + '.wav')

        else:
            soundFile = (self.settings['SoundsDir'] + 'softwareSound.wav')
        soundEffect.setSource(QUrl.fromLocalFile(soundFile))
        self.sound = soundEffect

#        # connect to serial devices
#        self.openSerial()

    def updateSpecies(self):
        '''updateSpecies is called when the Length form is initialized.
        It queries the species that have been entered into the catch form
        for the current haul and partition and adds them to the species list
        '''

        # populate species window with species that have been measured in by the catch form
        # first gather all the species information for the current haul and partition
        sql = ("SELECT species.common_name, species.scientific_name, samples.species_code, samples.sample_id, samples.subcategory"+
                    " FROM " + self.schema + ".species, " + self.schema + ".samples, " + self.schema + ".baskets"+
                " WHERE species.species_code = samples.species_code AND samples.ship=baskets.ship"+
                " AND samples.survey=baskets.survey AND samples.event_id=baskets.event_id"+
                " AND samples.sample_id=baskets.sample_id AND samples.ship="+self.ship+" AND samples.survey="+
                self.survey+" AND samples.event_id="+self.activeHaul+" AND samples.partition='"+self.activePartition+
                "' AND baskets.basket_type='Measure' AND samples.sample_type='Species'"+
                " GROUP BY species.common_name, samples.species_code, species.scientific_name, samples.sample_id, samples.subcategory")
        query = self.db.dbQuery(sql)
        self.sampleKeys = []
        self.speciesCodes = []
        self.subCats = []

        for common_name, scientific_name, species_code, sample_id,  subcategory in query:

            # check to see if the sample has a specified scientific or common name
            sql0 = ("SELECT PARAMETER_VALUE FROM " + self.schema + ".sample_data WHERE sample_parameter='sample_display_name' AND ship="+
                    self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+ " AND sample_id="+sample_id)
            query0 = self.db.dbQuery(sql0)

            # if there is a name category specified in the sample_data table,
            # use that for the assignment
            sample_name,  = query0.first()
            if sample_name:
                if sample_name.lower() == 'scientific':
                    species = scientific_name
                else:
                    species = common_name
            else:
                species = common_name

            # append the name of the subcategory to the name
            subcat=subcategory
            if subcat != 'None':
                name = species+'-'+subcat
            else:
                name = species

            # populate the lists with species information
            self.speciesList.addItem(name)
            self.speciesCodes.append(species_code)
            self.subCats.append(subcat)
            self.sampleKeys.append(sample_id)


    def getSpecies(self):
        '''getSpecies is called when a species is selected from the species list.
        Species data, including the max, min, primary and secondary lengths,
        are queried and saved.
        The primary length type for the species is set as the default
        measurement type.
        Additionally, the species picture is set & and the sex boxes are reset.
        '''

        # set active species and inform the user
        self.activeSpcName = self.speciesList.currentItem().text()
        self.freeze = True
        self.addspec.setMessage(self.errorIcons[1], self.errorSounds[2],
                "Changing the Active Species to: \n \n"+ self.activeSpcName ,'info')
        self.addspec.exec()
        self.freeze = False

        #  reset the GUI
        self.lengthTypeBox.clear()
        self.sumTable.setEnabled(True)
        self.groupSexBox.setEnabled(True)
        self.otherBox.setEnabled(True)

        # get species code and sample key
        self.activeSpcCode=self.speciesCodes[self.speciesList.currentRow()]
        self.activeSpcSubcat=self.subCats[self.speciesList.currentRow()]
        self.sampleKey=self.sampleKeys[self.speciesList.currentRow()]

        # get species_data parameters
        params = ['min_length', 'max_length', 'primary_length_type', 'secondary_length_type']
        nParms = len(params)
        vals = [None] * nParms
        for i in range(nParms):
            sql = ("SELECT parameter_value FROM " + self.schema + ".species_data WHERE species_code=" +
                    self.activeSpcCode+" AND subcategory='" + self.activeSpcSubcat +
                    "' AND lower(species_parameter)='" + params[i] + "'")
            query = self.db.dbQuery(sql)
            value,  = query.first()
            if value:
                vals[i] = value

        #  set the min and max lengths
        if vals[0] != None:
            self.minLength = float(vals[0])
        else:
            self.minLength = 0.
        if vals[1] != None:
            self.maxLength = float(vals[1])
        else:
            self.maxLength = 999.

        #  set primary length type and initialize the lengthTypes measurement_types
        #  query constraint string
        if vals[2] != None:
            self.lengthTypeBox.addItem(vals[2])
            self.lenthTypes = "'" + vals[2] + "'"
        else:
            #  by default we add fork_length if no primary is specified
            self.lengthTypeBox.addItem('fork_length')
            self.lenthTypes = "'fork_length'"

        #  set the length_type combo box to primary
        self.lengthTypeBox.setCurrentIndex(0)

        #  add alternative (secondary) length type
        if vals[3] != None:
            self.lengthTypeBox.addItem(vals[3])
            self.lenthTypes = self.lenthTypes + ",'" + vals[3] + "'"

        # set up picture
        if self.activeSpcSubcat.lower() != 'none':
            imgName = self.activeSpcCode+"_"+self.activeSpcSubcat
        else:
            imgName = self.activeSpcCode

        #  currently, all fish images must be .jpg.
        imgName = imgName + ".jpg"

        #  load the fish pic, if available
        self.picLabel.clear()
        pic = QImage()
        if pic.load(self.settings['ImageDir'] + 'fishPics' + os.sep + imgName):
            pic = pic.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio)
            self.picLabel.setPixmap(QPixmap.fromImage(pic))
            self.picLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.picLabel.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        else:
            #  no pic available
            self.picLabel.clear()
            self.picLabel.setText("<Image Unavailable>")

        # check for existing records going through length type changed
        self.lengthTypeChanged()

        # reset sex buttons
        if self.maleBtn.isChecked():
            self.maleBtn.setChecked(False)
            self.maleBtn.setPalette(self.black)
        if self.femaleBtn.isChecked():
            self.femaleBtn.setChecked(False)
            self.femaleBtn.setPalette(self.black)
        if self.unsexBtn.isChecked():
            self.unsexBtn.setChecked(False)
            self.unsexBtn.setPalette(self.black)
        self.sex=None


    def getManual(self):
        '''getManual is triggered when the manual length button is pressed
        This allows a user to enter a length using manual number pad.
        '''


        self.overrideFlag = False

        # make sure there is an active species and sex selected.  If there is not,
        # we will have problems inserting into the database later, so inform the user
        if self.activeSpcName == None:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                    "Please select a species!", 'info')
            self.message.exec()
            return
        if self.sex == None:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                    "Please select a sex!",'info')
            self.message.exec()
            return

        while self.valFlag:
            self.numDialog.msgLabel.setText("Enter Length in cm")
            self.numDialog.exec()
            val = self.numDialog.value

            # can this be converted to a float?  If not, it is no good, so pass and wait for the next
            try:
                float(val)
                self.value = val
            except:
                return

            #  set the active device ID to 0 to indicate software
            self.activeDeviceId = '0'

            # now check to see if it is within the acceptable range.  If not show a warning and ask if user wants to reenter.
            if float(self.value) > self.minLength and float(self.value) < self.maxLength:# measurement within specs
                # call writeTable to insert this measurement into the database
                self.writeTable()
                self.valFlag = False
                self.sound.play()
            else:
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1], self.firstName +
                        ", The length is out of range for this. Do you want to reenter length?", 'choice')
                if self.message.exec():
                    self.valFlag = True
                else:
                    self.message.setMessage(self.errorIcons[2],self.errorSounds[2], "You're in big trouble, "
                            +self.firstName, 'info')
                    self.message.exec()
                    self.overrideFlag = False
                    # insert the data anyway, even though the length fell outside the acceptable range
                    self.writeTable()
                    self.valFlag = False
        self.valFlag = True



# TODO: NEED TO MAP MEASUREMENT TYPE TO DEVICE, THEN CHECK IF THE MEASUREMENT TYPE IS PROVIDED BY
#       THE DEVICE NAMED IN getAuto. IF SO, RECORD THE VALUE. IF NOT, IGNORE.

    @pyqtSlot(str, str, object)
    def getAuto(self, device_name, val, err):
        '''getAuto is called when the connected serial device sends a signal with the device and the value.
        Check to make sure the value can be converted to a float, do some check on species, sex,
        and the acceptable length range.  If these pass, call writeTable to insert the measurement into the database.
        '''

        print(device_name, val)

        #  check if we're working on a previous length, if so  do not interrupt with new measurement
        if self.freeze:
            return

        #  check if this is a device we're interested in, if not, ignore this data.
        #  first check if there are any length measurements
        if 'length' not in self.deviceData[device_name]['measurements']:
            return

        #  make sure this is a number
        try:
            val = float(val)
        except:
            return

        # make sure there is an active species and sex selected.
        if self.activeSpcName == None:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                    "Please select a species!", 'info')
            self.message.exec()
            return
        if self.sex == None:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                    "Please select a sex!",'info')
            self.message.exec()
            return

        self.overrideFlag = False

        # set the value to be written as the input value
        self.value = val

        self.activeDeviceId = self.deviceData[device_name]['id']

        #  play the sound associated with this device if provided
        self.sound.play()

        # now check to see if it is within the acceptable range.  If not show a
        # warning and ask if user wants to reenter.
        if self.value < self.minLength or self.value > self.maxLength:
            #  value is out of range
            self.freeze = True
            self.message.setMessage(self.errorIcons[1],self.errorSounds[1], self.firstName +
                    ", The length is out of range for this. Do you want to reenter length?", 'choice')
            if self.message.exec():
                return
            else:
                self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                        "You're in big trouble, "+self.firstName, 'info')
                self.message.exec()

                # insert the data anyway, even though the length fell outside the acceptable range
                self.overrideFlag = True

        #  write the data into the database
        self.writeTable()
        self.freeze = False


    def getSex(self):
        '''getSex is called when the female, male or unsexed box are clicked.
        Gets the button that was pressed, color codes the buttons appropriately
        and sets the current sex to the one that was pressed.
        '''

        button = self.sender().text()
        if button == 'Male':
            self.maleBtn.setPalette(self.blue)
            self.femaleBtn.setChecked(False)
            self.femaleBtn.setPalette(self.black)
            self.unsexBtn.setChecked(False)
            self.unsexBtn.setPalette(self.black)
            self.sex = 'Male'
        elif button == 'Female':
            self.femaleBtn.setPalette(self.blue)
            self.maleBtn.setChecked(False)
            self.maleBtn.setPalette(self.black)
            self.unsexBtn.setChecked(False)
            self.unsexBtn.setPalette(self.black)
            self.sex='Female'
        elif button == 'Unsexed':
            self.unsexBtn.setPalette(self.blue)
            self.maleBtn.setChecked(False)
            self.maleBtn.setPalette(self.black)
            self.femaleBtn.setChecked(False)
            self.femaleBtn.setPalette(self.black)
            self.sex ='Unsexed'
        if not self.maleBtn.isChecked and not self.femaleBtn.isChecked and not self.unsexBtn.isChecked:
            self.sex=None


    def lengthTypeChanged(self):
        '''lengthTypeChanged is triggered when the length type box is activated
        or when the species is changed.
        Collects the current length type and reloads the length table and plot.
        '''
        # check for existing records
        self.len_type = self.lengthTypeBox.currentText()
        QMessageBox.information(self, "Length Measurement Type", "<font size = 9>You should now measure " +self.len_type)
        self.reloadTable()
        self.reloadLFPlot()

    def reloadTable(self):
        '''reloadTable is called from writeTable method once new data have been entered into the database
        or when the length type is changed or when an entry has been deleted.
        Re-query the data from the database to display what has been saved.
        '''

        # added/cleaned by Alicia Billings 4/2/26
        where_clauses = [
            f"m.measurement_type IN ('{self.len_type}')",
            f"m.ship = {self.ship}",
            f"m.survey = {self.survey}",
            f"m.event_id = {self.activeHaul}",
            f"m.sample_id = {self.sampleKey}",
            "s.protocol_name = 'Length_Sex'"
        ]
        if not self.admin:
            where_clauses.append(f"s.workstation_id = {self.workStation}")
        final_where_str = " AND ".join(where_clauses)

        sql = f"""
                    SELECT
                        a.length,
                        b.sex
                    FROM (
                        SELECT m.ship, m.survey, m.event_id, m.specimen_id, m.measurement_value AS length
                        FROM {self.schema}.measurements m
                        JOIN {self.schema}.specimen s ON
                            m.ship = s.ship
                            AND m.survey = s.survey
                            AND m.event_id = s.event_id 
                            AND m.specimen_id = s.specimen_id
                        WHERE {final_where_str}
                    ) a
                    LEFT OUTER JOIN (
                        SELECT ship, survey, event_id, specimen_id, measurement_value AS sex
                        FROM {self.schema}.measurements
                        WHERE measurement_type = 'sex'
                    ) b ON
                        b.ship = a.ship
                        AND b.survey = a.survey
                        AND b.event_id = a.event_id
                        AND b.specimen_id = a.specimen_id
                    ORDER BY a.specimen_id ASC
                """
        """
        if self.admin:
            sql = ("SELECT a.specimen_id, a.length, b.sex "+
                    " FROM "+
                    " (SELECT measurements.ship, "+
                     "  measurements.survey, "+
                      " measurements.event_id, "+
                      " measurements.specimen_id, "+
                      " measurements.measurement_value as length "+
                    " FROM  " + self.schema + ".measurements JOIN specimen ON "+
                      "  (measurements.ship = specimen.ship "+
                      " AND measurements.survey = specimen.survey "+
                      " AND measurements.event_id = specimen.event_id "+
                      " AND measurements.specimen_id = specimen.specimen_id) "+
                    " WHERE measurement_type = '" + self.len_type + "' and  "+
                    " measurements.ship="+self.ship+" and  "+
                    " measurements.survey="+self.survey+" and  "+
                    " measurements.event_id="+self.activeHaul+" and  "+
                    " measurements.sample_id="+self.sampleKey+" and "+
                    " specimen.protocol_name ='Length_Sex') a "+
                  " LEFT OUTER JOIN "+
                    " (SELECT ship, survey, event_id, specimen_id, measurement_value as sex "+
                    " FROM " + self.schema + ".measurements "+
                    " WHERE measurement_type = 'sex') b     "+
                  " ON (b.ship = a.ship "+
                  " AND b.survey = a.survey "+
                  " AND b.event_id = a.event_id "+
                  " AND b.specimen_id = a.specimen_id) ORDER BY  a.specimen_id")
        else:
            sql = ("SELECT a.specimen_id, a.length, b.sex "+
                    " FROM "+
                    " (SELECT " + self.schema + ".measurements.ship, "+
                     "  measurements.survey, "+
                      " measurements.event_id, "+
                      " measurements.specimen_id, "+
                      " measurements.measurement_value as length "+
                    " FROM  " + self.schema + ".measurements JOIN specimen ON "+
                      "  (measurements.ship = specimen.ship "+
                      " AND measurements.survey = specimen.survey "+
                      " AND measurements.event_id = specimen.event_id "+
                      " AND measurements.specimen_id = specimen.specimen_id) "+
                    " WHERE measurement_type in '" + self.len_type + "' and  "+
                    " measurements.ship="+self.ship+" and  "+
                    " measurements.survey="+self.survey+" and  "+
                    " measurements.event_id="+self.activeHaul+" and  "+
                    " measurements.sample_id="+self.sampleKey+" and "+
                    " specimen.protocol_name ='Length_Sex' and "+
                    " specimen.workstation_id = "+self.workStation+") a "+
                  " LEFT OUTER JOIN "+
                    " (SELECT ship, survey, event_id, specimen_id, measurement_value as sex "+
                    " FROM " + self.schema + ".measurements "+
                    " WHERE measurement_type = 'sex') b     "+
                  " ON (b.ship = a.ship "+
                  " AND b.survey = a.survey "+
                  " AND b.event_id = a.event_id "+
                  " AND b.specimen_id = a.specimen_id) ORDER BY a.specimen_id")
        """
        self.measureModel.setQuery(sql, self.db.db)

        #TODO: Manually add headers and data to a QTableView instead of the QSqlModelView
        # This will be faster and consistent with the Catch module- see updateTables method in CLAMScatch

        self.updateSumTable()


    def reloadLFPlot(self):
        '''reloadLFPlot is called from writeTable method once new data have been entered into the database
        or when the length type is changed or when an entry has been deleted.
        Re-query the data from the database to display in the plot to display what has been saved.
        '''

        # clear the plot area and initialize the length array
        self.lfPlotScene.clearPlot()
        self.lmax = []
        for i in range(80):
            self.lmax.append(0.)

        # added/cleaned by Alicia Billings 4/2/26
        where_clauses = [
            f"m.measurement_type IN ('{self.len_type}')",
            f"m.ship = {self.ship}",
            f"m.survey = {self.survey}",
            f"m.event_id = {self.activeHaul}",
            f"m.sample_id = {self.sampleKey}",
            "s.protocol_name = 'Length_Sex'"
        ]
        if not self.admin:
            where_clauses.append(f"s.workstation_id = {self.workStation}")
        final_where_str = " AND ".join(where_clauses)

        sql = f"""
            SELECT
                a.length,
                b.sex
            FROM (
                SELECT m.ship, m.survey, m.event_id, m.specimen_id, m.measurement_value AS length
                FROM {self.schema}.measurements m
                JOIN {self.schema}.specimen s ON
                    m.ship = s.ship
                    AND m.survey = s.survey
                    AND m.event_id = s.event_id 
                    AND m.specimen_id = s.specimen_id
                WHERE {final_where_str}
            ) a
            LEFT OUTER JOIN (
                SELECT ship, survey, event_id, specimen_id, measurement_value AS sex
                FROM {self.schema}.measurements
                WHERE measurement_type = 'sex'
            ) b ON
                b.ship = a.ship
                AND b.survey = a.survey
                AND b.event_id = a.event_id
                AND b.specimen_id = a.specimen_id
        """
        """
        # if we are under admin (on an administrative station), select ALL lengths
        if self.admin:
            sql = ("SELECT a.length, b.sex "+
                    " FROM  "+
                    " (SELECT measurements.ship, "+
                     "  measurements.survey, "+
                      " measurements.event_id, "+
                      " measurements.specimen_id, "+
                      " measurements.measurement_value as length "+
                    " FROM " + self.schema + ". measurements JOIN specimen ON "+
                      "  (measurements.ship = specimen.ship "+
                      " AND measurements.survey = specimen.survey "+
                      " AND measurements.event_id = specimen.event_id "+
                      " AND measurements.specimen_id = specimen.specimen_id) "+
                    " WHERE measurement_type in '" + self.len_type + "' and  "+
                    " measurements.ship="+self.ship+" and  "+
                    " measurements.survey="+self.survey+" and  "+
                    " measurements.event_id="+self.activeHaul+" and  "+
                    " measurements.sample_id="+self.sampleKey+" and "+
                    " specimen.protocol_name ='Length_Sex') a "+
                  " LEFT OUTER JOIN "+
                    " (SELECT ship, survey, event_id, specimen_id, measurement_value as sex "+
                    " FROM " + self.schema + ". measurements "+
                    " WHERE measurement_type = 'sex') b "+
                  " ON (b.ship = a.ship "+
                  " AND b.survey = a.survey "+
                  " AND b.event_id = a.event_id "+
                  " AND b.specimen_id = a.specimen_id)")

        # otherwise (not at an administrative station), query just the lengths measured at the current workstation
        else:
            sql = ("SELECT a.length, b.sex "+
                    " FROM  "+
                    " (SELECT measurements.ship, "+
                     "  measurements.survey, "+
                      " measurements.event_id, "+
                      " measurements.specimen_id, "+
                      " measurements.measurement_value as length "+
                    " FROM " + self.schema + ". measurements JOIN specimen ON "+
                      "  (measurements.ship = specimen.ship "+
                      " AND measurements.survey = specimen.survey "+
                      " AND measurements.event_id = specimen.event_id "+
                      " AND measurements.specimen_id = specimen.specimen_id) "+
                    " WHERE measurement_type in '" + self.len_type + "' and  "+
                    " measurements.ship="+self.ship+" and  "+
                    " measurements.survey="+self.survey+" and  "+
                    " measurements.event_id="+self.activeHaul+" and  "+
                    " measurements.sample_id="+self.sampleKey+" and "+
                    " specimen.protocol_name ='Length_Sex' and "+
                    " specimen.workstation_id = "+self.workStation+") a "+
                  " LEFT OUTER JOIN "+
                    " (SELECT ship, survey, event_id, specimen_id, measurement_value as sex "+
                    " FROM " + self.schema + ".measurements "+
                    " WHERE measurement_type = 'sex') b "+
                  " ON (b.ship = a.ship "+
                  " AND b.survey = a.survey "+
                  " AND b.event_id = a.event_id "+
                  " AND b.specimen_id = a.specimen_id)")
        """
        query = self.db.dbQuery(sql)
        self.scale = 1.
        # make the plot with the length and sex data from the query
        for length, sex in query:
            l = int(round(float(length)))
            self.lfPlotScene.update(l, sex)
            self.lmax[l] += self.scale
            # adjust the height so everything looks balanced on the plot
            if max(self.lmax) > 20.:
                self.lfPlotScene.rescale(0.8)
                self.scale=self.scale*0.8
                for i in range(80):
                    self.lmax[i] = self.lmax[i]*.8

        self.lfPlot.repaint()


    def writeTable(self):
        '''writeTable is called when a length measurement has been made is
        by either manual or auto methods.  Length data are inserted into the database
        into the specimen and measurement tables.
        Once data have been written, the display table and plot are updated
        '''

        self.specimenKey = None

        #  check if this is a random or non-random sample
        samplingMethod = self.samplingMethodBox.currentText()

        # write specimen table
        sql_insert = ("INSERT INTO " + self.schema + ".specimen (ship,survey,event_id,sample_id,workstation_id," +
                "scientist,sampling_method,protocol_name,comments) VALUES ("+self.ship+","+self.survey+
                ","+self.activeHaul+ ","+self.sampleKey+","+self.workStation+",'"+self.scientist+"','"+
                samplingMethod+"','Length_Sex','"+self.comment+"')")
        self.db.dbExec(sql_insert)

        #  get the key for the specimen record we just created
        sql = ("SELECT max(specimen_id) FROM " + self.schema + ".specimen WHERE workstation_id = "+
                self.workStation+" AND ship="+self.ship+ " AND survey="+self.survey+
                " AND event_id="+self.activeHaul)
        query = self.db.dbQuery(sql)
        self.specimenKey, = query.first()

        # get length_type
        len_type = self.lengthTypeBox.currentText()

        #  make sure we have a specimen key
        if (not self.specimenKey == None):
            #  Insert the length type that is selected in the lengthTypeBox combo 'len_type', now skip insert of 'length' type
            sql = ("INSERT INTO " + self.schema + ".measurements (ship, survey,event_id,sample_id,specimen_id," +
                    "measurement_type,device_id,measurement_value) VALUES ("+self.ship+","+self.survey+","+
                    self.activeHaul+ ","+self.sampleKey+","+self.specimenKey+",'"+len_type+"',"+self.activeDeviceId+
                    ",'"+str(self.value)+"')")
            self.db.dbExec(sql)

            # write sex
            sql = ("INSERT INTO " + self.schema + ".measurements (ship,survey,event_id,sample_id,specimen_id," +
                    "measurement_type,device_id,measurement_value) VALUES ("+self.ship+","+self.survey+","+
                    self.activeHaul+ ","+self.sampleKey+","+self.specimenKey+",'sex',0,'"+self.sex+"')")
            self.db.dbExec(sql)

            if self.overrideFlag:
                sql = ("INSERT INTO " + self.schema + ".overrides (ship,survey,event_id,table_name,scientist,description) VALUES ('"+
                        self.ship + "," + self.survey+ "," + self.activeHaul + "," +self.specimenKey+
                        "'measurements'," +self.scientist+"','Length is outside of valid range.')")
                self.db.dbExec(sql)

            # update table
            self.reloadTable()

            # update plot
            self.lfPlotScene.update(int(round(float(self.value))), self.sex)
            self.lmax[int(round(float(self.value)))] += self.scale
            if max(self.lmax) > 20.:
                self.lfPlotScene.rescale(0.8)
                self.scale = self.scale*0.8
                for i in range(80):
                    self.lmax[i] = self.lmax[i]*.8

            self.comment = ''

    def getMeasureRow(self):
        '''getMeasureRow gets the data from the row that is selected,
        including querying any comments from the database associated with the measurement
        '''

        self.selRecord = []
        selObj = self.measureView.currentIndex()
        for i in range(3):
            index = self.measureModel.index(selObj.row(), i, QModelIndex())
            self.selRecord.append(self.measureModel.data(index, Qt.ItemDataRole.DisplayRole))
        self.specimenKey = str(round(self.selRecord[0]))

        # get any comments
        self.comment = ''
        sql = ("SELECT comments FROM " + self.schema + ".specimen WHERE specimen_id = "+self.specimenKey+" AND ship="+self.ship+
        " AND survey="+self.survey+" AND event_id="+self.activeHaul)
        query = self.db.dbQuery(sql)
        val, = query.first()

        if val:
            self.comment = val


    def goDelete(self):
        '''goDelete is called when the delete button is pressed.
        A question check is presented to user to make sure it was not a mistake
        and then the associated data are deleted from the database
        then reloadTable is called to refresh the displayed data
        '''

        if not self.selRecord[0] == None:
            # make sure this was not a mistake and the data should be deleted
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "Are you sure you want to permanently delete this record, "+self.firstName+"?", 'choice')
            if self.message.exec():
                # delete from the measurements table
                sql = ("DELETE FROM " + self.schema + ".measurements WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = "+str(self.selRecord[0])) # delete away
                self.db.dbExec(sql)

                # delete from the specimen table
                sql = ("DELETE FROM " + self.schema + ".specimen WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = "+str(self.selRecord[0])) # delete away
                self.db.dbExec(sql)
                self.comment = ''

                # reload to display fresh data
                self.reloadTable()


    def updateSumTable(self):
        '''updateSumTable is called when the tables are length tables are reloaded.
        This updates the total number of lengths measured by sex
        into the sum table.
        '''
        # if this is admin (an administrative workstation), query ALL lengths
        if self.admin:
            sql = ("SELECT count(specimen_id), sex FROM " + self.schema + ".v_specimen_measurements WHERE ship = "
                   + self.ship + " AND survey = " + self.survey + " AND event_id = " + self.activeHaul +
                   " AND sample_id = " + self.sampleKey + " AND protocol_name = 'Length_Sex' GROUP BY sex")
            query = self.db.dbQuery(sql)
        # otherwise, if not admin, query the lengths from just the current workstation
        else:
            sql=("SELECT count(specimen_id), sex FROM " + self.schema + ".v_specimen_measurements  WHERE ship = "
                 + self.ship + " AND survey = " + self.survey + " AND event_id = " + self.activeHaul +
                 " AND sample_id = " + self.sampleKey + " AND workstation_id = " + self.workStation
                 + " AND protocol_name = 'Length_Sex' GROUP BY sex")
            query = self.db.dbQuery(sql)
        counts = []
        # Initialize the table to 0
        self.sumTable.setItem(0, 0,QTableWidgetItem('0'))
        self.sumTable.setItem(1, 0,QTableWidgetItem('0'))
        self.sumTable.setItem(2, 0,QTableWidgetItem('0'))

        # Add each count by sex to the table and sum for total
        for N, sex in query:
            #  check if this is a bad entry and skip
            if sex is None:
                continue
            if sex.lower() == 'male':
                self.sumTable.setItem(0, 0,QTableWidgetItem(N))
            elif sex.lower() == 'female':
                self.sumTable.setItem(1, 0,QTableWidgetItem(N))
            elif sex.lower() == 'unsexed':
                self.sumTable.setItem(2, 0,QTableWidgetItem(N))
            counts.append(int(N))

        self.sumTable.setItem(3, 0,QTableWidgetItem(str(sum(counts))))


#    def openSerial(self):
#        '''openSerial is called when the form is initialized.  It queries
#        the device configuration and measurement setup tables to determine
#        which measurement and de vice combinations are associated with
#        the current workstation and Length module.  The sound file name
#        for each device is also queried and saved.
#        '''
#
#        # initialize the lists that will be populated with measurements, devices and sounds
#        self.measurements = []
#        self.devices = []
#        self.sounds = []
#
#        # query device_configuration and measurement_setup tables
#        sql = ("SELECT measurement_setup.measurement_type, measurement_setup.device_id, device_configuration.parameter_value FROM " +
#                                "device_configuration INNER JOIN measurement_setup ON device_configuration.device_id " +
#                                "= measurement_setup.device_id WHERE measurement_setup.workstation_id=" +
#                                self.workStation+" AND measurement_setup.gui_module='Length' AND " +
#                                "device_configuration.device_parameter = 'SoundFile'")
#        query = self.db.dbQuery(sql)
#
#        # loop through results and store them in the lists for measurements, devices and sounds
#        for type,  device_id, sound_file in query:
#            self.measurements.append(type)
#            self.devices.append(device_id)
#            if sound_file:
#                hasExt = sound_file.split('.')
#                if len(hasExt) > 1:
#                    soundFile = (self.settings['SoundsDir'] + sound_file)
#                else:
#                    soundFile = (self.settings['SoundsDir'] + sound_file + '.wav')
#                soundEffect = QSoundEffect()
#                soundEffect.setSource(QUrl.fromLocalFile(soundFile))
#                self.sounds.append(soundEffect)
#            else:
#                self.sounds.append(None)


    def getComment(self):
        '''getComment is called when the comment button is clicked
        to save any new comments associated with length measurements
        '''

        if (self.specimenKey == None):
            return

        # pull up key dialog and tack on the current comment associated with the measurement
        keyDialog = keypad.KeyPad(self.comment, self)
        keyDialog.exec()

        # is everything looks ok, make a new comment and insert into the database
        if keyDialog.okFlag:
            string = keyDialog.dispEdit.toPlainText()
            self.comment = keyDialog.dispEdit.toPlainText()
            string = string.split('\n')
            p=''
            for s in string:
                p=p+s+' '

            # insert comment into specimen
            sql = ("UPDATE " + self.schema + ".specimen SET comments='"+p+ "' WHERE  ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = "+self.specimenKey)
            self.db.dbExec(sql)


    def closeEvent(self, event):
        event.accept()

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


