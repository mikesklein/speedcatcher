import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.style as mplstyle
from datetime import datetime
from matplotlib.lines import Line2D

# Dark theme
mplstyle.use('dark_background')

CSV_PATH = "speed_log.csv"

class SpeedDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Speed Tracker Dashboard 🚗")
        self.root.geometry("1000x750")

        # Top-level frame
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(pady=(10, 0))

        # % over speed limit label
        self.percent_over_label = tk.Label(
            self.top_frame, text="", fg="white", bg="black", font=("Helvetica", 22, "bold")
        )
        self.percent_over_label.pack()

        # Main plot frame
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        # Stats display
        self.stats_frame = ttk.Frame(self.plot_frame)
        self.stats_frame.pack(pady=20)

        self.avg_speed_label = tk.Label(
            self.stats_frame, text="", fg="white", bg="black", font=("Helvetica", 28, "bold")
        )
        self.avg_speed_label.grid(row=0, column=0, padx=20)

        self.max_speed_label = tk.Label(
            self.stats_frame, text="", fg="white", bg="black", font=("Helvetica", 28, "bold")
        )
        self.max_speed_label.grid(row=0, column=1, padx=20)

        self.total_label = tk.Label(
            self.stats_frame, text="", fg="white", bg="black", font=("Helvetica", 28, "bold")
        )
        self.total_label.grid(row=0, column=2, padx=20)

        self.speeders_label = tk.Label(
            self.stats_frame, text="", fg="white", bg="black", font=("Helvetica", 28, "bold")
        )
        self.speeders_label.grid(row=0, column=3, padx=20)

        # Matplotlib figure
        self.figure, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.load_and_plot()

    def load_and_plot(self):
        try:
            df = pd.read_csv(CSV_PATH)
        except Exception as e:
            self.percent_over_label.config(text=f"⚠️ Error loading CSV: {e}")
            return

        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

        # Drop suspect speeds for calculations
        filtered_df = df[df["speed_kph"] <= 90]
        avg_speed = filtered_df["speed_kph"].mean()
        std_dev = filtered_df["speed_kph"].std()
        max_speed = filtered_df["speed_kph"].max()
        total_vehicles = len(df)

        # Quartile thresholds
        q1 = filtered_df["speed_kph"].quantile(0.25)
        q2 = filtered_df["speed_kph"].quantile(0.5)
        q3 = filtered_df["speed_kph"].quantile(0.75)

        # Count vehicles over speed limit (50 km/h)
        over_limit_count = df[df["speed_kph"] > 50].shape[0]
        percent_over_limit = (over_limit_count / total_vehicles) * 100 if total_vehicles > 0 else 0

        # Count speeders (>50 and ≤80)
        speeders_count = df[(df["speed_kph"] > 50) & (df["speed_kph"] <= 80)].shape[0]

        # Update labels
        self.percent_over_label.config(text=f"🚨 {percent_over_limit:.1f}% of vehicles were over the 50 km/h speed limit")
        self.avg_speed_label.config(text=f"📊 Avg: {avg_speed:.1f} km/h")
        self.max_speed_label.config(text=f"🚀 Max: {max_speed:.1f} km/h")
        self.total_label.config(text=f"🚗 Total: {total_vehicles}")
        self.speeders_label.config(text=f"🏎️ Speeders: {speeders_count}")

        self.ax.clear()

        # Assign colors by quartile
        colors = []
        for speed in df["speed_kph"]:
            if speed > 90:
                colors.append("hotpink")
            elif speed <= q1:
                colors.append("lime")
            elif speed <= q2:
                colors.append("cyan")
            elif speed <= q3:
                colors.append("lightsalmon")
            else:
                colors.append("orange")

        # Plot scatter
        self.ax.scatter(df["datetime"], df["speed_kph"], c=colors)

        # Reference line at speed limit
        self.ax.axhline(50, color='lime', linestyle='-', linewidth=1.5, label='Speed Limit')

        # Labels
        self.ax.set_title("Speed Over Time")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Speed (km/h)")
        self.ax.grid(True)

        # Custom legend
        legend_elements = [
            Line2D([0], [0], color='lime', linestyle='-', label='Speed Limit (50 km/h)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lime', label='Q1: ≤ 25%', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='cyan', label='Q2: 25–50%', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightsalmon', label='Q3: 50–75%', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', label='Q4: Top 25%', markersize=10),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='hotpink', label='> 90 km/h (Inaccurate)', markersize=10)
        ]
        self.ax.legend(handles=legend_elements, loc="upper left")

        self.figure.autofmt_xdate()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = SpeedDashboard(root)
    root.mainloop()