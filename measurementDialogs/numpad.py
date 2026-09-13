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
    :module:: numpad

    :synopsis: is a GUI based number pad for touch screen entry of numbers.

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
        Alicia Billings <alicia.billings@noaa.gov>
"""


from PyQt6.QtWidgets import *
from PyQt6.QtCore import QEvent, Qt, QObject
from ui import ui_NumPad


class NumPad(QDialog, ui_NumPad.Ui_numpad):

    def __init__(self, parent=None):
        super(NumPad, self).__init__(parent)
        self.setupUi(self)

        self.value = None

        #  create the enter key filter
        enterEater = EnterFilter(self.Enter, parent=self)

        #  connect the signals and install the event filters on the digit keys
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
        self.pBtnd.clicked.connect(self.getDigit)
        self.pBtnd.installEventFilter(enterEater)
        self.pBtnClr.clicked.connect(self.Clear)
        self.pBtnClr.installEventFilter(enterEater)
        self.pBtnEnt.clicked.connect(self.Enter)


    def getDigit(self, keyVal=None):
        """
        gets the passed digit and adds it to the display
        :param keyVal: value of the key as the digit
        :return: none
        """
        if not keyVal:
            button = self.sender()
            s = button.text()
        else:
            s = keyVal

        p = self.dispBox.text()

        # if there is already a decimal and s=='.', don't allow it
        if '.' in p and s == '.':
            pass
        else:
            self.dispBox.setText(p + str(s))


    def Clear(self):
        """
        clears the display (sets it to empty string)
        :return: none
        """
        self.dispBox.setText("")
        self.value = None


    def Enter(self):
        """
        sets the value, clears the display, and returns
        :return: self.accept and return
        """

        value = self.dispBox.text()
        if value == '':
            value = None
        self.value = value
        self.dispBox.setText("")
        self.accept()


    def closeEvent(self, event=None):
        """
        sets the result to empty and closes the dialog with reject
        :param event:
        :return: self.reject and return
        """
        self.dispBox.setText("")
        self.value = None
        self.reject()


    def event(self, event):
        """
        event reimplements QDialog.event() and captures key presses so the user
        can use the keyboard keypad to enter values in. This greatly speeds input
        on stattions that have keyboards (for example editing stations)
        """

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



if __name__ == "__main__":
     #  import test specific libraries
    import sys

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  create an instance of the dialog
    form = NumPad()
    form.show()

    #  and start the application event loop
    app.exec()

