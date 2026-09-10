'''
    The CLAMS MACE Trawl event dialog. This form provides the MACE trawl event form and
    actions for CLAMS.
'''

#  import
from PyQt4.QtCore import *  
from PyQt4.QtGui import *
from PyQt4 import QtSql
from ui.xga import ui_ABLTrawlEvent
import numpad
import keypad
import messagedlg
import listseldialog
import netdlg
import timedlg
from acquisition.scs import QSCSClient

class mooringEvent(QDialog, ui_ABLTrawlEvent.Ui_ABLTrawlEvent):


    def __init__(self, parent=None):
        '''
            The CLAMS Trawl event dialog initialization method. Gets basic information
            and sets up the haul form
        '''

        #  call superclass init methods and GUI form setup method
        super(mooringEvent, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        #  copy some properties from our parent
        self.db = parent.db
        self.schema = parent.schema
        self.activeEvent=parent.activeEvent
        self.survey=parent.survey
        self.ship=parent.ship
        self.backLogger=parent.backLogger
        self.settings=parent.settings
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.workStation=parent.workStation
        self.birdStatus=parent.birdStatus
        self.mammalStatus=parent.mammalStatus
        self.testing=parent.testing
        self.reloaded = parent.reloaded

        #  setup reoccuring dialogs
        self.numpad = numpad.NumPad(self)
        self.message = messagedlg.MessageDlg(self)
        self.timeDlg = timedlg.TimeDlg(self)
        self.timeDlg.enableGetTimeButton(False)
        self.netdlg=netdlg.NetDlg(self)

        #  define default variable values
        self.fishingFlag=False
        self.recording=False
        self.abort = False
        self.displayMeasurements=['Latitude', 'Longitude']
        self.gearKey = []
        self.comment = ""
        self.incomplete = False
        self.gaCBList = [self.accessBox1, self.accessBox2, self.accessBox3, self.accessBox4]
        self.gaLabelList = [self.accessLabel1, self.accessLabel2, self.accessLabel3, self.accessLabel4]
        self.buttons=[self.btn1,self.btn2,self.btn3,self.btn4,self.btn5,self.btn6,self.btn7,self.btn8,self.btn9,self.btn10]
        self.eventTimer=QTime()
        self.recordStream=False
        self.dispVector=['','']
        self.SCSPollRate = 1
        self.reloaded=False

        #  max number of seconds data extracted from haul_stream_data during event button edits
        #  are allow to differ from the new event time. This is the half window size. The closest
        #  value to the edit time within this window is used.
        self.streamWindowSeconds = 5

        #  set the SCS logging rate default values
        self.streamEQHBLogInterval = 2
        self.streamSlowLogInterval = 5
        self.SCSLogInterval = self.streamSlowLogInterval

        #  set the SCS "last write" time used to track SCS logging interval
        self.lastSCSWriteTime = QDateTime.currentDateTime()

        # color palettes
        self.red=QPalette()
        self.red.setColor(QPalette.ButtonText,QColor(230, 0, 0))
        self.green=QPalette()
        self.green.setColor(QPalette.ButtonText,QColor(0, 230, 0))
        self.yellow=QPalette()
        self.yellow.setColor(QPalette.ButtonText,QColor(180, 180, 0))
        self.haulLabel.setText(self.activeEvent)

        #  create an instance of the SCS client
        self.scsClient = QSCSClient.QSCSClient(str(self.settings[QString('SCSHost')]),
                str(self.settings[QString('SCSPort')]))

        #  attempt to connect to the SCS server
        if not self.testing:
            self.setupSCS()

        #  connect signals...
        self.connect(self.gearBox, SIGNAL("activated(int)"), self.getOptions)
        self.connect(self.netDimBtn, SIGNAL("clicked()"), self.getNetDims)
        self.connect(self.transBtn, SIGNAL("clicked()"), self.getTransect)
        self.connect(self.stratumBtn, SIGNAL("clicked()"), self.getStratum)
        self.connect(self.commentBtn, SIGNAL("clicked()"), self.getComment)
        self.connect(self.doneBtn, SIGNAL("clicked()"), self.goExit)
        self.connect(self.scsClient, SIGNAL("SCSGetReceived"), self.writeStream)
        self.connect(self.scsClient, SIGNAL("SCSError"), self.errorSCS)
        self.connect(self.perfCheckBox, SIGNAL("stateChanged(int)"), self.getFullPerfList)
        #  signals for ABL modified form
        self.connect(self.stnBtn, SIGNAL("clicked()"), self.getStation)
        self.connect(self.depthStartBtn, SIGNAL("clicked()"),self.getDepthStart)
        self.connect(self.depthEndBtn, SIGNAL("clicked()"),self.getDepthEnd)

        for btn in self.buttons:
            self.connect(btn, SIGNAL("clicked()"), self.getEventData)

        # setup table
        self.dataTable.verticalHeader().setVisible(False)
        for i in range(4):
            self.dataTable.setColumnWidth(i, self.dataTable.width()/4)

        # make a bunch of buttons no longer used
        self.label_27.setText('')
        self.label_28.setText('')
        self.label_29.setText('')
        self.label_30.setText('')
        self.label_31.setText('Bot. Depth')
        
        self.stnBtn.setVisible(False)
        self.transBtn.setVisible(False)
        self.stratumBtn.setVisible(False)
        self.depthEndBtn.setVisible(False)
        
        
        #  set up the event duration timer
        self.timer = QTimer(self)
        self.connect(self.timer, SIGNAL("timeout()"), self.displayTime)

        #  set up the initialization timer
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        self.connect(initTimer, SIGNAL("timeout()"), self.initTrawlEventDialog)
        initTimer.start(0)


    def initTrawlEventDialog(self):

        #  query out the "slow" and "fast" SCS write to database rates. These rates do not affect polling
        #  only the rate at which data is written to event_stream_data. This is done to limit the amount
        #  of data that is written to this table as it is becoming a query performance issue.
        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".application_configuration " +
                "WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND parameter='EventStreamEQHBLogInt'")
        if query.first():
            (val,ok) = query.value(0).toInt()
            if ok:
                self.streamEQHBLogInterval = val
        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".application_configuration " +
                "WHERE ship=" + self.ship + " AND survey=" + self.survey + " AND parameter='EventStreamPreEQLogInt'")
        if query.first():
            (val,ok) = query.value(0).toInt()
            if ok:
                self.self.streamSlowLogInterval = val

        #  populate the gear combobox
        self.gear = []
        self.gearBox.setEnabled(True)
        query = QtSql.QSqlQuery("SELECT gear FROM " + self.schema + ".gear WHERE active=1 " +
                " AND gear_type = 'Mooring_Station' ORDER BY gear_gui_order", self.db)
        while query.next():
            self.gearBox.addItem(query.value(0).toString())
        self.gearBox.setCurrentIndex(0)

        # if this is a restart or continuation of an already started event, reload previously collected data
        query=QtSql.QSqlQuery("SELECT * FROM " + self.schema + ".events WHERE ship=" + self.ship +
                " AND survey=" + self.survey + " AND event_id=" + self.activeEvent)
        if query.first():
            #  this is a restart so reload any existing data
            self.reloaded = True
            self.reloadData()
        else:
            #  this is a new event - get scientist
            query=QtSql.QSqlQuery("SELECT personnel.scientist FROM " + self.schema + ".personnel WHERE " +
                    "personnel.active=1 ORDER BY personnel.scientist", self.db)
            # populate scientist list
            self.sciList=[]
            while query.next():
                self.sciList.append(query.value(0).toString())
            #  present the sci selection dialog
            self.listDialog = listseldialog.ListSelDialog(self.sciList, self)
            self.listDialog.label.setText('Identify yourself, please.')
            if self.listDialog.exec_():
                #  sci selected
                self.scientist = self.listDialog.itemList.currentItem().text()
                self.sciLabel.setText(self.scientist)
            else:
                #  scientist selection aborted - exit
                self.abort = True
                self.close()
        # PUT IN error dialog!!
        # update the form with the marine mammal interaction status
        if self.mammalStatus=='Y':
            self.marMammalBox.setChecked(True)
        else:
            self.marMammalBox.setChecked(False)
        if self.birdStatus=='Y':
            self.seaBirdBox.setChecked(True)
        else:
            self.seaBirdBox.setChecked(False)


    def getNetDims(self):
        """
        getNetDims is called when the user hits EQ or Haulback or the NetDims button
        """
        #  reload the net dimension values
        self.netdlg.reloadData

        #  display the dialog
        self.netdlg.exec_()


    def reloadData(self):
        """
        reloadData populates the form with whatever data exists in the database for this event
        """
        #populate gear type, scientist
        queryOld = QtSql.QSqlQuery("SELECT gear, event_type, performance_code, scientist, comments " +
                    "FROM " + self.schema + ".events WHERE ship=" +self.ship +
                    " AND survey=" + self.survey + " AND event_id=" + self.activeEvent, self.db)
        # get values
        queryOld.first()

        # set event_id gear type
        ind = self.gearBox.findText(queryOld.value(0).toString())
        self.gear=queryOld.value(0).toString()
        self.gearBox.setCurrentIndex(ind)
        self.scientist=queryOld.value(3).toString()
        self.comment=queryOld.value(4).toString()

        #populate lists
        self.getOptions()

        #set up selections
        if queryOld.value(1).toString() in self.typeCode:
            ind=self.typeCode.index(queryOld.value(1).toString())
        else:
            ind=-1
        self.typeBox.setCurrentIndex(ind)
        self.sciLabel.setText(self.scientist)

        # get from short list, otherwise, get full list
        if queryOld.value(2).toString() in self.perfCode:
            ind=self.perfCode.index(queryOld.value(2).toString())
        else:
            self.perfCheckBox.setCheckState(Qt.Checked)
            self.getFullPerfList()
            ind=-1
            if queryOld.value(2).toString() in self.perfCode:
                ind=self.perfCode.index(queryOld.value(2).toString())
        self.perfBox.setCurrentIndex(ind)

        #get report
        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+self.ship+
            " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='Stratum'")
        if query.first():
            self.stratumBtn.setText(query.value(0).toString())

        #get starting depth
        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+self.ship+
            " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='BottomDepth'")
        if query.first():
            self.depthStartBtn.setText(query.value(0).toString())

        # reload marine mammal and endangered bird boxes
        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+self.ship+
            " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='MarineMammalPresent'")
        query.first()
        if query.value(0).toString()=='Y':
            self.marMammalBox.setChecked(True)
        else:
            self.marMammalBox.setChecked(False)

        query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+self.ship+
            " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='EndangeredSeabirdPresent'")
        query.first()
        if query.value(0).toString()=='Y':
            self.seaBirdBox.setChecked(True)
        else:
            self.seaBirdBox.setChecked(False)

        # reload buttontimes
        row=0
        for btn in self.buttons:
            if btn.text().startsWith('C'):
                g=str(btn.text())
                partition='Codend_'+g[1]
                parameter=[g.split(' ')[1]]
            elif btn.text() in ['EQ', 'Haulback']:
                partition='Codend'
                parameter=[btn.text()]
            else:
                partition='MainTrawl'
                parameter=[btn.text()]

            query = QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship=" +
                    self.ship + " AND survey=" + self.survey + " AND event_id=" + self.activeEvent +
                    " AND partition='" + partition + "' AND event_parameter='" + parameter[0] + "'")

            if query.first():
                #  update the button's table values
                self.dataTable.setItem(row, 0, QTableWidgetItem(query.value(0).toString()))
                self.btnTimes[row]=QDateTime().fromString(query.value(0).toString(), 'MMddyyyy hh:mm:ss.zzz')
                buttonValues = self.getEventStreamValues(query.value(0).toString(), self.displayMeasurements)
                self.dataTable.setItem(row, 1, QTableWidgetItem(buttonValues[0]))
                self.dataTable.setItem(row, 2, QTableWidgetItem(buttonValues[1]))
                try:
                    self.dataTable.setItem(row, 3, QTableWidgetItem(buttonValues[2]))
                except:
                    pass
                self.buttons[row].setPalette(self.green)
            row+=1

        self.gearBox.setEnabled(False)

        #  check if this event has been completed. Completed is defined as having EQ and Haulback
        #  data. Once an event is completed, we only allow editing and do not collect stream data.
        for i in range(len(self.btnTimes)):
            #  check if either EQ or HB buttons are "empty"
            if self.btnTimes[i]==None and (self.buttons[i].text().endsWith('Released')):
                #  one of them is not complete - ask if we should consider this a live event
                reply = QMessageBox.question(self, 'Achtung!',"<font size = 14>This event was not completed. " +
                        "Is this event still taking place?</font>", QMessageBox.Yes, QMessageBox.No)
                if reply==QMessageBox.Yes:
                    #  this event is ongoing - set up for an active event

                    #  determine what SCS logging rate we should use
                    if self.btnTimes[i]==None and self.buttons[i].text().endsWith('Released'):
                        #  EQ has not been pressed yet
                        self.SCSLogInterval = self.streamSlowLogInterval
                        self.fishingFlag=False
                    else:
                        #  EQ has been pressed, but not HB
                        self.SCSLogInterval = self.streamEQHBLogInterval
                        self.fishingFlag=True

                    #  set other state variables for a "live" event
                    self.reloaded=False
                    self.recordStream=True
                    self.netdlg.reloaded = False
                else:
                    #  this is not a live event - treat this as an edit after the fact
                    self.reloaded=True
                    self.recordStream=False
                break

        #  brute force, but loop through again checking if BOTH EQ and HB have been pressed - if so,
        #  inform the user that they can only edit and not collect new data.
        nCompletedButtons = 0
        for i in range(len(self.btnTimes)):
            if self.btnTimes[i] <> None and (self.buttons[i].text().endsWith('Released') or self.buttons[i].text().endsWith('OnDeck')):
                nCompletedButtons = nCompletedButtons + 1
        if nCompletedButtons == 2:
            QMessageBox.information(self, 'Kipaumbele!',"<font size=14>This haul appears to have been completed. " +
                    "You can only edit it. New time values must be within the original time span of the event. " +
                    "No new stream data will be recorded.</font>", QMessageBox.Ok)
        if nCompletedButtons > 0:
            self.fishingFlag = False


    def getOptions(self):

        self.gear = self.gearBox.currentText()
        self.fishingFlag = True
        # ENABLE BOXES
        self.optionsGroup.setEnabled(True)
        self.buttonsGroup.setEnabled(True)

        #  populate haul type combo box
        query = QtSql.QSqlQuery("SELECT " + self.schema + ".event_types.event_type, " + self.schema +
                ".event_types.description FROM " + self.schema + ".event_types INNER JOIN " + self.schema +
                ".gear_options ON " + self.schema + ".event_types.event_type = " + self.schema +
                ".gear_options.event_type WHERE (((" + self.schema + ".gear_options.gear)='" + self.gear + "')) " +
                "ORDER BY " + self.schema + ".gear_options.haultype_gui_order")
        self.typeBox.setEnabled(True)
        self.typeCode = []
        self.typeBox.clear()
        while query.next():
            self.typeBox.addItem(query.value(1).toString())
            self.typeCode.append(query.value(0).toString())
        self.typeBox.setCurrentIndex(-1)

        #  populate gear performance combo box
        query = QtSql.QSqlQuery("SELECT " + self.schema + ".event_performance.performance_code, " + self.schema +
                ".event_performance.description FROM " + self.schema + ".event_performance INNER JOIN " + self.schema +
                ".gear_options ON " + self.schema + ".event_performance.performance_code = " + self.schema +
                ".gear_options.performance_code WHERE " + "(((" + self.schema + ".gear_options.gear)='" +
                self.gear + "')) ORDER BY " + self.schema + ".gear_options.perf_gui_order")
        self.perfBox.setEnabled(True)
        self.perfCode=[]
        self.perfBox.clear()
        while query.next():
            self.perfBox.addItem(query.value(1).toString())
            self.perfCode.append(query.value(0).toString())
        self.perfBox.setCurrentIndex(-1)


        for btn in self.buttons:
            btn.hide()
        # setup the action buttons
        query = QtSql.QSqlQuery("SELECT event_parameter FROM " + self.schema + ".gear_options WHERE gear='" +
                self.gear + "' AND event_parameter IS NOT NULL ORDER BY haultype_gui_order")
        cnt=0
        self.btnTimes=[]
        if not self.reloaded:
            self.recordStream=True
        cntx=1
        while query.next():
            self.buttons[cnt].show()

            if query.value(0).toString() in ['EQ','Haulback']:
                if self.gear in ['MOCC','Tucker']:
                    txt="C" + str(cntx) + " " + query.value(0).toString()
                    if query.value(0).toString() == 'Haulback':
                        cntx+=1
                else:
                    txt=query.value(0).toString()
                self.buttons[cnt].setPalette(self.red)
            else:
                txt=query.value(0).toString()
                self.buttons[cnt].setPalette(self.yellow)
            self.buttons[cnt].setText(txt)

            self.btnTimes.append(None)
            cnt=cnt+1
        self.endbutton=cnt-1
        self.dataTable.setRowCount(10)

        for i in range (10):
            self.dataTable.setRowHeight(i, 42)

        self.typeBoxFlag=False
        self.perfBoxFlag=False
        self.accessBox1Flag=False
        self.accessBox2Flag=False
        self.accessBox3Flag=False


    def displayTime(self):
        self.eventTimer=self.eventTimer.addSecs(1)
        self.elapseLabel.setText(self.eventTimer.toString('mm:ss'))


    def getEventStreamValues(self, time, parameters):
        """
        queryEventStreamValues queries the event_data_stream table for the specified parameter
        values at the specified time and returns the value closest to the time. If data is not
        available within the defined time window, empty strings are returned.

        ALL VALUES ARE RETURNED AS STRINGS
        """
        #  check that we've been given a list of one or more params
        if len(parameters) == 0 or not isinstance(parameters,list):
            return ''

        #  set up our default return value
        retVal = [''] * len(parameters)
        dt = [float('inf')] * len(parameters)

        #  convert our time to a QDateTime
        time = QDateTime().fromString(time, 'MMddyyyy hh:mm:ss.zzz')

        #  query the data from haul_stream data table within our window
        inClause = "'" + "','".join(parameters) + "'"
        query=QtSql.QSqlQuery("SELECT time_stamp,measurement_type,measurement_value FROM " + self.schema +
                ".event_stream_data WHERE time_stamp between to_timestamp('"+
                time.addSecs(-self.streamWindowSeconds).toString('MMddyyyy hh:mm:ss.zzz') +
                "','MMDDYYYY HH24:MI:SS.FF3') and to_timestamp('"+
                time.addSecs(self.streamWindowSeconds).toString('MMddyyyy hh:mm:ss.zzz') +
                "','MMDDYYYY HH24:MI:SS.FF3') AND measurement_type IN (" + inClause + ")")

        #  loop thru the returned values
        while query.next():
            try:
                #  get the index into our return array
                i = parameters.index(query.value(1).toString())
                #  calculate the time difference between this row and our specified time
                timeDiff = abs(QDateTime.fromString(query.value(0).toString(), 'MMddyyyy hh:mm:ss.zzz').secsTo(time))
                #  check if this delta is smaller
                if timeDiff < dt[i]:
                    #  difference is smaller, save this value
                    dt[i] = timeDiff
                    retVal[i] = query.value(2).toString()
            except:
                #  this is not the parameter we're looking for
                pass

        return retVal


    def getEventData(self):

        if not self.recording:
            self.writeHaulRecord()
            self.timer.start(1000)
            self.gearBox.setEnabled(False)
            self.recording=True

        #  get the index of the event action button that was pressed
        ind=self.buttons.index(self.sender())

        # get correct parameter
        time = str(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss.zzz'))
        lat = self.dispVector[0]
        lon = self.dispVector[1]
        g = str(self.buttons[ind].text())

        print self.buttons[ind].text()

        if self.buttons[ind].text().endsWith('Released'):
            
            partition='MainTrawl'
            parameter=['Released', 'EQLatitude', 'EQLongitude']
            if not self.reloaded:
                self.fishingFlag=False
                self.SCSLogInterval = self.streamEQHBLogInterval
                #self.netdlg.setTime=time
        else:
            partition='MainTrawl'
            parameter=[self.buttons[ind].text()]


        #  check to see if we already have data for this button in the database
        gotVal=False
        query = QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship=" + self.ship +
                " AND survey=" + self.survey + "AND partition='" + partition + "' AND event_parameter='" + parameter[0] +
                "' AND event_id=" + self.activeEvent)
        if query.first():
            #  a value is already in the database for this button
            gotVal=True

        #  at this point we can be either be in the middle of a new haul or editing a previous haul
        #  we behave differently when editing vs running a new event so we branch here. This logic
        #  could probably be cleaned up a bit (lots of code replication) but it works...

        #  if we're editing a past haul (or continuing a haul after exiting out)
        if self.reloaded:
            if ind>0:
                #  check if we should set the time of the edit time dialog to the existing time for this button
                if self.btnTimes[ind-1]<>None:
                    self.timeDlg.setTime(str(self.btnTimes[ind-1].toString('MMddyyyy hh:mm:ss.zzz')))

            #  if there is already data recorded for this button inform the user they will be overwriting it
            if self.dataTable.item(ind, 0)<>None:
                reply = QMessageBox.question(self, 'Achtung!',"<font size = 14>This will change the button time, " +
                        "and if this is an EQ or HB button the GPS location of this button press. Are you " +
                        "sure you want to do this?</font>", QMessageBox.Yes, QMessageBox.No)
                if reply==QMessageBox.No:
                    #  user cancelled edit - nothing to do
                    return
                else:
                    #  set the time dialog with the existing time for this button
                    self.timeDlg.setTime(str(self.dataTable.item(ind, 0).text()))

            #  show the time select dialog so the user can change the time
            if self.timeDlg.exec_():
                #  get the new time from the dialog
                time = self.timeDlg.time

                #  try to get a new lat/lon for the specified time so we can update these values if needed
                self.dispVector = self.getEventStreamValues(time, self.displayMeasurements)

                #  check if we got stream data
                if self.dispVector[0] == '':
                    #  we did not find any data, the time range must be outside the range of the available
                    #  event_stream_data. Warn the user if this is a event action that has stream data
                    #  values in the event_data table (like EQ and HB positions)
                    ok = QMessageBox.warning(self, 'Attenzione!',"<font size=14>The new event time appears to " +
                            "be out of the time span of the original event as no event stream data is " +
                            "available. If you continue, any existing data beyond time associated with " +
                            "this action will be erased. Are you SURE you want to do this?</font>",
                            QMessageBox.No | QMessageBox.Yes, QMessageBox.No)

                    if ok == QMessageBox.No:
                        #  user aborted edit
                        return

                #  extract the lat/lon
                lat = self.dispVector[0]
                lon = self.dispVector[1]

                # check if we've already have an entry for this button
                if not gotVal:
                    #  no previous data - insert
                    query=QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition, " +
                            "event_parameter, parameter_value) VALUES ("+ self.ship+","+self.survey+"," +
                            self.activeEvent + ",'" + partition + "','" + parameter[0] + "','" + time + "')")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())


                    if len(parameter)>0:
                        #  this is an EQ or Haulback button so we insert a GPS location too
                        query=QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, " +
                                "partition, event_parameter, parameter_value) VALUES ("+ self.ship+","+self.survey+
                                ","+self.activeEvent+",'"+partition+"','"+parameter[1]+"','"+ lat+"')")
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
                        query=QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, " +
                                "partition, event_parameter, parameter_value) VALUES ("+ self.ship+","+
                                self.survey+","+self.activeEvent+",'"+partition+"','"+parameter[2]+"','" + lon+"')")
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

                else:
                    #  data exists for this button - update record
                    query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+time+"' WHERE "+
                            "ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeEvent+
                            " AND partition='" + partition + "' AND event_parameter='" + parameter[0]+"'")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

                    if len(parameter)>1:
                        #  this is an EQ or Haulback button so we update the GPS location too
                        query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+lat+
                                "' WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id="+
                                self.activeEvent+" AND partition='"+partition+ "' AND event_parameter='"+
                                parameter[1]+"'")
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
                        query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+lon+
                                "' WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id="+
                                self.activeEvent+" AND partition='"+partition+ "' AND event_parameter='"+
                                parameter[2]+"'")
                        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            else:
                #  user cancelled the time edit dialog - nothing to do
                return
        else:
            #  we're not editing a past haul and are currently in the middle of an event

            # check if we've already have an entry for this button
            if gotVal:
                reply = QMessageBox.question(self, 'Achtung!',"<font size = 14>You've already pressed the " +
                        self.buttons[ind].text() + " button, are you sure you want to do this?\n" +
                        "Doing so will overwrite the data in the database with current values.</font>",
                        QMessageBox.Yes, QMessageBox.No)
                if reply==QMessageBox.No:
                    #  user cancelled - nothing to do
                    return

                #  data exists for this button - update record
                query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+time+"' WHERE "+
                        "ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeEvent+
                        " AND partition='" + partition + "' AND event_parameter='" + parameter[0]+"'")
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

                if len(parameter)>1:
                    #  this is an EQ or Haulback button so we update the GPS location too
                    query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+lat+
                            "' WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id="+
                            self.activeEvent+" AND partition='"+partition+ "' AND event_parameter='"+
                            parameter[1]+"'")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
                    query=QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+lon+
                            "' WHERE ship="+self.ship+" AND survey="+self.survey+" AND event_id="+
                            self.activeEvent+" AND partition='"+partition+ "' AND event_parameter='"+
                            parameter[2]+"'")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            else:
                # this is a new record for this button
                query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, " +
                        "partition, event_parameter, parameter_value) VALUES ("+ self.ship+","+self.survey+","+
                        self.activeEvent + ",'" + partition + "','" + parameter[0] + "','" + time+"')")
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

                #  this is an EQ or Haulback button so we insert a GPS location too
                if len(parameter)>1:
                    query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, " +
                            "partition, event_parameter, parameter_value) VALUES (" + self.ship + "," + self.survey +
                            ","+self.activeEvent+",'"+partition+"','"+parameter[1]+"','"+ lat+"')")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
                    query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, " +
                            "partition, event_parameter, parameter_value) VALUES (" + self.ship + ","+self.survey+","+
                            self.activeEvent + ",'"+partition + "','" + parameter[2] + "','" + lon + "')")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            #  display the net dimensions dialog is this was an EQ or HB button press
          #  if len(parameter)>1 and self.gear <> 'CTD':
           #     QTimer.singleShot(500,self.getNetDims)

        #  reset the event timer
        self.eventTimer.setHMS(0, 0, 0, 0)

        # query data back for validation
        query = QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+
                self.ship+" AND survey="+self.survey+" AND partition='"+  partition+"' AND event_parameter='"+
                parameter[0]+"' AND event_id="+self.activeEvent)

        #  display the data if the query (and this insert/update) was successful
        if query.first():
            self.buttons[ind].setPalette(self.green)
            self.dataTable.setItem(ind, 0, QTableWidgetItem(time))
            self.dataTable.setItem(ind, 1, QTableWidgetItem(self.dispVector[0]))
            self.dataTable.setItem(ind, 2, QTableWidgetItem(self.dispVector[1]))
            #self.dataTable.setItem(ind, 3, QTableWidgetItem(self.dispVector[2]))

        #  clear the display values
        self.dispVector=['', '']


    def getTransect(self):
        self.numpad.msgLabel.setText("Enter transect")
        if not self.numpad.exec_():
            return
        self.transBtn.setText(self.numpad.value)
        self.dirty=True


    def getStratum(self):
        self.numpad.msgLabel.setText("Enter Stratum")
        if not self.numpad.exec_():
            return
        self.stratumBtn.setText(self.numpad.value)
        self.dirty=True


    def getStation(self):
        self.numpad.msgLabel.setText("Enter station")
        if not self.numpad.exec_():
            return
        self.stnBtn.setText(self.numpad.value)
        self.dirty=True


    def getDepthStart(self):
        self.numpad.msgLabel.setText("Enter starting bottom depth")
        if not self.numpad.exec_():
            return
        self.depthStartBtn.setText(self.numpad.value)
        self.dirty=True


    def getDepthEnd(self):
        self.numpad.msgLabel.setText("Enter ending bottom depth")
        if not self.numpad.exec_():
            return
        self.depthEndBtn.setText(self.numpad.value)
        self.dirty=True


    def writeHaulRecord(self):
        # write to haul table
        query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".events (ship, survey, event_id, gear,  event_type, performance_code, "+
                "scientist, comments) VALUES ("+self.ship+","+self.survey+","+self.activeEvent+",'"+self.gear+
                "',0,0,'"+self.scientist+"','"+self.comment+"') ")
        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
        query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition,  event_parameter,  parameter_value) VALUES ("+
                                            self.ship+","+self.survey+","+self.activeEvent+",'MainTrawl','TrawlScientist','"+self.scientist+"')")
        self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())


    def stopStream(self):
        self.timer.stop()
        self.scsClient.disconnect()


    def setupSCS(self):
        # setup scs sensor list
        query = QtSql.QSqlQuery("SELECT " + self.schema + ".measurement_setup.measurement_type, " + self.schema +
                ".devices.device_id, " + self.schema + ".devices.device_name, " + self.schema +
                ".measurement_setup.device_interface FROM " + self.schema + ".measurement_setup, " +
                self.schema + ".devices " + "WHERE " + self.schema + ".measurement_setup.device_id=" +
                self.schema + ".devices.device_id AND "+ self.schema + ".measurement_setup.workstation_id=" +
                self.workStation+" AND " + self.schema + ".measurement_setup.gui_module='TrawlEvent'")
        self.sensorList=[]
        self.devices=[]
        self.deviceNames=[]
        self.measureTypes=[]
        while query.next():
            self.measureTypes.append(query.value(0).toString())
            self.devices.append(query.value(1).toString())
            self.deviceNames.append(query.value(2).toString())
            if query.value(3).toString()=='SCS':
                self.sensorList.append(str(query.value(2).toString()))

        #  create the SCS subscription
        self.scsSubscription = self.scsClient.subscribe(self.sensorList, self.SCSPollRate)
        try:
            #  initiate connection with SCS server
            self.scsClient.connect()
        except:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "Failed to connect to " +
                "SCS server - check port settings in application configuration!", 'info')
            self.message.exec_()


    def writeStream(self, data):
        """
        writeStream is called when we receive data from the SCS client.
        """

        #  check if we're recording data and return if not
        if not self.recordStream:
            return

        #  get the current time
        datetime = QDateTime.currentDateTime()
        time = str(datetime.toString('MMddyyyy hh:mm:ss.zzz'))

        #  iterate thru the the list of SCS sensor datagrams and write to database
        if self.testing:
            self.dispVector=['testlat', 'testlon']
        else:
            wroteToDb = False
            for sensor, value in data.iteritems():
                try:
                    #  get the index into the sensor list
                    idx = self.deviceNames.index(sensor)

                    # get the measurement type
                    measurement = self.measureTypes[idx]

                    #  get the value
                    val = value['data_value']

                    #  convert Lat/Lon to decimal degrees
                    if measurement in ['Latitude']:
                        val = self.convertDegToDecimalLat(val)
                    if measurement in ['Longitude']:
                        val = self.convertDegToDecimalLon(val)

                    #  check if we need to write this to the database
                    elapsedSecs = self.lastSCSWriteTime.secsTo(datetime)
                    if (elapsedSecs >= self.SCSLogInterval):
                        #  insert into the database
                        QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_stream_data (ship, survey, " +
                                "event_id, device_id, time_stamp, measurement_type, measurement_value) "+
                                "VALUES ("+self.ship+","+self.survey+","+self.activeEvent+"," +
                                self.devices[idx]+",'"+time+"','"+measurement+"','"+val+"')")
                        wroteToDb = True

                    # copy  measurements we use for display in the GUI
                    if measurement in self.displayMeasurements:
                        ind = self.displayMeasurements.index(measurement)
                        self.dispVector[ind] = val

                except:
                    #  this sensor is not in our sensor list so just ignore it.
                    #  This shouldn't ever happen though...
                    pass

            #  update the write time if we wrote to the db
            if wroteToDb:
                self.lastSCSWriteTime = datetime



    def getFullPerfList(self):
        """
        getFullPerfList queries out the full list of gear performance options from the database
        and
        """
        if self.perfCheckBox.checkState():
            query=QtSql.QSqlQuery("SELECT event_performance.performance_code, event_performance.description " +
                    "FROM " + self.schema + ".event_performance ORDER BY event_performance.performance_code DESC")
            self.perfBox.setEnabled(True)
            self.perfCode=[]
            self.perfBox.clear()
            while query.next(): # populate haul type list
                self.perfBox.addItem(query.value(1).toString())
                self.perfCode.append(query.value(0).toString())
            self.perfBox.setCurrentIndex(-1)
            self.perfBoxFlag=False
        else:
            query=QtSql.QSqlQuery("SELECT event_performance.performance_code, event_performance.description FROM "+
                    self.schema + ".event_performance INNER JOIN gear_options ON event_performance.performance_code" +
                    "=gear_options.performance_code WHERE (((gear_options.gear)='"+self.gearBox.currentText()+
                    "')) ORDER BY gear_options.perf_gui_order")
            self.perfBox.setEnabled(True)
            self.perfCode=[]
            self.perfBox.clear()
            while query.next(): # populate performance list
                self.perfBox.addItem(query.value(1).toString())
                self.perfCode.append(query.value(0).toString())
            self.perfBox.setCurrentIndex(-1)
            self.perfBoxFlag=False


    def computeMeans(self):

        inputMeasures=['NetHorizontalOpening', 'NetVerticalOpening', 'TrawlWireOut', 'HeadRopeDepth']
        if self.gear in ['MOCC', 'Tucker']:
            partitions=['Codend_1', 'Codend_2', 'Codend_3']
        else:
            partitions=['Codend']
        parameters=['EQ', 'Haulback']
        for p in partitions:
            query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+
            self.ship+" AND survey="+self.survey+" AND event_id= "+self.activeEvent+" AND partition='"+p+"' AND event_parameter = '"+parameters[0]+"'")
            if not query.first():
                continue
            eqTime=QDateTime().fromString(query.value(0).toString(),  'MMddyyyy hh:mm:ss.zzz')
            query=QtSql.QSqlQuery("SELECT parameter_value FROM " + self.schema + ".event_data WHERE ship="+
            self.ship+" AND survey="+self.survey+" AND event_id = "+self.activeEvent+" AND  partition='"+p+"' AND event_parameter = '"+parameters[1]+"'")
            if not query.first():
                continue
            hbTime=QDateTime().fromString(query.value(0).toString(),  'MMddyyyy hh:mm:ss.zzz')
            for m in inputMeasures:
                query=QtSql.QSqlQuery("SELECT measurement_value, to_char(time_stamp, 'MMDDYYYY HH24:MI:SS.FF3') FROM " + self.schema + ".event_stream_data WHERE time_stamp between to_timestamp('"+
                        eqTime.addMSecs(-500).toString('MMddyyyy hh:mm:ss.zzz')+"','MMDDYYYY HH24:MI:SS.FF3') and to_timestamp('"+
                        hbTime.addMSecs(500).toString('MMddyyyy hh:mm:ss.zzz')+"','MMDDYYYY HH24:MI:SS.FF3') AND measurement_type='"+m+"'")
                vals=[]
                times=[]
                while query.next():
                    vals.append(query.value(0).toFloat()[0])
                    times.append(QDateTime().fromString(query.value(1).toString(),  'MMddyyyy hh:mm:ss.zzz'))
                if len(times)>0:
                    totinterval=0
                    totmean=0
                    if len(times)>1:
                        for i in range(len(times)-1):
                            interval=times[i].secsTo(times[i+1])
                            totinterval+=interval
                            mean=(vals[i]+vals[i+1])/2
                            totmean+=mean*interval
                        if float(totinterval)==0:
                            break
                            return
                        totmean=float(totmean)/float(totinterval)
                    else:
                        totmean=vals[0]
                    query=QtSql.QSqlQuery("SELECT * FROM " + self.schema + ".event_data WHERE ship="+
                    self.ship+" AND survey="+self.survey+" AND event_id= "+self.activeEvent+" AND partition='"+p+"' AND event_parameter = '"+'Avg'+m+"'")
                    if query.first():
                        query = QtSql.QSqlQuery("UPDATE " + self.schema + ".event_data SET parameter_value='"+str(totmean)+"' WHERE "+
                                                            "ship="+self.ship+" AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND partition='"+p+
                                                            "' AND event_parameter='"+'Avg'+m+"'")
                    else:
                        query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id, partition,  event_parameter,  parameter_value) VALUES ("+
                                                    self.ship+","+self.survey+","+self.activeEvent+",'"+p+"','"+'Avg'+m+"','"+str(totmean)+"')")
                    self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

    def errorSCS(self):
        QMessageBox.warning(self, "ERROR", "<font size = 12> Lost connection to SCS server. "+
                             "Please continue trawl event - SCS Data will be matched up later.")
        self.dispVector=['', '']


    def getComment(self):
        keyDialog = keypad.KeyPad(self.comment,  self)
        keyDialog.exec_()
        if keyDialog.okFlag:
            self.commentstr=keyDialog.dispEdit.toPlainText()
            string=keyDialog.dispEdit.toPlainText()
            string=string.split('\n')
            self.comment=''
            for s in string:
                self.comment=self.comment+s+''


    def goExit(self):
        self.close()


    def exitCheck(self):

        self.incomplete=False
        # check the buttons
        if (self.fishingFlag and (self.gear <> 'CTD')):
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],"Please press released button!", 'info')
            self.message.exec_()
            self.incomplete=True
            return

        if self.typeBox.currentIndex()==-1:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],"Select an event type!", 'info')
            self.message.exec_()
            self.incomplete=True
            return

        if  self.perfBox.currentIndex()==-1:
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],"Select gear performance!",'info')
            self.message.exec_()
            self.incomplete=True
            return

        if (self.depthStartBtn.text() == '' and (self.gear <> 'CTD')):
            self.message.setMessage(self.errorIcons[0],self.errorSounds[0],"Select a Bottom depth!",'info')
            self.message.exec_()
            self.incomplete=True
            return

 


    def convertDegToDecimalLat(self,  deg):

        try:
            dec = float(deg[0:2]) + float(deg[2:-1])/60.
            if deg[-1:] in ['S', 'W']:
                dec = dec * -1
        except:
            dec=''
        return str(dec)


    def convertDegToDecimalLon(self,  deg):

        try:
            dec = float(deg[0:3]) + float(deg[3:-1])/60.
            if deg[-1:] in ['S', 'W']:
                dec = dec * -1
        except:
            dec=''
        return str(dec)


    def closeEvent(self, event):

        if (not self.abort):

            #check for completeness
            self.exitCheck()
            if self.incomplete:
                event.ignore()
                return
            if not self.reloaded:
                self.stopStream()

            # Haul Table
            # update performance and haul type
            query = QtSql.QSqlQuery("UPDATE " + self.schema + ".events SET event_type = "+self.typeCode[self.typeBox.currentIndex()]+
                    ", performance_code = "+self.perfCode[self.perfBox.currentIndex()]+" WHERE ship="+self.ship+
                    " AND survey="+self.survey+" AND event_id="+self.activeEvent)
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
            # update comment
            if self.comment<>'':
                query = QtSql.QSqlQuery("UPDATE " + self.schema + ".events SET comments = '"+self.comment+
                    "' WHERE ship="+self.ship+ " AND survey="+self.survey+" AND event_id="+self.activeEvent)
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            #delete current records if they exist
            query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='Station'")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
            query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='BottomDepth'")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
    
            query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='Stratum'")
            query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='MarineMammalPresent'")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
            query = QtSql.QSqlQuery("DELETE FROM " + self.schema + ".event_data WHERE ship="+self.ship+
                " AND survey="+self.survey+" AND event_id="+self.activeEvent+" AND event_parameter='EndangeredSeabirdPresent'")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())
        


            # write stratum (optional on this form)
            if self.stratumBtn.text() <> '':
                query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id,partition,  event_parameter,  parameter_value) VALUES "+
                                    " ("+self.ship+","+self.survey+","+self.activeEvent+",'MainTrawl', 'Stratum', '"+self.stratumBtn.text()+"')")
                self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            # write bottom depth num
            query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id,partition,  event_parameter,  parameter_value) VALUES "+
                                    " ("+self.ship+","+self.survey+","+self.activeEvent+",'MainTrawl', 'BottomDepth', '"+self.depthStartBtn.text()+"')")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            # write checkboxes
            if self.marMammalBox.isChecked():
                status='Y'
            else:
                status='N'
            query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id,partition,  event_parameter,  parameter_value) VALUES "+
                                    " ("+self.ship+","+self.survey+","+self.activeEvent+",'MainTrawl', 'MarineMammalPresent','"+status+"')")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            if self.seaBirdBox.isChecked():
                status='Y'
            else:
                status='N'
            query = QtSql.QSqlQuery("INSERT INTO " + self.schema + ".event_data (ship, survey, event_id,partition,  event_parameter,  parameter_value) VALUES "+
                                    " ("+self.ship+","+self.survey+","+self.activeEvent+",'MainTrawl', 'EndangeredSeabirdPresent','"+status+"')")
            self.backLogger.info(QDateTime.currentDateTime().toString('MMddyyyy hh:mm:ss')+","+query.lastQuery())

            query = QtSql.QSqlQuery("UPDATE " + self.schema + ".application_configuration SET parameter_value=" +
                            self.activeEvent + " WHERE parameter='ActiveEvent'")

            self.computeMeans()

        else:
            #  we've aborted this trawl before it began - do nothing
            pass

        event.accept()







