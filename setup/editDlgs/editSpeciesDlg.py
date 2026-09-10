from ui import ui_EditSpeciesDlg
from .baseEditDlg import BaseEditDlg

class editSpeciesDlg(BaseEditDlg, ui_EditSpeciesDlg.Ui_EditSpeciesDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)
        self.speciesCodes = parent.speciesCodes

        # Wire the buttons to the Base logic
        self.setup_base()

    def setUp(self, species):
        if species and len(species) > 0:
            self.speciesCodeLabel.setText(species[0])
            self.sciNameLabel.setText(species[1])
            self.commonNameLabel.setText(species[2])
        else:
            self.speciesCodeLabel.setText('')
            self.sciNameLabel.setText('')
            self.commonNameLabel.setText('')

    def validate_fields(self):
        # Check species code cannot be a string
        speciesCode = self.speciesCodeLabel.text()
        if not speciesCode.isnumeric():
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                f"Species code must be a number", 'info')
            self.message.exec()
            return False
                # Check if species code already exists
        if speciesCode in self.speciesCodes:
            self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                f"Species code already exists, please enter a different code", 'info')
            self.message.exec()
            return False
        # Use the Base helper to check for empty fields
        return self.validate_required_fields([
            ("Species Code", self.speciesCodeLabel.text()),
            ("Scientific Name", self.sciNameLabel.text()),
            ("Common Name", self.commonNameLabel.text())
        ])

    def getData(self):
        self.speciesCode = self.speciesCodeLabel.text()
        self.sciName = self.sciNameLabel.text()
        self.commonName = self.commonNameLabel.text()

    def perform_save(self):
        sql = (f"INSERT INTO {self.schema}.species (species_code, parent_taxon, scientific_name, common_name) "
                f"VALUES ('{self.speciesCode}', {161061}, '{self.sciName}', '{self.commonName}')")
        self.db.dbExec(sql)