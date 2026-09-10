from PyQt6.QtWidgets import QDialog, QTableWidgetItem

class BaseTableDlg(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.currentRow = 0
        # Handle parent attributes safely
        if parent:
            self.schema = getattr(parent, 'schema', '')
            self.errorSounds = getattr(parent, 'errorSounds', None)
            self.errorIcons = getattr(parent, 'errorIcons', None)
            self.settings=parent.settings

    def setup_base(self, table_widget, edit_dialog):
        """
        Call this from the Child Class after setupUi() to wire everything up.
        """
        self.table = table_widget
        self.edit_dialog = edit_dialog

        # Connect Child Dialog signal
       # if self.edit_dialog:
       #     self.edit_dialog.changed.connect(self.populate_table)

        # Connect Standard Buttons (assuming they exist in the UI)
        if hasattr(self, 'addBtn'):
            self.addBtn.clicked.connect(self.add_clicked)
        if hasattr(self, 'editBtn'):
            self.editBtn.clicked.connect(self.edit_clicked)
        if hasattr(self, 'doneBtn'):
            self.doneBtn.clicked.connect(self.done_clicked)
        
        # Connect Table Selection
        self.table.itemSelectionChanged.connect(self.update_button_status)

        # Initial Load
        self.populate_table()

    def update_button_status(self):
        """Enable Edit button only if a row is selected."""
        has_selection = bool(self.table.selectedRanges())
        self.currentRow = self.table.currentRow()

        if hasattr(self, 'editBtn'):
            self.editBtn.setEnabled(has_selection)
        
        # Hook for extra buttons (like Bulk Enable/Disable)
        if hasattr(self, 'on_selection_change'):
            self.on_selection_change(has_selection)

    def populate_table(self):
        """Generic table loader."""
        self.table.clearContents()
        self.table.setRowCount(0)
        
        # Get the specific SQL from the child class
        sql = self.get_select_sql() 
        if not sql:
            return

        query = self.db.dbQuery(sql)
        
        for row_idx, row_data in enumerate(query):
            self.table.insertRow(row_idx)
            # Let the child class decide how to fill the columns
            self.fill_row(row_idx, row_data)
        
        self.table.resizeColumnsToContents()
        self.table.scrollToBottom()

    def add_clicked(self):
        """Open dialog in Add mode (empty list)."""
        if self.edit_dialog:
            self.edit_dialog.setEditBtnLabel("Add")
            self.edit_dialog.setUp([])
            self.edit_dialog.exec()

    def edit_clicked(self):
        """Open dialog in Edit mode."""
        if self.currentRow < 0:
            return
         
        # Get specific data needed for the edit dialog from child
        record_data = self.get_data_for_edit(self.currentRow)
        
        if self.edit_dialog:
            self.edit_dialog.setEditBtnLabel("Update")
            self.edit_dialog.setUp(record_data)
            self.edit_dialog.exec()

    def done_clicked(self):
        self.reject()