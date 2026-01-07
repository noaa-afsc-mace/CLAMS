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
.. module:: cpsAddCatchSpcDlg

    :synopsis: cps specific dialog used to add samples
               to the Catch module. It allows the user to search for
               the species they want to add, then add it to the
               specified parent sample.

| Developed by:  Melina Shak <melina.shak@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS
|
| Author:
|       Melina Shak <melina.shak@noaa.gov>
| Maintained by:
|       Melina Shak <melina.shak@noaa.gov>
"""

#  imports
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import  ui_CPSAddCatchSpcDlg
import listseldialog
import sampletypeseldlg


class cpsAddCatchSpcDlg(QDialog, ui_CPSAddCatchSpcDlg.Ui_CPSAddCatchSpcDlg):

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super(cpsAddCatchSpcDlg, self).__init__(parent)

        self.setupUi(self)

        self.mixCreateFlag = False
        self.mixAddFlag = False
        self.db = parent.db
        self.schema = parent.schema
        self.ship = parent.ship
        self.survey = parent.survey
        self.activeHaul = parent.activeHaul
        self.activePartition = parent.activePartition
        self.message = parent.message
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.whHaulFlag = parent.whHaulFlag
        self.previous = None
        self.listOrigin = None
        self.chars = ''
        self.updatingDigit = False
        self.settings = parent.settings
        self.mixtureNames = {'100000':'WholeHaul', '100001':'SortingTable',
                '100002':'Mix1', '100003':'SubMix1', '100004':'Mix2'}
        self.parentSamples = parent.parentSamples
        self.scientist = parent.scientist
        self.isSubMix = False

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'AddCatchSppDialog')
        size = self.appSettings.value('winsize', QSize(946,690))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  create the sample type selection dialog
        self.SampTypeDlg = sampletypeseldlg.sampletypeseldlg(self)

        #  put the keyboard buttons into a list to easily reference them
        self.digitBtns=[self.A_Btn,self.B_Btn,self.C_Btn,self.D_Btn,self.E_Btn,self.F_Btn,
                        self.G_Btn,self.H_Btn,self.I_Btn,self.J_Btn,self.K_Btn,self.L_Btn,
                        self.M_Btn,self.N_Btn,self.O_Btn,self.P_Btn,self.Q_Btn,self.R_Btn,
                        self.S_Btn,self.T_Btn,self.U_Btn,self.V_Btn,self.W_Btn,self.X_Btn,
                        self.Y_Btn,self.Z_Btn]
        #  connect the keyboard key signals
        for btn in self.digitBtns:
            btn.clicked.connect(self.getDigit)

        #  connect the other signals
        self.fullspcCList.itemClicked[QListWidgetItem].connect(self.getSpcSel)
        self.fullspcSList.itemClicked[QListWidgetItem].connect(self.getSpcSel)
        self.lineEdit.textEdited.connect(self.searchEdited)
        self.space.clicked.connect(self.addSpace)
        self.backBtn.clicked.connect(self.clearOneChar)
        self.clearBtn.clicked.connect(self.clearAllChar)
        self.doneBtn.clicked.connect(self.close)
        self.addBtn.clicked.connect(self.sendSel)
        self.radio10.toggled[bool].connect(self.getSpcHistory)
        self.radioFull.toggled[bool].connect(self.clearAllChar)
        self.inStateWaters.clicked.connect(self.toggleStateWaters)
        self.subMixBtn.clicked.connect(self.setParentToSubMix)

        # parent sample buttons
        self.buttons=[self.subMixBtn]

        #  connect the sample button clicked signal to a method that manages their exclusivity
        #  it seems autoexclusive buttons in a container cannot all be unchecked. Once one is
        #  checked, you can't uncheck it (at least by calling setChecked()
        for btn in self.buttons:
            btn.clicked.connect(self.handleSampleBtnEx)


        # set default tab, get past haul species
        self.historyHauls = []

        sql = ("SELECT a.event_id, a.gear FROM (SELECT event_id, gear, " +
                "ship, survey FROM " + self.schema + ".events) a JOIN (SELECT gear, gear_type " +
                "FROM " + self.schema + ".gear) b ON a.gear = b.gear JOIN (SELECT gear_type, " +
                "retains_catch from " + self.schema + ".gear_types) c ON b.gear_type = c.gear_type " +
                "WHERE a.ship = " + self.ship + " AND a.survey= " + self.survey +
                " AND c.retains_catch > 0  ORDER BY event_id ASC")
        eventQuery = self.db.dbQuery(sql)
        for event_id, gear in eventQuery:
            self.historyHauls.append(event_id)

        #  reverse the list and keep up to 10
        self.historyHauls.reverse()
        self.historyHauls[:10]

        self.getSpcHistory()
        self.radio10.setChecked(True)

        #  set up the sample buttons
        self.setSampleBtnEnable()


    def handleSampleBtnEx(self):
        '''
        handleSampleBtnEx manages the exclusivity of the parent sample buttons
        This
        '''
        #  uncheck all buttons
        for btn in self.buttons:
            btn.setChecked(False)
        #  and check the button pressed
        self.sender().setChecked(True)


    def setSampleBtnEnable(self):
        '''
        setSampleBtnEnable enables/disables the parent sample buttons based on
        the
        '''

        #  set all buttons enabled
        for btn in self.buttons:
            btn.setEnabled(True)

        #  uncheck all buttons
        for btn in self.buttons:
            btn.setChecked(False)

        # find out if we have a mix1
        sql = ("SELECT sample_id FROM  " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey=" + self.survey+ " AND event_id=" + self.activeHaul +
                " AND partition='" + self.activePartition + "' AND species_code=100002")
        query = self.db.dbQuery(sql)
        sampleId, = query.first()

        if not sampleId:
            # no mix 1 in the system
            self.subMixBtn.setEnabled(False)
        else:
            # we have a mix 1 - check if we have a submix for mix 1
            sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                    " AND partition='" + self.activePartition + "' AND species_code=100003")
            query = self.db.dbQuery(sql)
            mixId, = query.first()
            if not mixId:
                # no submix1
                self.subMixBtn.setEnabled(False)

        #  check if there is a mix2
        sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                " AND survey = " + self.survey+ " AND event_id=" + self.activeHaul +
                " AND partition ='" + self.activePartition + "' AND species_code=100004")
        query = self.db.dbQuery(sql)
        mixId, = query.first()


    def getDigit(self):

        self.chars = self.chars + self.sender().text()
        self.lineEdit.setText(self.chars)
        self.radioFull.setChecked(True)

        self.getList()


    def clearOneChar(self):
        self.chars=self.chars[:-1]
        self.lineEdit.setText(self.chars)
        self.getList()
    
    def addSpace(self):
        self.chars=self.chars + ' '
        self.lineEdit.setText(self.chars)
        self.getList()

    @pyqtSlot()
    def clearAllChar(self):

        self.chars = ''
        self.spcLabel.setText('')
        self.picLabel.clear()
        self.lineEdit.setText(self.chars)
        self.getList()


    @pyqtSlot(str)
    def searchEdited(self, newChars):
        self.chars = newChars
        self.getList()

    def toggleStateWaters(self):
        if (self.inStateWaters.isChecked()):
            self.subMixBtn.setEnabled(True)
            
        else:
            self.subMixBtn.setEnabled(False)
    
    def setParentToSubMix(self):
        self.isSubMix = True
        # Check if submix already exists
        sql = ("select sample_id from samples where survey=" + self.survey + 
               " AND event_id=" + self.activeHaul + 
               " AND parent_sample=" + self.parentSamples + 
               " AND sample_type='SubMix'")
        query = self.db.dbQuery(sql)
        hasSubMix, = query.first()

        # Insert submix if it doesn't already exist
        if not hasSubMix:
            sql = ("INSERT INTO " + self.schema + ".samples (ship,survey,event_id,partition,sample_type," +
                "species_code,subcategory,parent_sample,scientist) VALUES("+
                self.ship +"," + self.survey+"," + self.activeHaul+",'" + self.activePartition+
                "','SubMix',3 ,'None', " + self.parentSamples+",'" + self.scientist+"')")
            self.db.dbExec(sql)

    def getList(self):

        self.fullspcCList.clear()
        self.fullspcSList.clear()

        if self.chars == '':
            commonQuery = "SELECT species.common_name FROM " + self.schema + ".species ORDER BY species.common_name"
            sciQuery = "SELECT species.scientific_name FROM " + self.schema + ".species WHERE species_code<999900 ORDER BY species.scientific_name"
        else:
            like_exp = "'%"+self.chars+"%'"
            commonQuery = ("SELECT species.common_name FROM " + self.schema + ".species WHERE upper(species.common_name)" +
                " LIKE upper(" + like_exp + ") AND species_code<999900 ORDER BY species.common_name")
            sciQuery = ("SELECT species.scientific_name FROM " + self.schema + ".species WHERE upper(species.scientific_name) "+
                " LIKE upper(" + like_exp + ") AND species_code<999900 ORDER BY species.scientific_name")

        query = self.db.dbQuery(commonQuery)
        for commonName, in query:
            self.fullspcCList.addItem(commonName)

        query = self.db.dbQuery(sciQuery)
        for sciName, in query:
            self.fullspcSList.addItem(sciName)

        if self.fullspcCList.count() < 2 and self.nameTab.currentIndex==0:
            self.fullspcCList.setCurrentRow(1)
        elif self.fullspcSList.count() < 2 and self.nameTab.currentIndex==1:
            self.fullspcSList.setCurrentRow(1)

        self.picLabel.clear()


    def getSpcSel(self):

        # image code
        self.listOrigin = self.sender()
        self.activeSpcName = self.listOrigin.currentItem().text()
        if self.nameTab.currentIndex() == 0:
            self.nameType='common'
            sql = ("SELECT species.species_code  "+
                    "FROM " + self.schema + ".species WHERE species.common_name='"+
                    self.listOrigin.currentItem().text()+"'")
        else:
            self.nameType='scientific'
            sql = ("SELECT species.species_code  "+
                    "FROM " + self.schema + ".species WHERE species.scientific_name='"+
                    self.listOrigin.currentItem().text()+"'")

        query = self.db.dbQuery(sql)
        spCode, = query.first()
        self.activeSpcCode = spCode
        imgName=None

        # check for species subcategories
        subcats = []
        sql = ("SELECT subcategory FROM " + self.schema + ".species_associations WHERE species_code="+
                self.activeSpcCode)
        query = self.db.dbQuery(sql)
        for subcat, in query:
            subcats.append(subcat)
        if len(subcats) > 1:
            # species has multiple subclasses in species associations
            #  display the subcat selection dialog
            self.listDialog = listseldialog.ListSelDialog(subcats, 'Short',  self)
            self.listDialog.label.setText('Choose Size Class')
            if self.listDialog.exec():
                if (self.listDialog.itemList.currentRow() < 0):
                    #  no name selected
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                            'Please select a Size Class or "All Sizes".', 'info')
                    self.message.exec()
                else:
                    self.activeSpcSubcat = self.listDialog.itemList.currentItem().text()
                    imgName = self.activeSpcCode #+"_"+self.activeSpcSubcat
                    labelText=self.activeSpcName + "-" + self.activeSpcSubcat
            else:
                return

        elif len(subcats) == 1:
            # species has one listing in species associations
            self.activeSpcSubcat = subcats[0]
            imgName = self.activeSpcCode
            labelText = self.activeSpcName
        else:
            # species not listed in species associations
            self.activeSpcSubcat = 'None'
            imgName = self.activeSpcCode
            labelText = self.activeSpcName

        #  Check for previous occurence if we're configured to. This is a simple check
        #  which can catch some sp identification errors.
        if self.settings['CheckForPreviousOccurrence'].lower() == 'true':
            #  yes, check if we have seen this species before
            self.previous = 0
            if int(self.activeSpcCode) < 99999:# not a mix
                sql = ("SELECT parameter_value FROM " + self.schema + ".species_data WHERE species_code="+
                        self.activeSpcCode+" AND subcategory='"+self.activeSpcSubcat+
                        "' AND LOWER(species_parameter)='previous_occurrence'")
                query = self.db.dbQuery(sql)
                prevOcc, = query.first()
                if prevOcc is None:
                    self.previous = -1
                else:
                    try:
                        self.previous = int(prevOcc)
                    except:
                        self.previous = 1
        else:
            #  we're not checking for previous occurence so set it to 1
            #  to skip user interaction
            self.previous = 1

        # load label
        self.spcLabel.setText(labelText)

        #TODO: get image name from image_file attribute of species_data
        # set image
        pic = QImage()
        if imgName:
            if pic.load(self.settings['ImageDir']+'\\fishPics\\'+imgName+".jpg"):
               pic = pic.scaled(self.picLabel.size(),Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
               self.picLabel.setPixmap(QPixmap.fromImage(pic))
            else:
                self.picLabel.clear()
        # submix check
        if self.activeSpcCode == '100003':
            # find out if we have some mixes
            sql = ("SELECT sample_id FROM " + self.schema + ".samples WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                    " AND partition='" + self.activePartition + "' AND species_code=100002")
            query = self.db.dbQuery(sql)
            mix, = query.first()

            if not mix:
                # no mix 1 in the system
                self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                        "There's no Mix1 sample for this partition. " +
                        "You need to create it before using the SubMix1", 'info')
                self.message.exec()
            else:
                # you can only choose Mix1!!
                for btn in self.buttons:
                    btn.setEnabled(False)


    def sendSel(self):

        if self.listOrigin == None:
            return

        # Only need to update the species data table with previous occurrence if it is not a mix
        if int(self.activeSpcCode) < 99999:
            if self.previous <= 0:
                #  ask if we want to add this exotic species we've never encountered
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "We've never seen a "+
                        self.listOrigin.currentItem().text() + ". Are you sure that's right? ", 'choice')
                if not self.message.exec():
                    return

                #  we do, update the Previous_Occurrence parameter in the species_data table for this species
                if self.previous < 0:
                    #  no Previous_Occurrence parameter in the database for this species, add it
                    sql = ("INSERT INTO " + self.schema + ".species_data (species_code,subcategory,species_parameter," +
                            "parameter_value) VALUES (" + self.activeSpcCode + ",'" + self.activeSpcSubcat +
                            "','Previous_Occurrence','1')")
                else:
                    #  Previous_Occurrence parameter is in the database. Update it.
                    sql = ("UPDATE " + self.schema + ".species_data SET parameter_value='1' WHERE " +
                            "species_code=" + self.activeSpcCode + " AND subcategory='" +
                            self.activeSpcSubcat+"' AND species_parameter='Previous_Occurrence'")
                self.db.dbExec(sql)

        #  set the sample type - first, check if we're adding a mix
        if self.activeSpcCode in ('100002', '100003', '100004'):
            #  this is a mix type
            self.activeSampleType = self.mixtureNames[self.activeSpcCode]

        #  if not, next check if we're enabling the 'Present' sample type
        elif self.settings['EnablePresentSampleType'] in ['1', 'true', 'True']:
            #  we are - present the sample type selection dialog
            self.SampTypeDlg.exec()

            #  check to make sure the user selected something
            if not self.SampTypeDlg.result[0]:
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0],
                    "You must select a sample type when adding a sample to your catch.", 'info')
                self.message.exec()
                return

            #  set the sample type
            self.activeSampleType = self.SampTypeDlg.result[1]
        else:
            #  if not a mix and Present type is not enabled - the sample type is Species
            self.activeSampleType = 'Species'

        #  emit the changed signal to update parent
        self.changed.emit()

        self.setSampleBtnEnable()

        #  only clear the text box and list if this isn't a history pick
        if not self.radio10.isChecked():
            self.clearAllChar()
        
        # Reset submix back to false, will be set to true if submix button selected
        self.isSubMix = False


    def getSpcHistory(self):
        '''
        Create a "short list" of the most common species from the last
        few hauls.
        '''

        #  clear the short list
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        wghtList=[]
        spcList=[]

        if (len(self.historyHauls) < 2):
            return

        hauls = ','.join(self.historyHauls)


        sql = ("SELECT species.common_name, species.species_code FROM " + self.schema + ".species INNER " +
                "JOIN " + self.schema + ".samples ON species.species_code=samples.species_code WHERE " +
                "(samples.event_id IN (" + hauls + ") AND (samples.survey = " +
                self.survey+") AND species.species_code not in (100000, 100001) " +
                "AND species.species_code<900000) GROUP BY species.common_name," +
                "species.species_code")
        spQuery = self.db.dbQuery(sql)

        #  loop through the events

        for commonName, spCode in spQuery:
            spcList.append(commonName)
            sql = ("SELECT SUM(BASKETS.WEIGHT) FROM " + self.schema + ".BASKETS, " + self.schema + ".SAMPLES WHERE " +
                    "((SAMPLES.SAMPLE_ID=BASKETS.SAMPLE_ID) AND (SAMPLES.SPECIES_CODE="+
                    spCode + ") AND (SAMPLES.SURVEY="+self.survey+ ") AND " +
                    "(SAMPLES.event_id IN(" + hauls + ")))" )

            weightQuery = self.db.dbQuery(sql)
            sampleWeight, = weightQuery.first()
            if sampleWeight:
                try:
                    wghtList.append(float(sampleWeight))
                except:
                    pass

        #  if we have a history - create the "short list"
        if wghtList:
            wghtList, spcList = (list(x) for x in zip(*sorted(zip(wghtList, spcList))))
            spcList.reverse()
            self.fullspcCList.addItems(spcList)


    def getRadioSel(self):

        self.history=10
        self.getSpcHistory()


    def closeEvent(self, event):
        '''closeEvent is called when the form is closed.
        '''

        #  store the window size and position
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
