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
.. module:: unsortedCatch

    :synopsis: Large CPS Hauls > 5 baskets information is entered here. 

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
from ui import ui_CPSUnsortedCatch
import numpad
import typeseldialog
import CPS.cpsBasketEditDlg as cpsBasketEditDlg
import keypad
import messagedlg
import measurementDialogs.FEATProjectDlg as project
import CPS.sortedCatch as sortedCatch

class unsortedCatch(QDialog, ui_CPSUnsortedCatch.Ui_CPSUnsortedCatch):

    def __init__(self, parent=None):

        #  call superclass init methods and GUI form setup method
        super(unsortedCatch, self).__init__(parent)
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
        self.planktonFlag = False
        self.activeSampleKey = None
        self.activeSpcName = None
        self.activeSpcCode = None
        self.activeFullName = None
        self.samplePicture = None
        self.comment = ''

        # get sample types
        self.basketTypes = (['Sort', 'Toss'])
        # sets valid sample type choices
        self.validList = [1, 1]

        self.freeze = False
        self.whHaulFlag = False
        self.devices = {}
        self.sounds = {}
        self.speciesProtos = {}
        self.subcategories = []
        self.manualDevice ='0'
        self.parentSamples = {}
        self.mixtureNames = {'100000':'WholeHaul', '100001':'SortingTable',
                '100002':'Mix1', '100003':'SubMix1', '100004':'Mix2'}
        self.wholeHaulKey = None
        self.headerFont = QFont("Arial Black", 11, -1, False)
        self.activeSampleType = None

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

        #  set up tables for data display - most of this is done in QDesigner
        #  but some properties don't seem to "stick" (maybe QDesigner is buggy?)
        self.basketTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.basketTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.basketTable.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.basketTable.horizontalHeader().setStretchLastSection(True)
        #self.speciesList.horizontalHeader().setStretchLastSection(True)

        #  set up the the basket table headers
        self.basketTable.clearContents()
        self.basketTable.setRowCount(0)
        headerItem = QTableWidgetItem("Weight (kg)")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(0, headerItem)
        headerItem = QTableWidgetItem("Basket Type")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(1, headerItem)

        # set up recurring dialogs
        self.message = messagedlg.MessageDlg(self)
        self.numpad = numpad.NumPad(self)
        self.typeDlg = typeseldialog.TypeSelDialog(self)

        #  connect signals and slots
        self.manualBtn.clicked.connect(self.getManual)
        self.doneBtn.clicked.connect(self.showCatch)
        self.delBtn.clicked.connect(self.goDelete)
        self.editBtn.clicked.connect(self.editTable)
        self.basketTable.itemSelectionChanged.connect(self.getBasketRow)
        self.commentBtn.setDisabled(True)  # initially disabled
        self.commentBtn.clicked.connect(self.getComment)

        #  connect the SensorMonitor SerialDataReceived signal to the
        #  getAuto method which processes input from devices.
        self.sensorMonitor.SensorDataReceived.connect(self.getAuto)

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

        #  Check for haul if not insert a dummy one
        if 'codend' in self.activePartition.lower():
            sql = ("SELECT parameter_value FROM  " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND partition='" + self.activePartition +
                "' AND event_parameter='PartitionWeightType'")

            query = self.db.dbQuery(sql)
            pwt, = query.first()
            if not pwt:
                #  No partition intialized yet, insert a dummy one
                sql = ("INSERT INTO " + self.schema + ".EVENT_DATA (ship, survey, event_id, partition, "
                    "event_parameter, parameter_value) "
                    "VALUES (" + self.ship + "," + self.survey + "," + self.activeHaul + ",'Codend',"
                    "'PartitionWeightType','not_subsampled'),"
                    "(" + self.ship + "," + self.survey + "," + self.activeHaul + ",'Codend',"
                    "'PartitionWeight','TBD')")
                self.db.dbExec(sql)

        #  Check for WholeHaul sample, if not insert a one
        sql = ("SELECT sample_id FROM  " + self.schema + ".samples WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul + 
                " AND sample_type = 'WholeHaul'")
        self.activeSampleKey, = self.db.dbQuery(sql).first()

        if self.activeSampleKey is None:
            sql = ("INSERT INTO " + self.schema + ".SAMPLES (ship, survey, event_id, partition, "
                    "sample_type, species_code, scientist) "
                    "VALUES (" + self.ship + "," + self.survey + "," + self.activeHaul + ",'Codend',"
                    "'WholeHaul',1 ,'" + self.scientist + "')")
            self.db.dbExec(sql)
            
            # initialize active sample key
            sql = ("SELECT SAMPLE_ID FROM " + self.schema + ".samples where event_id="+self.activeHaul+ 
                " AND partition='Codend' AND sample_type = 'WholeHaul'")
            self.activeSampleKey, = self.db.dbQuery(sql).first()

        self.updateTables()


    def getManual(self):
        '''getManual is called when the user clicks the manual weight button. It
        makes sure a species sample is selected and presents a dialog to enter
        the weight.
        '''

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

        #  weight passes basic validation
        return True


    def getBasketType(self):
        '''getBasketType is called after a basket weight is collected and
        presents the user with the basket type dialog where they choose if
        the basket is a measure, count, or toss basket.

        '''
        #  display the basket type dialog
        self.typeDlg.buttonSetup(self.validList, self.basketTypes)
        if self.typeDlg.exec():
            self.basketType = self.typeDlg.basketType
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
        sql = ("INSERT INTO " + self.schema + ".baskets (ship,survey,event_id,sample_id,basket_type," +
                "weight, device_id) VALUES ("+ self.ship+", "+self.survey+","+
                self.activeHaul+","+self.activeSampleKey+",'"+self.basketType+"',"
                +str(self.currentBasketWt)+","+self.activeDeviceId+")")
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
        sumTableRows = {}
        for i, bType in enumerate(self.basketTypes):
            basketTotalWeight[bType] = 0
            sumTableRows[bType] = i

        #  update the basket table - first, clear the contents
        self.basketTable.clearContents()
        self.basketTable.setRowCount(0)
        basketCount = 0

        #  set up the table headers
        headerItem = QTableWidgetItem("Weight (kg)")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(0, headerItem)
        headerItem = QTableWidgetItem("Basket Type")
        headerItem.setFont(self.headerFont)
        self.basketTable.setHorizontalHeaderItem(1, headerItem)

        #  query the baskets for this sample ID and populate the baskets table
        sql = ("SELECT basket_id, weight, basket_type " +
                "FROM " + self.schema + ".baskets WHERE ship="+self.ship+" AND survey="+self.survey+
                " AND event_id="+self.activeHaul+" AND sample_id ="+
                self.activeSampleKey+" ORDER BY basket_id")
        query = self.db.dbQuery(sql)
        for basketId, basketWeight, basketType in query:
            #  convert the weight to float and accumulate totals
            try:
                basketWeight = float(basketWeight)
                basketTotalWeight[basketType] += basketWeight
            except:
                basketWeight = 0
                basketTotalWeight[basketType] += 0

            #  add this basket to the table
            basketWeight = str(round(basketWeight, self.basketPrecision))
            self.basketTable.insertRow(basketCount)
            headerItem = QTableWidgetItem(basketId)
            headerItem.setFont(self.headerFont)
            self.basketTable.setVerticalHeaderItem(basketCount, headerItem)
            self.basketTable.setItem(basketCount, 0, QTableWidgetItem(basketWeight))
            self.basketTable.setItem(basketCount, 1, QTableWidgetItem(basketType))

            if 'nwfsc' in self.settings['OrganizationName'].lower() and basketType == 'Measure':
                self.basketTable.item(basketCount, 2).setBackground(QColor(127, 255, 212))
            basketCount += 1

        #  resize columns and scroll to bottom
        self.basketTable.resizeColumnsToContents()
        self.basketTable.scrollToBottom()

        #  now update the basket summary table
        totalSampleWeight = 0
        for basketType in self.basketTypes:
            weight = str(round(basketTotalWeight[basketType], self.basketPrecision))
            totalSampleWeight += basketTotalWeight[basketType]
            self.sumTable.setItem(sumTableRows[basketType], 1, QTableWidgetItem(weight))

        #  lastly, update the total sample weight in the samples table
        totalSampleWeight = str(round(totalSampleWeight, self.basketPrecision))




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
        #  update the tables
        self.updateTables()

    def editTable(self):
        '''editTable is called when the "Edit" button is pressed. This will present
        the Edit Basket dialog which allows the user to edit a specific basket.
        '''
        self.freeze=True

        # turn off count sample type for mixes
        #if self.activeSampleType and 'mix' in self.activeSampleType.lower():
        #    self.validList[self.basketTypes.index('Count')] = 0
        #else:
        #    self.validList[self.basketTypes.index('Count')] = 1

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
        header = ['Basket ID', 'Weight', 'Sample Type' ]
        editDlg = cpsBasketEditDlg.CPSBasketEditDlg(header, selRecord, self)
        editDlg.exec()
        if not editDlg.okFlag:
            #  user cancelled action
            return


        # update basket table
        sql = ("UPDATE baskets SET basket_type='"+editDlg.basketType+"', weight = "+
                editDlg.weight+"  WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeHaul+
                " AND sample_id = "+self.activeSampleKey+" AND basket_id = "+
                self.selRecord[0])
        self.db.dbExec(sql)

        self.freeze=False

        self.updateTables()


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
    
    def showCatch(self):
        #  show the catch form
        catchWindow = sortedCatch.sortedCatch(self)
        catchWindow.exec()
        self.close()