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
.. module:: sortedCatch

    :synopsis: small CPS hauls with < 5 baskets entered here. 
                Sorted Catch is also entered once a larger catch has been processed 
                and sorted, then information is entered here. 

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Melina Shak <melina.shak@noaa.gov>
"""

#  imports
import os
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QSoundEffect
from ui import ui_CLAMSCatch
import CPS.cpsAddCatchSpcDlg as cpsAddCatchSpcDlg
import numpad
import typeseldialog
import basketeditdlg
import keypad
import transferdlg
import messagedlg
import ZebraLabelPrinter
import addspecdlg
import FEATZebraPrinter
import measurementDialogs.FEATProjectDlg as project


class sortedCatch(QDialog, ui_CLAMSCatch.Ui_clamsCatch):

    def __init__(self, parent=None):

        #  call superclass init methods and GUI form setup method
        super(sortedCatch, self).__init__(parent)
        self.setupUi(self)

        #  copy some info from parent for convenience
        self.db = parent.db
        self.sensorMonitor = parent.sensorMonitor
        self.workStation = parent.workStation
        self.activeHaul = parent.activeHaul
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.activePartition = parent.activePartition
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.scientist = parent.scientist
        self.deviceData = parent.deviceData
        self.schema = parent.schema

        # initialize variables
        self.printer = None
        self.addspec_flag = True
        self.planktonFlag = False
        self.activeSampleKey = None
        self.activeSpcName = None
        self.activeSpcCode = None
        self.activeFullName = None
        self.samplePicture = None
        self.comment = ''
        self.validList = [1, 1, 1]# sets valid sample type choices
        self.basketTypes = ['Measure', 'Count', 'Toss']
        self.freeze = False
        self.whHaulFlag = False
        self.devices = {}
        self.sounds = {}
        self.speciesProtos = {}
        self.subcategories = []
        self.manualDevice ='0'
        self.parentSamples = {}
        self.mixtureNames = {'100000':'WholeHaul', '100001':'SortingTable',
                '100002':'Mix1', '100003':'SubMix1', '100004':'Mix2','3':"SubMix"}
        self.wholeHaulKey = None
        self.headerFont = QFont("Arial Black", 11, -1, False)
        self.activeSampleType = None
        self.isCurrSubMix = False

        #  set the basket precision - basket weights will be rounded to this many
        #  digits after the decimal. Note that currently the database supports
        #  UP TO 4 digits. Values beyond that will be lost.
        if 'CatchBasketPrecision' in self.settings:
            try:
                #  convert the setting in the database to an integer
                self.basketPrecision = int(self.settings['CatchBasketPrecision'])
            except:
                #  setting is in application_configuration but it isn't a number - default to 3
                self.basketPrecision = 3
        else:
            #  setting is not in application_configuration - default to 3
            self.basketPrecision = 3

        #  do some UI setup
        self.sciLabel.setText(self.scientist)
        self.firstName = self.scientist.split(' ')[0]
        # add partition to event
        haul_txt = str(self.activeHaul) + " - " + str(self.activePartition)
        self.haulNum.setText(haul_txt)
        self.transBtn.hide()

        #  set up tables for data display - most of this is done in QDesigner
        #  but some properties don't seem to "stick" (maybe QDesigner is buggy?)
        self.basketTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.basketTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.basketTable.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.basketTable.horizontalHeader().setStretchLastSection(True)
        self.speciesList.horizontalHeader().setStretchLastSection(True)

        #  set up the the basket table headers
        self.basketTable.clearContents()
        self.basketTable.setRowCount(0)
        headerItem = QTableWidgetItem("Weight (kg)")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(0, headerItem)
        headerItem = QTableWidgetItem("Count")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(1, headerItem)
        headerItem = QTableWidgetItem("Basket Type")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(2, headerItem)

        # set up recurring dialogs
        self.message = messagedlg.MessageDlg(self)
        self.numpad = numpad.NumPad(self)
        self.addspec = addspecdlg.addspecedlg(self)
        self.typeDlg = typeseldialog.TypeSelDialog(self)
        

        #  connect signals and slots
        self.addspcBtn.clicked.connect(self.getSpecies)
        self.manualBtn.clicked.connect(self.getManual)
        self.doneBtn.clicked.connect(self.closeWindow)
        self.delBtn.clicked.connect(self.goDelete)
        self.printBtn.clicked.connect(self.printLabel)
        self.editBtn.clicked.connect(self.editTable)
        self.speciesList.itemSelectionChanged.connect(self.getActiveSpc)
        self.speciesList.itemActivated.connect(self.getSpeciesFocus)
        self.basketTable.itemSelectionChanged.connect(self.getBasketRow)
        self.commentBtn.setDisabled(True)  # initially disabled
        self.commentBtn.clicked.connect(self.getComment)
        self.unsortedBtn.clicked.connect(self.showUnsorted)

        #  connect the SensorMonitor SerialDataReceived signal to the
        #  getAuto method which processes input from devices.
        self.sensorMonitor.SensorDataReceived.connect(self.getAuto)

        # Querying application_configuration table to set MaxMinDev from 
        # sampleThreshold value for sub-sample check
        sql = "SELECT parameter_value from application_configuration " \
              "where parameter='SubSampleCheckThreshold'"
        query = self.db.dbQuery(sql)
        threshold, = query.first()
        threshold = float(threshold) if threshold else 0.0
        self.settings['MaxMixDev'] = threshold

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'CatchForm')
        size = self.appSettings.value('winsize', QSize(1000,725))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  create a timer to complete init after initial form presentation
        checkHaulTimer = QTimer(self)
        checkHaulTimer.setSingleShot(True)
        checkHaulTimer.timeout.connect(self.formInit)
        checkHaulTimer.start(0)


    def formInit(self):
        '''formInit is called immediately after the form is presented on
        screen and it continues form/module setup. It checks to make sure we
        have completed the haul form for this partition and inserts/updates
        some base samples table entries

        '''

        #  First, check to see if haul form has been checked for codend partition
        if 'codend' in self.activePartition.lower():
            sql = ("SELECT parameter_value FROM  " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND partition='" + self.activePartition +
                "' AND event_parameter='PartitionWeightType'")

            query = self.db.dbQuery(sql)
            pwt, = query.first()
            if not pwt:
                #  no partition weight so add one 
                #  No partition intialized yet, insert a dummy one
                sql = ("INSERT INTO " + self.schema + ".EVENT_DATA (ship, survey, event_id, partition, "
                    "event_parameter, parameter_value) "
                    "VALUES (" + self.ship + "," + self.survey + "," + self.activeHaul + ",'Codend',"
                    "'PartitionWeightType','not_subsampled')")
                self.db.dbExec(sql)
                
                sql = ("INSERT INTO " + self.schema + ".EVENT_DATA (ship, survey, event_id, partition, "
                    "event_parameter, parameter_value) "
                    "VALUES (" + self.ship + "," + self.survey + "," + self.activeHaul + ",'Codend',"
                    "'PartitionWeight','TBD')")
                self.db.dbExec(sql)

            #  Check if we have a label printer attached at this workstation. If so,
            #  create the printer object and if not, disable the print button
            sql = ("SELECT MEASUREMENT_SETUP.DEVICE_ID, DEVICES.DEVICE_NAME " +
                   "FROM " + self.schema + ".MEASUREMENT_SETUP INNER JOIN  " + self.schema + ".DEVICES ON " +
                   "MEASUREMENT_SETUP.DEVICE_ID = DEVICES.DEVICE_ID WHERE " +
                   "MEASUREMENT_SETUP.WORKSTATION_ID = " + self.workStation +
                   " AND DEVICES.DEVICE_NAME = 'Label_Printer'" +
                   " GROUP BY MEASUREMENT_SETUP.DEVICE_ID, DEVICES.DEVICE_NAME")
            query = self.db.dbQuery(sql)
            printerId, printerName = query.first()
            if printerId:
                #  initialize the Label Printer
                if 'nwfsc' in self.settings['OrganizationName'].lower() or \
                        'swfsc' in self.settings['OrganizationName'].lower():
                    # get the ip and port
                    printer_sql = ("SELECT device_parameter, parameter_value "
                                   "FROM " + self.schema + ".device_configuration WHERE device_id = " + printerId)
                    print_query = self.db.dbQuery(printer_sql)
                    ip = None
                    port = None
                    for param, val in print_query:
                        if param.lower() == 'networkaddress':
                            ip = val
                        elif param.lower() == 'networkport':
                            port = val
                    self.printer = FEATZebraPrinter.PrintLabel(self.ship, self.survey, ip, port)
                else:
                    self.printer = ZebraLabelPrinter.ZebraLabelPrinter(self.sensorMonitor, printerName)
            else:
                #  no printer configured
                self.printer = None
                self.printBtn.setEnabled(False)
            #  set up the printer sound.
            sql = ("select a.parameter_value from " + self.schema + ".device_configuration a," +
                   self.schema + ".devices b where a.device_id=b.device_id " +
                   "and b.device_name='Label_Printer' and a.device_parameter='SoundFile'")
            query = self.db.dbQuery(sql)
            soundFile, = query.first()
            if soundFile:
                hasExt = soundFile.split('.')
                if len(hasExt) > 1:
                    soundFile = self.settings['SoundsDir'] + soundFile
                else:
                    soundFile = self.settings['SoundsDir'] + soundFile + '.wav'
                soundEffect = QSoundEffect()
                soundEffect.setSource(QUrl.fromLocalFile(soundFile))
                self.printSound = soundEffect
            else:
                self.printSound = None

        #  setup parent sample. if not present, create whole catch sample which is
        #  the top level sample (no parent)
        sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship="+self.ship+" AND survey="+
                self.survey+" AND event_id="+self.activeHaul+" AND partition ='"+self.activePartition+
                "' AND species_code=100001")
        query = self.db.dbQuery(sql)
        self.parentSamples, = query.first()
        if not self.parentSamples:
            #  the parent sample doesn't exist yet, so create it.
            # Get parent sample_id (species_code = 1)
            sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship="+self.ship+" AND survey="+
                self.survey+" AND event_id="+self.activeHaul+" AND partition ='"+self.activePartition+
                "' AND species_code=1")
            query = self.db.dbQuery(sql)
            parentId, = query.first()

            if parentId is None:
                sql = ("INSERT INTO " + self.schema + ".samples (ship, survey, event_id, partition, " +
                    "sample_type,species_code, scientist) VALUES("+self.ship+","+self.survey+
                    ","+self.activeHaul+ ",'"+self.activePartition+"','SortingTable',100001,'"
                    +self.scientist+"')")
                self.db.dbExec(sql)
            else:
                sql = ("INSERT INTO " + self.schema + ".samples (ship, survey, event_id, partition, " +
                        "sample_type,species_code, scientist, parent_sample) VALUES("+self.ship+","+self.survey+
                        ","+self.activeHaul+ ",'"+self.activePartition+"','SortingTable',100001,'"
                        +self.scientist+"',"+ parentId+")")
                self.db.dbExec(sql)

            #  now retrieve newly created sample ID from database
            sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                    " AND partition ='"+self.activePartition+"' AND species_code=100001")
            query = self.db.dbQuery(sql)
            self.parentSamples, = query.first()

        self.spcDlg = cpsAddCatchSpcDlg.cpsAddCatchSpcDlg(self)
        self.spcDlg.changed.connect(self.addSpecies)
        self.sortingTableKey = self.parentSamples

        #  get the list of possible subcategories
        sql = ("SELECT subcategory FROM " + self.schema + ".species_subcategories")
        query = self.db.dbQuery(sql)
        for subcategory, in query:
            self.subcategories.append(subcategory)

        # set up device sounds
        #self.loadDeviceSounds()

        #  reload the species list - this populates the species list
        self.reloadSamplesList()


        #self.updateParentKeys()
    
    def closeWindow(self):
        self.sensorMonitor.SensorDataReceived.disconnect(self.getAuto)
        self.close()

    def showUnsorted(self):
        self.sensorMonitor.SensorDataReceived.disconnect(self.getAuto)
        self.close()
        unsorted = unsortedCatch.unsortedCatch(self)
        unsorted.exec()


    def getSpecies(self):
        '''getSpecies is called when the Add Species button is pressed and it pauses
        device input and displays the add species dialog.
        '''
        #  set freeze to ignore sensor/device input while adding species
        self.freeze=True

        #  show the add species dialog
        self.spcDlg.exec()

        #  unset freeze to continue processing sensor/device input
        self.freeze=False


    def addSpecies(self):
        '''addSpecies is called when a species is added using the add species dialog.
        '''

        self.addspec_flag = False

        #  get the species info we need from the dialog
        code = self.spcDlg.activeSpcCode
        spcName = self.spcDlg.activeSpcName
        subCat = self.spcDlg.activeSpcSubcat
        sampleType = self.spcDlg.activeSampleType
        isSubMix = self.spcDlg.isSubMix

        # parent sample
        #parentKey  = self.parentSamples[self.spcDlg.parentSample]
        
        self.createSample(code, spcName, subCat,  self.spcDlg.nameType,  self.parentSamples, sampleType, isSubMix)

        #
        #self.updateParentKeys()

        # make this new addition the active one...
        self.reloadSamplesList()

        self.addspec_flag = True


    def updateParentKeys(self):

        #  check if we have a mix
        for code in ['100002', '100003', '100004']:
            sql = ("SELECT species.common_name, samples.sample_id  " +
                    "FROM " + self.schema + ".samples, " + self.schema + 
                    ".species WHERE species.species_code=samples.species_code " +
                    "AND samples.species_code =" + code + " AND samples.ship=" + self.ship +
                    " AND samples.survey=" + self.survey + " AND samples.event_id=" +
                    self.activeHaul + " AND samples.partition='" + self.activePartition + "'")
            query = self.db.dbQuery(sql)
            common_name, sample_id = query.first()

            if common_name:
                #  yes, we have a mix
                spcName = common_name
                parentKey = sample_id
                if not parentKey in self.parentSamples:
                    self.parentSamples.update({spcName:parentKey})

        if not self.wholeHaulKey in self.parentSamples:
            self.parentSamples.update({'WholeHaul':self.wholeHaulKey})
        if not self.sortingTableKey in self.parentSamples:
            self.parentSamples.update({'SortingTable':self.sortingTableKey})


    def createSample(self, code, name, subCat, nameType, parentSample, sampleType, isSubMix):

        #  check if the species that we're being told to add is already in
        #  out list of samples.
        if subCat != 'None':
            if self.speciesList.findItems(name+"-"+subCat, Qt.MatchFlag.MatchExactly):
                #  species + subcat is already in the list - just return
                return
        else:
            if self.speciesList.findItems(name, Qt.MatchFlag.MatchExactly):
                #  species is already in the list - just return
                return
            
        # Get parentId of submix and add count to basket types
        if isSubMix:
            sql = ("select sample_id from " + self.schema + ".samples where survey=" + self.survey +
               " AND event_id=" + self.activeHaul + 
               " AND parent_sample=" + self.parentSamples + 
               " AND sample_type='SubMix'")
            query = self.db.dbQuery(sql)
            parentSample, = query.first()

        #  insert this data into the samples table
        sql = ("INSERT INTO " + self.schema + ".samples (ship,survey,event_id,partition,sample_type," +
                "species_code,subcategory,parent_sample,scientist) VALUES("+
                self.ship+","+self.survey+","+ self.activeHaul+",'"+self.activePartition+
                "','"+sampleType+"',"+code+",'"+subCat+"',"+parentSample+",'"+
                self.scientist+"')")
        self.db.dbExec(sql)

        #  get the new sample ID for the just inserted sample
        sql = ("SELECT max(sample_id) FROM " + self.schema + ".samples WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+ self.activeHaul+
                " AND partition ='"+self.activePartition+"'")
        query = self.db.dbQuery(sql)
        sample_id, = query.first()


        #  insert the sample_display_name param in the sample_data table. This
        #  informs CLAMS as to which name (sci or common) to display in the UI
        #  for this sample.
        sql = ("INSERT INTO " + self.schema + ".sample_data (ship,survey,event_id,sample_id,sample_parameter,"
                "parameter_value) VALUES("+self.ship+","+self.survey+","+
                self.activeHaul+","+sample_id+",'sample_display_name','"+nameType+"')")
        self.db.dbExec(sql)


    def setActiveSpecies(self, spc_name, subcat):

        # this is for programattically setting active species

        if subcat.lower() == 'none':
            spc_tag = spc_name
        else:
            spc_tag = spc_name + "_" + subcat

        #  set the current list item
        self.speciesList.setCurrentItem(spc_tag, Qt.MatchFlag.MatchExactly)

        #  get the sample type for this sample
        sampleId = self.speciesList.verticalHeaderItem(self.speciesList.currentRow()).text()
        parentSample = self.speciesList.item(self.speciesList.currentRow(), 1).text()

        sql = ("SELECT sample_type from " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                " AND sample_id=" + sampleId)
        query = self.db.dbQuery(sql)
        sampleType, = query.first()

        #  set the active sample attributes
        self.activeSpcSubcat = subcat
        self.activeSpcName = spc_name
        self.activeSampleKey = sampleId
        self.activeSampleType = sampleType
        self.activeSpcCode = self.speciesDict[self.activeSpcName]

        #  if EnablePresentSampleType is true, we alter UI depending on the
        #  sample type. This will disable some controls if the activeSampleType
        #  is "Present" since we cannot add baskets to a Present sample.
        if self.settings['EnablePresentSampleType'] in ['1', 'true', 'True']:
            self.setActiveSampleType(self.activeSampleType)

        # look for previous data on species
        self.updateTables()
        self.focus='speciesList'

        #  load the spp image
        self.loadSppImage()

        #  check if user has selected a mix
        if 'mix' in parentSample:
            self.inMixFlag = True
        else:
            self.inMixFlag = False

        #  load this sample's comments
        sql = ("SELECT comments FROM " + self.schema + ".samples WHERE (ship=" + self.ship +
                " and survey=" + self.survey + " and event_id=" + self.activeHaul +
                " and sample_id=" +self.activeSampleKey + ")")
        query = self.db.dbQuery(sql)
        sampleComments, = query.first()
        if sampleComments:
            self.comment = sampleComments


    def setActiveSampleType(self, sampleType):
        '''setActiveSampleType enables/disables basket creation and other
        UI elements based on the sample type. The "Present" sample type
        (if enabled) cannot have baskets assigned to it so this method
        will disable controls that allow adding baskets.
        '''

        if sampleType == 'Present':
            enabled = False

            #  clear basket table
            self.basketTable.clearContents()
            self.basketTable.setRowCount(0)

            headerItem = QTableWidgetItem("Weight (kg)")
            headerItem.setFont(self.headerFont)
            self.basketTable.setHorizontalHeaderItem(0, headerItem)
            headerItem = QTableWidgetItem("Count")
            headerItem.setFont(self.headerFont)
            self.basketTable.setHorizontalHeaderItem(1, headerItem)
            headerItem = QTableWidgetItem("Basket Type")
            headerItem.setFont(self.headerFont)
            self.basketTable.setHorizontalHeaderItem(2, headerItem)

            #  zero out summary values
            for i in range(len(self.basketTypes)):
                self.sumTable.setItem(i, 0, QTableWidgetItem('0'))
                self.sumTable.setItem(i, 1, QTableWidgetItem('0'))

        else:
            enabled = True

        self.basketTable.setEnabled(enabled)
        self.sumTable.setEnabled(enabled)
        self.manualBtn.setEnabled(enabled)
        self.editBtn.setEnabled(enabled)


    def checkSampleExists(self, sampID):
        '''
        checkSampleExists checks if the sample ID is still present in the database. Returns
        True if so, and False if not.
        '''
        sql = ("SELECT sample_id from " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                " AND sample_id=" + sampID)
        query = self.db.dbQuery(sql)
        sampleID, = query.first()
        if sampleID:
            return True
        else:
            return False


    def loadSppImage(self):
        '''loadSppImage loads the active species image in GUI form and is called
        when the species selection changes.
        '''

        # set up picture
        if self.activeSpcSubcat.lower() != 'none':
            imgName = self.activeSpcCode+"_"+self.activeSpcSubcat
        else:
            imgName = self.activeSpcCode

        #  currently, all fish images must be .jpg.
        imgName = imgName + ".jpg"

        #  load the fish pic, if available
        self.picLabel.clear()
        self.samplePicture = QImage()
        if self.samplePicture.load(self.settings['ImageDir'] + 'fishPics' + os.sep + imgName):
            pic = self.samplePicture.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio)
            self.picLabel.setPixmap(QPixmap.fromImage(pic))
        else:
            #  no pic available
            self.picLabel.clear()
            self.picLabel.setText("<Image Unavailable>")
            self.samplePicture = None
        self.picLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.picLabel.setAlignment(Qt.AlignmentFlag.AlignVCenter)


    def getActiveSpc(self):
        '''getActiveSpc is called when the user selects a species from the species list.

        '''
        self.basketTable.setEnabled(True)
        self.sumTable.setEnabled(True)
        self.commentBtn.setEnabled(True)

        # default setting for a species is no whole haul

        #  This method will also be triggered when a species is deleted so
        #  we need check if there are any species left and if not, bail since
        #  there are no spp to set active.
        if self.speciesList.currentRow() < 0:
            #  nothing in the list
            return

        #  check if the sample ID is still present in the database. It could have been
        #  deleted by a different user after it was added here.
        sampleId = self.speciesList.verticalHeaderItem(self.speciesList.currentRow()).text()
        sql = ("SELECT sample_id, sample_type from " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul+
                " AND sample_id=" + sampleId)
        query = self.db.dbQuery(sql)
        sampleId, sampleType = query.first()
        if not sampleId:
            #  this sample has been deleted - inform the user and remove from the list
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                        "The sample you selected has been deleted by someone else. " +
                        "You must re-add it if you need it.",'info')
            self.message.exec()
            #  refresh the species list
            self.reloadSamplesList()
            return

        #  get the species name
        speciesName = self.speciesList.item(self.speciesList.currentRow(), 0).text()
        parentSample = self.speciesList.item(self.speciesList.currentRow(), 1).text()

        if parentSample == 'SubMix':
            self.isCurrSubMix = True
        else:
            self.isCurrSubMix = False

        #  display the dialog for confirming active species - this was introduced
        #  after it was discovered that if you select one item, then roll your
        #  finger to a different item, the first item appears visually to be
        #  selected but the second item is the one that is identified by
        #  self.speciesList.currentRow() resulting in confusion. This dialog
        #  confirms the user's selection and brings to attention any discrepancy
        #  if the select and roll happens.
        if self.addspec_flag == True:
            self.freeze = True
            self.addspec.setMessage(self.errorIcons[1], self.errorSounds[2],
                    "Changing the Active Species to: \n \n"+ speciesName ,'info')
            self.addspec.exec()
            self.freeze = False

        #  check if this species has a subcategory and adjust the name.
        nameSplit = speciesName.split('-')
        if nameSplit[-1] in self.subcategories:
            self.activeSpcSubcat = nameSplit[-1]
            self.activeSpcName='-'.join(nameSplit[0:-1])
        else:
            self.activeSpcSubcat = 'None'
            self.activeSpcName = speciesName

        self.activeSampleKey = sampleId
        self.activeSampleType = sampleType
        self.activeSpcCode = self.speciesDict[str(self.activeSpcName)]
        self.activeFullName = speciesName

        #  if EnablePresentSampleType is true, we alter UI depending on the
        #  sample type. This will disable some controls if the activeSampleType
        #  is "Present" since we cannot add baskets to a Present sample.
        if self.settings['EnablePresentSampleType'] in ['1', 'true', 'True']:
            self.setActiveSampleType(self.activeSampleType)

        # look for previous data on 
        self.updateTables()
        self.focus='speciesList'

        #  load the spp image
        self.loadSppImage()

        #  check if we're working with a Mix
        if 'mix' in parentSample:
            self.inMixFlag = True
        else:
            self.inMixFlag = False

        sql = ("SELECT comments FROM " + self.schema + ".samples WHERE (ship=" + self.ship +
                " and survey=" + self.survey + " and event_id=" +self.activeHaul +
                " and sample_id=" + self.activeSampleKey + ")")
        query = self.db.dbQuery(sql)
        sampleComments, = query.first()
        if sampleComments:
            self.comment = sampleComments


    def getManual(self):
        '''getManual is called when the user clicks the manual weight button. It
        makes sure a species sample is selected and presents a dialog to enter
        the weight.
        '''
        # is a species selected
        if self.activeSpcName is None:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2], self.firstName +
                    ", please select a species.",'info')
            self.message.exec()
            return

        #  display the numpad dialog for manual weight entry
        self.numpad.msgLabel.setText("Enter the Weight (kg)")
        if not self.numpad.exec():
            return

        #  ensure that the value is numeric
        try:
            val = float(self.numpad.value)
        except:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "You entered a non-numeric value!?! Please try again.", 'info')
            self.message.exec()
            return

        #  check that we didn't get a 0 weight
        if (val <= 0):
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "You have entered 0 (zero) for the basket weight which is not " +
                    "allowed. If your sample is too small to register " +
                    "on the scale, you should enter 0.001", 'info')
            self.message.exec()
            return

        #  get the manual weight using the numpad dialog
        self.currentBasketWt = val

        #  note that this is a manual entry
        self.manualFlag = True
        self.activeDeviceId = self.manualDevice

        #  do some basic checks, get the basket type, then insert into the database
        self.updateBasket()


    @pyqtSlot(str, str, object)
    def getAuto(self, device_name, val, err):
        '''getAuto is called when a device sends data

        '''
        #  check if we're "frozen" which means either adding spp or in the middle of
        #  weighing another basket. When frozen we ignore device input
        if self.freeze:
            return

        #  check if this is a device we're interested in, if not, ignore this data.
        #  first check if there are any catch measurements
        if 'catch' not in self.deviceData[device_name]['measurements']:
            return

        #  then make sure this is a basket_weight measurement which is the only
        #  measurement that Catch cares about
        if 'basket_weight' not in self.deviceData[device_name]['measurements']['catch']:
            return

        # check if a species is selected
        if self.activeSpcName == None:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2], self.firstName +
                    ", please select a species.",'info')
            self.message.exec()
            return

        #  check if the current sample type is "Present" and ignore input if so.
        #  we don't allow baskets to be assigned to Present samples.
        if self.activeSampleType in ['Present', None]:
            return

        #  ensure that the value is numeric - noise on the data lines, poor connections,
        #  or bad power can result in garbled data.
        try:
            val = float(val)
        except:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "The scale sent a non-numeric value!?! Please try again.", 'info')
            self.message.exec()
            return

        #  check that we didn't get a 0 weight
        if (val <= 0):
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "The scale sent a weight of 0 (zero) which is not allowed. " +
                    "If your sample is too small to register " +
                    "on the scale, you should manually enter 0.001", 'info')
            self.message.exec()
            return

        #  set the basket value
        self.currentBasketWt = val

        #  note that this is an "auto" (non manual) entry
        self.manualFlag = False
        self.activeDeviceId = self.deviceData[device_name]['id']

        #  play the sound associated with this device if provided
        if self.deviceData[device_name]['soundeffect']:
            self.deviceData[device_name]['soundeffect'].play()

        #  do some basic checks, get the basket type, then insert into the database
        self.updateBasket()


    def getWeightValidation(self):
        '''getWeightValidation performs some basic validations on the
        basket weight measurement.

        '''
        #  check basket weight against the max allowed basket weight
        if float(self.currentBasketWt) > float(self.settings['MaxBasketWt']):
            self.message.setMessage(self.errorIcons[1],self.errorSounds[1], self.firstName +
                    ", this Basket exceeds the maximum basket weight of " +
                    self.settings['MaxBasketWt']+".  Does this bother you?", 'choice')
            if self.message.exec():
                #  user has rejected the measurement
                return False

        #  if this is a mix, check for mix subsample weight and stuff
        if self.inMixFlag:
            #  yes, this is a mix

            (mixSubWeight, mixSpeciesWeight) = self.mixValidation(self.activeSampleKey, self.activeSpcCode)

            # validation for mix sub weight - can't have more weight in sub part of mix than in mix subsample
            if (mixSubWeight * (1 + float(self.settings['MaxMixDev']) / 100) <
                    (mixSpeciesWeight + float(self.currentBasketWt))):
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                        self.firstName + ", it appears that the total weight of species" +
                        " in the mix exceeds the mix subsample by more than " +
                        self.settings['MaxMixDev']+" % - this is usually bad. " +
                        "Do you want to fix this now?",'info')
                if self.message.exec():
                    #  user has rejected the measurement
                    return False

        #  weight passes basic validation
        return True


    def getBasketType(self):
        '''getBasketType is called after a basket weight is collected and
        presents the user with the basket type dialog where they choose if
        the basket is a measure, count, or toss basket.

        '''
        # turn off count sample type when sample is a submix
        if self.isCurrSubMix:
            self.validList[self.basketTypes.index('Count')] = 1
        else:
            self.validList[self.basketTypes.index('Count')] = 0

        #  display the basket type dialog
        self.typeDlg.buttonSetup(self.validList, self.basketTypes)
        if self.typeDlg.exec():
            self.basketType = self.typeDlg.basketType
            self.count = self.typeDlg.count
        else:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2],
                    "You didn't choose a Basket type. This basket weight will be ignored.",'info')
            self.message.exec()
            self.basketType = None


    def updateBasket(self):
        '''updateBasket is called after the user sends a weight with the scale
        or enters the weight manually. It performs basic validation, gets the basket
        type, and then inserts the data into the database.

        '''

        #  set the "freeze" flag so we ignore input from the scale while we're finishing this basket
        self.freeze = True

        #  run the weight validation
        ok = self.getWeightValidation()
        if not ok:
            #  this weight is not valid
            self.freeze = False
            return

        #  get the sample type
        self.getBasketType()
        if self.basketType == None:
            #  user cancelled sample type selection
            self.freeze = False
            return

        #  write basket record for this basket
        if self.count == None:
            sql = ("INSERT INTO " + self.schema + ".baskets (ship,survey,event_id,sample_id,basket_type," +
                    "weight, device_id) VALUES ("+ self.ship+", "+self.survey+","+
                    self.activeHaul+","+self.activeSampleKey+",'"+self.basketType+"',"
                    +str(self.currentBasketWt)+","+self.activeDeviceId+")")
        else:
            sql = ("INSERT INTO " + self.schema + ".baskets (ship,survey,event_id,sample_id,basket_type,count," +
                    "weight,device_id) VALUES ("+ self.ship+", "+self.survey+","+self.activeHaul +
                    ","+self.activeSampleKey+",'"+self.basketType+"',"+self.count+"," +
                    str(self.currentBasketWt)+","+self.activeDeviceId+")")
        self.db.dbExec(sql)

        # update the GUI
        self.updateTables()

        #  we're done with this basket - unfreeze
        self.freeze = False


    def updateTables(self):
        '''updateTables updates the basket and samples tables. It is called
        during initial form setup and also when a basket is added, modified, or deleted.
        '''

        #  create some dicts to handle basket totals by sample type. We accumulate
        #  totals for the summary table below when populating the baskets table
        basketTotalWeight = {}
        basketTotalCount = {}
        sumTableRows = {}
        for i, bType in enumerate(self.basketTypes):
            basketTotalWeight[bType] = 0
            basketTotalCount[bType] = 0
            sumTableRows[bType] = i

        #  update the basket table - first, clear the contents
        self.basketTable.clearContents()
        self.basketTable.setRowCount(0)
        basketCount = 0

        #  set up the table headers
        headerItem = QTableWidgetItem("Weight (kg)")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(0, headerItem)
        headerItem = QTableWidgetItem("Count")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(1, headerItem)
        headerItem = QTableWidgetItem("Basket Type")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(2, headerItem)

        #  query the baskets for this sample ID and populate the baskets table
        sql = ("SELECT basket_id, weight, count, basket_type " +
                "FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+self.activeHaul+" AND sample_id ="+
                self.activeSampleKey+" ORDER BY basket_id")
        query = self.db.dbQuery(sql)
        for basketId, basketWeight, count, basketType in query:
            #  convert the weight to float and accumulate totals
            try:
                basketWeight = float(basketWeight)
                basketTotalWeight[basketType] += basketWeight
                basketTotalCount[basketType] += 1
            except:
                basketWeight = 0
                basketTotalWeight[basketType] += 0
                basketTotalCount[basketType] += 1

            #  add this basket to the table
            basketWeight = str(round(basketWeight, self.basketPrecision))
            self.basketTable.insertRow(basketCount)
            headerItem = QTableWidgetItem(basketId)
            headerItem.setFont(self.headerFont)
            self.basketTable.setVerticalHeaderItem(basketCount, headerItem)
            self.basketTable.setItem(basketCount, 0, QTableWidgetItem(basketWeight))
            self.basketTable.setItem(basketCount, 1, QTableWidgetItem(count))
            self.basketTable.setItem(basketCount, 2, QTableWidgetItem(basketType))

            if 'nwfsc' in self.settings['OrganizationName'].lower() and basketType == 'Measure':
                self.basketTable.item(basketCount, 2).setBackground(QColor(127, 255, 212))
            basketCount += 1

        #  resize columns and scroll to bottom
        self.basketTable.resizeColumnsToContents()
        self.basketTable.scrollToBottom()

        #  now update the basket summary table
        totalSampleWeight = 0
        for basketType in self.basketTypes:
            count = str(basketTotalCount[basketType])
            weight = str(round(basketTotalWeight[basketType], self.basketPrecision))
            totalSampleWeight += basketTotalWeight[basketType]
            self.sumTable.setItem(sumTableRows[basketType], 0, QTableWidgetItem(count))
            self.sumTable.setItem(sumTableRows[basketType], 1, QTableWidgetItem(weight))

        #  lastly, update the total sample weight in the samples table
        totalSampleWeight = str(round(totalSampleWeight, self.basketPrecision))
        item = self.speciesList.findItems(self.activeFullName,  Qt.MatchFlag.MatchExactly)
        if item:
            self.speciesList.setItem(item[0].row(), 3, QTableWidgetItem(totalSampleWeight))


    def getSpeciesFocus(self):

        self.focus = 'speciesList'


    def getBasketRow(self):
        '''getBasketRow returns a list of the basket "measurements"
        [id, weight, count, type] for the currently selected row.
        I (believe) it returns an empty list if nothing is selected.
        '''
        self.focus = 'basketList'

        self.selRecord = []

        selectedRow = self.basketTable.currentRow()
        if selectedRow >= 0:
            self.selRecord.append(self.basketTable.verticalHeaderItem(selectedRow).text())
            self.selRecord.append(self.basketTable.item(selectedRow,0).text())
            self.selRecord.append(self.basketTable.item(selectedRow,1).text())
            self.selRecord.append(self.basketTable.item(selectedRow,2).text())


    def deleteSpecimen(self):
        """
        deleteSpecimen is called when the user wants to delete a basket or sample and
        specimen exist in the database. It asks them if they are sure, and then if so,
        it will delete all measurements related to the specimen and the related
        entries in the specimen table. It also deletes any associated data in the
        length_histogram and catch_summary tables.
        """

        #  double check that they want to delete the specimen
        self.message.setMessage(self.errorIcons[3],self.errorSounds[1],
                "Are you REALLY sure you want to delete these specimen?", 'choice')
        if self.message.exec():
            #  they want to do it - delete the measurements
            sql = ("DELETE FROM " + self.schema + ".measurements WHERE ship=" + self.ship +
                    " AND survey = " + self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+ self.activeSampleKey)
            self.db.dbExec(sql)

            #  delete the specimen records
            sql = ("DELETE FROM " + self.schema + ".specimen WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.db.dbExec(sql)

            #  try to delete from the catch summary and length histogram tables - these will be
            #  populated at this point if a user has come back into CLAMS to edit a past haul
            sql = ("DELETE FROM " + self.schema + ".catch_summary WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.db.dbExec(sql)
            sql = ("DELETE FROM " + self.schema + ".length_histogram WHERE ship=" + self.ship +
                    " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id ="+self.activeSampleKey)
            self.db.dbExec(sql)


            #  set the return value to true since we deleted the specimen
            deleted = True

        else:
            #  user changed their mind
            deleted = False

        return deleted


    def goDelete(self):
        """
        goDelete is called when a user clicks the delete button and it deletes either baskets or
        a sample depending on what widget has focus (basket list or sample list. This method
        will also delete all specimen and measurements that are associated with a sample or basket.
        """

        #  just return if nothing is selected
        if self.activeSampleKey is None:
            #  no species selected - show error dialog
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                    "Please pick a sample to print a label for, " +
                                    self.firstName + ".", 'info')
            self.message.exec()
            return

        #  initialize some variables
        hasSpecimen = False
        nOther = 0
        nMeasure = 0

        #  first check if we have specimen - this process a bit more complicated with specimen
        sql = ("SELECT specimen_id FROM " + self.schema + ".specimen WHERE ship="+self.ship+" AND survey="+
                self.survey+" AND event_id="+self.activeHaul+" AND sample_id ="+self.activeSampleKey)
        query = self.db.dbQuery(sql)
        specimenID, = query.first()
        if specimenID:
            # the active species has specimen data
            hasSpecimen = True

        #  determine type and count of baskets for this sample. We need to know this because if
        #  the user is trying to delete the last "measure" basket and there are samples, the
        #  samples have to be deleted too.
        sql = ("SELECT basket_type FROM " + self.schema + ".baskets WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "
                +self.activeSampleKey)
        query = self.db.dbQuery(sql)
        for basketType, in query:
            if basketType.lower() == 'measure':
                #  this is a measure basket
                nMeasure = nMeasure + 1
            else:
                #  this is a count, preserve, or toss basket
                nOther = nOther + 1

        #  now move ahead based on where the focus is in the GUI. If a basket is selected, we
        #  attempt to delete that single basket. If a sample is selected, we attempt to delete the
        #  whole sample.

        #  if the focus is on the basket list, delete the selected basket
        if self.focus == 'basketList':

            #  if there is only 1 measure basket left and there are specimen, check if the selected
            #  basket is that lone measure basket
            if nMeasure == 1 and hasSpecimen:
                sql = ("SELECT basket_type FROM " + self.schema + ".baskets WHERE ship="+self.ship+
                        " AND survey="+self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                        self.selRecord[0])
                query = self.db.dbQuery(sql)
                basketType, = query.first()
                if basketType.lower() == 'measure':
                    #  this is the last measure basket and specimen exist
                    self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                            "This is the last basket of type 'Measure' for this species and specimen " +
                            "exist for this species. If you delete this basket, the specimen will be " +
                            "deleted as well. Are you SURE you want to permanently delete this basket " +
                            "AND all of the specimen collected for this species, "+
                            self.firstName+"?", 'choice')
                    if self.message.exec():
                        #  user chose to delete the specimen (we'll ask one more time)
                        ok = self.deleteSpecimen()

                        if not ok:
                            #  user changed their mind when we asked if they're sure - we're done here
                            return
                    else:
                        #  user changed their mind - we're done here
                        return

                #  Either this basket wasn't a measure type or it was and we deleted all of the
                #  associated specimen. Now we delete the basket
                sql = ("DELETE FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                        self.selRecord[0])
                self.db.dbExec(sql)

            else:
                #  this is not the last measure basket so we just delete the basket regardless of
                #  type and assume the user knows what they are doing

                self.message.setMessage(self.errorIcons[3],self.errorSounds[1], "Are you sure you want " +
                        "to permanently delete this basket, "+self.firstName+"?", 'choice')
                if self.message.exec():
                    #  user chose to delete
                    sql = ("DELETE FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+
                            self.survey+" AND event_id="+self.activeHaul+" AND basket_id="+
                            self.selRecord[0])
                    self.db.dbExec(sql)

        #  if the focus is on the sample list so we're going to delete the entire sample
        elif self.focus == 'speciesList':

            #  make sure the user really wants to do the
            if hasSpecimen:
                #  if there are specimen associated with this sample, we present a different dialog
                #  and then have to first delete the specimen
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "There are "+
                        str(nMeasure+nOther)+" basket weights for this species AND you have " +
                        "collected specimen data too. Are SURE you want permanatly delete this "
                        "species and ALL of these baskets and ALL of your specimen data?",'choice')
                if self.message.exec():
                    #  user chose to delete the everything from this sample so first delete the specimen
                    ok = self.deleteSpecimen()

                    if not ok:
                        #  user changed their mind when we asked if they're sure - we're done here
                        return
            else:
                #  no specimen yet so we present a differently worded dialog. Only present a dialog
                #  if there are baskets though. Otherwise we just delete the sample.
                if nMeasure+nOther > 0:
                    self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "There are "+
                            str(nMeasure+nOther)+" basket weights for this species. " +
                            "Are sure you want to permanantly delete ALL of them?", 'choice')
                    if not self.message.exec():
                        #  user changed their mind
                        return

                    # kill the baskets
                    sql = ("DELETE FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+
                            self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                            self.activeSampleKey)
                    self.db.dbExec(sql)

                #  try to delete from the catch summary and length histogram tables - these will be
                #  populated at this point if a user has come back into CLAMS to edit a past haul
                #  (depending on the execution path this might have already been done but it doesn't
                #  hurt to try again here.)
                sql = ("DELETE FROM " + self.schema + ".catch_summary WHERE ship=" + self.ship +
                        " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                        " AND sample_id ="+self.activeSampleKey)
                self.db.dbExec(sql)
                sql = ("DELETE FROM " + self.schema + ".length_histogram WHERE ship=" + self.ship +
                        " AND survey = " +self.survey + " AND event_id=" + self.activeHaul +
                        " AND sample_id ="+self.activeSampleKey)
                self.db.dbExec(sql)

                # delete the sample_data
                sql = ("DELETE FROM " + self.schema + ".sample_data WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                        self.activeSampleKey)
                self.db.dbExec(sql)

                #  and then delete the sample
                sql = ("DELETE FROM " + self.schema + ".samples WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND sample_id = "+
                        self.activeSampleKey)
                self.db.dbExec(sql)
                self.activeSpcName = None

                sql = ("DELETE FROM " + self.schema + ".samples WHERE ship="+self.ship+" AND survey="+
                        self.survey+" AND event_id="+self.activeHaul+" AND sample_type='SubMix' AND 0=" +
                        "(SELECT COUNT(*) FROM " + self.schema + ".samples WHERE parent_sample=(SELECT sample_id from "+
                        self.schema+ ".samples WHERE ship="+self.ship+" AND survey="+self.survey+" AND "+
                        "event_id="+self.activeHaul+" AND sample_type='SubMix'))")
                self.db.dbExec(sql)

            #  refresh the species list
            self.reloadSamplesList()

        #  update the tables
        self.updateTables()


    def transferSample(self):
        '''transferSample is called when the "Transfer Weights" button is pressed. It
        presents the transfer dialog which allows the user to transfer weight from one
        sample to another. An example of use would be when a basket is weighed, then
        a different species is found in the basket, the weight of that other species
        would be transferred to the correct sample.

        The "transfer" is accomplished by creating two new basket records. The first
        removes the weight (and count, if applicable) from the source sample by creating
        a record with negative weights (and counts, if applicable) and then it creates
        a basket record in the destination sample with positive weights and counts.
        '''

        #  pause all processing while the transfer dialog is displayed.
        self.freeze = True

        #  display the transfer dialog
        transDlg = transferdlg.TransferDlg(self)
        if not transDlg.exec():
            #  user cancelled action
            self.freeze = False
            return

        # write basket records - first write the "from" record
        if transDlg.fromType=='Count':
            count=str(-transDlg.transCount)
        else:
            count='NULL'
        sql = ("INSERT INTO " + self.schema + ".baskets (ship, survey, event_id, sample_id, basket_type, count," +
                "weight, device_id) VALUES ("+ self.ship+", "+self.survey+","+self.activeHaul+
                ","+transDlg.fromSampleKey+",'"+transDlg.fromType+"',"+count+","+
                str(-transDlg.transWeight)+"," + transDlg.transDevice+")")
        self.db.dbExec(sql)

        #  then write the "to" record
        if transDlg.toType == 'Count':
            count = str(transDlg.transCount)
        else:
            count='NULL'

        sql = ("INSERT INTO " + self.schema + ".baskets (ship, survey, event_id, sample_id, basket_type, count," +
                "weight, device_id) VALUES ("+ self.ship+", "+self.survey+","+self.activeHaul+
                ","+transDlg.toSampleKey+",'"+transDlg.toType+"',"+count+","+
                str(transDlg.transWeight)+","+ transDlg.transDevice+")")
        self.db.dbExec(sql)

        # update basket tables
        self.activeSampleKey = transDlg.toSampleKey
        self.updateTables()

        self.freeze=False

    def editTable(self):
        '''editTable is called when the "Edit" button is pressed. This will present
        the Edit Basket dialog which allows the user to edit a specific basket.
        '''
        self.freeze=True

        # turn off count sample type for mixes
        if self.activeSampleType and 'mix' in self.activeSampleType.lower():
            self.validList[self.basketTypes.index('Count')] = 0
        else:
            self.validList[self.basketTypes.index('Count')] = 1

        #  set up the basket type dialog button states
        #  set getCount to False because we will handle the count
        #  number within the basketeditdlg
        self.typeDlg.buttonSetup(self.validList, self.basketTypes,
                getCount=False)

        #  get the current basket selection
        currentRow = self.basketTable.currentRow()

        #  check if something is selected
        if currentRow < 0:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[1],
                    "Please select a basket to edit " + self.firstName,'info')
            self.message.exec()
            self.freeze = False
            return

        #  build a list with the nasket id, weight, count, and type
        #  first get the ID
        selRecord = [self.basketTable.verticalHeaderItem(currentRow).text()]

        #  then append the weight, count, and type to our list
        for item in self.basketTable.selectedItems():
            selRecord.append(item.text())

        #  present the edit dialog
        header = ['Basket ID', 'Weight', 'Count', 'Basket Type' ]
        editDlg = basketeditdlg.BasketEditDlg(header, selRecord, self)
        editDlg.exec()
        if not editDlg.okFlag:
            #  user cancelled action
            return

        # update database - first check if this is a non-count basket type
        if editDlg.count in ['-', '', 'NULL', 'null']:
            #  this is not a count basket - set count to NULL
            editDlg.count = 'NULL'

        # update basket table
        sql = ("UPDATE baskets SET basket_type='"+editDlg.basketType+"', count = "+
                editDlg.count+", weight = "+editDlg.weight+"  WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND sample_id = "+self.activeSampleKey+" AND basket_id = "+
                self.selRecord[0])
        self.db.dbExec(sql)

        self.freeze=False

        self.updateTables()

    def exitValidation(self):
        '''exitValidation checks for mixes and if found will check if the
        sum of the mix baskets is close enough to the mix subsample weight and
        alert the user if not. It also checks to make sure each sample has
        at least one basket and if not, informs the user.
        '''

        self.returnFlag=False

# --- BEGIN NEW ANIMALIA/PRESENT VALIDATION ---
        # Check if there is any sample with sample_type = 'Present'
        sql = ("SELECT COUNT(sample_id) FROM " + self.schema + ".samples WHERE ship=" + self.ship +
               " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
               " AND partition='" + self.activePartition + "' AND sample_type='Present'")
        query = self.db.dbQuery(sql)
        presentCount, = query.first()
        
        if presentCount and int(presentCount) > 0:
            # We have a 'Present' sample, now check if Animalia (202423) exists in this partition
            sql = ("SELECT COUNT(sample_id) FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                   " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                   " AND partition='" + self.activePartition + "' AND species_code=202423 AND sample_type='Species'")
            query = self.db.dbQuery(sql)
            animaliaCount, = query.first()
            
            if not animaliaCount or int(animaliaCount) == 0:
                self.message.setMessage(self.errorIcons[2], self.errorSounds[1],
                        self.firstName + ", there is a sample marked as 'Present' but no 'Animalia' species was found. " +
                        "Please add the Animalia species and weigh group before continuing.", 'info')
                self.message.exec()
                self.returnFlag = True
                return
        # --- END NEW ANIMALIA/PRESENT VALIDATION ---

        #  check if all of the samples have at least one basket. First get the samples
        sql = ("SELECT species.common_name, samples.sample_id, samples.species_code, " +
                "samples.subcategory FROM " + self.schema + ".samples, " + self.schema + ".species WHERE " +
                "species.species_code=samples.species_code AND LOWER(samples.sample_type)" +
                "='species' AND samples.ship=" + self.ship + " AND samples.survey=" +
                self.survey + " AND samples.event_id=" + self.activeHaul +
                " AND samples.partition='" + self.activePartition + "'")
        sampleQuery = self.db.dbQuery(sql)

        #  loop thru each sample and check if it has at least one basket
        for commonName, sampleId, spCode, subcat in sampleQuery:
            sql = ("SELECT COUNT(basket_id) FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+
                    self.survey+" AND event_id = "+self.activeHaul+" AND sample_id = "+
                    sampleId)
            basketQuery = self.db.dbQuery(sql)
            numBaskets, = basketQuery.first()

            if int(numBaskets) == 0:
                # no baskets for this species
                if subcat.lower() != 'none':
                    spcName = commonName + " " + subcat
                else:
                    spcName = commonName
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                        self.firstName + ", There are are no basket weights for " +
                        spcName + ". Does this bother you?", 'choice')
                if self.message.exec():
                    self.returnFlag = True
                    return

        #  check for any mixes in this partition
        sql = ("SELECT sample_id, sample_type, species_code from " + self.schema + ".samples WHERE ship=" +
                self.ship + " AND survey=" + self.survey+" AND event_id = " +
                self.activeHaul+" AND partition='" + self.activePartition +
                "' AND LOWER(sample_type) LIKE LOWER('%mix%')")
        query = self.db.dbQuery(sql)
        for sampleId, sampleType, speciesCode in query:

            #  mix validation
            (mixSubWeight, mixSpeciesWeight) = self.mixValidation(sampleId, self.activeSpcCode)

            #  check the mix parts more or less make up the weight of the total
            dev = (mixSubWeight - mixSpeciesWeight) / mixSubWeight * 100.

            #  check that the deviation is below the allowed value
            if (abs(dev) > float(self.settings['MaxMixDev'])):
                #  it is not, issue a warning and ask user what they want to do
                self.message.setMessage(self.errorIcons[2], self.errorSounds[1], self.firstName+
                        ", the weight of the mix components is more or less than "+ str(dev) +
                        " % of the mix subsample weight for  "+self.mixtureNames[speciesCode]+
                        ". Does this bother you? ", 'choice')
                if self.message.exec():
                    #  user is bothered by this - set the failed validation flag
                    self.returnFlag = True
                else:
                    #  user doesn't care, make note of this and move on
                    sql = ("INSERT INTO " + self.schema + ".overrides (scientist, record_id, " +
                            "table_name, description, ship, survey, event_id) SELECT '" + 
                            self.scientist + "'," + sampleId + ",'sample', 'mix components are "+str(dev)+
                            " % less than the mix subsample weight', "+self.ship+","+self.survey+","+
                            self.activeHaul+" WHERE NOT EXISTS (SELECT 1 FROM " + self.schema + 
                            ".overrides WHERE record_id=" + sampleId + " AND table_name='sample' AND ship="+
                            self.ship+" AND survey="+self.survey+" AND event_id="+self.activeHaul+")")
                    self.db.dbExec(sql)

    def mixValidation(self, sampleId, speciesCode):
        #  get the SubMix sample id for this partition
        subMixCode = "3"
        animaliaCode = "202423"

        sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                " AND species_code=" + subMixCode)
        query = self.db.dbQuery(sql)
        submix1Id, = query.first()

        if submix1Id is not None:
            #  get the sum of Measure basket weights for Animalia species with SubMix1 as parent
            sql = ("SELECT SUM(b.weight) FROM " + self.schema + ".baskets b, " +
                    self.schema + ".samples s WHERE b.sample_id=s.sample_id AND " +
                    "b.ship=s.ship AND b.survey=s.survey AND b.event_id=s.event_id AND " +
                    "s.ship=" + self.ship + " AND s.survey=" + self.survey +
                    " AND s.event_id=" + self.activeHaul + " AND b.basket_type='Measure' AND " +
                    "s.species_code=" + animaliaCode)
            query = self.db.dbQuery(sql)
            mixSubWeight, = query.first()
            mixSubWeight = float(mixSubWeight) if mixSubWeight else 0.0

            #  get the sum of Count basket weights for species samples with SubMix1 as parent
            sql = ("SELECT SUM(b.weight) FROM " + self.schema + ".baskets b, " +
                    self.schema + ".samples s WHERE b.sample_id=s.sample_id AND " +
                    "b.ship=s.ship AND b.survey=s.survey AND b.event_id=s.event_id " +
                    "AND s.ship=" + self.ship + " AND s.survey=" + self.survey +
                    " AND s.event_id=" + self.activeHaul + " AND s.parent_sample=" +
                    submix1Id + " AND b.basket_type='Count'")
            query = self.db.dbQuery(sql)
            countBasketWeight, = query.first()
            mixSpeciesWeight = float(countBasketWeight) if countBasketWeight else 0.0
        
            return mixSubWeight, mixSpeciesWeight

    def reloadSamplesList(self):
        '''reloadSamplesList updates the Samples table

        '''

        #  disconnect the selection changed signal so we don't
        #  trigger it when the list is cleared.
        self.speciesList.itemSelectionChanged.disconnect()

        # clear out the existing entries
        self.speciesList.clearContents()
        self.speciesList.setRowCount(0)
        self.speciesDict = {}
        nSamples = 0

        #  set the column headers
        headerItem = QTableWidgetItem("Species")
        headerItem.setFont(self.headerFont)
        self.speciesList.setHorizontalHeaderItem(0, headerItem)
        headerItem = QTableWidgetItem("Parent")
        headerItem.setFont(self.headerFont)
        self.speciesList.setHorizontalHeaderItem(1, headerItem)
        headerItem = QTableWidgetItem("Type")
        headerItem.setFont(self.headerFont)
        self.speciesList.setHorizontalHeaderItem(2, headerItem)
        headerItem = QTableWidgetItem("Weight (kg)")
        headerItem.setFont(self.headerFont)
        self.speciesList.setHorizontalHeaderItem(3, headerItem)

        #  loop thru the samples and add them to the species list table
        # todo: AB - this would be nice if it could be ordered by the parent and then the sample_id
        sql = ("SELECT samples.sample_id, species.common_name, species.scientific_name," +
                "species.species_code, samples.parent_sample, samples.subcategory, samples.sample_type"+
                " FROM " + self.schema + ".samples, " + self.schema + ".species WHERE samples.species_code=species.species_code AND " +
                "samples.ship="+self.ship+" AND samples.survey=" + self.survey +
                " AND samples.event_id="+self.activeHaul+" AND samples.partition='"+
                self.activePartition+"' AND samples.species_code NOT IN " +
                "(1,3,100000,100001) ORDER BY samples.sample_id ASC")
        sampleQuery = self.db.dbQuery(sql)
        for sampleId, commonName, sciName, spCode, parentId, subcat, sample_type in sampleQuery:
            #  get the namespace - if the species is added using common name,
            #  then we display the common name. If added with the sci name,
            #  we display the sci name.
            sql = ("SELECT parameter_value FROM " + self.schema + ".sample_data WHERE sample_parameter=" +
                    "'sample_display_name' AND ship=" + self.ship + " AND survey=" +
                    self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id="+ sampleId)
            namespaceQuery = self.db.dbQuery(sql)
            namespace, = namespaceQuery.first()

            #  if there is a sample_display_name set, use it to
            #  set the species name
            if namespace:
                #  there is a sample_display_name entry
                if namespace.lower() == 'scientific':
                    #  display the scientific name
                    species = sciName
                else:
                    #  display the common name
                    species = commonName
            else:
                #  by default we display the common name
                species = commonName

            #  if applicable, add the subcategory to the name
            if subcat is None:
                name = species
            elif subcat.lower() != 'none':
                name = species+'-'+ subcat
            else:
                name = species

            #  get the parent sample name
            myParent = ''
            if parentId is not None:
                sql = ("SELECT b.common_name FROM " + self.schema + ".samples a JOIN " + self.schema + ".species b ON " +
                        "a.species_code=b.species_code WHERE a.ship=" + self.ship +
                        " AND a.survey=" + self.survey+" AND a.event_id=" +
                        self.activeHaul + " AND a.sample_id=" + parentId)
                parentQuery = self.db.dbQuery(sql)
                myParent, = parentQuery.first()

            #  get the total basket weights for this sample
            sql = ("SELECT SUM(weight) FROM " + self.schema + ".baskets WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                    " AND sample_id="+ sampleId + " GROUP BY sample_id")
            wtQuery = self.db.dbQuery(sql)
            sampleWeight, = wtQuery.first()
            try:
                sampleWeight = float(sampleWeight)
                sampleWeight = round(sampleWeight, self.basketPrecision)
            except:
                sampleWeight = 0

            #  add this sample to the table
            self.speciesList.insertRow(nSamples)
            headerItem = QTableWidgetItem(sampleId)
            headerItem.setFont(self.headerFont)
            self.speciesList.setVerticalHeaderItem(nSamples,headerItem)
            self.speciesList.setItem(nSamples, 0, QTableWidgetItem(name))
            self.speciesList.setItem(nSamples, 1, QTableWidgetItem(myParent))
            self.speciesList.setItem(nSamples, 2, QTableWidgetItem(sample_type))
            #  display the sample weight total based on type
            if sample_type in ['Present']:
                sampleWeight = ''
            else:
                sampleWeight = str(sampleWeight)
            self.speciesList.setItem(nSamples, 3, QTableWidgetItem(sampleWeight))

            # change the background color if the species is in the protocol map
            if 'DisplayProtoSp' in self.settings:
                if self.settings['DisplayProtoSp'] == 'True':
                    # check if species is in the protocol_map table as Active
                    proto_sql = ("SELECT protocol_name, species_code FROM " +
                                 self.schema + ".protocol_map WHERE species_code=" + spCode)
                    proto_query = self.db.dbQuery(proto_sql)
                    proto_list = list(proto_query)
                    sp_protos = ['BagNTag']
                    for protocol, sp_code in proto_list:
                        # for protocols in group collection, highlight them in yellow
                        if (protocol in ['Gleiber_02', 'Field_01'] and len(proto_list) == 1):
                            self.speciesList.item(nSamples, 0).setBackground(QColor(255, 222, 128))
                        else:
                            sp_protos.append(protocol)
                            self.speciesList.item(nSamples, 0).setBackground(QColor(127, 255, 212))
                    self.speciesProtos[spCode] = sp_protos

            nSamples += 1
            self.speciesDict.update({species:spCode})
        self.speciesList.resizeColumnsToContents()
        self.picLabel.clear()

        #  reconnect the selection changed signal now that we're done changing the list
        self.speciesList.itemSelectionChanged.connect(self.getActiveSpc)
        self.speciesList.scrollToBottom()


    def printLabel(self):
        '''
            printLabel prints a label for whole fish samples
        '''

        #  ensure that a species is selcted
        if (self.activeSpcName == None):
            #  no species selected - show error dialog
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                    "Please pick a sample to print a label for, " +
                    self.firstName + ".", 'info')
            self.message.exec()
            return
        else:
            if 'nwfsc' in self.settings['OrganizationName'].lower() \
                    or 'swfsc' in self.settings['OrganizationName'].lower():
                # get the project to apply the sample to for the species
                selected_project = project.FEATProjectDlg(self)
                if selected_project.result() == 1:
                    self.printer.print_label(selected_project.project_name, self.activeSpcName, self.activeSpcCode,
                                             self.activeHaul, selected_project.code, self.activeSampleKey)
            else:
                #  get species code
                speciesCode = self.activeSpcCode=self.speciesDict[self.activeSpcName]

                #  get the EQ time
                sql = ("SELECT event_data.PARAMETER_VALUE FROM " + self.schema + ".event_data  WHERE " +
                    "(event_data.SHIP="+self.ship+") AND (event_data.SURVEY="+self.survey+
                    ") AND (event_data.event_id="+self.activeHaul+") AND "+
                    "(event_data.PARTITION='"+self.activePartition+"') AND "+
                    "(event_data.event_parameter='EQ')")
                query = self.db.dbQuery(sql)
                eqTime, = query.first()
                if eqTime:
                    EQDate = eqTime.split(' ')[0]
                else:
                    EQDate = ''

                #  ask how many fish are being frozen
                self.numpad.msgLabel.setText("How many " + self.activeSpcName + " are you freezing?")
                if not self.numpad.exec():
                    return
                number = self.numpad.value

                data={'title':self.settings['OrganizationName'],
                      'ship':self.ship,
                      'survey':self.survey,
                      'haul':self.activeHaul,
                      'species_code':speciesCode,
                      'common_name':self.activeSpcName,
                      'date':EQDate,
                      'sample_type':'whole fish',
                      'count':number,
                      'scientist':self.scientist
                     }

                #  print the label
                self.printer.printSpecialSampleLabel2(data)

                # print sound
                if self.printSound:
                    self.printSound.play()

    def getComment(self):
        '''getComment is called when the user clicks the "Comment"
        button and displays the keybaord dialog with the existing comment
        (if any) alowing the user to add to or edit the selected sample's
        comment.
        '''

        #  display the keyboard dialog with the comment text
        keyDialog = keypad.KeyPad(self.comment, self)
        keyDialog.exec()

        #  if the user clicked ok, get the new comment and update the db
        if keyDialog.okFlag:
            self.comment = keyDialog.dispEdit.toPlainText()

            #  strip newlines from the comment before updating database
            newComment = self.comment.replace('\n', '') if self.comment else ''
            commentText = ' '.join(newComment)

            #  update the comment in samples
            sql = ("UPDATE samples SET comments='" + commentText + "' WHERE ship="+self.ship +
                    " AND survey=" + self.survey + " AND event_id = " + self.activeHaul +
                    " AND sample_id = "+self.activeSampleKey)
            self.db.dbExec(sql)

    def closeEvent(self, event):
        '''closeEvent is called when the form is closed. It performs some
        validations then exits.
        '''

        #  run our catch validations
        self.exitValidation()

        #self.refreshTimer.stop()

        if self.returnFlag:
            #  There was a validation error the user chose to address.
            #  ignore this close event.
            event.ignore()
        else:
            #  No validation issues or the user doesn't care - accept
            #  the event to close the dialog.
            event.accept()

        #  store the window size and position
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())

    def resizeEvent(self, event):

        #  resize the sample picture
        if self.samplePicture:
            pic = self.samplePicture.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio)
            self.picLabel.setPixmap(QPixmap.fromImage(pic))
        self.picLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.picLabel.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        super().resizeEvent(event)

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



