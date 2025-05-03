import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.style as mplstyle
from datetime import datetime

# Dark theme for "spacey" vibes
mplstyle.use('dark_background')

CSV_PATH = "speed_log.csv"

class SpeedDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Speed Tracker Dashboard 🚗")
        self.root.geometry("1200x700")

        self.data_frame = ttk.Frame(self.root)
        self.data_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Table
        self.table = ttk.Treeview(
            self.data_frame,
            columns=("Time", "Object ID", "Class", "Speed (km/h)", "Direction"),
            show="headings"
        )
        for col in self.table["columns"]:
            self.table.heading(col, text=col)
            self.table.column(col, anchor=tk.CENTER, width=100)
        self.table.pack(fill=tk.BOTH, expand=True)

        # Matplotlib figure
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.stats_label = tk.Label(self.plot_frame, text="", fg="white", bg="black", font=("Helvetica", 14))
        self.stats_label.pack(pady=10)

        self.load_and_plot()

    def load_and_plot(self):
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception as e:
            self.stats_label.config(text=f"⚠️ Error loading CSV: {e}")
            return

        # Convert timestamps
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

        # Clear table
        for row in self.table.get_children():
            self.table.delete(row)

        # Add to table
        for _, row in df.tail(20).iterrows():
            self.table.insert("", tk.END, values=(
                row["datetime"].strftime("%H:%M:%S"),
                int(row["object_id"]),
                row["class_name"],
                f"{row['speed_kph']:.1f}",
                row["direction"]
            ))

        # Stats
        avg_speed = df["speed_kph"].mean()
        max_speed = df["speed_kph"].max()
        most_recent = df["datetime"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")

        # Plot
        self.ax.clear()
        self.ax.plot(df["datetime"], df["speed_kph"], marker='o', linestyle='-', color='cyan')
        self.ax.set_title("Speed Over Time")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Speed (km/h)")
        self.ax.grid(True)
        self.figure.autofmt_xdate()

        self.stats_label.config(
            text=f"📈 Avg Speed: {avg_speed:.1f} km/h   |   🚀 Peak: {max_speed:.1f} km/h   |   Last Entry: {most_recent}"
        )

        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = SpeedDashboard(root)
    root.mainloop()