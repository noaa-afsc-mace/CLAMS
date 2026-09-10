from ui import ui_PersonnelDlg
import setup.editDlgs.editPersonDlg as editPersonDlg
from PyQt6.QtWidgets import QTableWidgetItem
from .baseTableDlg import BaseTableDlg

class personnelDlg(BaseTableDlg, ui_PersonnelDlg.Ui_PersonnelDlg):

    def __init__(self, db, parent=None):
        super().__init__(db, parent)
        self.setupUi(self)

        dialog = editPersonDlg.editPersonDlg(self.db, parent=self)
        dialog.changed.connect(self.populate_table)
        
        # Wire up Base
        self.setup_base(self.personnelTable, dialog)

        # Wire up the extra "Bulk" buttons specific to this dialog
        self.bulkEnableBtn.clicked.connect(self.bulkEnableClicked)
        self.bulkDisableBtn.clicked.connect(self.bulkDisableClicked)

    # --- Implement Hooks ---

    def get_select_sql(self):
        return (f"SELECT scientist, affiliation, active "
               f"FROM {self.schema}.personnel ORDER BY scientist")

    def fill_row(self, row_idx, row_data):
        scientist, affiliation, active = row_data
        active_str = 'Yes' if str(active) == '1' else 'No'
        
        self.table.setItem(row_idx, 0, QTableWidgetItem(scientist))
        self.table.setItem(row_idx, 1, QTableWidgetItem(affiliation))
        self.table.setItem(row_idx, 2, QTableWidgetItem(active_str))

    def get_data_for_edit(self, row_idx):
        # Personnel dialog sends 3 columns to the edit window
        return [
            self.table.item(row_idx, 0).text(),
            self.table.item(row_idx, 1).text(),
            self.table.item(row_idx, 2).text()
        ]

    def on_selection_change(self, has_selection):
        # This automatically runs when selection changes in the Base class
        self.bulkEnableBtn.setEnabled(has_selection)

    # --- Specific Logic (Bulk Actions) ---
    def bulkDisableClicked(self):
        sql = f"UPDATE {self.schema}.personnel SET active=0"
        self.db.dbExec(sql)
        self.populate_table()

    def bulkEnableClicked(self):
        ranges = self.table.selectedItems()
        if not ranges: 
            return

        # Get list of scientists from selection
        scientists = []
        for val in ranges:
            if (val.column() == 0):
                scientists.append(f"'{val.text()}'")
        formattedSci = ", ".join(scientists)
        
        # Use schema if available, else default        
        sql = f"UPDATE {self.schema}.personnel SET active=1 WHERE scientist in ({formattedSci})"
        self.db.dbExec(sql)
        self.populate_table()