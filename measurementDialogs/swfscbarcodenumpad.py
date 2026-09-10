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
.. module:: SWFSCBarcodeNumpad

    :synopsis: Dialog to enter an alphanumeric vial number following
               the SWFSC barcode requirements. The SWFSC uses barcodes
               that start with "A", "G", or "U" and then have 11 numeric
               digits. this dialog presents a modified numpad with
               "A", "G", and "U" keys to allow efficient manual entry of
               these barcodes.


THIS IS A WORK IN PROGRESS


| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assessment and Conservation Engineering Group (MACE)
|
| Author:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
| Updated February 2025 by:
|       Alicia Billings <alicia.billings@noaa.gov>
|           specific updates:
|               - PyQt import statement
|               - signal/slot connections
|               - added some function explanation
|               - fixed any PEP8 issues
|               - added a main to test if works (commented out)
|
"""

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QEvent, Qt, QObject
from ui import ui_SWFSCBCNumPad
import messagedlg
import re


class SWFSCBarcodeNumpad(QDialog, ui_SWFSCBCNumPad.Ui_SWFSCBCNumPad):

    def __init__(self, message, parent=None):
        super(SWFSCBarcodeNumpad, self).__init__(parent)
        self.setupUi(self)
        self.dispEdit.setText(message)

        # variable declarations
        self.msgLabel.setText('')
        self.errorSounds=parent.errorSounds
        self.errorIcons=parent.errorIcons

        #  create the enter key filter
        enterEater = EnterFilter(self.Enter, parent=self)

        self.message = messagedlg.MessageDlg(self)

        #  set the background color of the textbox
        # self.dispEdit.palette().setColor(self.dispEdit.backgroundRole(), QColor(255, 255, 255))

        # connect the signals and install the event filters on the digit keys
        self.pBtn1.clicked.connect(self.getDigit)
        self.pBtn1.installEventFilter(enterEater)
        self.pBtn2.clicked.connect(self.getDigit)
        self.pBtn2.installEventFilter(enterEater)
        self.pBtn3.clicked.connect(self.getDigit)
        self.pBtn3.installEventFilter(enterEater)
        self.pBtn4.clicked.connect(self.getDigit)
        self.pBtn4.installEventFilter(enterEater)
        self.pBtn5.clicked.connect(self.getDigit)
        self.pBtn5.installEventFilter(enterEater)
        self.pBtn6.clicked.connect(self.getDigit)
        self.pBtn6.installEventFilter(enterEater)
        self.pBtn7.clicked.connect(self.getDigit)
        self.pBtn7.installEventFilter(enterEater)
        self.pBtn8.clicked.connect(self.getDigit)
        self.pBtn8.installEventFilter(enterEater)
        self.pBtn9.clicked.connect(self.getDigit)
        self.pBtn9.installEventFilter(enterEater)
        self.pBtn0.clicked.connect(self.getDigit)
        self.pBtn0.installEventFilter(enterEater)
        self.pBtnA.clicked.connect(self.getDigit)
        self.pBtnA.installEventFilter(enterEater)
        self.pBtnG.clicked.connect(self.getDigit)
        self.pBtnG.installEventFilter(enterEater)
        self.pBtnU.clicked.connect(self.getDigit)
        self.pBtnU.installEventFilter(enterEater)
        self.pBtnBsp.clicked.connect(self.bkSpace)
        self.pBtnBsp.installEventFilter(enterEater)
        self.pBtnClr.clicked.connect(self.Clear)
        self.pBtnClr.installEventFilter(enterEater)
        self.pBtnEnt.clicked.connect(self.Enter)


    def setup(self, parent):
        pass


    def getDigit(self, keyVal: None):
        if keyVal:
            self.dispEdit.insertPlainText(keyVal)
        elif self.sender().text():
            self.dispEdit.insertPlainText(self.sender().text())


    def bkSpace(self):
        cursor = self.dispEdit.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deletePreviousChar()

    def Clear(self):
        """
        clears the display (sets it to empty string)
        :return: none
        """
        self.dispEdit.setText("")


    def Enter(self):
        """
        sets the vial, clears the display, sets the result tuple, and closes the dialog with success
        :return: self.accept and return
        """

        #  A BASIC VALIDATION ENSURING 12 CHARS SHOULD BE DONE HERE
        #
        #  DUPLICATE CHECK SHOULD BE A PROPER VALIDATION SINCE YOU WANT
        #  TO VALIDATE SERIAL/NETWORK INPUT TOO
        #
        #
        if re.search(r'^.\d+$', self.dispEdit.toPlainText()):
        #if len(self.dispEdit.toPlainText()) == 12 and re.search(r'^.\d+$', self.dispEdit.toPlainText()):
            self.done(1)
        else:
            self.message.setMessage(self.errorIcons[2],self.errorSounds[2], "Alpha Barcode must start with A, G, or U followed only by numbers, and must be 12 characters long", 'info')
            self.message.exec()
            return

    def closeEvent(self, event=None):
        """
        sets the result to empty and closes the dialog with reject
        :param event:
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


    def event(self, event):
        """
        event reimplements QDialog.event() and captures key presses so the user
        can use the keyboard keypad to enter values in. This greatly speeds input
        on stattions that have keyboards (for example editing stations)
        """

        #  NEED TO ADD A and G KEYS AND REMOVE "."

        if event.type() == QEvent.Type.KeyPress:

            if event.key() == Qt.Key.Key_0:
                self.getDigit(keyVal='0')
            if event.key() == Qt.Key.Key_1:
                self.getDigit(keyVal='1')
            if event.key() == Qt.Key.Key_2:
                self.getDigit(keyVal='2')
            if event.key() == Qt.Key.Key_3:
                self.getDigit(keyVal='3')
            if event.key() == Qt.Key.Key_4:
                self.getDigit(keyVal='4')
            if event.key() == Qt.Key.Key_5:
                self.getDigit(keyVal='5')
            if event.key() == Qt.Key.Key_6:
                self.getDigit(keyVal='6')
            if event.key() == Qt.Key.Key_7:
                self.getDigit(keyVal='7')
            if event.key() == Qt.Key.Key_8:
                self.getDigit(keyVal='8')
            if event.key() == Qt.Key.Key_9:
                self.getDigit(keyVal='9')
            if event.key() == Qt.Key.Key_Period:
                self.getDigit(keyVal='.')
            if event.key() == Qt.Key.Key_Enter:
                self.Enter()
            return True
        else:
            return QDialog.event(self, event)


class EnterFilter(QObject):
    """
    EnterFilter is a simple Qt Event filter that eats Enter key presses allowing the
    numpad dialog to receive these events instead of the dialog button that has focus.
    """

    def __init__(self, enterAction, parent=None):
        super(EnterFilter, self).__init__(parent)
        self.enterAction = enterAction

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.KeyPress) and (event.key() == Qt.Key.Key_Enter):
            #  eat the enter key press
            self.enterAction()
            return True
        else:
            # not an enter key press - pass along
            return QObject.eventFilter(self, obj, event)


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = VialNumDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
"""
