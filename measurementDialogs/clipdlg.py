"""
Special dialog for entering the cell number for the fin clip

created by: Alicia Billings - alicia.billings@noaa.gov
date: April 2019
notes:

updated January 2025 to PyQt6 and Python 3 by Alicia Billings, NWFSC
specific updates:
- PyQt import statement
- added some function explanation
- fixed any PEP8 issues
- added a main to test if works (commented out)
"""

from PyQt6.QtWidgets import *
from ui import ui_ClipDlg
from sys import argv
import numpad


class ClipDlg(QDialog, ui_ClipDlg.Ui_Dialog):
    def __init__(self, parent=None):
        super(ClipDlg, self).__init__(parent)
        self.setupUi(self)

        self.oto_present = True

        self.result = ()

        #  connect signals
        self.pb_clip.clicked.connect(self.get_cell_num)

        #  if there is already an entry, reset the button text
        self.set_btn_txt()

    def setup(self, parent):
        """
        does nothing
        :param parent: not used in this function
        :return: none
        """
        pass

    def set_btn_txt(self):
        """
        sets the button text
        :return: none
        """
        self.pb_clip.setText("Click here")

    def get_cell_num(self):
        """
        opens up the number pad to have user enter the cell number
        :return: none
        """
        rst = numpad.NumPad()
        rst.exec()
        self.pb_clip.setText(rst.value)
        self.result = (True, self.sender().text())
        self.accept()

    def closeEvent(self, event):
        """
        sets the result tuple to access from the calling dialog
        :return: self.reject and return
        """
        self.result = (False, '')
        self.reject()


"""
if __name__ == "__main__":
    #  create an instance of QApplication
    app = QApplication(argv)
    #  create an instance of the dialog
    form = ClipDlg()
    form.show()
    #  and start the application...
    app.exec()
"""
