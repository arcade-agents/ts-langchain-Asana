# An agent that uses Asana tools provided to perform any task

## Purpose

# Introduction
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

This structured approach ensures that your interactions with the agent are intuitive and efficient, allowing you to manage your Asana tasks with ease!

## MCP Servers

The agent uses tools from these Arcade MCP Servers:

- Asana

## Human-in-the-Loop Confirmation

The following tools require human confirmation before execution:

- `Asana_AttachFileToTask`
- `Asana_CreateTask`
- `Asana_MarkTaskAsCompleted`
- `Asana_UpdateTask`


## Getting Started

1. Install dependencies:
    ```bash
    bun install
    ```

2. Set your environment variables:

    Copy the `.env.example` file to create a new `.env` file, and fill in the environment variables.
    ```bash
    cp .env.example .env
    ```

3. Run the agent:
    ```bash
    bun run main.ts
    ```