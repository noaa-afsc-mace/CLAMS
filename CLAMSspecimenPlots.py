import math
import pyqtgraph as pg 

from PyQt6.QtCore import *
from PyQt6.QtWidgets import QDialog

from ui import ui_CPSSpecPlots

class SpecPlotsDialog(QDialog, ui_CPSSpecPlots.Ui_Dialog):
    '''Dialog class for CPSSpecPlots.ui'''
    def __init__(self, parent=None):
        super(SpecPlotsDialog, self).__init__(parent)
        self.setupUi(self)
        # Style the plots (optional, but looks nice!)
        self.LWPlot.setBackground('w') # white background
        self.LWPlot.setTitle("Length vs. Weight - Current Haul", color="b", size="12pt")
        self.LWPlot.setLabel('left', 'Weight (g)', color='black')
        self.LWPlot.setLabel('bottom', 'Length (mm)', color='black')
        self.LWPlot.showGrid(x=True, y=True)

        self.OtoLengthPlot.setBackground('w')
        self.OtoLengthPlot.setTitle("Otolith vs. Lengths Taken - Whole Survey", color="b", size="12pt")
        self.OtoLengthPlot.setLabel('left', 'Count', color='black')
        self.OtoLengthPlot.setLabel('bottom', 'Length (mm)', color='black')
        self.OtoLengthPlot.showGrid(x=True, y=True)
        
        # Call the method to draw the data
        self.plot_data()

    def showPlots(self):
        # Pass `self` so the dialog can access the database or variables from the main window!
        plots_dialog = SpecPlotsDialog(parent=self)
        plots_dialog.exec()

    def plot_data(self):
        '''Extracts data from the database and plots it on the graph widgets.'''
        
        # 1. Grab the active species info
        species_name = self.parent().activeSpcName.lower()
        species_code = str(self.parent().activeSpcCode)
        
        # 2. Determine the correct length column and bin sizes based on the species
        if "anchovy" in species_name or "sardine" in species_name or species_code in ['161828', '161729']:
            length_col = "standard_length_mm"
            x_label = "Standard Length (mm)"
            bin_step = 10
            bins = list(range(10, 330, bin_step)) # 10 to 320
        elif "mackerel" in species_name or species_code in ['172412', '168586', '164792', '161746', '551209','161702','162053','162028','162030','162035','162049','166012','162051',
                                                            '161983','161975','161976','161977','161979','161980','161989','161974'
                                                            ]:
            length_col = "fork_length_mm"
            x_label = "Fork Length (mm)"
            bin_step = 25
            bins = list(range(0, 625, bin_step)) # 0 to 600
        else:
            length_col = "length" 
            x_label = "Length (mm)"
            bin_step = 10
            bins = list(range(0, 1000, bin_step))

        # Update the X-axis labels
        self.LWPlot.setLabel('bottom', x_label, color='black')
        self.OtoLengthPlot.setLabel('bottom', x_label, color='black')

        # ==========================================
        # PLOT 1: LENGTH VS WEIGHT (Current Haul)
        # ==========================================
        sql_lw = (f"SELECT {length_col}, weight_g FROM {self.parent().schema}.v_specimen_measurements "
                  f"WHERE ship = {self.parent().ship} AND survey = {self.parent().survey} "
                  f"AND event_id = {self.parent().activeHaul} " # Only current haul
                  f"AND species_code = {self.parent().activeSpcCode} "
                  f"AND {length_col} IS NOT NULL AND weight_g IS NOT NULL")
        
        query_lw = self.parent().db.dbQuery(sql_lw)
        
        lengths = []
        weights = []
        for length, weight in query_lw:
            lengths.append(float(length))
            weights.append(float(weight))
            
        self.LWPlot.clear() 
        if lengths and weights:
            self.LWPlot.plot(lengths, weights, pen=None, symbol='o', symbolSize=8, symbolBrush='k')

# --- Theoretical Length-Weight Curve ---
            lw_params = {
                "sardine": {"intercept": -12.31667, "slope": 3.198896},
                "anchovy": {"intercept": -12.03663, "slope": 3.114000},
                "pacific mackerel": {"intercept": -13.01634, "slope": 3.299816},
                "jack mackerel": {"intercept": -11.42293, "slope": 3.010456},
                "pacific herring": {"intercept": -12.72208, "slope": 3.235567},
                "hake": {"intercept": -12.39755, "slope": 3.078660}
            }

            # Figure out if our active species is in the reference dictionary
            matched_key = None
            for key in lw_params:
                if key in species_name:
                    matched_key = key
                    break
            
            # If we have a match, draw the theoretical curve!
            if matched_key:
                intercept = lw_params[matched_key]["intercept"]
                slope = lw_params[matched_key]["slope"]
                
                # Create a smooth X array from the minimum to maximum lengths in our scatter plot
                min_l = max(1.0, min(lengths)) # Avoid log(0) just in case
                max_l = max(lengths)
                
                # Generate 100 points for a smooth curve
                step = (max_l - min_l) / 100.0
                if step > 0:
                    curve_x = [min_l + i * step for i in range(101)]
                    
                    # Apply the power-law equation: W = exp(intercept + slope * ln(L))
                    curve_y = [math.exp(intercept + slope * math.log(x)) for x in curve_x]
                    
                    # Plot the theoretical line (solid red line, thickness 2)
                    self.LWPlot.plot(curve_x, curve_y, pen=pg.mkPen(color='r', width=2))

        # ==========================================
        # PLOT 2: OTOLITH FREQUENCY (Entire Survey)
        # ==========================================
        # Notice we omit 'event_id' here to grab data for the entire survey
        sql_oto = (f"SELECT {length_col}, alpha_barcode FROM {self.parent().schema}.v_specimen_measurements "
                   f"WHERE ship = {self.parent().ship} AND survey = {self.parent().survey} "
                   f"AND species_code = {self.parent().activeSpcCode} "
                   f"AND {length_col} IS NOT NULL")
                   
        query_oto = self.parent().db.dbQuery(sql_oto)

        # Initialize dictionaries to hold our counts for each bin
        len_only_counts = {b: 0 for b in bins}
        oto_counts = {b: 0 for b in bins}

        for row in query_oto:
            length_val = float(row[0])
            barcode = row[1]
            
            # Replicate R's cut() function by flooring to the nearest bin step
            bin_val = int((length_val // bin_step) * bin_step)
            
            if bin_val in bins:
                if barcode: 
                    # Has a barcode -> It's an Otolith
                    oto_counts[bin_val] += 1
                else: 
                    # No barcode -> It's just a Length
                    len_only_counts[bin_val] += 1

        self.OtoLengthPlot.clear()
        
        # Add a legend if it doesn't already exist
        if self.OtoLengthPlot.plotItem.legend is None:
            legend = self.OtoLengthPlot.addLegend()
        else:
            legend = self.OtoLengthPlot.plotItem.legend
            legend.clear()

        # Anchor the top-right of the legend (1, 0) to the top-right of the plot (1, 0)
        # The offset=(-10, 10) gives it a nice 10-pixel padding from the very edge
        legend.anchor((1, 0), (1, 0), offset=(-10, 10))

        # Extract data into lists for plotting
        x_vals = list(oto_counts.keys())
        oto_y = list(oto_counts.values())
        
        # To mimic a stacked bar chart, the background bar must be the TOTAL height
        total_y = [len_only_counts[x] + oto_counts[x] for x in x_vals]

        # Draw the total (Lengths + Otoliths) as dark grey in the back
        bg_total = pg.BarGraphItem(x=x_vals, height=total_y, width=bin_step*0.9, brush='black', name='Lengths')
        self.OtoLengthPlot.addItem(bg_total)
        
        # Draw the Otoliths as black in the front
        bg_oto = pg.BarGraphItem(x=x_vals, height=oto_y, width=bin_step*0.9, brush='darkgray', name='Otoliths')
        self.OtoLengthPlot.addItem(bg_oto)

# --- ADD THE HORIZONTAL LINE ---
        # pos=50 sets the Y intercept. angle=0 makes it horizontal.
        # We use a dashed red line (style=Qt.PenStyle.DashLine) so it is highly visible.
        hline = pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine))
        self.OtoLengthPlot.addItem(hline)
      