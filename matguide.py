import os

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from ui import ui_MatGuide


class MatGuide(QDialog, ui_MatGuide.Ui_matGuide):
    def __init__(self,  parent=None):
        super(MatGuide, self).__init__(parent)
        self.setupUi(self)

        self.db=parent.db
        self.speciesName=parent.speciesName
        self.activeSpcCode = parent.activeSpcCode
        self.activeSpcSubcat = parent.activeSpcSubcat
        self.settings=parent.settings
        self.matButtons = [self.mat1Btn, self.mat2Btn, self.mat3Btn, self.mat4Btn,
            self.mat5Btn, self.mat6Btn, self.mat7Btn, self.mat8Btn]

        self.descLabel.palette().setColor(self.descLabel.backgroundRole(), QColor(255, 255, 255))

        #  connect signals/slots
        self.nextBtn.clicked.connect(self.getNext)
        self.prevBtn.clicked.connect(self.getPrev)
        self.maleBtn.clicked.connect(self.getMat)
        self.femaleBtn.clicked.connect(self.getMat)
        self.exitBtn.clicked.connect(self.goExit)

        #  restore the window state
        self.appSettings = QSettings('CLAMS', 'MatGuide')
        size = self.appSettings.value('winsize', QSize(1000,650))
        position = self.appSettings.value('winposition', QPoint(10,10))

        #  check the current position and size to make sure the app is on the screen
        position, size = self.checkWindowLocation(position, size)

        #  now move and resize the window
        self.move(position)
        self.resize(size)

        #  finish initialization in another method
        initTimer = QTimer(self)
        initTimer.setSingleShot(True)
        initTimer.timeout.connect(self.dialogInit)
        initTimer.start(0)


    def dialogInit(self):

        self.spcLabel.setText(self.speciesName)

        #  get the maturity table for this species
        sql = ("SELECT parameter_value FROM species_data WHERE lower(species_parameter)='maturity_table' "+
                "AND species_code="+self.activeSpcCode + " AND subcategory='" + self.activeSpcSubcat + "'")
        query = self.db.dbQuery(sql)
        maturityTable, = query.first()
        self.maturityTable = maturityTable

        #  check if there is a maturity table for this sp
        if self.maturityTable:

            #  set the description
            sql = ("SELECT description FROM " +
                    "maturity_tables WHERE maturity_table="+self.maturityTable)
            query = self.db.dbQuery(sql)
            matDescription, = query.first()
            self.matTabLabel.setText(matDescription)

            #  get the maturity table info and set up the UI
            sql = ("SELECT button_text, description_text_male, description_text_female FROM " +
                    "maturity_description WHERE maturity_table="+self.maturityTable+
                    " ORDER BY maturity_key")
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

            #  get the list of images for this species
            self.imageList=[]
            fileList=os.listdir(self.settings['ImageDir'] + os.sep + 'matPics')
            for i in range(len(fileList)):
                if fileList[i].startswith(str(self.activeSpcCode)):
                    self.imageList.append(fileList[i])

            #  set up the maturity buttons based on our query results
            for i in range(8):
                try:
                    self.matButtons[i].setText(self.maturityBtnText[i])
                    self.matButtons[i].clicked.connect(self.getMat)
                except:
                    self.matButtons[i].setText(' - ')
                    self.matButtons[i].hide()

        else:

            #  no table found for this species
            self.matTabLabel.setText("<None>")
            self.nextBtn.setEnabled(False)
            self.prevBtn.setEnabled(False)
            self.maleBtn.setEnabled(False)
            self.femaleBtn.setEnabled(False)
            for i in range(8):
                self.matButtons[i].hide()
            self.picLabel.setText('<No maturity table ddefined in database for this species>')
            self.descLabel.setText('')


    def getMat(self):
        matStage=-1
        #  check which button has been, er, checked
        for i in range(8):
            button = self.matButtons[i].isChecked()

            if button:
                matStage=i
        if matStage<0:# no maturity has been selected
            return
        self.dispImages=[]
        if self.maleBtn.isChecked():
            self.descLabel.setText(self.maleDesc[matStage])
            for i in range(len(self.imageList)):
                if self.imageList[i].startswith(str(self.activeSpcCode)+"_M_"+str(matStage+1)):
                    self.dispImages.append(self.imageList[i])
        else:
            self.descLabel.setText(self.femaleDesc[matStage])
            for i in range(len(self.imageList)):
                if self.imageList[i].startswith(str(self.activeSpcCode)+"_F_"+str(matStage+1)):
                    self.dispImages.append(self.imageList[i])
        self.pic=QImage()
        self.counter=0
        try:
            self.pic.load(self.settings['ImageDir']+ os.sep + 'matPics' +
                    os.sep + self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.TransformationMode.SmoothTransformation)
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
            self.pic.load(self.settings['ImageDir'] + os.sep + 'matPics' +
                    os.sep + self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.TransformationMode.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(self.pic))
        except:
            self.picLabel.setText("<font size = 24> No Image </font>")


    def getPrev(self):
        if self.counter>0:
            self.counter-=1
        else:
            self.counter=len(self.dispImages)-1

        try:
            self.pic.load(self.settings['ImageDir'] + os.sep + 'matPics' +
                    os.sep + self.dispImages[self.counter])
            self.pic=self.pic.scaledToHeight(511, Qt.TransformationMode.SmoothTransformation)
            self.picLabel.setPixmap(QPixmap.fromImage(self.pic))
        except:
            self.picLabel.setText("<font size = 24> No Image </font>")


    def goExit(self):

        #  store the window size and position
        self.appSettings.setValue('winposition', self.pos())
        self.appSettings.setValue('winsize', self.size())

        self.accept()


    def checkWindowLocation(self, position, size, padding=[5, 25]):
        '''
        checkWindowLocation accepts a window position (QPoint) and size (QSize)
        and returns a potentially new position and size if the window is currently
        positioned off the screen.

        This function uses QScreen.availableVirtualGeometry() which returns the full
        available desktop space *not* including taskbar. For all single and "typical"
        multi-monitor setups this should work reasonably well. But for multi-monitor
        setups where the monitors may be different resolutions, have different
        orientations or different scaling factors, the app may still fall partially
        or totally offscreen. A more thorough check gets complicated, so hopefully
        those cases are very rare.

        If the user is holding the <shift> key while this method is run, the
        application will be forced to the primary monitor.
        '''

        #  create a QRect that represents the app window
        appRect = QRect(position, size)

        #  check for the shift key which we use to force a move to the primary screem
        resetPosition = QGuiApplication.queryKeyboardModifiers() == Qt.KeyboardModifier.ShiftModifier
        if resetPosition:
            position = QPoint(padding[0], padding[0])

        #  get a reference to the primary system screen - If the app is off the screen, we
        #  will restore it to the primary screen
        primaryScreen = QGuiApplication.primaryScreen()

        #  assume the new and old positions are the same
        newPosition = position
        newSize = size

        #  Get the desktop geometry. We'll use availableVirtualGeometry to get the full
        #  desktop rect but note that if the monitors are different resolutions or have
        #  different scaling, some parts of this rect can still be offscreen.
        screenGeometry = primaryScreen.availableVirtualGeometry()

        #  if the app is partially or totally off screen or we're force resetting
        if resetPosition or not screenGeometry.contains(appRect):

            #  check if the upper left corner of the window is off the left side of the screen
            if position.x() < screenGeometry.x():
                newPosition.setX(screenGeometry.x() + padding[0])
            #  check if the upper right is off the right side of the screen
            if position.x() + size.width() >= screenGeometry.width():
                p = screenGeometry.width() - size.width() - padding[0]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setX(p)
            #  check if the top of the window is off the top/bottom of the screen
            if position.y() < screenGeometry.y():
                newPosition.setY(screenGeometry.y() + padding[0])
            if position.y() + size.height() >= screenGeometry.height():
                p = screenGeometry.height() - size.height() - padding[1]
                if p < padding[0]:
                    p = padding[0]
                newPosition.setY(p)

            #  now make sure the lower right (resize handle) is on the screen
            if (newPosition.x() + newSize.width()) > screenGeometry.width():
                newSize.setWidth(screenGeometry.width() - newPosition.x() - padding[0])
            if (newPosition.y() + newSize.height()) > screenGeometry.height():
                newSize.setHeight(screenGeometry.height() - newPosition.y() - padding[1])

        return [newPosition, newSize]

