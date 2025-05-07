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
.. module:: CLAMSspecimen

    :synopsis: CLAMSspecimen presents the CLAMS specimen form.
                The specimen form is used to make measurements on individual specimens.
                Once a species is weighed into a partition, the specimen module can be
                used to select the species and make specific measurements on each specimen
                based species-specific protocols.

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
from ui import ui_CLAMSSpecimen
import importlib
import listseldialog
import numpad
import keypad
import messagedlg
import collectionsdlg
import ZebraLabelPrinter


class CLAMSSpecimen(QDialog, ui_CLAMSSpecimen.Ui_clamsSpecimen):
    '''CLAMSSpecimen presents the CLAMS specimen form.  The specimen form is used
    to collect and store measurements on specimens, structured based on established protocols.
    The species that can be measured for the haul that have been added using the catch
    form are displayed.
    '''

    def __init__(self, parent=None):
        '''The CLAMS specimen dialog initialization method. Gets basic information
            and sets up the specimen form.
        '''
        # initialize the super class and GUI
        super(CLAMSSpecimen, self).__init__(parent)
        self.setupUi(self)

        # pass variables from parent window
        self.db=parent.db
        self.workStation=parent.workStation
        self.survey=parent.survey
        self.ship=parent.ship
        self.activeHaul=parent.activeHaul
        self.activePartition=parent.activePartition
        self.settings=parent.settings
        self.sensorMonitor = parent.sensorMonitor
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.scientist=parent.scientist
        self.deviceData = parent.deviceData
        self.sqlLengthIndex = None
        self.freeze=False

        if not self.db.db.isOpen():
            self.db.dbOpen()

        # set the serial I/O temporal filter interval (in ms)
        #   Identical measurements from the same device will be ignored for this
        #   period of time filtering out accidental double scans/measurements
        #   from devices.
        self.__serialIOTimerInterval = 3000

        # set the scientist labels
        self.sciLabel.setText(self.scientist)
        self.firstName = self.scientist.split(' ')[0]

        # figure out if this is administrative station
        actions = str(self.settings['MainActions'])
        actions = actions.split(',')
        if 'Administration' in actions:
            self.admin = True
        else:
            self.admin = False

        # initialize variables
        self.activeSpcName = None
        self.activeSpcCode = None
        self.comment = ''
        self.value = None
        self.manualFlag = False
        self.serialValue = None
        self.specimenKey = None
        self.editFieldFlag = False
        self.editStateFlag = False
        self.incomplete = False
        self.protocol = None
        self.buttons = [self.btn_0, self.btn_1, self.btn_2, self.btn_3, self.btn_4, self.btn_5, self.btn_6, self.btn_7, self.btn_8, self.btn_9]
        self.lastSerialValue = [None,None]
        self.devices = []
        self.sqlString = None
        self.activeCollections = []
        self.collectionMeasurementTypes = [] # also temporary for now
        self.collectionDevices = [] # also temporary for now

        # setup reoccuring dlgs
        self.numpad = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)

        #  set the event number
        self.haulNum.setText(self.activeHaul)

        # if there is a printer set up, initialize the printer and add the sound
        if 'Label_Printer' in self.deviceData:
            #  initialize the Label Printer
            self.printer = ZebraLabelPrinter.ZebraLabelPrinter(self.sensorMonitor, self.deviceData['Label_Printer']['id'])

            sound_file = self.deviceData['Label_Printer']['soundeffect']
            if sound_file:
                hasExt = sound_file.split('.')
                if len(hasExt) > 1:
                    soundFile = (self.settings['SoundsDir'] + '/' + sound_file)
                else:
                    soundFile = (self.settings['SoundsDir'] + '/' + sound_file +'.wav')
                soundEffect = QSoundEffect()
                soundEffect.setSource(QUrl.fromLocalFile(soundFile))
                self.printSound=soundEffect
            else:
                self.printSound = None
        else:
            #  no printer configured
            self.printer = None
            #self.printBtn.setEnabled(False)

        # set up window position
        self.appSettings = QSettings('CLAMS', 'SpecimenForm')
        size = self.appSettings.value('winsize', QSize(1000,725))
        position = self.appSettings.value('winposition', QPoint(10,10))

       #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        # set default sampling methods
        sql = "SELECT sampling_method FROM sampling_methods"
        query = self.db.dbQuery(sql)
        for sampling_method,  in query:
            self.samplingMethodBox.addItem(sampling_method)
        self.samplingMethodBox.setCurrentIndex(self.samplingMethodBox.findText('random'))

        # set up our QTableView
        font = QFont('helvetica', 12, -1, False)
        self.measureView.setFont(font)
        self.measureModel = QtSql.QSqlQueryModel() #TODO: change this to a QTableView using QtDesigner, following ~ line 107 of ClamsCatch
        self.measureView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.measureView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.measureView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.measureView.setModel(self.measureModel)
        self.selModel = QItemSelectionModel(self.measureModel, self.measureView)
        self.measureView.setSelectionModel(self.selModel)

        #  Connect signal and slots
        self.printBtn.clicked.connect(self.printLabel)
        self.addspcBtn.clicked.connect(self.getSpecies)
        self.cycleBtn.clicked.connect(self.getNext)
        self.deleteBtn.clicked.connect(self.goDelete)
        self.collectBtn.clicked.connect(self.getCollections)
        self.doneBtn.clicked.connect(self.close)
        self.protoBtn.clicked.connect(self.getProtocol)
        self.selModel.selectionChanged.connect(self.getEditSel)
        self.sensorMonitor.SensorDataReceived.connect(self.serialInput)
        self.commentBtn.clicked.connect(self.getComment)
        self.samplingMethodBox.activated[int].connect(self.editSamplingMethod)
        self.lengthTypeBox.activated[int].connect(self.lengthTypeChanged)

        #  Connect up slots for protocol buttons
        for btn in self.buttons:
            btn.clicked.connect(self.btnInput)

        #  initialize the timer for the serial I/O "temporal filter"
        self.__serialIOTimer = QTimer(self)
        self.__serialIOTimer.setSingleShot(True)
        self.__serialIOTimerOK = True
        self.__serialIOTimer.timeout.connect(self.__serialIOFilter)

        #  set up an init timer
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.applicationInit)
        initTimer.start(0)


    def applicationInit(self):
        '''applicationInit is called immediately after the form is presented on the screen
        and it continues form/module setup, by entering into initializing the species
        '''
        self.initializing = True
        # get the first species
        self.getSpecies()


    def __serialIOFilter(self):
        '''__serialIOFilter is an internal method that simply resets the __serialIOTimerOK
        property after a specific amount of time. When __serialIOTimerOK is false, serialInput
        will filter (ignore) values matching the last received value from a serial device.
        This helps eliminate accidental 2nd scans of bar codes, for example.
        '''
        self.__serialIOTimerOK = True


    def lengthTypeChanged(self):
        '''lengthTypeChanged is called when the length type combo box changes. It simply calls
        updateMeasureView to update the view to show the current length type.
        '''
        lengthType=self.lengthTypeBox.currentText()
        self.updateMeasureView()
        # Provide user with the length type that should be measured.
        # Use this to re-inforce the new length type policy
        QMessageBox.information(self, "Length Measurement Type", "<font size = 12>You should now measure " +lengthType)

    def getSpecies(self):
        '''getSpecies is called when initializing the module and then when the new species button is pressed.
        It queries all species info and allows the user to select the species/subcat for sampling.
        Then finds length types (sets the default), and determined the maturity tables
        and picture associated with the species.

        '''

        #  check if we've been collecting data - if so, make sure we're done with this specimen
        if self.activeSpcCode and self.specimenKey:
            #  We've taken some specimens, call getNext() to make sure we're
            #  not in the middle of a specimen
            self.getNext()
            if self.incomplete:
                #  current specimen is incomplete - exit
                return

        # get valid species from catch
        species = []
        samples = []
        subCats = []
        self.speciesDict = {}
        sql = ("SELECT species.common_name, species.scientific_name, samples.species_code, samples.sample_id, samples.subcategory FROM" +
                              " species, samples, baskets WHERE species.species_code = samples.species_code" +
                              " AND samples.ship=baskets.ship AND samples.survey=baskets.survey AND samples.event_id=baskets.event_id AND samples.sample_id=baskets.sample_id AND samples.ship=" + self.ship +
                              " AND samples.survey=" + self.survey + " AND samples.event_id=" + self.activeHaul +
                              " AND samples.partition='" + self.activePartition + "' AND baskets.basket_type=" +
                              " 'Measure' AND samples.species_code <> 0 GROUP BY species.common_name," +
                              " samples.species_code, species.scientific_name, samples.sample_id, samples.subcategory")
        query = self.db.dbQuery(sql)
        for common_name, scientific_name, species_code, sample_id, subcategory in query:

            # check to see if the sample has a specified scientific or common name
            sql0 = ("SELECT PARAMETER_VALUE FROM sample_data WHERE sample_parameter='sample_name' AND ship="+
                    self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+ " AND sample_id="+sample_id)
            query0 = self.db.dbQuery(sql0)

            # if there is a name category specified in the sample_data table,
            # use that for the assignment
            sample_name, = query0.first()
            if sample_name:
                if (query0.value(0).toString() == 'scientific'):
                    spc = scientific_name
                else:
                    spc = common_name
            else:
                spc = common_name

            # append the name of the subcategory to the name
            subcat = subcategory
            if subcat != 'None':
                name = spc+'-'+subcat
            else:
                name = spc

            # populate the lists the species information
            species.append(name)
            samples.append(sample_id)
            subCats.append(subcat)
            self.speciesDict.update({str(name):species_code})

        #  Populate the list dialog with our species and present to user
        listDialog = listseldialog.ListSelDialog(species, 'Short', self)
        listDialog.label.setText('Pick a species to sample...')
        if not listDialog.exec():
            #  user cancelled action
            return

        #  user selected a species - set some properties based on selection
        text = str(listDialog.itemList.currentItem().text())
        text1 = text.split('-')
        self.activeSpcName = text1[0]
        if len(text1) > 1:
            self.activeSpcSubcat = text1[1]
        else:
            self.activeSpcSubcat = 'None'
        self.activeSample = samples[species.index(text)]
        self.speciesLabel.setText(text)
        self.activeSpcCode = self.speciesDict[text]

        #  determine the length type
        self.lengthTypeBox.clear()
        self.lengthTypes = []
        params = ['primary_length_type',  'secondary_length_type']
        nParms = len(params)
        vals = [None] * nParms
        for i in range(nParms):
            sql = ("SELECT parameter_value FROM species_data WHERE species_code=" +
                    self.activeSpcCode+" AND subcategory='" + self.activeSpcSubcat +
                    "' AND lower(species_parameter)='" + params[i] + "'")
            query = self.db.dbQuery(sql)
            parameter_value,  = query.first()
            if parameter_value:
                vals[i] = parameter_value

        # add primary length type
        if vals[0] != None:
            self.lengthTypeBox.addItem(vals[0])
            self.lengthTypes.append(vals[0])
        else:
            #  if no primary length type is specified for this species+subcategory
            #  default to fork_length
            self.lengthTypeBox.addItem('fork_length')
            self.lengthTypes.append('fork_length')

        #  set the length type combo box to the primary measurement
        self.lengthTypeBox.setCurrentIndex(0)

        # add alternative (secondary) length type
        if vals[1] != None:
            self.lengthTypeBox.addItem(vals[1])
            self.lengthTypes.append(vals[1])

        #  determine the maturity table
        sql = ("SELECT parameter_value FROM species_data WHERE species_code="+self.activeSpcCode+
                " AND subcategory='"+self.activeSpcSubcat+"' AND lower(species_parameter)='maturity_table'")
        query = self.db.dbQuery(sql)
        parameter_value,  = query.first()
        if parameter_value:
             self.maturityTable =  parameter_value
        else:
            self.maturityTable = ''

        #  have the user select the protocol
        ok = self.getProtocol()
        if not ok:
            if self.initializing:
                #  user cancelled and we're still setting up - close out
                self.close()
                return
            else:
                #  user cancelled action
                return
        self.initializing = False

        #get picture
        if self.activeSpcSubcat != 'None':
            imgName=self.activeSpcCode # +"_"+self.activeSpcSubcat
        else:
            imgName=self.activeSpcCode
        pic=QImage()
        if pic.load(self.settings['ImageDir']+'\\fishPics\\'+imgName+".jpg"):
            pic = pic.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio)#,  Qt.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(pic))
        else:
             self.picLabel.clear()

        #check for existing records
        self.updateMeasureView()
        self.cycleBtn.setEnabled(True)


    def getProtocol(self):
        '''getProtocol prompts the user to select a protocol for the currently active species.
        '''

        #  build a list of the active protocols for this species
        self.protocols = []
        nProtocols = 0
        sql = ("SELECT protocol_name FROM protocol_map WHERE species_code = " +
                              self.activeSpcCode + " AND subcategory= '"+self.activeSpcSubcat +"' AND active=1")
        query = self.db.dbQuery(sql)
        for protocol_name,  in query:
            nProtocols = nProtocols + 1
            self.protocols.append(protocol_name)

        if nProtocols == 0:
            QMessageBox.information(self, "Huh...", "<font size = 12>There are no protocols defined " +
                    "for this species. If you want to sample this species you must link it to some " +
                    "protocols in the protocol_map table.")
            return False

        #  present the list to the user
        listDialog = listseldialog.ListSelDialog(self.protocols,'Short', self)
        listDialog.label.setText('Pick a sampling protocol...')
        listDialog.okBtn.setText('Sample')
        if listDialog.exec():
            #  user selected a protocol - set some props and return true
            self.protocol = listDialog.itemList.currentItem().text()
            self.protoLabel.setText(self.protocol)
            self.setup()
            self.updateMeasureView()
            return True
        else:
            #  user cancelled selection - return false
            return False


    def serialInput(self, device, val):
        '''serialInput is called when a connected serial device sends a signal and contains the device and value.
        Check to make sure the value is not a duplicate and is in order and then call either cycle or outCycle for recording.
        '''

        #  ignore empty inputs
        if (val == None) or (val == ''):
            return
        if self.freeze:
            return

        # figure out code direction for value
        self.manualFlag = False

        # get the device ID for this device if it is in the specimen module
        if 'specimen' in self.deviceData[device]['measurements']:
            device_id = self.deviceData[device]['id']
        else:
            return

        try:
            #  get an index into our devices list for this device
            ind = self.devices.index(device_id)
        except:
            #  somehow we have received data from a device we didn't configure?
            print("ERROR: CLAMSspecimen.serialInput: received data from unknown device? How can that be?")
            return

        #  Check if we have a duplicate serial value within the filter timer period
        if (self.__serialIOTimerOK == False):
            if (ind == self.lastSerialValue[0]) and (val == self.lastSerialValue[1]):
                #  This measurement is the same as the last and we're within our filter period - ignore
                return

        #  set the serial value variables
        self.lastSerialValue = [ind, val]
        self.serialValue = val

        #  set the timer OK value to false and start the filter timer
        self.__serialIOTimerOK = False
        self.__serialIOTimer.start(self.__serialIOTimerInterval)

        # determine if this device provides multiple measurements
        if (self.devices.count(device_id) == 1):
            # only one measurement using this device
            if (self.forceOrder[ind] == '1'):
                #  this measurement is an in order measurement
                self.cycle(ind)
            else:
                #  this measurement is an out of order measurement
                self.outCycle(ind)
        else:
            # this device can provide multiple measurements - find next empty value
            for i in self.iterator:
                if (self.devices[i] == device_id):
                    last_ind = i
                    if (self.values[i] == None):
                        if (self.forceOrder[i] == '1'):
                            self.cycle(i)
                        else:
                            self.outCycle(i)
                        return
            # made it through without finding a None in the values, so they are all filled- do the last one
            if (self.forceOrder[last_ind] == '1'):
                self.cycle(last_ind)
            else:
                self.outCycle(last_ind)



    def btnInput(self):
        '''btnInput is called when a protocol button is pressed. The protocol buttons can be
        pressed to manually enter or edit a value.
        '''

        #  determine what button was pressed
        ind = self.buttons.index(self.sender())

        #  set the manual flag
        self.manualFlag = True

        #  Check if this measurement is "in order" or out of order.
        if (self.forceOrder[ind] == '1'):
            #  measurement is in order
            self.cycle(ind)
        else:
            #  this measurement is an out of order measurement
            self.outCycle(ind)


    def cycle(self, i):
        '''cycle is called each time a measurement is taken. It performs the validations before
            passing measurement on to writeMeasurement.
        '''

        #  check if this measurement has been disabled
        if (not self.buttons[i].isEnabled()):
            # this measurement is disabled - skip on to the next measurement
            self.moveOn(i)
            return

        # check for existing measurement
        self.editFieldFlag = False
        if (not self.values[i] == None):
            self.freeze=True
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2], 'You already measured the ' +
                                    self.label[i] + '. Do you want to overwrite it?', 'choice')
            if self.message.exec():
                # overwrite the measurement
                self.editFieldFlag = True
                self.freeze = False
            else:
                # redo the measurement
                self.freeze = False
                return

        #check the order
        if not self.editStateFlag:
            self.checkOrder(i)
            if self.orderCheckFlag:
                return

        #  Get the measurement value
        if (self.interface[i] == 'Software'):
            #  The measurement value comes from a custom dialog box (for example sex selection)

            #  setup and display the dialog
            self.i = i
            current_dialog = self.dialogs[i](self)
            current_dialog.setup(self)
            current_dialog.exec()

            #  process the result
            result = current_dialog.result
            if result[0]:
                #  user slected a value
                val = result[1]
            else:
                #  user cancelled action
                return
        else:
            #  The measurement value can come from a device or it could come from
            #  a dialog if the user has pushed the measurement button in the GUI

            #  check if this is a manually entered value or from a device
            if (self.manualFlag):
                if (self.settings['OrganizationName'] == 'SWFSC' and 
                    (self.measureType[i] == 'barcode' 
                    or self.measureType[i] == 'dna_finclip_number')):
                    keyDialog = keypad.KeyPad(self.comment, self)
                    keyDialog.exec()
                    val = keyDialog.dispEdit.toPlainText()
                else:
                    #  this value is entered manually - display the number pad
                    self.numpad.msgLabel.setText("Enter " + self.label[i])
                    if not self.numpad.exec():
                        #  user cancelled action
                        return
                    #  get the number from the numpad and unset manualFlag value
                    val = self.numpad.value
                    #  check that we didn't get a 0 weight
                    if (val == '0'):
                        self.message.setMessage(self.errorIcons[2],self.errorSounds[2], "You have entered 0 (zero) "
                            "for the basket weight which is not allowed. If your sample is too small to register " +
                            "on the scale, you should enter 0.001", 'info')
                        self.message.exec()
                        return
                self.manualFlag = False

            elif not (self.serialValue == None):
                # value coming from serial device
                val = self.serialValue
                self.serialValue = None
            else:
                return

        # play the sound
        self.sounds[i].play()

        # do the validations and record any time the user ignores the error
        missing_validations = []
        for valObj, valName in zip(self.validations[i], self.valNames[i]):
            # instantiate the validation object with the database credentials and the current species
            valObj = valObj(self.db, self.activeSpcCode)
            # perform the validation
            result = valObj.validate(val, self.measureType, self.values)
            if not result[0] and not result[0] == None:
                # validation failed - ask if user wants to redo or override
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1], result[1], 'choice')
                if self.message.exec():
                    # redo the measurement
                    return
                else:
                    # user has overridden the validation error
                    self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                                                "You're in big trouble, " + self.firstName, 'info')
                    missing_validations.append(valName)

        if missing_validations:
            if (self.specimenKey == None):
                self.getNewSpecimen()

            update_missing_validations = False
            # check to see if we have a validation error already for this specimen
            sql = ("SELECT description FROM overrides " +
                        "WHERE ship = " + self.ship + " AND survey = " + self.survey +
                        " AND table_name = 'validations'"
                        " AND record_id = "+ self.specimenKey)
            query = self.db.dbQuery(sql)
            description,  = query.first()
            # already entered in a validation error for this specimen, now need to update
            if description:
                missing_validations.append(','+description.split(' ')[2])
                update_missing_validations = True

            if len(missing_validations) == 1:
                #  user skipped through a single validation error
                missing_validation_text = ('User allowed ' + missing_validations[0] +
                        ' validation error(s).')
            else:
                missing_validation_text = ('User skipped ' + ','.join(missing_validations) +
                        ' validation error(s).')

            if update_missing_validations:
                #  insert event into overrides table
                sql = ("UPDATE overrides SET description = '" + missing_validation_text +
                        "' WHERE ship = " + self.ship + " AND survey = " + self.survey +
                        " AND table_name = 'validations'"
                        " AND record_id = "+ self.specimenKey)
                self.db.dbExec(sql)
            else:
                #  insert event into overrides table
                sql = ("INSERT INTO overrides (ship,survey,event_id,record_id,table_name," +
                        "scientist,description) VALUES (" + self.ship + ", " + self.survey +
                        "," + self.activeHaul + "," + self.specimenKey + ",'validations','" +
                        self.scientist + "','" + missing_validation_text + "')")
                self.db.dbExec(sql)

        self.values[i]=val
        self.writeMeasurement(i, True)


    def outCycle(self, i):
        '''OutCycle is called each time an out of order serial measurement is taken. It performs the validations before
            passing measurement on to writeMeasurement.
        '''

        #  check if this measurement has been disabled
        if (not self.buttons[i].isEnabled()):
            return

        # check for existing measurement
        self.editFieldFlag = False
        if (not self.values[i] == None):
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2], 'You already measured the ' +
                                    self.label[i] + '. Do you want to overwrite it?', 'choice')
            if self.message.exec():
                # overwrite the measurement
                self.editFieldFlag = True
            else:
                # redo the measurement
                return

        # get the value
        if self.interface[i] == 'Software':
            result = [None]

            current_dialog = self.dialogs[i](self)
            current_dialog.setup(self)
            current_dialog.exec()

            #  process the result
            result = current_dialog.result

            #  check if we got a value from the dialog
            if result[0]:
                val = result[1]
            else:
                return
        else:
            #  check if this is a manually entered value or from a device
            if self.manualFlag:
                if (self.settings['OrganizationName'] == 'SWFSC' and 
                    (self.measureType[i] == 'barcode' or 
                    self.measureType[i] == 'dna_finclip_number')):
                    keyDialog = keypad.KeyPad(self.comment, self)
                    keyDialog.exec()
                    val = keyDialog.dispEdit.toPlainText()
                else:
                    #  this value is entered manually
                    self.numpad.msgLabel.setText("Enter " + self.label[i])
                    if not self.numpad.exec():
                        return
                    val = self.numpad.value
                    #  check that we didn't get a 0 weight
                    if (val == '0'):
                        self.message.setMessage(self.errorIcons[2],self.errorSounds[2], "You have entered 0 (zero) "
                            "for the basket weight which is not allowed. If your sample is too small to register " +
                            "on the scale, you should enter 0.001", 'info')
                        self.message.exec()
                        return
                self.manualFlag = False

            elif not self.serialValue == None:
                # value coming from serial device
                val = self.serialValue
                self.serialValue = None
            else:
                return

        # play the sound
        self.sounds[i].play()

        # do the validations and record any time the user ignores the error
        missing_validations = []
        for valObj, valName in zip(self.validations[i], self.valNames[i]):
            # instantiate the validation object with the database credentials and the current species
            valObj = valObj(self.db, self.activeSpcCode)
            # perform the validation
            result = valObj.validate(val, self.measureType, self.values)
            if not result[0] and not result[0] == None:
                # validation failed - ask if user wants to redo or override
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1], result[1], 'choice')
                if self.message.exec():
                    # redo the measurement
                    return
                else:
                    # user has overridden the validation error
                    self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                                                "You're in big trouble, " + self.firstName, 'info')
                    missing_validations.append(valName)

        if missing_validations:
            if (self.specimenKey == None):
                self.getNewSpecimen()
            update_missing_validations = False
            # check to see if we have a validation error already for this specimen
            sql = ("SELECT description FROM overrides " +
                        "WHERE ship = " + self.ship + " AND survey = " + self.survey +
                        " AND table_name = 'validations'"
                        " AND record_id = "+ self.specimenKey)
            query = self.db.dbQuery(sql)
            description,  = query.first()
            # already entered in a validation error for this specimen, now need to update
            if description:
                missing_validations.append(','+description.split(' ')[2])
                update_missing_validations = True

            if len(missing_validations) == 1:
                #  user skipped through a single validation error
                missing_validation_text = ('User allowed ' + missing_validations[0] +
                        ' validation error(s).')
            else:
                missing_validation_text = ('User skipped ' + ','.join(missing_validations) +
                        ' validation error(s).')

            if update_missing_validations:
                #  insert event into overrides table
                sql = ("UPDATE overrides SET description = '" + missing_validation_text +
                        "' WHERE ship = " + self.ship + " AND survey = " + self.survey +
                        " AND table_name = 'validations'"
                        " AND record_id = "+ self.specimenKey)
                self.db.dbExec(sql)
            else:
                #  insert event into overrides table
                sql = ("INSERT INTO overrides (ship,survey,event_id,record_id,table_name," +
                        "scientist,description) VALUES (" + self.ship + ", " + self.survey +
                        "," + self.activeHaul + "," + self.specimenKey + ",'validations','" +
                        self.scientist + "','" + missing_validation_text + "')")
                self.db.dbExec(sql)

        self.values[i]=val
        self.writeMeasurement(i, False)


    def writeMeasurement(self, i, keepGoing):
        '''writeMeasurement is called each time a measurement is taken. It inserts or updates data in the db
            for that measurement type and also logs the SQL to a text file.
        '''

        #  check if this is the first measurement for this specimen
        if (self.specimenKey == None):
            # first measurement - get a specimen key
            self.getNewSpecimen()

        #  disable the protocol change button - only can change protocols
        #  when you're not in the middle of processing a specimen
        self.protoBtn.setEnabled(False)
        #  change the button text to green
        self.buttons[i].setStyleSheet("background-color: green")
        if self.measureType[i] == 'length':
            measure_type = self.lengthTypeBox.currentText()
        else:
            measure_type = self.measureType[i]

        #  check if we're editing (overwriting) a record or inserting a new one
        if self.editFieldFlag:
            # overwrite record - UPDATE
            sql =("UPDATE measurements SET measurement_value ='" +
                                   self.values[i] + "' WHERE  ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+
                                   " AND sample_id="+self.activeSample+" AND specimen_id = " +self.specimenKey + " AND measurement_type = '" +
                                   measure_type+"'")
            self.db.dbExec(sql)
            # update table
            self.updateMeasureView()
            # check conditionals
            self.checkConditionals()

        else:
            #  this is a new record - INSERT
            sql = ("INSERT INTO measurements (ship, survey, event_id, sample_id, specimen_id, measurement_type, device_id, " +
                                    "measurement_value) VALUES (" +self.ship+","+self.survey+","+self.activeHaul+ ","+self.activeSample+","+ self.specimenKey + ",'" +
                                    measure_type + "'," + self.devices[i] + ",'" +
                                    self.values[i] + "')")
            self.db.dbExec(sql)

            # When finClip taken marked as true, then autofill dna_finclip_number
            # with last four survey digits + 'SH' + speciesNumber eg 2506SH001
            dnaFinclipNum = 'dna_finclip_number'
            if measure_type == 'finclip_taken' and self.values[i] == 'Yes' and dnaFinclipNum in self.measureType:
                speciesNum = str(self.measureModel.rowCount() + 1).zfill(3)
                dnaFinclip = self.survey[-4:] + 'SH' + speciesNum
                sql = ("INSERT INTO measurements (ship, survey, event_id, sample_id, specimen_id, measurement_type, device_id, " +
                                    "measurement_value) VALUES (" +self.ship+","+self.survey+","+self.activeHaul+ ","+self.activeSample+","+ self.specimenKey + ",'" +
                                    dnaFinclipNum + "'," + self.devices[i] + ",'" +
                                    dnaFinclip + "')")
                self.db.dbExec(sql)
                self.buttons[i+1].setStyleSheet("background-color: green")

            # update table
            self.updateMeasureView()
            # check conditionals
            self.checkConditionals()
            if keepGoing:
                self.moveOn(i)


    def moveOn(self, i):
        '''moveOn checks to make sure last measurement has been collected and then
        moves to the next specimen.
        '''
        #  check if this is the last measurement
        while i < len(self.values)-1:
            # this is not the last available measurement - check if the next measurement is forced

            if self.forcing[i+1]=='1' and self.values[i+1]==None and self.buttons[i+1].isEnabled():
                # next measurement is forced - check if it is from a serial device
                if self.interface[i+1]=='Software':# next input is software, fire it away

                    self.cycle(i+1)
                    break
                else:
                    # next measurement is serial, just wait for it
                    break

            else:
                i=i+1

        # this is the last measurement
        if i == len(self.values)-1:
            if self.autoCheck.isChecked():
                self.protoBtn.setEnabled(True)
                self.getNext()


    def checkConditionals(self):
            self.buttonEnable = []

            for i in self.iterator:
                self.buttonEnable.append(True)

            for condObj in self.conditionals:
                condObj = condObj(self.db)
                self.buttonEnable = condObj.evaluate(self.measureType,  self.values, self.buttonEnable)

            for i in self.iterator:
                btn = self.buttons[i]
                btn.setEnabled(self.buttonEnable[i])
                if not self.buttonEnable[i]:
                    btn.setStyleSheet("background-color: gray")

    def getNext(self, skipChecks=False):
        '''getNext checks that all required measurements have been collected for a sample
        and then resets the system for the next sample. The skipChecks keyword can be set
        to True to bypass the checks when you are deleting a sample.
        '''

        if (not skipChecks) and (not self.specimenKey == None):
            # check specimen and make sure all required measurements have been collected
            missing_measurements = []
            for i in self.iterator:
                self.incomplete = False
                btn = self.buttons[i]
                if (self.values[i] == None) and (self.forcing[i] == '1') and (btn.isEnabled()):
                    #  a measurement is missing - ask the user what they want to do
                    self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                            "You still need a " + self.measureType[i] +
                            " measurement. Does this bother you, " +
                            self.firstName + "?", 'choice')
                    if self.message.exec():
                        #  user doesn't want to skip the measurement - return to sampling
                        self.incomplete = True
                        return
                    else:
                        #  user has chosen to skip this required measurement. Add it
                        #  to our list of missing measurements.
                        missing_measurements.append(self.measureType[i])

            #  if there are any missing required measurements, scold the user and
            #  insert something in the overrides table
            if missing_measurements:
                #  user wants to skip this measurement - log it
                self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                        "You're in big trouble, " + self.firstName, 'info')
                self.message.exec()

                if len(missing_measurements) == 1:
                    #  user skipped a single measurement
                    missing_measurements_text = ('User skipped ' + missing_measurements[0] +
                            ' measurement.')
                else:
                    #  user skipped multiple measurements
                    missing_measurements_text = ('User skipped ' + ','.join(missing_measurements) +
                            ' measurements.')

                #  insert event into overrides table
                sql = ("INSERT INTO overrides (ship,survey,event_id,record_id,table_name," +
                        "scientist,description) VALUES (" + self.ship + ", " + self.survey +
                        "," + self.activeHaul + "," + self.specimenKey + ",'measurements','" +
                        self.scientist + "','" + missing_measurements_text + "')")
                self.db.dbExec(sql)

        # make the 'next' sound effect
        soundEffect = QSoundEffect()
        soundEffect.setSource(QUrl.fromLocalFile(self.settings['SoundsDir']+'\\snapjaw.wav'))
        soundEffect.play()

        # re-show all the buttons
        for i in self.iterator:
            self.values[i] = None
            self.buttons[i].setEnabled(True)
        #  reset the specimen key
        self.specimenKey = None
        self.specimenLabel.setText('')
        #  reset the button colors
        self.resetColors()
        #  clear the comment
        self.comment=''
        #  reset the editing state
        self.editStateFlag = False
        #  enable the change protocol button - only enabled when you're not processing a specimen
        self.protoBtn.setEnabled(True)


    def getNewSpecimen(self):
        '''getNewSpecimen inserts the initial data into the specimen table and then queries
        the table for the newly generated specimen id. Specimen Id's are generated by a
        sequence in the database.
        '''

        #  get the current sampling method
        samplingMethod = self.samplingMethodBox.currentText()

        #  check that we're connected to the db
        if not self.db.db.isOpen():
            #  we're not connected
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2], "Database is not connected" +
                                    " - restart clams", 'info')
            self.message.exec()
            return

        #  insert the initial data into specimen
        sql = ("INSERT INTO specimen (ship, survey, event_id, sample_id, workstation_id, scientist, " +
                " sampling_method, protocol_name, comments) VALUES (" +self.ship+","+self.survey+","+
                self.activeHaul+ ","+self.activeSample+","+ self.workStation + ",'" + self.scientist +
                "','" + samplingMethod + "','" + self.protocol + "','" + self.comment + "')")
        self.db.dbExec(sql)

        # get the newly created specimen key
        sql = ("SELECT max(specimen_id) FROM specimen WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+self.activeHaul+ " AND sample_id="+self.activeSample+
                " AND workstation_id=" + self.workStation)
        query = self.db.dbQuery(sql)
        max_specimen, = query.first()
        self.specimenKey = max_specimen
        self.specimenLabel.setText(self.specimenKey)


    def updateMeasureView(self):
        '''updateMeasureView updates the GUI table that presents the specimen measurements to the user.
        This method is called every time the specimen data changes. We take a very conservative approach
        where we requery the specimen data on every update to convince the user that the data are
        being recorded.
        '''

        #  if we have "length" as a measurement in the protocol - switch
        #  the generic length with the specific length type currently being used
        #  If there is no "length" as a measurement, we want all specimens from that sample and protocol,
        #  without length type is not null attached to the end of the sql query
        if (self.sqlLengthIndex != None):
            #  create the SQL string based on the current length type
            length_type = str(self.lengthTypeBox.currentText())
            sqlStringEnd=' AND '+length_type+' IS NOT NULL '
            #  insert the current length type
            self.sqlString[self.sqlLengthIndex] = length_type
        else:
            # For this case, the sqlString will already be formatted correctly because the length types were established in the protocol
            # And we want all of the specimens for that sample and protocol, so no ending sql string is needed- set it to one space string
            sqlStringEnd=' '

        #  create the string
        sqlString = ','.join(self.sqlString)

        #  set the model view SQL
        if self.admin:
            #  admin mode shows all measurements
            sql = ("SELECT SPECIMEN_ID, "+ sqlString +" FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                                      "ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+
                                      " AND sample_id="+self.activeSample+"  AND " +
                                      "PROTOCOL_NAME = '" + self.protocol +"'" + sqlStringEnd +
                                      "ORDER BY SPECIMEN_ID")
            self.measureModel.setQuery(sql, self.db.db)
        else:
            #  regular mode shows only measurements at that station
            sql = ("SELECT SPECIMEN_ID, "+ sqlString +" FROM V_SPECIMEN_MEASUREMENTS WHERE " +
                  "ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+
                  " AND sample_id="+self.activeSample+
                  " AND PROTOCOL_NAME = '" + self.protocol + "' AND WORKSTATION_ID = " +
                  self.workStation + sqlStringEnd + "ORDER BY SPECIMEN_ID")
            self.measureModel.setQuery(sql, self.db.db)



    def setup(self):
        '''setup is called after a protocol has been selected
        '''
        # hide all of the measurement buttons
        for btn in self.buttons:
            btn.hide()

        #  initialize the various lists that store operational details
        self.measureType = []
        self.devices = []
        self.forcing = []
        self.forceOrder = []
        self.label = []
        self.sounds = []
        self.dialogs = []
        self.interface = []
        self.validations = []
        self.valNames = []
        self.values = []
        self.sqlString = []
        self.sqlLengthIndex = None
        nMeasurements = 0

        # get the measurements for this species
        sql = ("SELECT PROTOCOL_DEFINITIONS.MEASUREMENT_TYPE, MEASUREMENT_SETUP.DEVICE_ID," +
                "DEVICES.DEVICE_INTERFACE,PROTOCOL_DEFINITIONS.FORCE_MEASUREMENT," +
                "PROTOCOL_DEFINITIONS.FORCE_ORDER,PROTOCOL_DEFINITIONS.LABEL " +
                "FROM MEASUREMENT_SETUP JOIN PROTOCOL_DEFINITIONS " +
                "ON PROTOCOL_DEFINITIONS.MEASUREMENT_TYPE=MEASUREMENT_SETUP.MEASUREMENT_TYPE " +
                "JOIN DEVICES ON DEVICES.DEVICE_ID=MEASUREMENT_SETUP.DEVICE_ID " +
                "WHERE PROTOCOL_DEFINITIONS.PROTOCOL_NAME='"+self.protocol+"' AND " +
                "MEASUREMENT_SETUP.WORKSTATION_ID="+self.workStation+" AND  " +
                "MEASUREMENT_SETUP.GUI_MODULE='Specimen' " +
                "ORDER BY PROTOCOL_DEFINITIONS.MEASUREMENT_ORDER ASC")

        query = self.db.dbQuery(sql)

        #  Initialize length type combo box to disabled until you encounter a 'length' in the protocol
        self.lengthTypeBox.setEnabled(False)

        #  loop through the measurements we have found and extract the deets
        for type,  device,  interface,  force_measurement, force_order, label in query:
            self.measureType.append(type)
            self.devices.append(device)
            self.interface.append(interface)
            self.forcing.append(force_measurement)
            self.forceOrder.append(force_order)
            self.label.append(label)

            # get the sounds for the device
            sql = ("SELECT device_configuration.PARAMETER_VALUE FROM device_configuration WHERE " +
                    "(device_configuration.DEVICE_ID = "+device+") AND (" +
                    "device_configuration.DEVICE_PARAMETER = 'SoundFile' )")
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
                soundFile = (self.settings['SoundsDir']+'softwareSound.wav')
            soundEffect.setSource(QUrl.fromLocalFile(soundFile))
            self.sounds.append(soundEffect)

           # for software inputs, get the dialog to be used
            if interface.lower() == 'software':
                sql1=("SELECT device_configuration.PARAMETER_VALUE FROM device_configuration WHERE " +
                        "(device_configuration.DEVICE_ID = " + device + " ) AND (" +
                        "device_configuration.DEVICE_PARAMETER = 'Module' )")
                query1 = self.db.dbQuery(sql1)
                value, =query1.first()
                if value:
                    #  module name found - import and instantiate an instance of it
                    dlg = value
                    updlg = dlg
                    try:
                        dlgModule = ('measurementDialogs.'+dlg.lower())
                        dlgObj = importlib.import_module(dlgModule)
                        dlgObj = getattr(dlgObj, updlg)
                        self.dialogs.append(dlgObj)
                    except Exception as e:
                        #  there was a problem importing or instantiating the measurement dialog
                        self.dialogs.append(None)
                        self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                            "Error importing or instantiating the " + dlg.lower() +
                            " measurement dialog.\nError text: '" + str(e) + "'\n"
                            "This measurement will not be available until the issue is fixed.", 'info')
                        self.message.exec()
                else:
                    #  we were unable to find a Module entry in device_configuration for this device ID
                    self.dialogs.append(None)

                    #  get the device name for the error dialog
                    sql1 = ("SELECT device_name FROM devices WHERE device_id=" +device)
                    query1 = self.db.dbQuery(sql1)
                    device_name, = query1.first()
                    if device_name:
                        deviceName = device_name
                    else:
                        deviceName = "Unknown (device ID " + device + ")"

                    #  present the error dialog
                    self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                        "No module definition found in the device_configuration table for " +
                        "software device " + deviceName + ". The measurement associated with " +
                        "this device will not function." , 'info')
                    self.message.exec()
            else:
                #  this measurement does not have a dialog (aka hardware measurement)
                self.dialogs.append(None)

            # get validations
            sql1 = ("SELECT VALIDATION FROM VALIDATIONS WHERE ( "+
                    "PROTOCOL_NAME = '"+self.protocol+"' ) AND ( "+
                    "MEASUREMENT_TYPE = '"+type+"') "+
                    "ORDER BY VALIDATION_ORDER ASC ")
            query1 = self.db.dbQuery(sql1)
            vals = []
            valNames = []

            #  create an instance of the validation object and add to our list of validations
            for validations,  in query1:
                valModule = ('validations.'+validations)
                valObj = importlib.import_module(valModule)
                valObj = getattr(valObj, validations)
                valNames.append(validations)
                vals.append(valObj)

            self.valNames.append(valNames)
            self.validations.append(vals)

            #  build the measureView SQL list - this is a list of the measurements that
            #  we join with a comma to generate a string right before using it in the
            #  updateMeasureView method. We store the items as a list so we can easily
            #  swap out the length type if the user changes it.

            #  First we check if this is a length measurement. Lengths are treated special
            #  since we are allowing the generic measurement "length" to map to multiple
            #  real measurement types. This breaks the rules and is not ideal, but this
            #  change was implemented years after CLAMS was initially written and it is
            #  too late at this point to change everything.
            #  Enable lengthType combo box if there is 'length' type- otherwise it will be disabled
            if (type == 'length'):
                #  store the index of "length" in the SQL string so we can swap it out
                #  when the user changes the length_type
                self.sqlLengthIndex = nMeasurements
                self.lengthTypeBox.setEnabled(True)
                # Provide user with the length type that should be measured.
                # Use this to re-inforce the new length type policy
                lengthType=self.lengthTypeBox.currentText()
                QMessageBox.information(self, "Length Measurement Type", "<font size = 12>You should now measure " +lengthType)


            #  append this measurement onto our sqlString list
            self.sqlString.append(type)

            #  increment the measurements counter
            nMeasurements = nMeasurements + 1

            # initialize the value vector
            self.values.append(None)

        #  set up the measurement buttons
        for i in range(len(self.label)):
            # show button
            self.buttons[i].show()
            self.buttons[i].setText(self.label[i])
        # if there are optional items, cant use autocycle
        if '0' in self.forcing:
            self.autoCheck.setEnabled(False)
        else:
            self.autoCheck.setEnabled(True)
        # default is always random
        self.samplingMethodBox.setCurrentIndex(self.samplingMethodBox.findText('random'))

        # get conditionals
        sql = ("SELECT CONDITIONALS.CONDITIONAL FROM CONDITIONALS WHERE ( "+
                                            "CONDITIONALS.PROTOCOL_NAME = '"+self.protocol+"')")
        query = self.db.dbQuery(sql)
        self.conditionals = []

        for conditional, in query:
            upcond = conditional
            condModule = ('conditionals.'+conditional.lower())
            condObj = importlib.import_module(condModule)
            condObj = getattr(condObj, upcond)
            self.conditionals.append(condObj)

        self.iterator = range(len(self.measureType))
        # collections - this will be done though DB in the future
        self.activeCollections = ['Stomach', 'Ovary']
        self.collectionMeasurementTypes = ['stomach_taken', 'ovary_taken']# also temporary for now
        self.collectionDevices = ['5', '7']# also temporary for now

        self.resetColors()
        self.editStateFlag=False

        #  check to make sure we set up at least one measurement
        if len(self.values) == 0:
            #  we don't even have one measurement :(
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                "Either this protocol is not set up correctly or your workstation does not have any measurements " +
                "configured in measurement_setup. Please select a different protocol or configure your " +
                "workstation correctly.", 'info')
            self.message.exec()
        else:
            self.cycle(0)


    def goDelete(self):
        '''goDelete is called when the delete button is pressed.
        A question check is presented to user to make sure it was not a mistake
        and then the associated data are deleted from the database
        then updateMeasureView is called to refresh the displayed data
        '''

        #  ensure that a specimen is selected
        if (self.specimenKey == None):
            #  no specimen is currently selected
            self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                    "Please select a specimen to delete.", 'info')
            self.message.exec()
            return

        #  verify that the user wants to delete the specimen
        self.message.setMessage(self.errorIcons[0], self.errorSounds[0], "Are you sure you want to delete" +
                                " specimen " + self.specimenKey + ", " + self.firstName + "? ", 'choice')
        if self.message.exec():
            #  yes - delete the specimen
            sql = ("DELETE FROM measurements WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = " + self.specimenKey)
            self.db.dbExec(sql)
            sql = ("DELETE FROM specimen WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = "+self.specimenKey)
            self.db.dbExec(sql)

            #  update the view
            self.updateMeasureView()
            self.specimenLabel.setText('')
            #  reset for the next sample - skip the checks since we're deleting this sample
            self.getNext(skipChecks=True)


    def resetColors(self):
        '''resetColors resets the button colors after a specimen has been taken, deleted, or is being edited
        '''

        #  loop thru the buttons
        for i in self.iterator:
            btn = self.buttons[i]

            #  check if we're editing this specimen
            if self.editStateFlag:
                #  we're editing - check if there is a value for this measurement
                if self.values[i]:
                    # already measured - set the button green
                    btn.setStyleSheet("background-color: green")
                else:
                    #  we haven't taken this measurement - check if it's required or optional
                    if (self.forcing[i] == '1'):
                        #  this measurement is required - set the button red
                        btn.setStyleSheet("background-color: red")
                    else:
                        #  this measurement is optional - set yellow
                        btn.setStyleSheet("background-color: yellow")
            else:
                #  we're not editing so we don't check for any existing values\
                #  just check for required vs optional measurements
                if (self.forcing[i] == '1'):
                    #  this measurement is required - set the button red
                    btn.setStyleSheet("background-color: red")
                else:
                    #  this measurement is optional - set yellow
                    btn.setStyleSheet("background-color: yellow")

        #  check if we're editing
        if self.editStateFlag:
            #  we're editing so we need to check the conditionals
            self.checkConditionals()


    def getEditSel(self):
        '''getEditSel is called when a selection is made in the specimen list.
        It pulls up the the specimen data from the selection but first enforces measurements
        are complete on the current specimen.
        '''

        # this prevents method from firing on DE-selection
        if self.selModel.selection().count() == 0:
            return

        #  get the specimen id for the selected row
        selObj = self.measureView.currentIndex()
        index = self.measureModel.index(selObj.row(), 0, QModelIndex())
        thisSpecimenKey = self.measureModel.data(index, Qt.ItemDataRole.DisplayRole)

        #  check if the selected row is the most current specimen
        if (thisSpecimenKey == self.specimenKey):
            #  The selected row is the current specimen - nothing else to do here
            return

        #  The selected row is not the most current specimen
        #  check that the current specimen is complete before editing an old specimen
        content = False
        for i in self.values:
            if i != None:
                content = True
        if content:
            #  there are missing measurements throw up a dialog
            for i in range(len(self.measureType)):
                btn = self.buttons[i]
                if (self.values[i] == None) and (self.forcing[i] == '1') and (btn.isEnabled()):
                    self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "Dear "+self.firstName+", "+
                                        "Please finish up your current specimen before editing.",'info' )
                    self.message.exec()
                    self.selModel.clearSelection()
                    return

        #  set the specimen_id and update it on the GUI
        self.specimenKey = str(int(thisSpecimenKey))
        self.specimenLabel.setText(str(int(thisSpecimenKey)))

        # re-initialize measurement array
        self.values = [None] * len(self.measureType)

        #  query the measurements for this specimen
        sql = ("SELECT measurement_type, measurement_value FROM measurements WHERE ship=" +
                self.ship+ " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND specimen_id = " +
                self.specimenKey)
        query = self.db.dbQuery(sql)

        for type, value in query:
            #  now try to get the index into our measurements array for this
            #  measurement type. This will work for every measurement *except*
            #  the specific length types since lengths break the rule of
            try:
                ind = self.measureType.index(type)
            except:

                #  since we failed finding this measurement, this should be one of
                #  the specific length measurements for this species+subcode
                if (type in self.lengthTypes):
                    ind = self.measureType.index('length')
                else:
                    #  huh. This shouldn't happen....
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                            "Measurement '" + type + "' found when reloading " +
                            "the specimen for edit. This measurement is not in the current protocol." +
                            " This can only happen if the protocol was changed after data was already " +
                            "collected which is generally considered bad form. You will not be able to" +
                            " alter this measurement using CLAMS.", 'info')
                    self.message.exec()
                    continue

            #  Now that we did all that work to get the index, set the measurement value
            self.values[ind] = value

        # set the random flag and get the comments
        sql = ("SELECT sampling_method, comments FROM specimen WHERE ship="+
                self.ship+ " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND specimen_id = "+self.specimenKey)
        query = self.db.dbQuery(sql)
        data = query.first()
        self.samplingMethodBox.setCurrentIndex(self.samplingMethodBox.findText(data[0]))
        self.comment = data[1]
        self.editStateFlag = True
        self.resetColors()

        # get any comments
        self.comment = ''
        sql = ("SELECT comments FROM specimen WHERE specimen_id = "+self.specimenKey+" AND ship="+self.ship+
        " AND survey="+self.survey+" AND event_id="+self.activeHaul)
        query = self.db.dbQuery(sql)
        val, = query.first()

        if val:
            self.comment = val

    def checkOrder(self, i):
        '''checkOrder enforces the protocol order.
        '''
        # this is not a validation but an internal check that the protocol order is being followed
        self.orderCheckFlag = False
        self.outOfOrder=False
        if (self.forceOrder[i] == '1'):
            for j in range(i):
                if (self.values[j] == None) and (self.forceOrder[j] == '1') and (self.buttons[j].isEnabled()) and (self.forcing[j] == '1'):
                    # a measurement below this one in order has not been made and the order for this is forced
                    self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "Dear " +
                                            self.firstName + ", you screwed up the order. Measure the " +
                                            self.measureType[j]+" first, please.",'info' )
                    self.message.exec()
                    self.values[i] = None
                    self.orderCheckFlag = True
                    break
        else:
            self.outOfOrder=True


    def getCollections(self):
        if self.specimenKey == None:
            return
        # fire up dialog
        collectionDialog = collectionsdlg.CollectionsDlg(self.activeCollections, self)
        #listDialog.okBtn.setText('Sample')
        if collectionDialog.exec():# we want to print stuff and we made collections
            # iterate though boxes and get checked ones - non-visible boxes default to uncecked
            for i, box in enumerate(collectionDialog.checkboxes):
                if box.isChecked():
                    # insert measurement
                    sql=("INSERT INTO measurements (ship,survey,event_id,sample_id,specimen_id," +
                            "measurement_type,device_id,measurement_value) VALUES ("+self.ship+","+
                            self.survey+","+self.activeHaul+ ","+self.activeSample+","+ self.specimenKey + ",'" +
                            self.collectionMeasurementTypes[i] + "'," + self.collectionDevices[i] + ",'Yes')")
                    self.db.dbExec(sql)
                    self.printLabel()



    def printLabel(self):
        '''printLabel is called when the "Print Label" button is pressed. Labels are usually
        printed for special specimen collection projects and they contain information that
        allows the person processing the sample to link it back to the specimen in CLAMSBASE.
        '''

        #  make sure that a specimen has been selected
        if (self.specimenKey == None):
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0], "Please Select a "+
                    "specimen to print a label for.")
            self.message.exec()
            return

        #  check that all requried measurements have been obtained
        for i in self.iterator:
            btn = self.buttons[i]
            if (self.values[i] == None) and (self.forcing[i] == '1') and (btn.isEnabled()):
                #  a measurement is missing - ask the user what they want to do
                self.message.setMessage(self.errorIcons[0], self.errorSounds[0], "You still need a " +
                                        self.measureType[i] + " measurement. Does this bother you, " +
                                        self.firstName + "?", 'choice')
                if self.message.exec():
                    #  user doesn't want to print label - return to sampling
                    self.incomplete = True
                    return
                else:
                    #  user wants to print a label anyways
                    break

        #  get data from db - query everything *BUT* length
        sql = ("SELECT ship, survey, haul, specimen_id, species_code, common_name, "+
                "organism_weight, sex, maturity, scientist, barcode FROM v_specimen_measurements WHERE "+
                "survey=" + self.survey +" AND ship="+self.ship+" AND specimen_id="+self.specimenKey)
        query = self.db.dbQuery(sql)
        data = query.first()
        vessel = data[0]
        survey = data[1]
        haul = data[2]
        spec_id = data[3]
        code = data[4]
        name = data[5]
        weight = data[6]
        sex = data[7]
        maturity = data[8]
        scientist = data[9]
        barcode =  data[10]

        #  with the latest version of the CLAMS schema, we have a "is_length" column in the
        #  measurements table that is set to 1 for "length" measurements which allows us
        #  to query all of the length measurements regardless of their name. First we build
        #  a list of all length types.
        len_list = []
        sql = ("SELECT measurement_type FROM measurement_types WHERE " +
                "is_length=1")
        query = self.db.dbQuery(sql)
        for type, in query:
            len_list.append(type)

        # When the length type is changed in the combo box, only the specimens with that
        # length type are shown in the table, therefore, the only option for length type
        #  selected is the one currently active in the combo box- query using that type
        if self.lengthTypeBox.isEnabled():
            lengthType = str(self.lengthTypeBox.currentText())

            sql = ("SELECT lower(measurement_type), measurement_value from measurements WHERE " +
                "measurement_type = '"+lengthType+"' AND survey=" + self.survey +
                " AND ship="+self.ship+" AND specimen_id="+self.specimenKey)
            query = self.db.dbQuery(sql)
            data  = query.first()
            length=data[1]

            #  now build the length string to print
            if lengthType in len_list:
                ind=lengthType.find('_')+1
                if ind != 0:
                    lt = lengthType[0].upper()+lengthType[ind].upper()
                else:
                    # This case is for length types without an underscore, which doesn't happen now but might in the future
                    lt = lengthType[0].upper()+lengthType[1].upper()
        else:
            # Just stick the first length type (from protocol) value on the label in the length section, if it exists (if not, NaN)
            length='NaN'
            for lengthType in self.measureType:
                if lengthType in len_list:
                    lengthType = str(lengthType)
                    query = ("SELECT lower(measurement_type), measurement_value from measurements WHERE " +
                        "measurement_type = '"+lengthType+"' AND survey=" + self.survey +
                        " AND ship="+self.ship+" AND specimen_id="+self.specimenKey)
                    query = self.db.dbQuery(sql)
                    data  = query.first()
                    length = data[1]
                    ind = lengthType.find('_')+1
                    if ind != 0:
                        lt = lengthType[0].upper()+lengthType[ind].upper()
                    else:
                        # This case is for length types without an underscore, which doesn't happen now but might in the future
                        # Just take first two letter of length type word
                        lt = lengthType[0].upper()+lengthType[1].upper()
                    break


        length = length + ' ' + lt

        #create dictionary
        data={'title':'NOAA/AFSC/RACE/MACE',
              'ship':vessel,
              'survey':survey,
              'haul':haul,
              'specimen_id':spec_id,
              'species_code':code,
              'common_name':name,
              'length':length,
              'weight':weight,
              'sex':sex,
              'maturity_table':self.maturityTable,
              'maturity_key':maturity,
              'scientist':scientist,
              'otolith':barcode
              }

        #  print the label
        self.printer.printSpecialSampleLabel1(data)

        # print sound
        if self.printSound:
            self.printSound.play()


    def getComment(self):
        '''getComment displays the comment dialog then "cleans" the comment string and inserts
        it into the database.
        '''

        if self.specimenKey:

            keyDialog = keypad.KeyPad(self.comment, self)
            keyDialog.exec()
            if keyDialog.okFlag:
                #  get the comment string
                commentString = keyDialog.dispEdit.toPlainText()
                self.comment = commentString

                #  clean string by removing newline chars and replacing with a space
                commentString = commentString.split('\n')
                newString = ''
                for c in commentString:
                    newString = newString + c + ' '

                # insert comment into sample
                sql =("UPDATE specimen SET comments='" + newString +
                        "' WHERE ship="+self.ship+ " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                        " AND specimen_id = " + self.specimenKey)
                self.db.dbExec(sql)
        else:
            QMessageBox.information(self, "Huh...", "<font size = 12>No specimen has been selected. " +
                    "Please choose a specimen before you try to add a comment.")


    def editSamplingMethod(self):
        # user toggles in sample flag - have to update data
        if self.editStateFlag:
            sql = ("UPDATE specimen SET sampling_method =" + self.samplingMethodBox.currentText() +
                    " WHERE ship="+self.ship+ " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                    " AND specimen_id = "+self.specimenKey)
            self.db.dbExec(sql)


    def closeEvent(self, event):

        #  check if we're in the middle of a specimen
        if self.activeSpcCode and self.specimenKey:
            self.getNext()
            if self.incomplete:
                event.ignore()
                return

        #  store the application size and position
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())

        event.accept()


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        '''checkWindowLocation accepts a window position (QPoint) and size (QSize)
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




