import os
import asyncio
from dotenv import load_dotenv
from notion_client import AsyncClient
from notion_client.errors import APIResponseError
import json

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion = AsyncClient(auth=NOTION_TOKEN)


async def fetch_tasks(database_id: str = DATABASE_ID) -> list[dict]:
    """
    Retrieves database metadata to extract the underlying data source ID,
    queries the data source, and extracts row properties.
    
    Args:
        database_id (str): The 32-character Notion database identifier.
        
    Returns:
        list[dict]: A list of dictionaries containing parsed row data.
    """
    parsed_data = []
    
    try:
        database_info = await notion.databases.retrieve(database_id=database_id)
        data_sources = database_info.get("data_sources", [])
        if not data_sources:
            return parsed_data
        
        for ds in data_sources:
            if ds.get("name") == 'Tasks':
                primary_data_source_id = ds.get("id")
                break
        
        response = await notion.data_sources.query(data_source_id=primary_data_source_id)
        results = response.get("results", [])
        
        for row in results:
            properties = row.get("properties", {})
            parsed_data.append(properties)
            continue
            
            # Print raw properties once to inspect the actual schema
            if not parsed_data:
                print(f"Raw Database Schema Keys: {list(properties.keys())}\n")
            
            # Extracting the Title property (assumes default 'Name' column)

            title_property = properties.get("Name", {}).get("title", [])
            print(title_property)
            row_name = title_property[0].get("plain_text") if title_property else "Untitled"
            
            parsed_data.append({
                "id": row.get("id"),
                "name": row_name,
            })
            
        return parsed_data

    except APIResponseError as e:
        print(f"Notion API Error: {e}")
        return []

def safe_get(dct, keys, default=None):
    """Safely retrieves nested dictionary values."""
    try: 
        for key in keys:
            dct = dct[key]
        return dct
    except (KeyError, TypeError):
        return default
    

async def clean_tasks() -> list[dict]:
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: Missing environment variables.")
        raise ValueError("NOTION_TOKEN and DATABASE_ID must be set in the .env file.")
    
    cleaned_tasks = []
    try:
        tasks = await fetch_tasks()
        for task in tasks:
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

            task = {
                "name": name,
                "assignees": assignees,
                "status": status,
                "due_date": due_date,
                "features": feature_names,
                "estimation": estimation,
                "priority": priority
            }
            cleaned_tasks.append(task)
    finally:
        # Ensures underlying HTTP connections are gracefully closed
        await notion.aclose()
    return cleaned_tasks


async def get_sprint_by_id(sprint_id: str) -> dict:
    """
    Retrieves sprint page properties using the sprint ID.
    
    Args:
        sprint_id (str): The Notion page ID of the sprint.
        
    Returns:
        dict: Parsed sprint metadata including name and status.
    """
    try:
        response = await notion.pages.retrieve(page_id=sprint_id)
        properties = response.get("properties", {})
        
        name_prop = properties.get("Name", {}).get("title", [])
        sprint_name = safe_get(name_prop, ["properties", "Name", "title", 0, "plain_text"], "Untitled Sprint")
        
        status_prop = properties.get("Status", {}).get("status", {})
        sprint_status = safe_get(status_prop, ["name"], "No Status")
        
        dates_prop = properties.get("Dates", {}).get("date", {})
        start_date = dates_prop.get("start") if dates_prop else None
        end_date = dates_prop.get("end") if dates_prop else None
        
        return {
            "id": response.get("id"),
            "name": sprint_name,
            "status": sprint_status,
            "start_date": start_date,
            "end_date": end_date
        }
        
    except APIResponseError as e:
        print(f"Notion API Error retrieving sprint: {e}")
        return {}
    

def classify_tasks_by_status(tasks: list[dict]) -> dict[str, list[dict]]:
    classified = {}
    for task in tasks:
        status = task.get("status", "No Status")
        classified.setdefault(status, []).append(task)
    return classified


if __name__ == "__main__":
    # Windows specific fix for ProactorEventLoop cleanup
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # tasks = asyncio.run(clean_tasks())
    # classified_tasks = classify_tasks_by_status(tasks)
    # with open("classified_tasks.json", "w") as f:
    #     json.dump(classified_tasks, f, indent=4)
    sprint = asyncio.run(get_sprint_by_id("2fe91cda-2191-8024-a780-ce5d0ca3df22"))
    print(sprint)