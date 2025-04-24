"""
updated November 2022 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- signal/slot connections
- moved variable declarations into __init__
- added import of PyQt6.QtSql for database query
- added some function explanation
- fixed any PEP8 issues

todo: couldn't check because need parent dialog set up first to connect to database
"""

from PyQt6.QtWidgets import *
from PyQt6.QtSql import QSqlQuery
from ui import ui_ExtendedSampleCollection
from sys import argv


class ExtendedSampleCollectionDlg(QDialog, ui_ExtendedSampleCollection.Ui_extendedsamplecollectionDlg):
    def __init__(self,  parent=None):
        super(ExtendedSampleCollectionDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declarations
        # from the passed parent
        self.db = parent.db
        self.survey = parent.survey
        self.ship = parent.ship
        self.activeHaul = parent.activeHaul
        self.activeSample = parent.activeSample
        self.specimenKey = parent.specimenKey

        # used in class
        self.list = []
        self.label = []
        self.code = []
        self.buttons = [self.Btn1,  self.Btn2,  self.Btn3,  self.Btn4,  self.Btn5,  self.Btn6,  self.Btn7,
                        self.Btn8,  self.Btn9,  self.Btn10,  self.Btn11,  self.Btn12,  self.Btn13,  self.Btn14]
        self.result = ()

        # signal/slot connections
        for btn in self.buttons:
            # set the signal/slot and disable the button
            btn.clicked.connect(self.select)
            btn.setEnabled(False)

        self.doneBtn.clicked.connect(self.Enter)
        self.clearBtn.clicked.connect(self.Clear)

    def setup(self, parent):
        """

        :param parent: not used in this function
        :return: none
        """
        # get buttons out of database
        query = QSqlQuery("SELECT ex_sample_code, button_text, active "
                          "FROM extended_sample_collections"
                          "WHERE active = 1 "
                          "ORDER BY ex_sample_code")

        # set the code and label lists from the query
        while query.next():
            self.code.append(query.value(0).toString())
            self.label.append(query.value(1).toString())

        # show and set the test for the button, enable it, and uncheck it
        for i in range(len(self.label)):
            self.buttons[i].show()
            self.buttons[i].setText(self.label[i])
            self.buttons[i].setEnabled(True)
            self.buttons[i].setChecked(False)

        # check to see if there's already something in the DB to check the button
        if self.specimenKey:
            query = QSqlQuery("Select measurement_value FROM measurements WHERE  ship=" + self.ship +
                              " AND survey=" + self.survey + " AND event_id=" + self.activeHaul +
                              " AND sample_id=" + self.activeSample + " AND specimen_id = " + self.specimenKey +
                              " AND measurement_type = 'ex_sample_collections'")
            query.first()
            # if there is something in the database
            if query.first():
                # todo: do we need the toString()?
                currentList = query.value(0).toString().split(',')
                for i in range(len(self.code)):
                    if self.code[i] in currentList:
                        # if there is a measurement, set the button to 'Collected' and check the button
                        self.list.append(self.code[i])
                        self.buttons[i].setText('Collected')
                        self.buttons[i].setChecked(True)

    def select(self):
        """
        if a button is selected, it either resets the text or sets it to 'Collected', depending on the current
        state of the button
        :return: none
        """
        ind = self.buttons.index(self.sender())
        if self.code[ind] in self.list:
            self.sender().setText(self.label[ind])
            self.list.remove(self.code[ind])
            self.buttons[ind].setChecked(False)
        else:
            self.sender().setText('Collected')
            self.list.append(self.code[ind])
            self.buttons[ind].setChecked(True)

    def Clear(self):
        """
        resets the lists and re-queries the database for the buttons and sets them
        :return: none
        """
        self.list = []
        self.label = []
        self.code = []
        query = QSqlQuery("SELECT ex_sample_code, button_text, active "
                          "FROM extended_sample_collections "
                          "WHERE active = 1 ORDER BY ex_sample_code")
        while query.next():
            self.code.append(query.value(0).toString())
            self.label.append(query.value(1).toString())
        for i in range(len(self.label)):
            self.buttons[i].show()
            self.buttons[i].setText(self.label[i])
            self.buttons[i].setEnabled(True)
            self.buttons[i].setChecked(False)
            
    def Enter(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        listString = ''
        if self.list:
            self.list.sort()
            for code in self.list:
                listString = listString + code + ','
        else:
            listString = ' '

        self.result = (True, listString)
        if self.result[-1] != '':
            if self.result[-1][-1] == ',':
                self.result = (True, self.result[-1][0:-1])

            self.accept()

    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()
