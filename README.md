# Notion Sprint Automation

A script that pulls sprints and tasks out of a team's Notion workspace and turns them into clean, structured data and a plain-text status report. It saves the manual work of copying sprint status out of Notion by hand.

## What it does

- Connects to Notion's API with the async client and reads the **Sprints** and **Tasks** databases.
- Cleans Notion's deeply nested property format into simple records: name, status, assignees, due date, features, estimation and priority for tasks, and name, status, dates and linked tasks for sprints.
- Fetches the tasks of each sprint concurrently with `asyncio`, which is much faster than one request at a time.
- Groups sprints and tasks by status (for example Current, Past, Last for sprints; Not Started, In Progress, To Validate for tasks) and prints a report of who is working on what, ready to paste into an update.

## Tech stack

Python, `notion-client` (async), `asyncio`, `python-dotenv`.

## Getting started

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
NOTION_TOKEN=your_notion_integration_token
TASKS_DATABASE_ID=your_tasks_database_id
SPRINTS_DATABASE_ID=your_sprints_database_id
```

Share both databases with your Notion integration, then run:

```bash
python app.py
```
