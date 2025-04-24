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
.. module:: abortdlg

    :synopsis: abortdlg is a dialog that collects the information for an event that is being aborted;
                used by the NWFSC;
                created by Alicia Billings <alicia.billings@noaa.gov>

| Developed by:  Rick Towler   <rick.towler@noaa.gov>
|                Kresimir Williams   <kresimir.williams@noaa.gov>
| National Oceanic and Atmospheric Administration (NOAA)
| National Marine Fisheries Service (NMFS)
| Alaska Fisheries Science Center (AFSC)
| Midwater Assesment and Conservation Engineering Group (MACE)
|
| Author:
|       Kresimir Williams   <kresimir.williams@noaa.gov>
| Maintained by:
|       Rick Towler   <rick.towler@noaa.gov>
|       Kresimir Williams   <kresimir.williams@noaa.gov>
|       Mike Levine   <mike.levine@noaa.gov>
|       Nathan Lauffenburger   <nathan.lauffenburger@noaa.gov>
"""

from PyQt6.QtWidgets import *
from ui import ui_AbortDlg
import keypad
import messagedlg


class AbortDlg(QDialog, ui_AbortDlg.Ui_abortDlg):

    def __init__(self, parent=None):
        super(AbortDlg, self).__init__(parent)
        self.setupUi(self)
        self.settings = parent.settings
        self.db = parent.db
        self.activeEvent = parent.activeEvent
        self.survey = parent.survey
        self.schema = parent.schema
        self.ship = parent.ship
        self.reloaded = parent.reloaded
        self.timeDlg = parent.timeDlg
        self.errorSounds = parent.errorSounds
        self.errorIcons = parent.errorIcons
        self.gear = parent.gear
        self.scientist = parent.scientist
        self.final = False

        self.message = messagedlg.MessageDlg(self)

        # set up performance box
        # fill the performance dialog
        self.cb_perf.clear()
        perf_sql = ("SELECT event_performance.performance_code, event_performance.description "
                    "FROM " + self.schema + ".event_performance WHERE performance_code < 0 "
                                            "ORDER BY event_performance.performance_code DESC")
        perf_query = self.db.dbQuery(perf_sql)
        for perfCode, desc in perf_query:
            perf_txt = str(perfCode) + " - " + desc
            self.cb_perf.addItem(perf_txt)
            self.cb_perf.setCurrentIndex(-1)

        # set signals and slots
        self.te_comment.selectionChanged.connect(self.display_keypad)
        self.pb_done.clicked.connect(self.save)
        self.pb_cancel.clicked.connect(self.cancel)

    def display_keypad(self):
        """
        displays the keypad in case the user doesn't have a keyboard (although keyboard works as well)
        and updates the text edit with the entered content
        :return:
        """
        keyDialog = keypad.KeyPad('', self)
        keyDialog.exec()
        if keyDialog.okFlag:
            text = keyDialog.dispEdit.toPlainText()
            self.te_comment.setText(text)

    def save(self):
        """
        # force reason for abort with comment
        # remind that the operation number will be burned
        # set the performance to the reason

        :return: none
        """
        # check if the performance has been recorded and that a comment has been entered
        if self.cb_perf.currentText() == '':
            self.final = False
        elif self.te_comment.toPlainText() == '':
            self.final = False
        else:
            self.final = True

        if not self.final:
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "You must enter all fields to abort this operation", "error")
            self.message.show()
        else:
            # get the performance code from the cb text
            code, desc = self.cb_perf.currentText().split(" - ")
            # get current comments
            com_sql = ("SELECT comments FROM " + self.schema + ".events WHERE ship=" + self.ship +
                       " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent))
            com_query = self.db.dbQuery(com_sql)
            comments, = com_query.first()
            if comments not in ['', None]:
                # add to comments
                fin_coms = comments + "; ABORT COMS: " + self.te_comment.toPlainText()
            else:
                fin_coms = "ABORT COMS: " + self.te_comment.toPlainText()
            # update
            update_sql = ("UPDATE " + self.schema + ".events SET performance_code = " + str(code) +
                          " AND comments = '" + fin_coms + "' WHERE ship=" + self.ship +
                          " AND survey=" + self.survey + " AND event_id=" + str(self.activeEvent))
            print(update_sql)
            # update_query = self.db.dbQuery(update_sql)

            self.accept()

    def cancel(self):
        self.reject()

    def closeEvent(self, event=None):
        self.reject()
