"""
updated January 2025 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- signal/slot connections
- moved variable declarations into __init__
- added some function explanation
- fixed any PEP8 issues
- updated to query for species list ONCE and put into a dataframe to be filtered with search parameters

NOTE: cannot test this fully until it is called with parent values
"""


from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
from ui import ui_AddCatchSpcDlg
import listseldialog
import pandas as pd
import messagedlg
from os.path import exists, join

from sys import argv

class AddCatchSpcDlg(QDialog, ui_AddCatchSpcDlg.Ui_addcatchspcDlg):
    def __init__(self, parent=None):
        super(AddCatchSpcDlg, self).__init__(parent)

        self.setupUi(self)
        """
        self.ship = parent.ship
        self.survey = parent.survey
        self.activeHaul = parent.activeHaul
        self.activePartition = parent.activePartition
        self.message = parent.message
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.whHaulFlag = parent.whHaulFlag
        self.settings = parent.settings
        # I feel like we'll need to add this one?
        self.db = parent.db
        """
        # delete after testing
        self.whHaulFlag = True
        self.settings = {'ImageDir': "C:\\Git\\CLAMS\\images"}

        self.mixCreateFlag = False
        self.mixAddFlag = False
        self.previous = None
        self.listOrigin = None
        self.chars = ''
        self.updatingDigit = False
        self.all_species = None
        self.spc_assoc = None
        self.spc_data = None
        self.nameType = None
        self.activeSpcName = None
        self.activeSpcCode = None
        self.activeSpcSubcat = None
        self.parentSample = None
        self.planktonList = None
        self.history = None

        self.hauls = []

        self.message = messagedlg.MessageDlg(self)

        # put the keyboard buttons into a list to easily reference them
        self.digitBtns = [self.A_Btn, self.B_Btn, self.C_Btn, self.D_Btn, self.E_Btn, self.F_Btn,
                          self.G_Btn, self.H_Btn, self.I_Btn, self.J_Btn, self.K_Btn, self.L_Btn,
                          self.M_Btn, self.N_Btn, self.O_Btn, self.P_Btn, self.Q_Btn, self.R_Btn,
                          self.S_Btn, self.T_Btn, self.U_Btn, self.V_Btn, self.W_Btn, self.X_Btn,
                          self.Y_Btn, self.Z_Btn, self.space]

        # put parent sample buttons into list to easily reference
        self.buttons = [self.wholeHaulBtn, self.sortTableBtn, self.mix1Btn,
                        self.subMix1Btn, self.mix2Btn]

        # set up signals and slots
        for btn in self.digitBtns:
            btn.clicked.connect(self.getDigit)

        self.fullspcCList.itemClicked.connect(self.getSpcSel)
        self.fullspcSList.itemClicked.connect(self.getSpcSel)
        self.backBtn.clicked.connect(self.clearOneChar)
        self.clearBtn.clicked.connect(self.clearAllChar)
        self.doneBtn.clicked.connect(self.goExit)
        self.addBtn.clicked.connect(self.sendSel)
        self.radio10.toggled.connect(self.getSpcHistory)
        self.radioFull.toggled.connect(self.clearAllChar)

        #  connect the sample button clicked signal to a method that manages their exclusivity
        #  it seems auto-exclusive buttons in a container cannot all be unchecked. Once one is
        #  checked, you can't uncheck it (at least by calling setChecked())
        for btn in self.buttons:
            btn.clicked.connect(self.handleSampleBtnEx)
            # self.connect(btn, SIGNAL("clicked()"), self.handleSampleBtnEx)

        # get overall species list
        self.set_all_spc_lsts()
        self.getList()

        """
        #  create an instance of our dbConnection
        self.db = None
        self.connectToDatabase()
        # set default tab, get past haul species
        sql = ("SELECT event_id FROM events WHERE survey = " + self.survey + " AND event_id <= " + self.activeHaul)
        query = self.db.dbQuery(sql)
        # query = QtSql.QSqlQuery("SELECT event_id FROM events WHERE survey = "+self.survey+
        #         " AND event_id <= "+self.activeHaul+"")
        while query.next():
            self.hauls.append(int(query.value(0).toString()))
        self.hauls.reverse()
        self.history = 10
        self.getSpcHistory()
        self.radio10.setChecked(True)
        """
        #  set up the sample buttons
        self.setSampleBtnEnable()

    def set_all_spc_lsts(self):
        """
        added this function to read in all species, associations, and data once (or can be called multiple times)
        :return:
        """
        # todo: included dummy data here for testing; delete when have access to database
        d = {'species_code': [3, 10, 21, 100, 109, 120],
             'scientific_name': ['Actinopterygii unident', 'Petromyzontidae', 'Entosphenus tridentatus', 'Myxinidae',
                                 'Eptatretus sp', 'Eptatretus stoutii'],
             'common_name': ['Fish unident', 'Lamprey unident', 'Pacific lamprey', 'Hagfish unident',
                             'Eptatretus genus', 'Pacific hagfish']}
        d_a = {'species_code': [3, 10, 21, 100, 109, 120],
               'subcategory': ['None', 'None', 'None', 'None', 'None', 'None']}
        d_d = {'species_code': [3, 10, 21, 100, 109, 120],
               'previous_occurrence': [1, 1, 1, 1, 1, 0]}

        # todo: add code here to grab data out of database
        self.all_species = pd.DataFrame(data=d)
        self.spc_assoc = pd.DataFrame(data=d_a)
        self.spc_data = pd.DataFrame(data=d_d)

    def handleSampleBtnEx(self):
        """
        handleSampleBtnEx manages the exclusivity of the parent sample buttons
        This ?
        """
        #  uncheck all buttons
        for btn in self.buttons:
            btn.setChecked(False)
        #  and check the button pressed
        self.sender().setChecked(True)

    def setSampleBtnEnable(self):
        """
        setSampleBtnEnable enables/disables the parent sample buttons based on
        the ?
        :return:
        """
        #  set all buttons enabled
        for btn in self.buttons:
            btn.setEnabled(True)

        #  uncheck all buttons
        for btn in self.buttons:
            btn.setChecked(False)

        # set default values
        if not self.whHaulFlag:
            self.wholeHaulBtn.setEnabled(False)

        # find out if we have a mix1
        # todo: check that mix1 species_code is still 100002
        """
        mix_sql = ("SELECT sample_id FROM samples WHERE ship = " + self.ship+" AND survey = " + self.survey + 
                   " AND event_id = " + self.activeHaul + " AND partition = '" + self.activePartition + 
                   "' AND species_code=100002")
        if not query.first():
            # no mix 1 in the system
            self.mix1Btn.setEnabled(False)
            self.subMix1Btn.setEnabled(False)
        else:
            # we have a mix 1 - check if we have a submix for mix 1
            submix_sql = ("SELECT sample_id FROM samples WHERE ship = " + self.ship + " AND survey = " + self.survey + 
                          " AND event_id = "+self.activeHaul+" AND partition ='"+self.activePartition+
                    "' AND species_code=100003")
            if not query.first():
                # no submix1
                self.subMix1Btn.setEnabled(False)

        #  check if there is a mix2
        query=QtSql.QSqlQuery("SELECT sample_id FROM samples WHERE ship = "+self.ship+" AND survey = "+
                self.survey+ " AND event_id = "+self.activeHaul+" AND partition ='"+self.activePartition+
                "' AND species_code=100004")
        if not query.first():
            #  there is no mix2
            self.mix2Btn.setEnabled(False)
        """

    def getDigit(self):
        """
        gets the digit that is entered from the screen, adds it to the line edit, and updates the list
        :return:
        """
        self.updatingDigit = True
        cur_text = self.sender().text()
        if cur_text.lower() == 'space':
            cur_text = " "
        self.chars = self.chars + cur_text
        self.lineEdit_search.setText(self.chars)

        self.radioFull.setChecked(True)
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        self.getList()
        self.updatingDigit = False

    def clearOneChar(self):
        """
        removes the final character and resets the line edit with the new term
        :return:
        """
        self.chars = self.chars[:-1]
        self.lineEdit_search.setText(self.chars)

        self.getList()

    def clearAllChar(self):
        """
        removes all characters and resets everything
        :return:
        """
        if not self.updatingDigit:
            self.chars = ''
            self.spcLabel.setText('')
            self.picLabel.clear()
            self.lineEdit_search.setText(self.chars)
            self.fullspcCList.clear()
            self.fullspcSList.clear()

            self.getList()

    def getList(self):
        """
        queries the species dataframe to return common and scientific names that fit the search characters
        :return:
        """
        # check if the species dataframe has been filled, and fill it if it hasn't
        if self.all_species.empty:
            species_sql = "SELECT * FROM species"
            # todo: how to read in sql with current database connection?
            # self.all_species = pd.read_sql(species_sql, self.db)

        # clear both lists
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        # fill the lists
        if self.chars == '':
            com_names = self.all_species['common_name'].tolist()
            sci_names = self.all_species['scientific_name'].tolist()
        else:
            com_names = self.all_species[self.all_species['common_name'].str.contains(self.chars, case=False)][
                'common_name'].tolist()
            sci_names = self.all_species[self.all_species['scientific_name'].str.contains(self.chars, case=False)][
                'scientific_name'].tolist()
        self.fullspcCList.addItems(com_names)
        self.fullspcSList.addItems(sci_names)
        """
        if self.chars == '':
            commonQuery = "SELECT species.common_name FROM species ORDER BY species.common_name"
            sciQuery = "SELECT species.scientific_name FROM species ORDER BY species.scientific_name"
        else:
            like_exp = "'"+self.chars+"%'"
            commonQuery = ("SELECT species.common_name FROM species WHERE upper(species.common_name)" +
                " LIKE upper(" + like_exp + ") AND species_code<999900 ORDER BY species.common_name")
            sciQuery = ("SELECT species.scientific_name FROM species WHERE upper(species.scientific_name) "+
                " LIKE upper(" + like_exp + ") AND species_code<999900 ORDER BY species.scientific_name")

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
        """

    def getSpcSel(self):
        """
        gets the species that is selected by the user and sets the active species name, species code, and subcategory
        :return:
        """
        # set variables
        label_text = None
        img_name = None

        # get the sender and set the active species name
        self.listOrigin = self.sender()
        self.activeSpcName = self.listOrigin.currentItem().text()

        # check if selected common or scientific name and set the active species code
        if self.nameTab.currentIndex() == 0:
            self.nameType = 'common'
            self.activeSpcCode = list(self.all_species[self.all_species['common_name'] ==
                                                       self.activeSpcName]['species_code'])[0]
        else:
            self.nameType = 'scientific'
            self.activeSpcCode = list(self.all_species[self.all_species['scientific_name'] ==
                                                       self.activeSpcName]['species_code'])[0]

        # check for multiple subcategories
        subcats = self.spc_assoc[self.spc_assoc['species_code'] == self.activeSpcCode]['subcategory'].tolist()

        if len(subcats) > 1:
            # species has multiple subclasses in species associations
            # display the subcategory selection dialog
            listDialog = listseldialog.ListSelDialog(subcats, 'Short', self)
            listDialog.label.setText('Choose Size Class')
            if listDialog.exec():
                if listDialog.itemList.currentRow() < 0:
                    #  no name selected
                    self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                            'Please select a Size Class or "All Sizes".', 'info')
                    self.message.exec()
                else:
                    self.activeSpcSubcat = listDialog.itemList.currentItem().text()
                    img_name = self.activeSpcCode
                    label_text = self.activeSpcName + "-" + self.activeSpcSubcat
            else:
                return

        elif len(subcats) == 1:
            # species has one listing in species associations
            self.activeSpcSubcat = subcats[0]
            img_name = self.activeSpcCode
            label_text = self.activeSpcName
        else:
            # species not listed in species associations
            self.activeSpcSubcat = 'None'
            img_name = self.activeSpcCode
            label_text = self.activeSpcName

        # find out previous occurrence
        self.previous = 1
        # todo: check if 99999 is still mix?
        if int(self.activeSpcCode) < 99999:
            prev = list(self.spc_data[self.spc_data['species_code'] == self.activeSpcCode]['previous_occurrence'])
            if len(prev) > 0:
                self.previous = prev[0]

        # load label
        self.spcLabel.setText(label_text)

        if img_name:
            img_loc = join(self.settings['ImageDir'], 'fishPics', str(img_name) + ".jpg")
            if exists(img_loc):
                # load the image
                pixmap = QPixmap(img_loc)
                # set the image to the label
                self.picLabel.setPixmap(pixmap)
            else:
                self.picLabel.clear()

        # todo: submixes? check with rick about this before updating
        """
        # submix check
        if self.activeSpcCode=='100003':
            # find out if we have some mixes
            query=QtSql.QSqlQuery("SELECT sample_id FROM samples WHERE ship = "+self.ship+" AND survey = "+self.survey+
                    " AND event_id = "+self.activeHaul+" AND partition ='"+self.activePartition+"' AND 
                    species_code=100002")
            if not query.first():  # no mix 1 in the system

                self.message.setMessage(self.errorIcons[1], self.errorSounds[1],
                                            "There's no Mix1 sample for this partition.  you need to create it 
                                            before using the SubMix1", 'info')
                self.message.exec_()
            else:# you can only choose Mix1!!
                for btn in self.buttons:
                    btn.setEnabled(False)
                self.mix1Btn.setEnabled(True)
                self.mix1Btn.setChecked(True)
        """

    def sendSel(self):
        """

        :return:
        """

        #  get the selected parent sample
        for btn in self.buttons:
            if btn.isChecked():
                self.parentSample = btn.text()
                break
        if self.parentSample is None:
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "You need to select a parent sample! ", 'info')
            self.message.exec()
            return

        if self.listOrigin is None:
            return

        if self.previous == 0:
            #  ask if we want to add this exotic species we've never encountered
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0], "We've never seen a "
                                    + self.listOrigin.currentItem().text()+". Are you sure that's right? ", 'choice')
            if not self.message.exec():
                return

        #  emit the changed signal to update parent
        # todo: figure out how to emit a signal in pyqt6
        self.emit(SIGNAL("changed"))

        self.setSampleBtnEnable()

        #  only clear the text box and list if this isn't a history pick
        if not self.radio10.isChecked():
            self.clearAllChar()

    def getSpcHistory(self):
        """
        Create a "short list" of the most common species from the last 10 hauls
        :return:
        """
        #  clear the lists
        self.fullspcCList.clear()
        self.fullspcSList.clear()

        spcList = []

        if len(self.hauls) < 2:
            return

        hauls = str(self.hauls[0])
        if len(self.hauls) < self.history:
            count = len(self.hauls)
        else:
            count = self.history
        for i in range(count-1):
            hauls = (hauls + "," + str(self.hauls[i+1]))

        # query database to get species that are in past x hauls
        haul_sql = "SELECT species.common_name, species.species_code " \
                   "FROM species " \
                   "INNER JOIN samples ON species.species_code=samples.species_code " \
                   "WHERE samples.event_id in (" + hauls + ") AND samples.survey = " + self.survey + \
                   " AND species.species_code not in (100000, 100001) AND species.species_code < 900000 " \
                   "GROUP BY species.common_name, species.species_code"
        wghtList = []
        haul_query = self.db.dbQuery(haul_sql)
        # todo: is this how to iterate through query results here? this needs to be fixed up
        while haul_query.next():
            spcList.append(haul_query.value(0).toString())
            basket_sql = "SELECT sum(baskets.weight) " \
                         "FROM baskets, samples  " \
                         "WHERE samples.sample_id = baskets.sample_id AND samples.species_code = " \
                         + haul_query.value(1).toString() + " AND samples.survey = " + self.survey + \
                         " AND samples.event_id IN (" + hauls + ")"
            basket_query = self.db.dbQuery(basket_sql)
            basket_query.first()
            wghtList.append(basket_query.value(0).toFloat()[0])

        #  if we have a history - create the "short list"
        if wghtList:
            wghtList, spcList = (list(x) for x in zip(*sorted(zip(wghtList, spcList))))
            spcList.reverse()
            self.fullspcCList.addItems(spcList)

    def getMethotSpecies(self):
        """
        store species that are flagged as a plankton species
        :return:
        """
        spcList = []
        # todo: this is not a column in my version of the database...
        #  need to get updated version to make sure I'm doing this right
        sql = "SELECT species.common_name FROM species WHERE plankton_species=1 ORDER BY species.common_name"
        query = self.db.dbQuery(sql)
        while query.next():
            spcList.append(query.value(0).toString())
        self.planktonList.addItems(spcList)

    def getRadioSel(self):
        """
        returns the species from the last x hauls
        :return:
        """
        self.history = 10
        self.getSpcHistory()

    def goExit(self):
        """
        accepts the dialog to close and continue
        :return:
        """
        self.accept()


# """
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = AddCatchSpcDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
# """
