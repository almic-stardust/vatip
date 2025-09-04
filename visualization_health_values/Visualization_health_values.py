#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import yaml
import datetime
import matplotlib.pyplot as plt
import itertools
import matplotlib
from collections import Counter


def Load_marker(Filename, Event):
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
				try:
					# First part is the date in DD/MM/YYYY
					Date = datetime.datetime.strptime(Parts[0], "%d/%m/%Y")
					Dates.append(Date)
					# When the file is a list of pairs date+value
					if not Event:
						# Second part is the numeric value
						Value = float(Parts[1])
						Values.append(Value)
				# Ignore bad lines
				except ValueError:
					print(f"Error: Incorrect value in file {Filename}.")
					continue
			# For a event marker, the list Values corresponds to the number of times the event
			# occurred during a day (= the number of times that date appears in the file)
			if Event:
				# Count occurrences of each date
				Counts = Counter(Dates)
				Dates = []
				# Remove duplicate dates, and add their count in the list Values
				for Date, Count in Counts.items():
					Dates.append(Date)
					Values.append(Count)
				# If instead we want to add the dates that doesn’t appear in the file with 0 in the
				# list Values
				#Start_date = Dates[0]
				#End_date = Dates[-1]
				#Dates = []
				#for Date in [Start_date + datetime.timedelta(days=Date) for Date in range((End_date - Start_date).days + 1)]:
				#	Dates.append(Date)
				#	# If a date doesn’t appear in Counts (no event that day) = the value is 0
				#	Values.append(Counts.get(Date, 0))
	except FileNotFoundError:
		print(f"Error: File {Filename} not found.")
		sys.exit(1)
	return Dates, Values


def Load_modifs(Filename, Type_modifs):
	"""Load modifications list from file."""
	Dates = []
	Problems = []
	Labels = []
	try:
		with open(Filename, "r", encoding="utf-8") as File:
			for Line in File:
				Line = Line.strip()
				# Skip empty or commented lines
				if not Line or Line.startswith("#"):
					continue
				Parts = Line.split()
				try:
					# First part is the date in DD/MM/YYYY
					Date = datetime.datetime.strptime(Parts[0], "%d/%m/%Y")
					# Second part is the type of problem
					Problem = Parts[1]
					# All words after (and including) the third are the label
					Label = " ".join(Parts[2:])
				# Ignore bad lines
				except ValueError:
					print(f"Error: Incorrect value in file {Filename}.")
					continue
				Dates.append(Date)
				Problems.append(Problem)
				Labels.append(Label)
				# If instead we want only the dates for the type of problem of the current graph
				#if Problem == Type_modifs or Type_modifs == "all":
				#	Dates.append(Date)
				#	Problems.append(Problem)
				#	Labels.append(Label)
	except FileNotFoundError:
		print(f"Error: File {Filename} not found.")
		sys.exit(1)
	return Dates, Problems, Labels


def Plot_graph(Graph_name, Period):
	"""Create the graph, with a hidden Y axis for each marker’s scale"""
	Graph_markers = []
	Earliest_connected_marker = None
	Anterior_value = None
	All_colors = []
	Color_cycle = itertools.cycle(matplotlib.rcParams["axes.prop_cycle"].by_key()["color"])
	All_dates = []
	Scale_to_axis = {}
	Legend_handles = []
	Legend_labels = []

	# Load and verify the configuration file
	with open("Config.yaml", "r") as File:
		Config = yaml.safe_load(File)
	Graphs = Config.get("Graphs", None)
	if not Graphs:
		print(f"Error: The configuration file doesn’t have a list of graphs.")
		print(f"Please complete the configuration file.")
		sys.exit(1)
	if Graph_name not in Graphs:
		print(f"Error: Unknown graph “{Graph_name}”.\nAvailable graphs: {', '.join(Graphs.keys())}")
		sys.exit(1)
	Markers = Config.get("Markers", None)
	if not Markers:
		print(f"Error: The configuration file doesn’t have a list of markers.")
		print(f"Please complete the configuration file.")
		sys.exit(1)
	List_modifs = Config.get("Modifications", None)
	if not List_modifs:
		print(f"Warning: The configuration file doesn’t have a list of medical treatment modifications.")
	List_markers = Graphs[Graph_name].get("markers", None)
	if not List_markers:
		print(f"Error: “{Graph_name}” doesn’t have a list of markers.")
		print(f"Please complete the configuration file.")
		sys.exit(1)
	List_markers = List_markers[0]
	Ranges = Graphs[Graph_name].get("ranges", None)
	if not Ranges:
		print(f"Warning: “{Graph_name}” doesn’t have a list of ranges.")
	Ranges = Ranges[0]

	if List_modifs:
		Modifs = None
		File = List_modifs.get("file", None)
		if not File:
			print(f"Error: The “Modifications” section doesn’t indicate the file to load.")
			print(f"Please complete the configuration file.")
			sys.exit(1)
		Type_modifs = Graphs[Graph_name].get("modifications", None)
		if Type_modifs:
			Modifs = Load_modifs(File, Type_modifs)
			Colors_modifs = List_modifs.get("colors", None)
			if not Colors_modifs:
				print(f"Warning: The “Modifications” section doesn’t include a complete list of colors for each problem.")
				print(f"The problems without an associated color will be displayed in red.")
		elif Type_modifs != "none":
			print(f"Warning: “{Graph_name}” doesn’t have a list of medical treatment modifications.")

	# First loop to load this graph’s markers:
	# 1) When a range of dates is selected, for horizontal markers we need the last value before the
	#	 beginning of the range, and the earliest date among connected markers
	# 2) We need all the colors before starting drawing, so as not to use the same twice
	for Marker_name in List_markers:
		if not Markers.get(Marker_name):
			print(f"Error: The marker {Marker_name} has no section in the config file.")
			sys.exit(1)
		Color = Markers[Marker_name].get("color", "")
		Horizontal = Markers[Marker_name].get("horizontal", False)
		Event = Markers[Marker_name].get("event", False)
		Normal_range = Markers[Marker_name].get("normal_range", False)
		if Normal_range:
			# Parse the string "min-max"
			Parts = Markers[Marker_name].get("normal_range", "").split("-")
			if Parts:
				try:
					Normal_range = float(Parts[0]), float(Parts[1])
				except Exception:
					Normal_range = False
		Target = Markers[Marker_name].get("target", False)
		Dates, Values = Load_marker(Markers[Marker_name]["file"], Event)
		if not Dates:
			print(f"Error: No data to plot for file {Markers[Marker_name]['file']}.")
			sys.exit(1)
		# If a range of dates is selected
		if Period:
			Start_date, End_date = Period
			# If it’s a horizontal marker, find the last value before Start_date (if any)
			if Horizontal:
				for Date, Value in zip(Dates, Values):
					if Date < Start_date:
						Anterior_value = Value
					# Stop checking after Start_date
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
			if not Horizontal and not Event:
				if Earliest_connected_marker is None or Dates[0] < Earliest_connected_marker:
					Earliest_connected_marker = Dates[0]
		Max_value = max(Values)
		# Add 0.3% to the highest value, to prevent its point from being cut off in the graph
		if Event:
			Scale = 0, Max_value/0.05
		else:
			Scale = 0, Max_value + (Max_value * 0.0334)
		# For readability, there’s an offset between the labels and their points. This offset must
		# be consistent from one marker to another. So the label offset of a marker is based on its
		# scale (= its highest value).
		Offset = Max_value * 0.016

		Graph_markers.append((Marker_name, Color, Horizontal, Event, Normal_range, Target, Scale, Offset, Dates, Values, Anterior_value))
		All_colors.append(Color)
		All_dates.extend(Dates)

	if not All_dates:
		print("Error: No data in the selected period")
		sys.exit(1)
	# Remove duplicates and sort
	All_dates = sorted(set(All_dates))
	Start_date = All_dates[0]
	End_date = All_dates[-1]
	Fig, Main_axis = plt.subplots(figsize=(10, 6))

	# Second loop to draw the plots for each marker
	for Marker_name, \
			Color, \
			Horizontal, Event, \
			Normal_range, Target, \
			Scale, Offset, \
			Dates, Values, \
			Anterior_value \
	in Graph_markers:
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

		# This is a horizontal marker, drawn with segments
		if Horizontal:
			# If a horizontal marker have a last value before the beginning of the range of dates,
			# add it as a new value for the date Earliest_connected_marker
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
		else:
			if Event:
				Marker_shape="v"
				Line_style=""
			# This is a connected marker
			else:
				Marker_shape="o"
				Line_style="-"
			Line, = Axis.plot(Dates, Values, marker=Marker_shape, linestyle=Line_style, label=Marker_name, color=Color)
		Legend_handles.append(Line)
		Legend_labels.append(Marker_name)

		# Apply the marker’s scale
		if Scale:
			Axis.set_ylim(Scale[0], Scale[1])

		# Add value labels next to each point, with same color as the plot
		for Counter, (Date, Value) in enumerate(zip(Dates, Values)):
			# No label for event markers and for zero values
			if not Event and Value > 0:
				# If the config file specifies a label color different from the line for this
				# marker, or we use the color of the line
				Label_color = Markers[Marker_name].get("label_color", Color)
				# Horizontal marker = label below
				if Horizontal:
					Vertical_alignment = "top"
					Label_offset = -Offset
				# Connected marker
				else:
					# Downward slope ahead = label above
					if Counter < len(Values) - 1 and Values[Counter + 1] < Value:
						Vertical_alignment = "bottom"
						Label_offset = Offset
					# Upward or stable slope ahead = label below
					else:
						Vertical_alignment = "top"
						Label_offset = -Offset
				Axis.text(Date, Value + Label_offset, str(Value), ha="center", va=Vertical_alignment, fontsize=8, color=Label_color)

		# If this marker is part of the ranges list for this graph, display the target values with
		# horizontal lines
		if Marker_name in Ranges:
			if Target == "above_min" or Target == "middle":
				Axis.axhline(y=Normal_range[0], color=Color, linewidth=1, linestyle="-", alpha=0.5)
			if Target == "below_max" or Target == "middle":
				Axis.axhline(y=Normal_range[1], color=Color, linewidth=1, linestyle="-", alpha=0.5)
			if Target == "middle":
				# Example with T4: min 15 + max 50 + target ~30 → 15+(50-15)/2 = 32
				Middle = Normal_range[0] + (Normal_range[1] - Normal_range[0]) / 2
				Axis.axhline(y=Middle, color=Color, linewidth=1, linestyle=":")

	# Display each medical treatment modification with a vertical line associated to a label
	if Modifs:
		Dates, Problems, Labels = Modifs
		# If a range of dates is selected, exclude modifications that occurred outside of it
		if Period:
			Start_date, End_date = Period
			# clamp End_date to the last available data point on the X axis
			End_date = min(End_date, All_dates[-1])
		else:
			Start_date, End_date = All_dates[0], All_dates[-1]
		for Date, Problem, Label in zip(Dates, Problems, Labels):
			# The problems without an associated color will be displayed in red
			Color = Colors_modifs.get(Problem, "red")
			if not (Start_date <= Date <= End_date):
				continue
			# If the label is longer than 18 characters, cut it in two lines
			if len(Label) > 18:
				# Find the last space before or at position 18
				Position = Label.rfind(" ", 0, 18)
				# No space found, hard cut
				if Position == -1:
					Position = 18
				Label = Label[:Position].rstrip() + "\n" + Label[Position:].lstrip()
			# Vertical line
			Axis.axvline(x=Date, color=Color, linestyle="--", linewidth=1, alpha=0.9, zorder=0)
			# Vertical label, anchored to the X axis coordinates (independent of Y scale)
			Axis.text(Date, 1.02, Label,
					rotation=90, va="bottom", ha="center", multialignment="left", color=Color,
					transform=Main_axis.get_xaxis_transform(),
					fontsize=8, clip_on=False)

	# Hide Y axes on both sides
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

	# Setting the exact X axis range to remove padding
	Main_axis.set_xlim(min(All_dates), max(All_dates))

	# Build X axis labels depending on period length
	Labels = []
	Tick_dates = []
	Previous_year = None
	# If a range of dates is selected, and it’s less than one year = display the monday of each week
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
	# No range selected, or the range is greater than one year = display the date of the measures
	else:
		for Date in All_dates:
			Tick_dates.append(Date)
			if Date.year != Previous_year:
				Labels.append(Date.strftime("%Y-%m-%d"))
				Previous_year = Date.year
			else:
				Labels.append(Date.strftime("%m-%d"))
	# Apply custom X-tick labels, rotated vertically
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
