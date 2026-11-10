# Notion Sprint Automation

## Problem statement

Project updates start with someone opening Notion, going through the sprint board and typing out who is working on what. The data is in Notion, but its API returns deeply nested properties that are awkward to read, so the status update gets written by hand every time.

## Solution

A script that reads the Sprints and Tasks databases through the Notion API, flattens the nested properties into clean records and prints a status report of tasks grouped by status with their assignees, ready to paste into an update.

## Tech stack

Python, `notion-client` (async), `asyncio`, `python-dotenv`.

## Features

- Reads the Sprints and Tasks databases with Notion's async client
- Cleans nested Notion properties into simple records: name, status, assignees, due date, features, estimation and priority for tasks; name, status, dates and linked tasks for sprints
- Fetches the tasks of every sprint concurrently with `asyncio`, which is much faster than one request at a time
- Groups sprints (Current, Past, Last) and tasks (Not Started, In Progress, To Validate) by status
- Prints a plain-text report of who is working on what

## Future steps

- Post the report straight to Slack
- Run it on a schedule
- Flag overdue tasks and unassigned work

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
