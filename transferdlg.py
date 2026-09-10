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
    :module:: TransferDlg

    :synopsis: TransferDlg presented when the user selects
               ""Transfer Weight"" in the Catch module. This is used
               to transfer weights and counts between baskets and is
               used to fix mistakes when weighing baskets.

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
        Melina Shak <melina.shak@noaa.gov>
"""

from PyQt6.QtWidgets import QDialog
import numpad
import messagedlg
import typeseldialog
from ui import ui_TransferDlg

class TransferDlg(QDialog, ui_TransferDlg.Ui_transferDlg):
    def __init__(self, parent=None):
        super(TransferDlg, self).__init__(parent)
        self.setupUi(self)
        # get stuff from your parent
        self.activeHaul=parent.activeHaul
        self.survey=parent.survey
        self.ship=parent.ship
        self.activePartition=parent.activePartition
        self.db=parent.db
        self.schema = parent.schema
        self.basketTypes=parent.basketTypes
        self.sensorMonitor=parent.sensorMonitor
        self.devices=parent.devices
        self.sounds=parent.sounds
        self.validList=[1, 1, 1]
        self.errorIcons=parent.errorIcons
        self.errorSounds=parent.errorSounds
        self.manualDevice=parent.manualDevice
        self.transCount=0
        self.transWeight=0

        # set up dialog windows
        self.message=messagedlg.MessageDlg(self)
        self.numpad = numpad.NumPad(self)
        self.typeDlg = typeseldialog.TypeSelDialog(self)

        # populate lists
        self.sampleIds={}
        sql = ("SELECT samples.sample_id, species.common_name, samples.parent_sample," +
                "samples.subcategory FROM " + self.schema + ".samples, " + self.schema + ".species WHERE " +
                "samples.species_code=species.species_code AND samples.ship=" +
                self.ship + " AND samples.survey=" + self.survey + " AND samples.event_id=" +
                self.activeHaul + " AND samples.partition='" + self.activePartition +
                "' AND samples.species_code <> 0")
        query = self.db.dbQuery(sql)

        for id, commonName, parentSample, subCategory in query:
            if subCategory is not None:
                species_tag=commonName+'-'+subCategory
            else:
                species_tag=commonName
            self.fromSampleSpc.addItem(species_tag)
            self.sampleIds.update({species_tag:id})
            self.toSampleSpc.addItem(species_tag)

        self.fromSampleSpc.setCurrentIndex(-1)
        self.toSampleSpc.setCurrentIndex(-1)

        self.cancelBtn.clicked.connect(self.bail)
        self.okBtn.clicked.connect(self.bail)
        self.getWtBtn.clicked.connect(self.getWeight)
        self.getCntBtn.clicked.connect(self.getCount)
        self.fromSampleSpc.activated[int].connect(self.getSampleList)
        self.toSampleSpc.activated[int].connect(self.getSampleList)
        self.fromBasketType.activated[int].connect(self.getOK)
        self.toBasketType.activated[int].connect(self.getOK)
        self.sensorMonitor.SensorDataReceived.connect(self.getAuto)

    def getWeight(self):
        self.numpad.msgLabel.setText("Enter Weight to Transfer")
        if self.numpad.exec():
            self.wtLabel.setText(self.numpad.value)
            self.transWeight=float(self.numpad.value)
            self.transDevice=self.manualDevice

    def getAuto(self, device, val):
        if self.getWtBtn.isEnabled():
            self.wtLabel.setText(val)
            self.transWeight=float(val)
            self.transDevice=device
            self.sounds[self.devices.index(device)].play()
            if self.frombasketType.currentText()=='Count' or self.tobasketType.currentText()=='Count':
                self.getCount()

    def getCount(self):
        self.numpad.msgLabel.setText("Enter Count to Transfer")
        self.numpad.exec()
        self.cntLabel.setText(self.numpad.value)
        self.transCount=float(self.numpad.value)

    def getSampleList(self):

        box = self.sender().objectName().lower()
        if box.startswith('from'):
            self.fromSpc = self.fromSampleSpc.currentText()
            self.fromSampleKey = self.sampleIds[self.fromSampleSpc.currentText()]
            self.fromBasketType.setEnabled(True)
            self.fromBasketType.clear()

            sql = ("SELECT baskets.basket_type FROM " + self.schema + ".baskets WHERE baskets.ship = " +
                    self.ship + " AND baskets.survey=" + self.survey +
                    " AND baskets.event_id=" + self.activeHaul + " AND baskets.sample_id=" +
                    self.fromSampleKey+" GROUP BY baskets.basket_type")
            query = self.db.dbQuery(sql)

            for basketType, in query:
                self.fromBasketType.addItem(basketType)
                self.fromBasketType.setCurrentIndex(-1)
        else:
            self.toSpc=self.toSampleSpc.currentText()
            self.toSampleKey=self.sampleIds[self.toSampleSpc.currentText()]
            self.toBasketType.setEnabled(True)
            self.toBasketType.clear()

            sql = ("SELECT gear_options.basket_type FROM " + self.schema + ".gear_options INNER JOIN " +
                    "events ON gear_options.gear=events.gear WHERE events.ship=" +
                    self.ship+" AND events.survey="+self.survey+" AND events.event_id="+
                    self.activeHaul+" AND gear_options.basket_type "+
                    "is not NULL ORDER BY gear_options.basket_type")
            query = self.db.dbQuery(sql)

            for basketType, in query:
                self.toBasketType.addItem(basketType)
                self.toBasketType.setCurrentIndex(-1)


    def getOK(self):
        if self.fromBasketType.currentIndex() >= 0 and self.toBasketType.currentIndex() >= 0:
            self.getWtBtn.setEnabled(True)
            self.fromType=self.fromBasketType.currentText()
            self.toType=self.toBasketType.currentText()
            if  self.fromBasketType.currentText()=='Count' or self.toBasketType.currentText()=='Count':
                self.getCntBtn.setEnabled(True)


    def bail(self):
        # make sure you have goods
        if self.sender().text() == 'OK':
            if self.transWeight==0:
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                        'No transfer weight provided...', 'info')
                self.message.exec()
                return

            # check weight
            sql = ("SELECT sum(baskets.weight) FROM " + self.schema + ".baskets WHERE baskets.ship = "+
                    self.ship+" AND baskets.survey="+ self.survey+" AND baskets.event_id="+
                    self.activeHaul+" AND baskets.sample_id = "+self.fromSampleKey+
                    " AND baskets.basket_type ='"+self.fromType+"'")
            query = self.db.dbQuery(sql)
            wt, = query.first()
            fullWeight = float(wt)
            if (fullWeight-self.transWeight) < 0: # the transfer is more than the total
                self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                        "Transfer weight exceeds original sample weight, can't do...", 'info')
                return

            if not self.transCount == 0:
                #  only verify count if source and destination are both count sample types
                #  (subsample will not have a count at this time so you can't verify)
                if self.fromType== 'Count':
                    sql = ("SELECT sum(baskets.count) FROM " + self.schema + ".baskets WHERE baskets.ship = "+
                        self.ship+" AND baskets.survey="+self.survey+ " AND baskets.event_id="+
                        self.activeHaul+" AND baskets.sample_id = "+self.fromSampleKey+
                        " AND baskets.basket_type ='Count'")
                    query = self.db.dbQuery(sql)
                    cnt, = query.first()
                    fullCount=float(cnt)
                    if (fullCount-self.transCount) < 0:
                        self.message.setMessage(self.errorIcons[1],self.errorSounds[1],
                            "Transfer count exceeds original sample weight, You're asking the impossible.", 'info')
                        return

            self.accept()

        else:
            #  user hit cancel button
            self.reject()
