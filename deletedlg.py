"""
deletedlg is a dialog that presents options for deleting a specimen or
individual measurements associated with a specimen.

"""

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from ui import ui_DeleteDlg



class DeleteDlg(QDialog, ui_DeleteDlg.Ui_deleteDlg):

    def __init__(self,  parent=None):

        #  execute superclass inits
        super(DeleteDlg, self).__init__(parent)
        #  setup the UI elements
        self.setupUi(self)

        #  connect signals
        self.cancelBtn.clicked.connect(self.reject)
        self.okayBtn.clicked.connect(self.accept)


    def set_delete_options(self, measurements):
        """
        Populates the dropdown with the available deletion options.
        """
        self.deleteItems.clear()
        self.deleteItems.addItems(measurements)


    def get_selected_option(self):
        """
        Returns the user's selection from the dropdown.
        """
        return self.deleteItems.currentText()


    def goYes(self):
        """
        Accepts the dialog when the 'Yes' button is clicked.
        """
        self.accept()


    def goNo(self):
        self.reject()