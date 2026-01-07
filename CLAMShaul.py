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
.. module:: CLAMShaul

    :synopsis: CLAMShaul presents the CLAMS haul form. The haul form
               is used to specify how the main partition weight(s) will
               be determined. The "main" partition(s) are partitions that
               have sizeable catch. Think codend. Pocketnets are not
               considered main partitions. If the partition(s) will be
               subsampled, this form allows the user to enter the partition
               total weight. The haul form is the first form that is completed
               when processing the catch.

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

#  imports
import os
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_CLAMSHaul
import haulwtseldlg
import numpad
import keypad
from math import *
import messagedlg

class CLAMSHaul(QDialog, ui_CLAMSHaul.Ui_clamsHaul):
    '''CLAMShaul presents the CLAMS haul form. The haul form is used to specify
    how the main partition weight(s) will be determined. The "main" partition(s)
    are partitions that have sizeable catch. Think codend. Pocketnets are not
    considered main partitions. If the partition(s) will be subsampled, this
    form allows the user to enter the partition weight. The haul form is the
    first form that is completed when processing the catch.
    '''

    def __init__(self,  parent=None):
        '''
            The CLAMS Haul dialog initialization method. Gets basic information
            and sets up the haul form
        '''

        #  call superclass init methods and GUI form setup method
        super(CLAMSHaul, self).__init__(parent)
        self.setupUi(self)

        #  copy some info from parent for convenience
        self.db = parent.db
        self.schema = parent.schema
        self.workStation = parent.workStation
        self.activeHaul = parent.activeHaul
        self.survey = parent.survey
        self.ship = parent.ship
        self.settings = parent.settings
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.sensorMonitor = parent.sensorMonitor
        self.blue = parent.blue
        self.black = parent.black
        self.scientist = parent.scientist

        #  set the sci name and extract the first name
        self.sciLabel.setText(self.scientist)
        self.firstName = self.scientist.split(' ')[0]

        #  create lists of our dynamic buttons and associated labels
        self.haulInfoBtns=[[self.haulInfoBtn1_1, self.haulInfoBtn1_2, self.haulInfoBtn1_3, self.haulInfoBtn1_4],
                           [self.haulInfoBtn2_1, self.haulInfoBtn2_2, self.haulInfoBtn2_3, self.haulInfoBtn2_4],
                           [self.haulInfoBtn3_1, self.haulInfoBtn3_2, self.haulInfoBtn3_3, self.haulInfoBtn3_4]]
        self.partitionLabels=[self.partitionLabel1,self.partitionLabel2,self.partitionLabel3, self.partitionLabel4]
        self.haulInfoGroups=[self.groupBox1, self.groupBox2, self.groupBox3]

        #  define default variable values
        self.comment = ""
        self.incomplete = False
        self.perfBoxFlag = False
        self.reloadFlag=False
        self.forceExit = False
        self.partitions = []
        self.parameters = []
        self.perfCode = 0

        #  load the error icon
        self.errorIcon = QPixmap()
        self.errorIcon.load(self.settings['IconDir'] + "\\error.bmp")

        #  connect button signals...
        self.commentBtn.clicked.connect(self.getComment)
        self.doneBtn.clicked.connect(self.close)
        self.perfBox.activated[int].connect(self.setFlag)
        self.perfCheckBox.stateChanged[int].connect(self.getPerfList)

        #  restore the application state
        self.appSettings = QSettings('CLAMS', 'HaulForm')
        size = self.appSettings.value('winsize', QSize(950,665))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  setup recurring dialogs
        self.numpad = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)

        #  create a single-shot timer that runs the application initialization code
        #  this allows the application to complete the main window init method before
        #  the rest of the initialization code runs. We do this because we can't
        #  close the main window (as we would if there was an initialization error)
        #  from the window's init method.
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.formInit)
        initTimer.start(0)


    def formInit(self):
        '''formInit is called when the init timeout timer expires. It completes
        setup of the form, querying data and updating the GUI based on gear type.
        '''

        # get the basic event information
        sql = ("SELECT gear, event_type, performance_code, scientist, comments " +
                    "FROM " + self.schema + ".events WHERE ship=" + self.ship + " AND survey=" + self.survey +
                    " AND event_id=" + self.activeHaul)
        query = self.db.dbQuery(sql)
        self.gear, event_type, perf_code, trawl_sci, comments = query.first()

        #  update the comment and set the performance code from the event
        self.comment = comments
        self.perfCode = perf_code

        #  update the gear and scientists label
        self.gearLabel.setText(self.gear)
        self.sciLabel.setText(self.scientist)

        #  load and display the gear image (if available)
        try:
            imgPath = os.path.normpath(self.settings['ImageDir'] + os.sep +
                    'gearPics' + os.sep + self.gear + '.jpg')
            gearImage = QImage(imgPath)
            gearImage = gearImage.scaled(self.picLabel.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(gearImage))
        except:
            self.picLabel.setText("<Image Unavailable>")

        #  update the performance code list and set the combobox
        self.getPerfList()

        #  determine what gear we're working with and set up the form details. The
        #  base form has a bunch of buttons and labels and they are shown/hidden
        #  based on the general gear type. CLAMS supports 3 general gear types:
        #
        #    SingleCodendTrawl - a standard fishing net with a single codend. This
        #           type of trawl will only have a single "main" partition and
        #           the form will present a single row of buttons allowing the
        #           user to specify the weight type and (optionally) the weight.
        #    MultiCodendTrawl - a standard fishing net with multiple codends. This
        #           type of trawl will have 3 "main" partitions and the form will
        #           present 3 rows of buttons.
        #    PlanktonNet - a net designed to catch plankton with a single "codend".
        #           PlanktonNet codends are treated like a pocketnet and are never
        #           subsampled so the user does not specify the haul weight type but
        #           these nets are deployed with a flow meter and the haul form buttons
        #           are configured to capture the flow meter readings.

        sql = ("SELECT gear_type FROM " + self.schema + ".gear WHERE gear='" + self.gear + "'")
        query = self.db.dbQuery(sql)
        self.gearType, = query.first()
        self.haulInfo = []
        self.completeTest = []
        if self.gearType.lower() == 'singlecodendtrawl':
            self.singleCodendTrawl()
        elif self.gearType.lower() == 'planktonnet':
            self.planktonNet()
        elif self.gearType.lower() == 'multicodendtrawl':
            self.multiCodendTrawl()
        else:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[1],
                                    "This gear type, " + self.gearType + ", is not supported at this time", 'info')
            self.message.exec()

        #  populate Haul Info
        for i, partition  in enumerate(self.partitions):
            for j, parameter  in enumerate(self.parameters):
                sql = ("SELECT event_data.parameter_value FROM " + self.schema + ".event_data WHERE event_data.ship="+
                        self.ship+ " AND event_data.survey=" + self.survey+ " AND event_data.event_id=" +
                        self.activeHaul + " AND event_data.partition='" + partition +
                        "' AND event_data.event_parameter = '" + parameter + "'")
                query = self.db.dbQuery(sql)
                paramVal, = query.first()
                if paramVal:
                    self.haulInfoBtns[j][i].setText(paramVal)


    '''
    The following three methods set up the GUI depending on the type of gear
    that was deployed. They hide unused buttons/labels and set the text on
    buttons and labels that are needed for the type of gear that was deployed.

    The single codend and plankton trawls are pretty standard. The multi codend
    trawl is set up for a 3 codend system which was what MACE has used. Multi
    codend trawls are pretty uncommon, but if a 2 or 4 codend trawl system was
    being used, the multi codend setup would need to be extended to store the
    number of codends in the database somehow attached to the gear and this
    form would need to be updated to query that out. For now it is fixed at 3.
    '''

    def singleCodendTrawl(self):
        '''singleCodendTrawl sets the form up for a single codend trawl net. This
        will present the user with a single row of buttons where they will specify
        the haul weight type and optionally the weight (if they are subsampling)
        '''

        #  connect the button signals
        for i in range(1):
            self.haulInfoBtns[0][i].clicked.connect(self.getWeight)

        #  hide the other buttons and labels
        for j in range(4):
                self.haulInfoBtns[2][j].hide()
        for i in range(1, 4):
            self.partitionLabels[i].hide()
            for j in range(2):
                self.haulInfoBtns[j][i].hide()
        self.groupBox3.hide()

        #  set the GUI labels
        self.haulInfoBtns[0][0].setText('')
        self.haulInfoBtns[1][0].setText('')
        self.groupBox1.setTitle('Haul Weight Type')
        self.groupBox2.setTitle('Haul Weight')
        self.partitionLabels[0].setText('<font size=16>Codend')

        #  set up the partion and haul parameters for a single codend trawl
        self.partitions = ['Codend']
        self.parameters = ['PartitionWeightType', 'PartitionWeight']


    def multiCodendTrawl(self):
        '''multiCodendTrawl sets the form up for a triple codend trawl net. This
        will present the user with a three rows of buttons where they will specify
        the haul weight type and optionally the weight (if they are subsampling) for
        each codend.
        '''

        #  connect the button signals
        for i in range(4):
            self.haulInfoBtns[0][i].clicked.connect(self.getWeight)

        #  hide the other buttons and labels
        for j in range(4):
                self.haulInfoBtns[2][j].hide()
        self.partitionLabels[3].hide()
        for j in range(2):
            self.haulInfoBtns[j][3].hide()

        #  set the GUI labels
        self.haulInfoBtns[0][0].setText('')
        self.haulInfoBtns[1][0].setText('')
        self.groupBox1.setTitle('Haul Weight Type')
        self.groupBox2.setTitle('Haul Weight')

        #  for now, we assume the first codend was always deployed
        self.partitionLabels[0].setText('Codend 1')

        #  now check if the 2nd codend was deployed - determined by the
        #  presence of EQ for the 2nd codend
        sql = ("SELECT parameter_value FROM  " + self.schema + ".event_data WHERE ship=" + self.ship + " AND survey=" +
                self.survey + " AND event_id=" + self.activeHaul +
                " AND partition='Codend_2' AND event_parameter='EQ'")
        query = self.db.dbQuery(sql)
        hasEQ, = query.first()
        if hasEQ:
            #  it was, set the label
            self.haulInfoBtns[0][1].setText('')
            self.haulInfoBtns[1][1].setText('')
            self.partitionLabels[1].setText('Codend 2')
        else:
            #  it wasn't - hide the button
            self.haulInfoBtn1_2.setEnabled(False)
            self.partitionLabels[1].setText('')


        #  now check if the 3rd codend was deployed - determined by the
        #  presence of EQ for the 3rd codend
        sql = ("SELECT parameter_value FROM  " + self.schema + ".event_data WHERE ship=" + self.ship + " AND survey=" +
                self.survey + " AND event_id=" + self.activeHaul +
                " AND partition='Codend_3' AND event_parameter='EQ'")
        query = self.db.dbQuery(sql)
        hasEQ, = query.first()
        if hasEQ:
            #  it was, set the label
            self.haulInfoBtns[0][2].setText('')
            self.haulInfoBtns[1][2].setText('')
            self.partitionLabels[2].setText('Codend 3')
        else:
            #  it wasn't - hide the button
            self.haulInfoBtn1_3.setEnabled(False)
            self.partitionLabels[2].setText('')


        #  set up the partion and haul parameters for a multi codend trawl
        self.partitions=['Codend_1', 'Codend_2', 'Codend_3']
        self.parameters=['PartitionWeightType', 'PartitionWeight']


    def planktonNet(self):
        '''planktonNet sets the form up for a methot or bongo trawl. This
        will present the user with a one (or two for bongo) row of buttons where
        they will specify the flowmeter start and stop readings. Plankton nets
        like this are traditionally deployed with flow meters to determine the
        volume of water sampled. The haul form is used to capture this data.
        Methots and Bongos are always "not subsampled" so there is no partition
        weight type and weight to log.
        '''

        if self.gear == 'Bongo':
            #  Set up for a bongo - a bongo has two codends

            #  connect the signals and hide unused buttons
            for i in range(0,2):
                self.haulInfoBtns[i][0].clicked.connect(self.getFlowmeter)
                self.haulInfoBtns[i][1].clicked.connect(self.getFlowmeter)
                self.haulInfoBtns[i][2].hide()
                self.haulInfoBtns[i][3].hide()
            #  and hide unused labels
            for i in range(2,4):
                self.partitionLabels[i].hide()
            #  and hide some more buttons
            for i in range(0,4):
                self.haulInfoBtns[2][i].hide()
            self.groupBox3.hide()

            #  set the labels
            self.groupBox1.setTitle('Flow Meter Start')
            self.groupBox2.setTitle('Flow Meter End')
            self.partitionLabels[0].setText('Codend 1')
            self.partitionLabels[1].setText('Codend 2')
            self.haulInfoBtns[0][0].setText('')
            self.haulInfoBtns[1][0].setText('')
            self.haulInfoBtns[0][1].setText('')
            self.haulInfoBtns[1][1].setText('')

            #  set up the partion and haul parameters for a bongo
            self.partitions=['Codend_1', 'Codend_2']
            self.parameters=['FlowMeterStart', 'FlowMeterEnd']

        else:
            #  set up for a methot
            for i in range(0,2):
                self.haulInfoBtns[i][0].clicked.connect(self.getFlowmeter)
            self.haulInfoBtns[2][0].hide()
            for i in range(1,4):
                self.partitionLabels[i].hide()
                for j in range(3):
                    self.haulInfoBtns[j][i].hide()
            self.groupBox3.hide()

            #  set the labels
            self.groupBox1.setTitle('Flow Meter Start')
            self.groupBox2.setTitle('Flow Meter End')
            self.partitionLabels[0].setText('Codend')
            self.haulInfoBtns[0][0].setText('')
            self.haulInfoBtns[0][1].setText('')

            #  set up the partion and haul parameters for a methot
            self.partitions=['Codend']
            self.parameters=['FlowMeterStart', 'FlowMeterEnd']


    def getWeight(self):
        '''getWeight is called when the user clicks the "Haul Weight Type" button for a given
        partition. This dialog will allow the user to select the weight measurement type
        (not subsampled, load cell, estimate) and depending on the selection, enter the
        weight. It then returns the type and weight (or "TBD" for not subsampled since
        non-subsampled weight is determined by summing all of the basket weights.)

        '''
        ind = self.haulInfoBtns[0].index(self.sender())
        wtDlg = haulwtseldlg.HaulWtSelDlg(self)
        wtDlg.exec()
        if wtDlg.ok:
            self.haulInfoBtns[0][ind].setText(wtDlg.weightType)
            self.haulInfoBtns[1][ind].setText(wtDlg.weight)


    def getFlowmeter(self):
        '''getFlowmeter is called when a user presses the start or end flowmeter
        buttons on the Bongo or Methot form. It presents the numpad so the user
        can enter the flowmeter readings.
        '''
        self.numpad.msgLabel.setText("Enter flowmeter number," + self.firstName)
        if self.numpad.exec():
            self.sender().setText(self.numpad.value)


    def writeHaul(self):


        #  first check if all of the haul buttons have been completed
        haulInfoCompleteFlag = True
        for btns in self.haulInfoBtns:
            for btn in btns:
                if btn.isVisible() and btn.text() == '':
                    #  a button is empty - IOW the form isn't complete
                    haulInfoCompleteFlag = False

        if not haulInfoCompleteFlag:
            #  the form is incomplete - ask the user if they want to close it or fix it
            self.incomplete = True
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                    'Haul information has not been completely ' +
                    'entered! Do you still want to close this form?', 'choice')
            ok = self.message.exec()
            if ok:
                #  force the exit with an incomplete form
                self.forceExit = True
            else:
                #  we don't want to exit with an incomplete form
                self.forceExit = False

            #  either way, we don't write anything to the database so we return
            return

        # Insert or update the haul parameters and values for each main partition
        for i, partition in enumerate(self.partitions):
            for j, parameter in enumerate(self.parameters):
                sql = ("SELECT event_parameter FROM " + self.schema + ".event_data WHERE ship=" + self.ship + " AND survey=" + self.survey +
                       " AND event_id=" + self.activeHaul + " AND partition='" + partition +
                       "' AND event_parameter='" + parameter + "'")
                query = self.db.dbQuery(sql)
                val, = query.first()
                if val is not None:
                    #  There is an existing record - update it with new values
                    sql = ("UPDATE " + self.schema + ".event_data SET parameter_value='" + self.haulInfoBtns[j][i].text() +
                        "' WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND event_id=" +
                        self.activeHaul + " AND partition='" + partition +
                        "' AND event_parameter='" + parameter + "'")
                else:
                    #  This is a new record - insert it
                    sql = ("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, event_parameter," +
                        " parameter_value) VALUES ("+ self.ship + "," + self.survey + "," +
                        self.activeHaul + ",'" + partition + "','" + parameter +
                        "','" + self.haulInfoBtns[j][i].text() + "')")
                self.db.dbExec(sql)

        #  Now update the haul info data for pocketnets (i.e. partitions named like
        #  'pocketnet' or 'pnet'). These are ALWAYS set to "not_subsampled".
        #  first query the pocketnet partitions.
        sql = ("SELECT partition FROM " + self.schema + ".GEAR_OPTIONS, " + self.schema + ".EVENTS WHERE GEAR_OPTIONS.GEAR = " +
                "EVENTS.GEAR and EVENTS.SHIP = " + self.ship + "  AND  " + "EVENTS.SURVEY = " +
                self.survey + " AND EVENTS.EVENT_ID = " + self.activeHaul +
                " AND (LOWER(GEAR_OPTIONS.PARTITION) LIKE 'p-net' OR " +
                "LOWER(GEAR_OPTIONS.PARTITION) LIKE '%pocketnet%')")
        query = self.db.dbQuery(sql)

        #  if there are pocketnets, check if PartitionWeight param exists. If not, we assume
        #  that this is the first time we have run the Haul form for this event and insert
        #  and insert the PartitionWeightType and PartitionWeight parameters into event_data.
        for pnet_partition, in query:
            #  check if the haul info is already in the database for this partition
            sql = ("SELECT event_data.event_parameter FROM " + self.schema + ".event_data WHERE event_data.ship = " +
                    self.ship + "  AND event_data.SURVEY = " + self.survey + " AND event_data.EVENT_ID = " +
                    self.activeHaul + " AND event_data.partition = '" + pnet_partition +
                    "' AND event_data.event_parameter = 'PartitionWeight'")
            query2 = self.db.dbQuery(sql)
            hasParam, = query2.first()

            #  if PartitionWeight doesn't exist, then insert the PartitionWeightType and
            #  PartitionWeight parameters.
            if not hasParam:
                sql = ("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, event_parameter," +
                        "parameter_value) VALUES (" + self.ship+ "," + self.survey + "," + self.activeHaul +
                        ",'" + pnet_partition + "', 'PartitionWeightType','not_subsampled')")
                self.db.dbExec(sql)
                sql = ("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, event_parameter," +
                        "parameter_value) VALUES (" + self.ship + "," + self.survey + "," +
                        self.activeHaul+ ",'" + pnet_partition + "','PartitionWeight','TBD')")
                self.db.dbExec(sql)

        #  Methot and Bongo hauls are also never subsampled so we always set their
        #  PartitionWeightType to not_subsampled and PartitionWeight 'TBD'.
        if (self.gearType == 'PlanktonNet'):
            sql = ("SELECT event_parameter FROM " + self.schema + ".event_data WHERE ship=" + self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                    " AND event_parameter='PartitionWeightType'")
            query = self.db.dbQuery(sql)
            hasParam, = query.first()
            if not hasParam:
                sql = ("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, event_parameter," +
                        "parameter_value) VALUES (" + self.ship+ "," + self.survey + "," +
                        self.activeHaul + ",'Codend','PartitionWeightType','not_subsampled')")
                self.db.dbExec(sql)
                sql = ("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, event_parameter," +
                        "parameter_value) VALUES (" + self.ship+ "," + self.survey + "," +
                        self.activeHaul + ",'Codend','PartitionWeight','TBD')")
                self.db.dbExec(sql)

        #  update the performance - if the user interacted with the combobox we will update
        #  the event performance code in the database
        if self.perfBoxFlag:
            perfCode = self.performanceCodes[self.perfBox.currentIndex()]
            sql = ("UPDATE " + self.schema + ".events SET performance_code="+perfCode+ " WHERE ship=" + self.ship+
                    " AND survey=" + self.survey+ " AND event_id = " + self.activeHaul)
            self.db.dbExec(sql)


    def setFlag(self):
        '''setFlag is called when the user clicks the performance combobox. We assume
        that if they interact with the perf combobox, then we update the event performance
        code. This method just sets a flag to trigger the update when the haul data is
        inserted/updated in the database.
        '''
        self.perfBoxFlag = True


    def getPerfList(self):
        '''getPerfList is called both when the form is initialize and when the
        "show full performance code list" checkbox is checked. It loads the
        appropriate list ("short" and "long") and the trys to set the combobox
        index to the current performance code. If, somehow, a performance code
        is not set, it will load the long list and set the combobox index to
        -1 to force the user to set a valid performance code.
        '''

        #  initialize our bits
        comboInd = -1
        self.perfBox.clear()
        self.performanceCodes = []

        #  if the "long" list checkbox is NOT checked, first get the "short"
        #  performance list and check if the curent perf code is in that list
        if not self.perfCheckBox.isChecked():
            #  get the short list
            sql = ("SELECT event_performance.performance_code, event_performance.description " +
                    "FROM " + self.schema + ".event_performance INNER JOIN " + self.schema + ".gear_options ON event_performance.performance_code" +
                    "= gear_options.performance_code WHERE (((gear_options.gear)='" +
                    self.gearLabel.text() + "')) ORDER BY gear_options.perf_gui_order")
            query = self.db.dbQuery(sql)
            for perfCode, description in query:
                self.perfBox.addItem(description)
                self.performanceCodes.append(perfCode)

        #  check if the current performance code is in the short list
        if self.perfCode in self.performanceCodes:
            #  it is, get the index so we can set the combobox
            comboInd = self.performanceCodes.index(self.perfCode)
        else:
            #  it isn't, get the full list and check if it is in that
            self.perfBox.clear()
            self.performanceCodes = []

            sql = ("SELECT event_performance.performance_code, event_performance.description " +
                    "FROM " + self.schema + ".event_performance")
            query = self.db.dbQuery(sql)
            for perfCode, description in query:
                self.perfBox.addItem(description)
                self.performanceCodes.append(perfCode)

            #  set the "full list" checkbox since we now loaded the full list
            self.perfCheckBox.setCheckState(Qt.CheckState.Checked)

            #  now see if the perf code is in the full list
            if self.perfCode in self.performanceCodes:
                comboInd = self.performanceCodes.index(self.perfCode)

        #  set the combobox index to the current performance code
        self.perfBox.setCurrentIndex(comboInd)

        #  reset our perf code changed flag
        self.perfBoxFlag = False


    def getComment(self):
        '''getComment is called when the user clicks the "Comment" button on the form.
        It displays the current comment text in the keyboard dialog allowing the user
        to read and edit the comment using the on-screen touch keyboard.
        '''

        #  create the keyboard dialog and set the comment text
        keyDialog = keypad.KeyPad(self.comment, self)

        #  display it
        keyDialog.exec()

        #  if the user clicked "OK" when closing, update the database
        if keyDialog.okFlag:
            self.comment = keyDialog.dispEdit.toPlainText()
            sql = ("UPDATE " + self.schema + ".events SET comments='" + self.comment + "' WHERE ship=" +
                    self.ship + " AND survey=" + self.survey+ " AND event_id = " +
                    self.activeHaul)
            self.db.dbExec(sql)


    def closeEvent(self, event):
        '''closeEvent is called when the dialog is closed. It runs some checks
        and if ok, writes the data to the database. If not, it asks the
        user if they want to go back and complete the form or exit anyways
        and write whatever data is available.
        '''

        #  check if we're all filled in and write data to database
        self.writeHaul()

        #  check if our form was complete
        if self.incomplete:
            #  form is not complete - check if we're to exit anyways
            if (self.forceExit):
                #  user opted to exit without completing form
                event.setAccepted(False)
                self.reject()
            else:
                #  user has chosen to return to the form to complete it
                event.ignore()
        else:
            #  form is complete - we're done here
            event.accept()
            self.accept()

        #  store the application size and position
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
