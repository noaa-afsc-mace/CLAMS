from PyQt6.QtWidgets import QDialog, QCheckBox
from PyQt6.QtCore import pyqtSignal
import messagedlg

class BaseEditDlg(QDialog):
    # Common signal for all edit dialogs
    changed = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        
        # Inherit resources safely
        if parent:
            self.schema = getattr(parent, 'schema', '')
            self.errorSounds = getattr(parent, 'errorSounds', None)
            self.errorIcons = getattr(parent, 'errorIcons', None)
            self.settings=parent.settings
        
        # Common message dialog
        self.message = messagedlg.MessageDlg(self)

    def setup_base(self):
        """
        Call this in your Child __init__ to wire up the buttons.
        """
        self.editBtn.clicked.connect(self.on_save_clicked)
        self.cancelBtn.clicked.connect(self.close)
    
    def setEditBtnLabel(self, label):
        self.editBtn.setText(label)

    def on_save_clicked(self):
        """
        Orchestrates the save process: Validate -> Save -> Emit -> Close
        """
        if self.validate_fields():
            self.getData()  # Gather current data from UI
            if 'Update' in self.editBtn.text():
                self.update()
            else:
                self.perform_save()
            self.changed.emit()
            self.close()

    # --- Helper: Validation ---
    def validate_required_fields(self, field_map):
        """
        field_map: list of tuples [('Field Name', value_to_check), ...]
        Returns True if all valid, False (and shows alert) if not.
        """
        for name, value in field_map:
            if not value or (isinstance(value, str) and not value.strip()):
                if self.errorIcons and self.errorSounds:
                    self.message.setMessage(self.errorIcons[2], self.errorSounds[2],
                                f"Empty {name} field! Please complete before updating.", 'info')
                    self.message.exec()
                return False
        return True

    # --- Helper: Checkboxes (Moved from WorkstationDlg so everyone can use) ---
    def sync_checkboxes(self, csv_string, widget_map):
        active_items = {x.strip() for x in (csv_string or "").split(',')}
        for key, widget in widget_map.items():
            widget.setChecked(key in active_items)
    
    # fill QGridLayout with check boxes 
    def populateCheckBoxes(self, layout, modules, maxCols):
        module_map = {}

        # 1. Loop through config with 'enumerate' to get an index counter (0, 1, 2...)
        for index, (setting_name) in enumerate(modules):
            checkbox = QCheckBox(setting_name)
            module_map[setting_name] = checkbox
            
            # Calculate the current row and column based on the index
            row = index // maxCols
            col = index % maxCols
            
            # 3. Add to layout at the calculated row and column
            layout.addWidget(checkbox, row, col)

        return module_map

    def create_csv_from_checkboxes(self, widget_map):
        vals = [key for key, widget in widget_map.items() if widget.isChecked()]
        return ','.join(vals)

    # --- Hooks (Child classes must override these) ---
    def setUp(self, record):
        """Load data into the UI."""
        pass

    def validate_fields(self):
        """Return True if UI is valid to save."""
        return True

    def perform_save(self):
        """Execute the SQL Insert/Update."""
        raise NotImplementedError