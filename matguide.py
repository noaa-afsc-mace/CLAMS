import os

from PyQt6 import QtSql
from PyQt6.QtCore import Qt, QTimer, QObject, QUrl
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QApplication

from ui import ui_MatGuide


class MatGuide(QDialog, ui_MatGuide.Ui_matGuide):
    def __init__(self,  parent=None):
        super(MatGuide, self).__init__(parent)
        self.setupUi(self)
        self.db=parent.db
        self.speciesName=parent.speciesName
        self.settings=parent.settings

        self.descLabel.palette().setColor(self.descLabel.backgroundRole(), QColor(255, 255, 255))

        #  get the maturity table information
        sql=("SELECT species_code FROM species WHERE common_name='"+self.speciesName+"'")
        query = self.db.dbQuery(sql)
        speciesCode, = query.first()
        self.speciesCode=speciesCode

        sql = ("SELECT parameter_value FROM species_data WHERE lower(species_parameter)='maturity_table' "+
                "AND species_code="+self.speciesCode)
        query = self.db.dbQuery(sql)
        maturityTable, = query.first()
        self.maturityTable=maturityTable


        self.picLabel.setText(self.speciesName)
        self.matTabLabel.setText(self.maturityTable)
        sql = ("SELECT button_text, description_text_male, description_text_female FROM " +
                "maturity_description WHERE maturity_table="+self.maturityTable+" ORDER BY maturity_key")
        self.maturityBtnText=[]
        self.maleDesc=[]
        self.femaleDesc=[]
        self.nextBtn.setEnabled(False)
        self.prevBtn.setEnabled(False)
        query = self.db.dbQuery(sql)
        for buttonText, descriptionTextMale, descriptionTextFemale in query:
            self.maturityBtnText.append(buttonText)
            self.maleDesc.append(descriptionTextMale)
            self.femaleDesc.append(descriptionTextFemale)

        self.imageList=[]
        fileList=os.listdir(self.settings['ImageDir']+'\\matPics')
        for i in range(len(fileList)):
            if fileList[i].startswith(str(self.speciesCode)):
                self.imageList.append(fileList[i])

        for i in range(8):
            try:
                exec(str("self.mat"+str(i+1)+"Btn.setText(self.maturityBtnText[i])"))
            except:
                exec(str("self.mat"+str(i+1)+"Btn.setText(' -  ')"))
                exec(str("self.mat"+str(i+1)+"Btn.setEnabled(False)"))

        self.mat1Btn.clicked.connect(self.getMat)
        self.mat2Btn.clicked.connect(self.getMat)
        self.mat3Btn.clicked.connect(self.getMat)
        self.mat4Btn.clicked.connect(self.getMat)
        self.mat5Btn.clicked.connect(self.getMat)
        self.mat6Btn.clicked.connect(self.getMat)
        self.mat7Btn.clicked.connect(self.getMat)
        self.mat8Btn.clicked.connect(self.getMat)
        self.nextBtn.clicked.connect(self.getNext)
        self.prevBtn.clicked.connect(self.getPrev)
        self.exitBtn.clicked.connect(self.goExit)
        self.maleBtn.clicked.connect(self.getMat)
        self.femaleBtn.clicked.connect(self.getMat)

       # screen=QDesktop().screenGeometry()
       # window=self.geometry()
       # self.setGeometry((screen.width()-window.width())/2, self.settings['WindowAnchor']-
       #         window.height(), window.width(), window.height())
       # self.setMinimumSize(window.width(), window.height())
       # self.setMaximumSize(window.width(), window.height())


    def getMat(self):
        matStage=-1
        for i in range(8):
            exec(str("button=self.mat"+str(i+1)+"Btn.isChecked()"))
          #  if button:
          #      matStage=i
        if matStage<0:# no maturity has been selected
            return
        self.dispImages=[]
        if self.maleBtn.isChecked():
            self.descLabel.setText(self.maleDesc[matStage])
            for i in range(len(self.imageList)):
                if self.imageList[i].startswith(str(self.speciesCode)+"_M_"+str(matStage+1)):
                    self.dispImages.append(self.imageList[i])
        else:
            self.descLabel.setText(self.femaleDesc[matStage])
            for i in range(len(self.imageList)):
                if self.imageList[i].startswith(str(self.speciesCode)+"_F_"+str(matStage+1)):
                    self.dispImages.append(self.imageList[i])
        self.pic=QImage()
        self.counter=0
        try:
            self.pic.load(self.settings['ImageDir']+'\\matPics\\'+self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(self.pic))
        except:
            self.picLabel.setText("<font size = 24> No Image </font>")
        self.nextBtn.setEnabled(True)
        self.prevBtn.setEnabled(True)

    def getNext(self):
        if self.counter<len(self.dispImages)-1:
            self.counter+=1
        else:
            self.counter=0
        try:
            self.pic.load(self.settings['ImageDir']+'\\matPics\\'+self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(self.pic))
        except:
            self.picLabel.setText("<font size = 24> No Image </font>")
    def getPrev(self):
        if self.counter>0:
            self.counter-=1
        else:
            self.counter=len(self.dispImages)-1
        try:
            self.pic.load(self.settings['ImageDir']+'\\matPics\\'+self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(self.pic))
        except:
            self.picLabel.setText("<font size = 24> No Image </font>")


    def goExit(self):
        self.accept()

'''
Simple dialogs can be tested by executing directly in main, but dialogs that
require additional setup and/or the full application event loop running must
be executed by a testing class that executes the dialog within the event loop.
'''
class dialogTest(QObject):
        def __init__(self):
            super(dialogTest, self).__init__(None)

            #  we use a timer here to add runTest to the event processing queue and
            #  then exit the init. Execution will return to main, where the
            #  application event loop will be started by the call to app.exec() which
            #  will then start processing events on the queue which will then execute
            #  runTest with the event loop running.
            startTimer = QTimer(self)
            startTimer.timeout.connect(self.runTest)
            startTimer.setSingleShot(True)
            startTimer.start(0)


        def runTest(self):

            #  set up the error sound and icon for the test
            errorSoundFile = 'sounds/Blaster.wav'
            errorSound = QSoundEffect()
            errorSound.setSource(QUrl.fromLocalFile(errorSoundFile))

            errorIconFile = 'icons/plankton.jpg'
            errorIcon = QPixmap.fromImage(QImage(errorIconFile))

            #  create an instance of the dialog and show
            testDialog = MatGuide()
            testDialog.setMessage(errorIcon, errorSound, "Do you want to do this?",
                    'choice')
            result = testDialog.exec()

            #  print the output to the console
            print(result)

            #  exit the application
            QApplication.instance().quit()


if __name__ == "__main__":
    #  import test specific libraries
    import sys
    from PyQt6.QtMultimedia import QSoundEffect

    #  create an instance of QApplication
    app = QApplication(sys.argv)

    #  instantiate the test
    form = dialogTest()

    #  and start the application event loop
    app.exec()
