import os
import asyncio
from dotenv import load_dotenv
from notion_client import AsyncClient
from notion_client.errors import APIResponseError
import json

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TASKS_DATABASE_ID = os.getenv("TASKS_DATABASE_ID")
SPRINTS_DATABASE_ID = os.getenv("SPRINTS_DATABASE_ID")

notion = AsyncClient(auth=NOTION_TOKEN)


async def fetch_tasks(database_id: str = TASKS_DATABASE_ID) -> list[dict]:
    """
    Retrieves database metadata to extract the underlying data source ID,
    queries the data source, and extracts row properties.
    
    Args:
        database_id (str): The 32-character Notion database identifier.
        
    Returns:
        list[dict]: A list of dictionaries containing parsed row data.
    """
    tasks = []
    try:
        database_info = await notion.databases.retrieve(database_id=database_id)
        data_sources = database_info.get("data_sources", [])
        if not data_sources:
            return tasks
        for ds in data_sources:
            if ds.get("name") == 'Tasks':
                primary_data_source_id = ds.get("id")
                break
        response = await notion.data_sources.query(data_source_id=primary_data_source_id)
        results = response.get("results", [])
        for row in results:
            properties = row.get("properties", {})
            tasks.append(properties)
        return tasks
    except APIResponseError as e:
        print(f"Notion API Error: {e}")
        return []
    

async def fetch_sprints(database_id: str = SPRINTS_DATABASE_ID) -> list[dict]:
    """
    Retrieves sprint pages from the specified Notion database.
    
    Args:
        database_id (str): The 32-character Notion database identifier for sprints.
        
    Returns:
        list[dict]: A list of dictionaries containing sprint metadata.
    """
    sprints = []
    try:
        database_info = await notion.databases.retrieve(database_id=database_id)
        data_sources = database_info.get("data_sources", [])
        for ds in data_sources:
            if ds.get("name") == 'Sprints':
                primary_data_source_id = ds.get("id")
                break
        response = await notion.data_sources.query(data_source_id=primary_data_source_id)
        results = response.get("results", [])
        for row in results:
            properties = row.get("properties", {})
            sprints.append(properties)
        return sprints
    except APIResponseError as e:
        print(f"Notion API Error retrieving sprints: {e}")
        return []


def safe_get(dct, keys, default=None):
    """Safely retrieves nested dictionary values."""
    try: 
        for key in keys:
            dct = dct[key]
        return dct
    except (KeyError, TypeError):
        return default
    

def clean_task(task: dict) -> dict:
    name = safe_get(task, ["Task name", "title", 0, "plain_text"], "Untitled Task")
    assignees = []
    status = safe_get(task, ["Status", "status", "name"], "No Status")
    due_date = safe_get(task, ["Due date", "date", "start"], "")
    people = safe_get(task, ["Assignee", "people"], [])
    assignees = [person.get("name", "Unknown") for person in people]
    features = safe_get(task, ["Features", "multi_select"], [])
    feature_names = [feature.get('name', 'Unknown') for feature in features]
    estimation = safe_get(task, ["Estimation", "number"], 0)
    priority = safe_get(task, ["Priority", "select", "name"], "No Priority")

    return {
        "name": name,
        "assignees": assignees,
        "status": status,
        "due_date": due_date,
        "features": feature_names,
        "estimation": estimation,
        "priority": priority
    }


def clean_sprint(sprint: dict) -> dict:
    name = safe_get(sprint, ["Sprint name", "title", 0, "plain_text"], "Untitled Sprint")
    status = safe_get(sprint, ["Sprint status", "status", "name"], "No Status")
    dates = safe_get(sprint, ["Dates", "date"], {})
    start_date = dates.get("start") if dates else None
    end_date = dates.get("end") if dates else None
    tasks = safe_get(sprint, ["Tasks", "relation"], [])
    return {
        "name": name,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "tasks": [task.get("id") for task in tasks]
    }


def clean_tasks(tasks: list[dict]) -> list[dict]:
    cleaned_tasks = []
    try:
        for task in tasks:
            task = clean_task(task)
            cleaned_tasks.append(task)
    except Exception as e:
        print(f"Error cleaning tasks: {e}")
    return cleaned_tasks


def clean_sprints(sprints: list[dict]) -> list[dict]:
    cleaned_sprints = []
    try:
        for sprint in sprints:
            sprint = clean_sprint(sprint)
            cleaned_sprints.append(sprint)
    except Exception as e:
        print(f"Error cleaning sprints: {e}")
    return cleaned_sprints


async def get_task_by_ids(task_ids: list[str]) -> list[dict]:
    """
    Retrieves task page properties concurrently using a list of task IDs.
    
    Args:
        task_ids (list[str]): A list of Notion page IDs for the tasks.
        
    Returns:
        list[dict]: A list of parsed task metadata dictionaries.
    """
    tasks_data = []
    
    coroutines = [notion.pages.retrieve(page_id=tid) for tid in task_ids]
    
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Notion API Error retrieving task: {result}")
        else:
            properties = result.get("properties", {})
            tasks_data.append(clean_task(properties))
            
    return tasks_data


async def get_sprint_by_ids(sprint_ids: list[str]) -> list[dict]:
    """
    Retrieves sprint page properties concurrently using a list of sprint IDs.
    
    Args:
        sprint_ids (list[str]): A list of Notion page IDs for the sprints.
        
    Returns:
        list[dict]: A list of parsed sprint metadata dictionaries.
    """
    sprints_data = []
    
    coroutines = [notion.pages.retrieve(page_id=sid) for sid in sprint_ids]
    
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Notion API Error retrieving sprint: {result}")
        else:
            properties = result.get("properties", {})
            sprints_data.append(clean_sprint(properties))
            
    return sprints_data
    

def get_sprints_by_status(sprints: list[dict], status_list: list[str] = None) -> dict[str, list[dict]]:
    classified = {}
    for sprint in sprints:
        status = sprint.get("status", "No Status")
        if status_list is None or status in status_list:
            classified.setdefault(status, []).append(sprint)
    return classified


def get_tasks_by_status(tasks: list[dict], status_list: list[str] = None) -> dict[str, list[dict]]:
    classified = {}
    for task in tasks:
        status = task.get("status", "No Status")
        if status_list is None or status in status_list:
            classified.setdefault(status, []).append(task)
    return classified


def write_tasks_stringified(tasks: list[dict], status: list[str] = None) -> str:
    try:
        filtered_tasks = [task for task in tasks if task.get("status") in status] if status else tasks
        s = """"""
        for task_status in filtered_tasks:
            tasks = filtered_tasks[task_status]
            s += task_status + "\n"
            s += "------------------\n"
            for task in tasks:
                s += "\t" + task["name"] + ": " + ', '.join(task["assignees"]) + "\n"
        return s
    except Exception as e:
        print(f"Error stringifying tasks: {e}")
        return ""

async def main():
    """
    Main execution loop orchestrating data fetching, cleaning, and connection management.
    """
    try:
        all_sprints_raw = await fetch_sprints()
        cleaned_sprints_list = clean_sprints(all_sprints_raw)
        
        classified_sprints = get_sprints_by_status(cleaned_sprints_list, ['Last', 'Past', 'Current'])
        allowed_statuses = ['Not Started', 'In Progress', 'To Validate']
        for status, sprints in classified_sprints.items():
            for sprint in sprints:
                task_ids = sprint.get('tasks', [])
                if task_ids:
                    task_details = await get_task_by_ids(task_ids)
                    tasks = get_tasks_by_status(task_details)
                    print(write_tasks_stringified(tasks))
    finally:
        await notion.aclose()


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())