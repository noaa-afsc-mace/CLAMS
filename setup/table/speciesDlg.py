from ui import ui_SpeciesDlg
import setup.editDlgs.editSpeciesDlg as editSpeciesDlg
from PyQt6.QtWidgets import QTableWidgetItem
from .baseTableDlg import BaseTableDlg

class speciesDlg(BaseTableDlg, ui_SpeciesDlg.Ui_SpeciesDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)
        self.speciesCodes = []

        dialog = editSpeciesDlg.editSpeciesDlg(self.db, parent=self)
        dialog.changed.connect(self.populate_table)
        
        # Wire up Base
        self.setup_base(self.speciesTable, dialog)

    # --- Implement Hooks ---

    def get_select_sql(self):
        return (f"SELECT species_code, parent_taxon, scientific_name, common_name "
               f"FROM {self.schema}.species ORDER BY species")

    def fill_row(self, row_idx, row_data):
        species_code, parent_taxon, scientific_name, common_name = row_data
        self.speciesCodes.append(species_code)  # Store the ID for later use (like Edit)
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(species_code))
        self.table.setItem(row_idx, 1, QTableWidgetItem(parent_taxon))
        self.table.setItem(row_idx, 2, QTableWidgetItem(scientific_name))
        self.table.setItem(row_idx, 3, QTableWidgetItem(common_name))