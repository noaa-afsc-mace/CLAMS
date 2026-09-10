
#import base64
import uuid
import hashlib
from PyQt4 import QtCore, QtGui
from ui import ui_AdminLoginDlg

def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex

    hashed_password = hashlib.sha512(password + salt).hexdigest()

    return (hashed_password, salt)


def verify_password(password, hashed_password, salt):
    re_hashed, salt = hash_password(password, salt)

    return re_hashed == hashed_password


class AdminLoginDlg(QtGui.QDialog, ui_AdminLoginDlg.Ui_AdminLoginDlg):

    def __init__(self, db, parent=None):
        #  set up the GUI
        super(AdminLoginDlg, self).__init__(parent)
        self.setupUi(self)

        self.ok = False
        self.db = db

        #  set up signals
        self.connect(self.okBtn, QtCore.SIGNAL("clicked()"), self.okClicked)
        self.connect(self.cancelBtn, QtCore.SIGNAL("clicked()"), self.cancelClicked)


    def okClicked(self):
        query = self.db.dbQuery("SELECT parameter_value from " + self.schema + ".application_configuration WHERE " +
                "application_parameter='AdminPassword'")
        password = query[0]
        query = self.db.dbQuery("SELECT parameter_value from " + self.schema + ".application_configuration WHERE " +
                "application_parameter='AdminSalt'")
        salt = query[0]

        if verify_password(password, salt):
            self.accept()
        else:
            QtGui.QMessageBox.fatal(self, "Incorrect Administrator Password.")
            self.reject()


    def cancelClicked(self):
        self.reject()


