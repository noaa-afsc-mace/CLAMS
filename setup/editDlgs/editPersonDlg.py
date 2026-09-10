from ui import ui_EditPersonnelDlg
from .baseEditDlg import BaseEditDlg

class editPersonDlg(BaseEditDlg, ui_EditPersonnelDlg.Ui_EditPersonnelDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        # Wire the buttons to the Base logic
        self.setup_base()

    def setUp(self, currPerson):
        if currPerson and len(currPerson) > 0:
            self.scientistLabel.setText(currPerson[0])
            self.affiliationLabel.setText(currPerson[1])
            self.isActive.setChecked(currPerson[2] == 'Yes')
        else:
            self.scientistLabel.setText('')
            self.affiliationLabel.setText('')
            self.isActive.setChecked(False)

    def validate_fields(self):
        # Use the Base helper to check for empty fields
        return self.validate_required_fields([
            ("Scientist", self.scientistLabel.text()),
            ("Affiliation", self.affiliationLabel.text())
        ])

    def getData(self):
        self.currScientist = self.scientistLabel.text()
        self.currAffiliation = self.affiliationLabel.text()
        self.currIsActive = 1 if self.isActive.isChecked() else 0

    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.personnel (scientist, affiliation, active) "
                f"VALUES ('{self.currScientist}', '{self.currAffiliation}', '{self.currIsActive}')")
        self.db.dbExec(sql)
    
    def update(self):
        sql = (f"UPDATE {self.schema}.personnel SET active={self.currIsActive} "
                f"WHERE scientist='{self.currScientist}' and affiliation='{self.currAffiliation}'")
        self.db.dbExec(sql)