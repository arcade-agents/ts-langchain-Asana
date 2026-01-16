from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,)
from functools import partial
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from human_in_the_loop import (UserDeniedToolCall,
                               confirm_tool_usage,
                               auth_tool)

import globals


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self,
                       context: RunContextWrapper,
                       agent: Agent) -> None:
        self.event_counter += 1
        print(f"### ({self.display_name}) {
              self.event_counter}: Agent {agent.name} started")

    async def on_end(self,
                     context: RunContextWrapper,
                     agent: Agent,
                     output: Any) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended with output {output}"
                agent.name} ended"
        )

    async def on_handoff(self,
                         context: RunContextWrapper,
                         agent: Agent,
                         source: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                source.name} handed off to {agent.name}"
        )

    async def on_tool_start(self,
                            context: RunContextWrapper,
                            agent: Agent,
                            tool: Tool) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}:"
            f" Agent {agent.name} started tool {tool.name}"
            f" with context: {context.context}"
        )

    async def on_tool_end(self,
                          context: RunContextWrapper,
                          agent: Agent,
                          tool: Tool,
                          result: str) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended tool {tool.name} with result {result}"
                agent.name} ended tool {tool.name}"
        )


async def main():

    context = {
        "user_id": os.getenv("ARCADE_USER_ID"),
    }

    client = AsyncArcade()

    arcade_tools = await get_arcade_tools(
        client, toolkits=["Asana"]
    )

    for tool in arcade_tools:
        # - human in the loop
        if tool.name in ENFORCE_HUMAN_CONFIRMATION:
            tool.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=tool.name,
                callback=tool.on_invoke_tool,
            )
        # - auth
        await auth_tool(client, tool.name, user_id=context["user_id"])

    agent = Agent(
        name="",
        instructions="# Introduction
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
        model=os.environ["OPENAI_MODEL"],
        tools=arcade_tools,
        hooks=CustomAgentHooks(display_name="")
    )

    # initialize the conversation
    history: list[TResponseInputItem] = []
    # run the loop!
    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=history,
                context=context
            )
            history = result.to_input_list()
            print(result.final_output)
        except UserDeniedToolCall as e:
            history.extend([
                {"role": "assistant",
                 "content": f"Please confirm the call to {e.tool_name}"},
                {"role": "user",
                 "content": "I changed my mind, please don't do it!"},
                {"role": "assistant",
                 "content": f"Sure, I cancelled the call to {e.tool_name}."
                 " What else can I do for you today?"
                 },
            ])
            print(history[-1]["content"])

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())