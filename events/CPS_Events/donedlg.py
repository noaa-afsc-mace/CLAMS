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
.. module:: donedlg

    :synopsis: donedlg is a dialog that collects the gear performance and overall comments from a tow;
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
from ui import ui_DoneDlg
import keypad
import messagedlg


class DoneDlg(QDialog, ui_DoneDlg.Ui_doneDlg):

    def __init__(self, parent=None):
        super(DoneDlg, self).__init__(parent)
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
        self.cur_coms = ""

        self.message = messagedlg.MessageDlg(self)
        self.cb_perf.setCurrentIndex(0)

        # list to hold performance codes
        perfVal = []

        # set up performance box
        # fill the performance dialog
        self.cb_perf.clear()
        perf_sql = ("SELECT event_performance.performance_code, event_performance.description "
                    "FROM " + self.schema + ".event_performance ORDER BY event_performance.performance_code DESC")
        perf_query = self.db.dbQuery(perf_sql)

        # init reason options and set current reason
        for perfCode, desc in perf_query:
            perf_txt = str(perfCode) + " - " + desc
            self.cb_perf.addItem(perf_txt)
            perfVal.append(perfCode)

        # get overall comments and performance code from db to display
        query = ("SELECT performance_code, comments FROM " + self.schema + ".events WHERE ship=" +
                   self.ship + " AND survey=" + self.survey + " AND event_id=" + self.activeEvent)
        result_query = self.db.dbQuery(query)
        val = result_query.first()

        # set comment to db comment
        self.te_comment.setText(val[1])

        # set cb_perf index
        if val[0] is not None:
            # find index of performance code
            index = perfVal.index(val[0])
            self.cb_perf.setCurrentIndex(index)
        
        # get average values from events_data table
        if (hasattr(parent, 'avgLabels') and len(parent.avgLabels) > 0):
            formattAvgLabels = ", ".join([f"'{x}'" for x in parent.avgLabels])
            avgQuery = ("SELECT event_parameter, parameter_value FROM " + self.schema +
                        ".event_data WHERE ship=" + self.ship + " AND survey=" + self.survey + 
                        " AND event_id=" + self.activeEvent +
                        " AND event_parameter in (" + formattAvgLabels + ") ")
            avg_query = self.db.dbQuery(avgQuery)

            # display average values
            row = 0
            for val in avg_query:
                label = QLabel("<b>" + val[0] + ':</b>')
                label.setMinimumHeight(20)
                self.avgVals.addWidget(label, row, 0)

                value = QLabel(val[1])
                value.setMinimumHeight(20)
                self.avgVals.addWidget(value, row, 1)
                row+=1

        # set signals and slots
        self.te_comment.selectionChanged.connect(self.display_keypad)
        self.pb_done.clicked.connect(self.save)
        self.pb_cancel.clicked.connect(self.cancel)
        self.ckb_man.hide()

    def display_keypad(self):
        """
        displays the keypad in case the user doesn't have a keyboard (although keyboard works as well)
        and updates the text edit with the entered content
        :return:
        """
        keyDialog = keypad.KeyPad(self.cur_coms, self)
        keyDialog.exec()
        if keyDialog.okFlag:
            text = keyDialog.dispEdit.toPlainText()
            self.te_comment.setText(text)

    def save(self):
        """

        :return: none
        """
        # check if the performance has been recorded and that a comment has been entered
        if self.cb_perf.currentText() == '':
            self.message.setMessage(self.errorIcons[0], self.errorSounds[0],
                                    "You must enter the gear performance for this operation", "error")
            self.message.show()
        else:
            # get the performance code from the cb text
            comments = self.te_comment.toPlainText() if self.te_comment.toPlainText() else ''
            code = self.cb_perf.currentText().split(" - ")
            update_sql = ("UPDATE " + self.schema + ".events SET performance_code = " + str(code[0]) +
                          ", comments = '" + comments + "' WHERE ship=" + self.ship + " AND survey="
                          + self.survey + " AND event_id=" + str(self.activeEvent))
            self.db.dbQuery(update_sql)

            self.accept()

    def cancel(self):
        self.reject()

    def closeEvent(self, event=None):
        self.reject()
