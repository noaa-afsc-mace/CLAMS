
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtSql
from ui.xga import  ui_AddCatchSpcDlg_alt2
import listseldialog


class AddCatchSpcDlg(QDialog, ui_AddCatchSpcDlg_alt2.Ui_addcatchspcDlg):
    def __init__(self, parent=None):
        super(AddCatchSpcDlg, self).__init__(parent)

        self.setupUi(self)
        self.mixCreateFlag=False
        self.mixAddFlag=False
        self.survey = parent.survey
        self.activeHaul=parent.activeHaul
        self.message=parent.message
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons
        self.whHaulFlag=parent.whHaulFlag
        self.previous = None
        self.listOrigin = None
        self.chars=''
        self.updatingDigit = False
        self.settings=parent.settings

        #  put the keyboard buttons into a list to easily reference them
        self.digitBtns=[self.A_Btn,self.B_Btn,self.C_Btn,self.D_Btn,self.E_Btn,self.F_Btn,
                        self.G_Btn,self.H_Btn,self.I_Btn,self.J_Btn,self.K_Btn,self.L_Btn,
                        self.M_Btn,self.N_Btn,self.O_Btn,self.P_Btn,self.Q_Btn,self.R_Btn,
                        self.S_Btn,self.T_Btn,self.U_Btn,self.V_Btn,self.W_Btn,self.X_Btn,
                        self.Y_Btn,self.Z_Btn]

        #  connect signals
        for btn in self.digitBtns:
            self.connect(btn, SIGNAL("clicked()"),self.getDigit)
        self.connect(self.fullspcCList, SIGNAL("itemClicked (QListWidgetItem *)"), self.getSpcSel)
        self.connect(self.fullspcSList, SIGNAL("itemClicked (QListWidgetItem *)"), self.getSpcSel)
        self.connect(self.backBtn, SIGNAL("clicked()"), self.clearOneChar)
        self.connect(self.clearBtn, SIGNAL("clicked()"), self.clearAllChar)
        self.connect(self.doneBtn, SIGNAL("clicked()"), self.goExit)
        self.connect(self.addBtn, SIGNAL("clicked()"), self.sendSel)
        self.connect(self.addmixBtn, SIGNAL("clicked()"), self.sendSel)
        self.connect(self.mixBtn, SIGNAL("clicked()"), self.sendSel)
        self.connect(self.wholeBtn, SIGNAL("clicked()"), self.sendSel)
        self.connect(self.radio10, SIGNAL("toggled(bool)"), self.getSpcHistory)
        self.connect(self.radioFull, SIGNAL("toggled(bool)"), self.clearAllChar)

        # position the window
        screen=QDesktopWidget().screenGeometry()
        window=self.geometry()
        self.setGeometry(round(screen.width()*.28, 0), round(screen.height()*.05, 0),
                window.width(), window.height())

        # set default tab, get past haul species
        query=QtSql.QSqlQuery("SELECT event_id FROM " + self.schema + ".events WHERE survey = "+self.survey+
                " AND event_id <= "+self.activeHaul+"")
        self.hauls=[]
        while query.next():
            self.hauls.append(int(query.value(0).toString()))
        self.hauls.reverse()
        self.history=10
        self.getSpcHistory()
        self.radio10.setChecked(True)

        if not parent.whHaulFlag:
            self.wholeBtn.setEnabled(False)
        if parent.mixKey==None:
            self.addmixBtn.setEnabled(False)
            self.mixBtn.setEnabled(True)
        else:
            self.addmixBtn.setEnabled(True)
            self.mixBtn.setEnabled(False)


    def getDigit(self):

        self.updatingDigit=True
        self.chars=self.chars+self.sender().text()
        self.lineEdit.setText(self.chars)

        self.radioFull.setChecked(True)
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        self.getList()
        self.updatingDigit=False


    def clearOneChar(self):
        self.chars=self.chars[:-1]
        self.lineEdit.setText(self.chars)
        self.getList()


    def clearAllChar(self):
        if not self.updatingDigit:
            self.chars=''
            self.spcLabel.setText('')
            self.picLabel.clear()
            self.lineEdit.setText(self.chars)
            self.fullspcCList.clear()
            self.fullspcSList.clear()
            self.getList()



    def getList(self):

        if self.chars=='':
            commonQuery = "SELECT species.common_name FROM " + self.schema + ".species ORDER BY species.common_name"
            sciQuery = "SELECT species.scientific_name FROM " + self.schema + ".species ORDER BY species.scientific_name"
        else:
            commonQuery = ("SELECT species.common_name FROM " + self.schema + ".species WHERE upper(species.common_name)" +
                "LIKE upper('"+ self.chars+"%') ORDER BY species.common_name")
            sciQuery = ("SELECT species.scientific_name FROM " + self.schema + ".species WHERE upper(species.scientific_name) "+
                "LIKE upper('"+self.chars+"%') ORDER BY species.scientific_name")

        query=QtSql.QSqlQuery(commonQuery)
        trunc=[]
        while query.next():
            trunc.append(query.value(0).toString())
        self.fullspcCList.addItems(QStringList(trunc))

        query=QtSql.QSqlQuery(sciQuery)
        trunc1=[]
        while query.next():
            trunc1.append(query.value(0).toString())
        self.fullspcSList.addItems(QStringList(trunc1))

        if len(trunc)<2 and self.nameTab.currentIndex==0:
            self.fullspcCList.setCurrentRow(1)
        elif len(trunc1)<2 and self.nameTab.currentIndex==1:
            self.fullspcSList.setCurrentRow(1)

        self.picLabel.clear()


    def getSpcSel(self):

        # image code
        self.listOrigin=self.sender()
        self.activeSpcName=self.listOrigin.currentItem().text()
        if self.nameTab.currentIndex()==0:
            self.nameType='common'
            query=QtSql.QSqlQuery("SELECT species.species_code  "+
                    "FROM " + self.schema + ".species WHERE species.common_name='"+
                    self.listOrigin.currentItem().text()+"'")
        else:
            self.nameType='scientific'
            query=QtSql.QSqlQuery("SELECT species.species_code  "+
                    "FROM " + self.schema + ".species WHERE species.scientific_name='"+
                    self.listOrigin.currentItem().text()+"'")
        query.first()
        self.activeSpcCode=query.value(0).toString()
        imgName=None

        # check for multiple subcategories
        query=QtSql.QSqlQuery("SELECT subcategory FROM " + self.schema + ".species_associations WHERE species_code="+
                self.activeSpcCode)
        subcats=[]
        while query.next():
            subcats.append(query.value(0).toString())
        if len(subcats)>1:# species has multiple subclasses in species associations
            self.listDialog = listseldialog.ListSelDialog(subcats, 'Short',  self)
            self.listDialog.label.setText('Choose Size Class')
            if self.listDialog.exec():
                if (self.listDialog.itemList.currentRow() < 0):
                    #  no name selected
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                            'Please select a Size Class or "All Sizes".', 'info')
                    self.message.exec_()
                else:
                    self.activeSpcSubcat = self.listDialog.itemList.currentItem().text()
                    imgName=self.activeSpcCode #+"_"+self.activeSpcSubcat
                    labelText=self.activeSpcName+"-"+self.activeSpcSubcat
        elif len(subcats)>1:
            self.activeSpcSubcat=subcats[0]# species has one listing in species associations
            imgName=self.activeSpcCode
            labelText=self.activeSpcName
        else:
            self.activeSpcSubcat='None' # species not listed in species associations
            imgName=self.activeSpcCode
            labelText=self.activeSpcName
        # find out previous occurence
        query=QtSql.QSqlQuery("SELECT parameter_value  "+ "FROM " + self.schema + ".species_data WHERE species_code="+
                self.activeSpcCode+" AND subcategory='"+self.activeSpcSubcat+
                "' AND lower(species_parameter)='previous_occurrence'")
        if query.first():
            self.previous=int(query.value(0).toString())
        else:
            self.previous=1
        # load label
        self.spcLabel.setText(labelText)
        # set image
        pic=QImage()
        if imgName:
            if pic.load(self.settings[QString('ImageDir')]+'\\fishPics\\'+imgName+".jpg"):
               pic=pic.scaled(self.picLabel.size(),Qt.KeepAspectRatio,  Qt.SmoothTransformation)
               self.picLabel.setPixmap(QPixmap.fromImage(pic))
            else:
                self.picLabel.clear()

    def sendSel(self):

        #  get the button ID and text
        self.buttonId = self.sender()

        #  make sure that if we're adding, we've selected something
        if self.buttonId.text() in ['Add to List',  'Add to Mix',  'Whole Haul']:
            if self.listOrigin == None:
                return
            if self.previous==0:
                #  ask if we want to add this exotic species we've never encountered
                self.message.setMessage(self.errorIcons[0],self.errorSounds[0], "We've never seen a "+
                        self.listOrigin.currentItem().text()+". Are you sure that's right? ", 'choice')
                if not self.message.exec_():
                    return
        else:# this is the create mix button
            self.addmixBtn.setEnabled(True)
            self.mixBtn.setEnabled(False)# only one mix per
            self.activeSpcCode='0'
            self.activeSpcName='mix1'
            self.nameType='common'
            self.activeSpcSubcat='None'
        #  emit the changed signal to update parent
        self.emit(SIGNAL("changed"))

        #  only clear the text box and list if this isn't a history pick
        if not self.radio10.isChecked():
            self.clearAllChar()


    def getSpcHistory(self):
        '''
        Create a "short list" of the most common species from the last
        few hauls.
        '''

        #  clear the short list
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        spcList=[]

        if (len(self.hauls) < 2):
            return

        hauls = str(self.hauls[0])
        if len(self.hauls)<self.history:
            count=len(self.hauls)
        else:
            count=self.history
        for i in range(count-1):
            hauls=(hauls+","+str(self.hauls[i+1]))
        query=QtSql.QSqlQuery("SELECT species.common_name, species.species_code FROM " + self.schema + ".species INNER " +
                "JOIN samples ON species.species_code=samples.species_code WHERE (samples.event_id in("+
                hauls+") AND (samples.survey = "+self.survey+") AND (species.species_code<>0)) " +
                "GROUP BY species.common_name, species.species_code")
        wghtList=[]
        while query.next():
            spcList.append(query.value(0).toString())
            query1=QtSql.QSqlQuery("SELECT sum(BASKETS.WEIGHT ) FROM " + self.schema + ".BASKETS, "
                                   + self.schema + ".SAMPLES  WHERE " +
                    "(( SAMPLES.SAMPLE_ID = BASKETS.SAMPLE_ID ) and (SAMPLES.SPECIES_CODE = "+
                    query.value(1).toString()+") AND  (SAMPLES.SURVEY = "+self.survey+
                    ") AND  (SAMPLES.event_id in("+hauls+")))" )
            query1.first()
            wghtList.append(query1.value(0).toFloat()[0])

        #  if we have a history - create the "short list"
        if wghtList:
            wghtList, spcList = (list(x) for x in zip(*sorted(zip(wghtList, spcList))))
            spcList.reverse()
            self.fullspcCList.addItems(QStringList(spcList))


    def getMethotSpecies(self):
        spcList=[]
        query=QtSql.QSqlQuery("SELECT species.common_name FROM " + self.schema + ".species WHERE plankton_species=1 ORDER BY species.common_name");
        while query.next():
            spcList.append(query.value(0).toString())
        self.planktonList.addItems(QStringList(spcList))


    def getRadioSel(self):

        self.history=10
        self.getSpcHistory()


    def goExit(self):
        self.accept()



