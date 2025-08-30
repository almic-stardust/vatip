#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import yaml
import datetime
import matplotlib.pyplot as plt
import itertools
import matplotlib


def Load_file(Filename):
	"""Load date and value pairs from file."""
	Dates = []
	Values = []
	try:
		with open(Filename, "r", encoding="utf-8") as File:
			for Line in File:
				Line = Line.strip()
				# Skip empty or commented lines
				if not Line or Line.startswith("#"):
					continue
				Parts = Line.split()
				if len(Parts) < 2:
					continue
				try:
					# First part is the date in DD/MM/YYYY
					Date = datetime.datetime.strptime(Parts[0], "%d/%m/%Y")
					# Second part is the numeric value
					Value = float(Parts[1])
				# Ignore bad lines
				except ValueError:
					continue
				Dates.append(Date)
				Values.append(Value)
	except FileNotFoundError:
		print(f"Error: File {Filename} not found.")
		sys.exit(1)
	return Dates, Values


def Plot_graph(Graph_name, Period):
	"""Create the graph, with a hidden Y-axis for each marker’s scale"""
	with open("Config.yaml", "r") as File:
		Config = yaml.safe_load(File)
	Graphs = Config["Graphs"]
	if Graph_name not in Graphs:
		print(f"Unknown graph '{Graph_name}'.\n Available graphs: {', '.join(Graphs.keys())}")
		sys.exit(1)
	Markers = []
	Anterior_value = None
	Earliest_connected_marker = None
	All_dates = []
	All_colors = []
	Color_cycle = itertools.cycle(matplotlib.rcParams["axes.prop_cycle"].by_key()["color"])
	Scale_to_axis = {}
	Legend_handles = []
	Legend_labels = []

	# First loop to load the markers:
	# 1) We need all the colors before starting drawing, so as not to use the same twice
	# 2) When a range of dates is selected, for horizontal markers we need the last value before the
	# beginning of the range
	for Marker_name, Marker_dict in Graphs[Graph_name].items():
		Dates, Values = Load_file(Marker_dict["file"])
		if not Dates:
			print(f"Error: No data to plot for file {Marker_dict['file']}.")
			sys.exit(1)
		# Check if this marker’s plot is connected or horizontal
		Connected = True
		if Marker_dict.get("horizontal", False):
			Connected = False
		Color = Marker_dict.get("color", "")

		# If a range of dates is selected
		if Period:
			Start_date, End_date = Period
			# If it’s a horizontal marker, find the last value before Start_date (if any)
			if not Connected:
				for Date, Value in zip(Dates, Values):
					if Date < Start_date:
						Anterior_value = Value
					# When we pass Start_date
					else:
						break
			Filtered = []
			for Date, Value in zip(Dates, Values):
				if Start_date <= Date <= End_date:
					Filtered.append((Date, Value))
			if not Filtered:
				continue
			Dates, Values = zip(*Filtered)
			if not Dates:
				continue
			# Find the earliest date among the connected markers
			if Connected:
				if Earliest_connected_marker is None or Dates[0] < Earliest_connected_marker:
					Earliest_connected_marker = Dates[0]
		Max_value = max(Values)
		# Add 0.3% to the highest value, to prevent its point from being cut off in the graph
		Scale = 0, Max_value + (Max_value * .0334)
		# For readability, there’s an offset between the labels and their points. This offset must
		# be consistent from one marker to another. So the label offset of a marker is based on its
		# scale (= its highest value).
		Offset = Max_value * .016

		Markers.append((Marker_name, Connected, Color, Scale, Offset, Dates, Values, Anterior_value))
		All_dates.extend(Dates)
		All_colors.extend(Color)

	if not All_dates:
		print("Error: No data in the selected period")
		sys.exit(1)
	# Remove duplicates and sort
	All_dates = sorted(set(All_dates))

	# Second loop to draw the plots for each marker
	Fig, Main_axis = plt.subplots(figsize=(10, 6))
	for Marker_name, Connected, Color, Scale, Offset, Dates, Values, Anterior_value in Markers:
		# Get or create axis for this scale
		if Scale not in Scale_to_axis:
			if not Scale_to_axis:
				Axis = Main_axis
			else:
				Axis = Main_axis.twinx()
			Scale_to_axis[Scale] = Axis
		else:
			Axis = Scale_to_axis[Scale]

		# If the color wasn’t specified in the config file, pick the next from the shared cycle
		if not Color:
			Color = next(Color_cycle)
			while Color in All_colors:
				Color = next(Color_cycle)

		# Draw the plot for this marker
		if Connected:
			Line, = Axis.plot(Dates, Values, marker="o", linestyle="-", label=Marker_name, color=Color)
		# This is a horizontal marker, drawn with segments
		else:
			# If a horizontal marker have a last value before the beginning of the range of dates,
			# add it at a new value for the date Earliest_connected_marker
			if Period and Anterior_value:
				Dates = [Earliest_connected_marker] + list(Dates)
				Values = [Anterior_value] + list(Values)
			for Counter in range(len(Dates) - 1):
				if Values[Counter] > 0:
					Axis.hlines(
						y=Values[Counter],
						xmin=Dates[Counter],
						xmax=Dates[Counter + 1],
						colors=Color,
						linewidth=2)
			# Overlay points at the beginning of the segments
			Axis.plot(Dates, Values, "o", color=Color)
			# Dummy plot for the legend
			Line, = Axis.plot([], [], marker="o", linestyle="-", label=Marker_name, color=Color)
		Legend_handles.append(Line)
		Legend_labels.append(Marker_name)

		# Apply the marker’s scale
		if Scale:
			Axis.set_ylim(Scale[0], Scale[1])

		# Add value labels next to each point, with same color as the plot
		for Counter, (Date, Value) in enumerate(zip(Dates, Values)):
			if Value > 0:
				if Connected:
					if Counter < len(Values) - 1 and Values[Counter + 1] < Value:
						# Downward slope ahead = label above
						Vertical_alignment = "bottom"
						Label_offset = Offset
					else:
						# Upward or stable = label below
						Vertical_alignment = "top"
						Label_offset = -Offset
				else:
					# Horizontal marker = label below
					Vertical_alignment = "top"
					Label_offset = -Offset
				Axis.text(Date, Value + Label_offset, str(Value), ha="center", va=Vertical_alignment, fontsize=9, color=Color)

	# Hide Y-axes on both sides
	for Axis in Scale_to_axis.values():
		Axis.yaxis.set_visible(False)
		if "left" in Axis.spines:
			Axis.spines["left"].set_visible(False)
		if "right" in Axis.spines:
			Axis.spines["right"].set_visible(False)
		if "top" in Axis.spines:
			Axis.spines["top"].set_visible(False)
		Axis.patch.set_alpha(0)
		if Axis is not Main_axis:
			Axis.xaxis.set_visible(False)

	# Setting the exact X-axis range to remove padding
	Main_axis.set_xlim(min(All_dates), max(All_dates))

	# Build X-axis labels depending on period length
	Labels = []
	Tick_dates = []
	Previous_year = None
	Start_date = All_dates[0]
	End_date = All_dates[-1]
	# We asked for a range of dates less than one year = display the monday of each week
	if Period and (End_date - Start_date).days <= 365:
		Fist_monday = Start_date - datetime.timedelta(days=Start_date.weekday())
		Last_monday = End_date - datetime.timedelta(days=End_date.weekday())
		Current = Fist_monday
		while Current <= Last_monday:
			Tick_dates.append(Current)
			if Current.year != Previous_year:
				Labels.append(Current.strftime("%Y-%m-%d"))
				Previous_year = Current.year
			else:
				Labels.append(Current.strftime("%m-%d"))
			Current += datetime.timedelta(days=7)
	# No range selected, or it’s greater than one year = display the date of the measures
	else:
		for Date in All_dates:
			Tick_dates.append(Date)
			if Date.year != Previous_year:
				Labels.append(Date.strftime("%Y-%m-%d"))
				Previous_year = Date.year
			else:
				Labels.append(Date.strftime("%m-%d"))
	# Apply custom x-tick labels, rotated vertically
	Main_axis.set_xticks(Tick_dates)
	Main_axis.set_xticklabels(Labels, rotation=90)

	# Display the graph
	Main_axis.set_title(f"{Graph_name}")
	Main_axis.legend(
			Legend_handles,
			Legend_labels,
			bbox_to_anchor=(-0.05, 1))
	plt.show()


if __name__ == "__main__":

	if len(sys.argv) < 2:
		print(f"Usage: {sys.argv[0]} <Graph> [YYYYMM- | YYYYYMM-YYYYMM]")
		sys.exit(1)
	Graph = sys.argv[1]

	# 202503- = from March 2025 until last available date
	# 202410-202509 = October 2024 through September 2025
	# -202503 = from first available date until March 2025
	if len(sys.argv) >= 3:
		try:
			Period_string = sys.argv[2]
			if "-" not in Period_string:
				raise ValueError
			Start_string, End_string = Period_string.split("-")
			# Get start date for YYYYMM-YYYYMM and YYYYMM-
			if Start_string:
				Start_date = datetime.datetime.strptime(Start_string, "%Y%m")
			# Case -YYYYMM = from first available date
			else:
				Start_date = datetime.datetime.min
			# Get end date for YYYYMM-YYYYMM and -YYYYMM
			if End_string:
				# End of month handling: go to first of next month, subtract a day
				End_year, End_month = int(End_string[:4]), int(End_string[4:])
				if End_month == 12:
					End_date = datetime.datetime(End_year + 1, 1, 1) - datetime.timedelta(days=1)
				else:
					End_date = datetime.datetime(End_year, End_month + 1, 1) - datetime.timedelta(days=1)
			# Case YYYYMM- = until last available date
			else:
				End_date = datetime.datetime.max
			Period = Start_date, End_date
		except Exception:
			print(f"Invalid period format: “{sys.argv[2]}”. Use YYYYMM-YYYYMM, YYYYMM-, or -YYYYMM")
			sys.exit(1)
	else:
		Period = None

	Plot_graph(Graph, Period)
