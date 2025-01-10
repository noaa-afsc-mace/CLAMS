"""
updated December 2024 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- signal/slot connections
- moved variable declarations into __init__
- changed order of functions to put setup first
- added some function explanation
- fixed any PEP8 issues
- added a main to test if works (commented out)
"""

from PyQt6.QtWidgets import *
from ui import ui_YesNoDlg
from sys import argv


class BIAYesNoDlg(QDialog, ui_YesNoDlg.Ui_YesNoDlg):
    def __init__(self,  parent=None):
        super(BIAYesNoDlg, self).__init__(parent)
        self.setupUi(self)

        # variable declaration
        self.result = ()

        # signal/slot connections
        self.yesBtn.clicked.connect(self.getResponse)
        self.noBtn.clicked.connect(self.getResponse)

        #  set the caption
        self.setCaption('Are you taking a BIA sample?')

    def setup(self, parent):
        """
        does nothing
        :param parent: not used in this function
        :return: none
        """
        pass

    def setCaption(self, text):
        """
        sets the message label to the passed text
        :param text: text to set label to
        :return: none
        """
        self.msgLabel.setText(text)

    def getResponse(self):
        """
        sets the result tuple to access from the calling dialog with the variables
        :return: self.accept the dialog and return
        """
        #  return the text
        self.result = (True, self.sender().text())
        self.accept()

    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


# """
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = BIAYesNoDlg()
    #  show it
    form.show()
    #  and start the application...
    app.exec()
# """
