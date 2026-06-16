# Alternative Uses Builder

A clean starter version of a behavioral experiment for creative object-use generation.
It is open source and uses only Python's standard library.

Participants are asked:

> Using only the shapes on the screen, create as many different uses for a brick as possible.

They drag basic shapes into a blank workspace, move/resize/rotate them, type a short description of the idea, and submit it. Each submitted idea is saved as one CSV row.

## Run

```bash
python alternative_uses_builder.py
```

If you downloaded the project as a ZIP from GitHub, unzip it first, then run the command above from the unzipped folder.

## Download

Recommended public link format for a class document:

```text
Alternative Uses Builder: https://github.com/YOUR-USERNAME/alternative-uses-builder
```

After you publish the folder to GitHub, participants can click the green **Code** button, choose **Download ZIP**, unzip the folder, and run:

```bash
python alternative_uses_builder.py
```

## Current Flow

1. Welcome screen with ID, first name, last name, TAMU email preferred, and phone number
2. Instructions screen
3. Practice round using the same shape workspace
4. Main shape workspace with draggable square, rectangle, circle, and triangle
5. Description field and Submit Idea button
6. CSV data saved in `data/`
7. End screen with total number of submitted ideas

## Interaction

- Drag a shape from the left panel into the workspace.
- Drag an existing shape to move it.
- Select a shape to show controls.
- Drag the blue square handle to resize.
- Drag the green circular handle to rotate.
- Type a short description, then press Submit Idea.
- The practice round is not saved to the experiment CSV.
- TAMU email is preferred but optional.

## CSV Fields

- `participant_id`
- `first_name`
- `last_name`
- `tamu_email`
- `phone_number`
- `idea_number`
- `description`
- `time_spent_seconds`
- `number_of_shapes_used`
- `number_of_moves`
- `mouse_positions_json`
- `total_mouse_distance_px`
- `rotation_count`
- `resize_count`
- `idea_started_at`
- `submitted_at`
- `shape_layout_json`

## Expansion Points

The code is intentionally organized for later study variants:

- `ExperimentConfig` can enable idea limits, countdown timers, stress conditions, sounds, AI hints, or EEG markers.
- `ExperimentHooks` contains no-op methods for task start, idea start, idea submit, and EEG marker sending.
- `IdeaState` holds per-idea behavior data.
- `DataLogger` owns the CSV format.
- `ShapeItem` owns the final layout information for each shape.

Originality is usually scored after data collection by comparing descriptions across participants or against a coding scheme. This starter app records the descriptions and behavioral traces needed for that analysis.
