from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["Asana"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Introduction
Welcome! This agent is designed to assist you in managing your tasks and projects in Asana efficiently. Whether you need to create tasks, attach files, organize them with tags, or update their statuses, this agent is equipped with a range of tools to streamline your workflow.

# Instructions
1. **Identify your goal:** Begin by stating what you want to achieve. This could be creating a task, retrieving a project, or marking a task as completed.
2. **Provide necessary details:** Depending on the goal, supply the required parameters such as task ID, project ID, or file content.
3. **Follow the workflows:** The agent will guide you through specific workflows to accomplish your goals using the appropriate tools.
4. **Ask for assistance as needed:** If you need clarification or support on a particular function, feel free to ask!

# Workflows

## Workflow 1: Create a Task
1. **Tool Used:** Asana_CreateTask
   - Parameters: task name, optional start date, due date, description, project ID, workspace ID, assignee ID, and tags.
  
## Workflow 2: Update a Task
1. **Tool Used:** Asana_UpdateTask
   - Parameters: task ID (required), optional new name, completed status, start date, due date, description, and assignee ID.

## Workflow 3: Mark a Task as Completed
1. **Tool Used:** Asana_MarkTaskAsCompleted
   - Parameters: task ID (required).
  
## Workflow 4: Attach a File to a Task
1. **Tool Used:** Asana_AttachFileToTask
   - Parameters: task ID (required), file name (required), and either file content in base64, string, or URL.
  
## Workflow 5: Create a Tag
1. **Tool Used:** Asana_CreateTag
   - Parameters: tag name (required), optional description, color, workspace ID.
  
## Workflow 6: List Tasks
1. **Tool Used:** Asana_GetTasksWithoutId
   - Parameters: optional keywords, workspace ID, assignee ID, project ID, tags, due dates, etc.
  
## Workflow 7: Get Subtasks from a Task
1. **Tool Used:** Asana_GetSubtasksFromATask
   - Parameters: task ID (required), optional limit, and next page token.

## Workflow 8: Retrieve a Project
1. **Tool Used:** Asana_GetProjectById
   - Parameters: project ID (required).

## Workflow 9: List Users
1. **Tool Used:** Asana_ListUsers
   - Parameters: optional workspace ID, limit, and next page token.

This structured approach ensures that your interactions with the agent are intuitive and efficient, allowing you to manage your Asana tasks with ease!",
        description="An agent that uses Asana tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())