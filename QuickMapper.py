import tkinter as tk
from tkinter import messagebox
import folium
import webbrowser
import os

# Function to create and display a dynamic map
def display_map():
    try:
        lat = float(lat_entry.get())
        lon = float(lon_entry.get())
        radius = float(radius_entry.get())

        if radius <= 0:
            raise ValueError("Radius must be greater than 0")

        # Create a folium map centered on the given coordinates
        map_ = folium.Map(location=[lat, lon], zoom_start=15)

        # Add a marker for the given location
        folium.Marker([lat, lon], popup="Location", icon=folium.Icon(color="red")).add_to(map_)

        # Add a circle to represent the uncertainty radius
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color="blue",
            fill=True,
            fill_opacity=0.3
        ).add_to(map_)

        # Save the map as an HTML file
        map_file = "dynamic_map.html"
        map_.save(map_file)

        # Open the map in the default web browser
        webbrowser.open(f"file://{os.path.abspath(map_file)}")
    except ValueError as ve:
        messagebox.showerror("Input Error", str(ve))
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Create the main GUI window
root = tk.Tk()
root.title("Dynamic Map Viewer")

# Create and place input fields and labels
tk.Label(root, text="Latitude:").grid(row=0, column=0, padx=5, pady=5)
lat_entry = tk.Entry(root)
lat_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(root, text="Longitude:").grid(row=1, column=0, padx=5, pady=5)
lon_entry = tk.Entry(root)
lon_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(root, text="Radius (meters):").grid(row=2, column=0, padx=5, pady=5)
radius_entry = tk.Entry(root)
radius_entry.grid(row=2, column=1, padx=5, pady=5)

# Add a button to display the map
tk.Button(root, text="Show Map", command=display_map).grid(row=3, column=0, columnspan=2, pady=10)

# Start the main event loop
root.mainloop()
