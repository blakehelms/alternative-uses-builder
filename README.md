# Alternative Uses Builder

Alternative Uses Builder is a simple Python-based behavioral experiment for studying creative idea generation and mouse movement behavior.

Participants are asked to create as many different uses for a brick as possible using only the basic shapes on the screen. They build each idea by dragging, moving, resizing, and rotating shapes in a blank workspace, then submit a short written description of the object they made.

The task is designed as a clean starter version that is easy to run, inspect, and expand for future research conditions.

## Experiment Prompt

> Using only the shapes on the screen, create as many different uses for a brick as possible.

Example responses might include:

- phone stand
- doorstop
- hammer
- small house

## Task Flow

1. Welcome screen with participant information fields
2. Instructions screen
3. Practice round
4. Main drag-and-drop shape workspace
5. Short written description for each idea
6. Submit Idea button
7. Workspace reset after each submitted idea
8. End screen with the total number of ideas submitted

## Participant Interaction

- Drag shapes from the side panel into the workspace.
- Move shapes around the workspace.
- Resize shapes using the blue handle.
- Rotate shapes using the green handle.
- Type a short description of the idea.
- Submit the idea and begin the next one.

The practice round is not saved to the experiment CSV.

## Data Collected

Each submitted idea is saved as one CSV row. The app records:

- participant ID
- first name
- last name
- TAMU email, preferred but optional
- phone number
- idea number
- typed description
- time spent on the idea
- number of shapes used
- number of moves
- mouse position history
- total mouse distance
- number of rotations
- number of resizes
- idea start timestamp
- submission timestamp
- final shape layout

CSV files are saved locally in the `data/` folder.

## Main Research Measures

This starter task supports common creativity and behavioral measures such as:

- fluency: total number of submitted ideas
- originality: scored later from the written descriptions
- time per idea
- mouse movement patterns
- total mouse distance
- shape manipulation behavior
- rotation and resize behavior

## Running the Experiment

This project uses only Python's standard library. No extra packages are required.

```bash
python alternative_uses_builder.py
```

On some computers, the command may be:

```bash
python3 alternative_uses_builder.py
```

## Downloading the Project

Open the repository page:

```text
https://github.com/blakehelms/alternative-uses-builder
```

Then click **Code**, choose **Download ZIP**, unzip the folder, and run the Python file.

## Expansion Points

The code is organized so later study versions can add:

- stress conditions
- countdown timers
- warning sounds
- AI hints
- EEG markers
- idea limits
- condition assignment
- additional shape tools
- more detailed movement analysis

Useful places to extend the code include:

- `ExperimentConfig` for task settings
- `ExperimentHooks` for task events and future EEG markers
- `IdeaState` for per-idea behavioral data
- `DataLogger` for the CSV format
- `ShapeItem` for each shape's saved layout

Originality is usually scored after data collection by comparing descriptions across participants or against a coding scheme. This app records the descriptions and behavioral traces needed for that analysis.
