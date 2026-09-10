

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import connectdlg
import AdminLoginDlg
from ui import ui_CLAMSMaintenance


class CLAMSMaintenance(QMainWindow, ui_CLAMSMaintenance.Ui_CLAMSMaintenance):

    def __init__(self, parent=None):
        #  initialize the superclasses
        super(CLAMSMaintenance, self).__init__(parent)
        self.setupUi(self)

        self.db=None

        #  connect signals
        self.connect(self.trawlEventBtn, SIGNAL("clicked()"), self.launchEvent)
        self.connect(self.procBtn, SIGNAL("clicked()"), self.processHaul)
        self.connect(self.utilitiesBtn, SIGNAL("clicked()"), self.utilities)
        self.connect(self.adminBtn, SIGNAL("clicked()"),self.administration)
        self.connect(self.exitBtn, SIGNAL("clicked()"), self.goExit)

        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        self.connect(initTimer, SIGNAL("timeout()"), self.applicationInit)
        initTimer.start(0)


    def applicationInit(self):

        connectDlg = connectdlg.ConnectDlg(label='CLAMSMaintenance', parent=self)
        if not connectDlg.exec_():
            self.db = None
            self.close()
            return

        self.db=connectDlg.db

        # set the date format for our session
        sql="alter session set NLS_TIMESTAMP_FORMAT='MMDDYYYY HH24:MI:SS.FF3'"
        db.dbExec(sql)

        adminDlg = AdminLoginDlg.AdminLoginDlg(self)
        if not adminDlg.exec_():
            self.close()
            return



    def getSurveys(self):
        query = self.db.dbQuery("SELECT parameter_value from " + self.schema + ".application_configuration WHERE " +
                "application_parameter='AdminPassword'")
        password = query[0]
        query = self.db.dbQuery("SELECT parameter_value from " + self.schema + ".application_configuration WHERE " +
                "application_parameter='AdminSalt'")
        salt = query[0]


    def closeEvent(self, event=None):

        if not self.db==None:
            self.db.dbClose()




if __name__ == "__main__":

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  create an instance of the CLAMS main form
    form = CLAMSMaintenance()

    #  show it
    form.show()

    #  and start the application...
    app.exec_()
