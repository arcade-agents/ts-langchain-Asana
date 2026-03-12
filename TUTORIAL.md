---
title: "Build a Asana agent with LangChain (TypeScript) and Arcade"
slug: "ts-langchain-Asana"
framework: "langchain-ts"
language: "typescript"
toolkits: ["Asana"]
tools: []
difficulty: "beginner"
generated_at: "2026-03-12T01:34:13Z"
source_template: "ts_langchain"
agent_repo: ""
tags:
  - "langchain"
  - "typescript"
  - "asana"
---

# Build a Asana agent with LangChain (TypeScript) and Arcade

In this tutorial you'll build an AI agent using [LangChain](https://js.langchain.com/) with [LangGraph](https://langchain-ai.github.io/langgraphjs/) in TypeScript and [Arcade](https://arcade.dev) that can interact with Asana tools — with built-in authorization and human-in-the-loop support.

## Prerequisites

- The [Bun](https://bun.com) runtime
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Project Setup

First, create a directory for this project, and install all the required dependencies:

````bash
mkdir asana-agent && cd asana-agent
bun install @arcadeai/arcadejs @langchain/langgraph @langchain/core langchain chalk
````

## Start the agent script

Create a `main.ts` script, and import all the packages and libraries. Imports from 
the `"./tools"` package may give errors in your IDE now, but don't worry about those
for now, you will write that helper package later.

````typescript
"use strict";
import { getTools, confirm, arcade } from "./tools";
import { createAgent } from "langchain";
import {
  Command,
  MemorySaver,
  type Interrupt,
} from "@langchain/langgraph";
import chalk from "chalk";
import * as readline from "node:readline/promises";
````

## Configuration

In `main.ts`, configure your agent's toolkits, system prompt, and model. Notice
how the system prompt tells the agent how to navigate different scenarios and
how to combine tool usage in specific ways. This prompt engineering is important
to build effective agents. In fact, the more agentic your application, the more
relevant the system prompt to truly make the agent useful and effective at
using the tools at its disposal.

````typescript
// configure your own values to customize your agent

// The Arcade User ID identifies who is authorizing each service.
const arcadeUserID = process.env.ARCADE_USER_ID;
if (!arcadeUserID) {
  throw new Error("Missing ARCADE_USER_ID. Add it to your .env file.");
}
// This determines which MCP server is providing the tools, you can customize this to make a Slack agent, or Notion agent, etc.
// all tools from each of these MCP servers will be retrieved from arcade
const toolkits=['Asana'];
// This determines isolated tools that will be
const isolatedTools=[];
// This determines the maximum number of tool definitions Arcade will return
const toolLimit = 100;
// This prompt defines the behavior of the agent.
const systemPrompt = "# Agent Prompt \u2014 Asana ReAct Agent\n\n## Introduction\nYou are an autonomous ReAct-style agent that helps users interact with Asana. Your purpose is to read user requests about tasks, projects, tags, attachments, users, teams, and workspaces, plan the minimal correct sequence of Asana tool calls, execute them, and report results back to the user in clear, actionable language. Use the provided Asana tools to perform real operations; do not fabricate responses \u2014 always use tool outputs for facts about the Asana state.\n\n## Instructions\n- Follow the ReAct pattern: for every step you produce, explicitly separate your chain-of-thought style reasoning from actions and from final messages. Use the following labels in this exact format:\n  - Thought: (your short reasoning about what to do next)\n  - Action: (the name of the tool to call)\n  - Action Input: (the JSON-style input for the tool)\n  - Observation: (the exact output returned by the tool \u2014 insert it when available)\n  - Answer: (a short, user-facing reply or next step)\n- Only call a tool when you need to get or change Asana state. If the user request can be answered without using a tool, respond directly (still follow Thought/Answer labels).\n- Ask clarifying questions when required parameters are missing (e.g., task id, workspace id, due date format, file content).\n- Validate inputs before calling tools:\n  - Dates must be YYYY-MM-DD.\n  - Numeric limits must be within allowed ranges.\n  - For Asana_AttachFileToTask provide exactly one of file_content_str, file_content_base64, or file_content_url. Never supply more than one.\n  - Task creation requires at least one of: parent_task_id, project, or workspace_id (or rely on single-workspace accounts).\n  - Tag names must be 1\u2013100 characters.\n- Handle errors gracefully: if a tool fails, include the tool error in Observation, analyze, and either retry with corrected input or ask the user for more info.\n- When you need to reference a tag, task, project, team, or user and the user provided a name rather than an ID, prefer searching (Asana_GetTaskById / Asana_GetProjectById / Asana_ListTags / Asana_ListProjects, etc.) to resolve the name to an ID first.\n- Never expose internal system tokens or secrets.\n\n## Workflows\nBelow are common workflows and the recommended sequence of tools (with examples). Use the shortest safe sequence to satisfy the user request.\n\n1) Create a new task\n- When: user asks to create a task, optionally with assignee, due date, project, tags, description.\n- Steps:\n  1. (Optional) If user provided project name but not ID: Asana_ListProjects -\u003e find the project id.\n  2. Asana_CreateTask\n- Example:\n```\nThought: Create a task named \"Prepare Q1 report\" in project \"Finance\" due 2026-02-15 with tag \"Quarterly\".\nAction: Asana_ListProjects\nAction Input: { \"workspace_id\": \"W123\", \"limit\": 100 }\nObservation: { ... }  // (tool output)\nThought: Found project id \"P456\".\nAction: Asana_CreateTask\nAction Input: {\n  \"name\": \"Prepare Q1 report\",\n  \"due_date\": \"2026-02-15\",\n  \"project\": \"P456\",\n  \"description\": \"Collect numbers and draft report.\",\n  \"assignee_id\": \"me\",\n  \"tags\": [\"Quarterly\"]\n}\nObservation: { ... }  // created task response\nAnswer: Task created: [task link or id]. I added the tag \"Quarterly\".\n```\nNotes:\n- If a tag name given does not exist, Asana_CreateTask will create it automatically when passed as a tag string.\n\n2) Update a task (change name, dates, description, assignee)\n- When: user asks to update a task.\n- Steps:\n  1. Asana_GetTaskById (recommended to confirm current state)\n  2. Asana_UpdateTask\n- Example:\n```\nThought: User wants to move due date of task T789 to 2026-03-01.\nAction: Asana_GetTaskById\nAction Input: { \"task_id\": \"T789\", \"max_subtasks\": 0 }\nObservation: { ... }\nThought: Task found. Update due date.\nAction: Asana_UpdateTask\nAction Input: { \"task_id\": \"T789\", \"due_date\": \"2026-03-01\" }\nObservation: { ... }\nAnswer: Due date updated to 2026-03-01.\n```\n\n3) Attach a file to a task\n- When: user wants to upload an attachment to a task.\n- Rules: Provide exactly one of file_content_str (for text), file_content_base64 (for binary), or file_content_url (if hosted). Provide file_name and task_id.\n- Steps:\n  1. (Optional) Asana_GetTaskById to verify task exists.\n  2. Asana_AttachFileToTask\n- Example:\n```\nThought: Attach report.pdf to task T789 using base64 content.\nAction: Asana_AttachFileToTask\nAction Input: {\n  \"task_id\": \"T789\",\n  \"file_name\": \"report.pdf\",\n  \"file_content_base64\": \"JVBERi0xLjcK...\" \n}\nObservation: { ... }\nAnswer: File \"report.pdf\" attached to task T789.\n```\n\n4) Create or get a tag\n- When: user wants to create a tag or confirm a tag exists.\n- Steps:\n  1. Asana_ListTags (to find tag by name; pass workspace_id if necessary)\n  2. If not found: Asana_CreateTag\n- Example:\n```\nThought: Check if tag \"Urgent\" exists in workspace W123.\nAction: Asana_ListTags\nAction Input: { \"workspace_id\": \"W123\", \"limit\": 100 }\nObservation: { ... }\nThought: Not found. Create tag.\nAction: Asana_CreateTag\nAction Input: { \"name\": \"Urgent\", \"workspace_id\": \"W123\", \"color\": \"red\" }\nObservation: { ... }\nAnswer: Tag \"Urgent\" created (id ...).\n```\n\n5) Search for tasks by keywords, project, tag, date, or assignee\n- When: user asks to find tasks matching criteria.\n- Steps:\n  1. Asana_GetTasksWithoutId with appropriate filters (keywords, project, tags, due_on_or_after, due_on_or_before, completed, assignee_id, etc.)\n- Example:\n```\nThought: Search tasks with \"Q1 report\" due before 2026-03-01 in workspace W123.\nAction: Asana_GetTasksWithoutId\nAction Input: {\n  \"workspace_id\": \"W123\",\n  \"keywords\": \"Q1 report\",\n  \"due_on_or_before\": \"2026-03-01\",\n  \"limit\": 50\n}\nObservation: { ... }\nAnswer: Found N tasks: [list top results with ids and names].\n```\nNotes:\n- Use page tokens (next_page_token) if results exceed limit and the user asks to see more.\n\n6) Get details for an item (task, project, tag, team, user, workspace)\n- When: user asks for details about a specific resource.\n- Steps:\n  - Use the corresponding Get tool:\n    - Asana_GetTaskById\n    - Asana_GetProjectById\n    - Asana_GetTagById\n    - Asana_GetTeamById\n    - Asana_GetUserById\n    - Asana_GetWorkspaceById\n- Example:\n```\nThought: Fetch task details for T789.\nAction: Asana_GetTaskById\nAction Input: { \"task_id\": \"T789\", \"max_subtasks\": 10 }\nObservation: { ... }\nAnswer: Task details: name, assignee, due date, project, top subtasks (if asked).\n```\n\n7) List projects, tags, teams, users, workspaces\n- When: user asks for a list.\n- Tools:\n  - Asana_ListProjects, Asana_ListTags, Asana_ListTeams, Asana_ListUsers, Asana_ListWorkspaces\n- Example:\n```\nThought: List projects in team TT1.\nAction: Asana_ListProjects\nAction Input: { \"team_id\": \"TT1\", \"limit\": 100 }\nObservation: { ... }\nAnswer: Found projects: [names and ids].\n```\n- Use next_page_token to fetch additional pages when necessary.\n\n8) Get subtasks of a task\n- When: user asks for subtasks or to operate on subtasks.\n- Steps:\n  1. Asana_GetSubtasksFromATask (pass limit and next_page_token if needed)\n- Example:\n```\nThought: Retrieve subtasks of T789.\nAction: Asana_GetSubtasksFromATask\nAction Input: { \"task_id\": \"T789\", \"limit\": 100 }\nObservation: { ... }\nAnswer: Found X subtasks: [list].\n```\n\n9) Mark a task as completed\n- When: user asks to complete a task.\n- Steps:\n  1. (Optional) Asana_GetTaskById to confirm status and warn if already completed.\n  2. Asana_MarkTaskAsCompleted\n- Example:\n```\nThought: Mark T789 completed if not already.\nAction: Asana_GetTaskById\nAction Input: { \"task_id\": \"T789\", \"max_subtasks\": 0 }\nObservation: { ... }\nThought: Not completed. Mark complete.\nAction: Asana_MarkTaskAsCompleted\nAction Input: { \"task_id\": \"T789\" }\nObservation: { ... }\nAnswer: Task T789 marked completed.\n```\n\n10) Complex flows (e.g., create task in project, attach file, add tag)\n- Compose the minimal sequence from the above primitives. Example order:\n  1. Resolve project id (Asana_ListProjects) if needed\n  2. Asana_CreateTask\n  3. Asana_AttachFileToTask (if attachment)\n  4. Asana_CreateTag / Asana_ListTags (if tag resolution required) \u2014 but tags can also be passed to Asana_CreateTask as strings.\n\n## Example ReAct Interaction Template\nUse this template for each operation:\n```\nThought: \u003cbrief reasoning\u003e\nAction: \u003cToolName\u003e\nAction Input: \u003cJSON object with required fields\u003e\nObservation: \u003ctool output here once available\u003e\nThought: \u003cfollowup reasoning if any\u003e\nAction: \u003cnext ToolName\u003e  // if another tool is needed\nAction Input: \u003c...\u003e\nObservation: \u003c...\u003e\nAnswer: \u003cfinal user-facing message summarizing the result or asking clarifying questions\u003e\n```\n\n## Tool-specific constraints \u0026 hints\n- Asana_CreateTask: ensure at least one of parent_task_id, project, or workspace_id is included. Tags may be strings (names) or IDs.\n- Asana_AttachFileToTask: Provide exactly one of file_content_str, file_content_base64, or file_content_url. If attaching text files, use file_content_str and optionally file_encoding (default utf-8). For binary (images, PDFs) use file_content_base64.\n- Asana_GetSubtasksFromATask: default limit 100. Use next_page_token for pagination.\n- Asana_GetTasksWithoutId: respects filters; use careful date ranges to avoid very large result sets. Limit min 1 max 100.\n- Asana_List* endpoints: respect limit and next_page_token for pagination.\n- Asana_CreateTag: tag name length must be 1\u2013100 characters. Include workspace_id when you want the tag in a specific workspace.\n\n## Error handling \u0026 clarifying questions\n- If a user gives ambiguous or incomplete input (e.g., \u201cattach the file to the task\u201d without task id, or \u201ccreate tag\u201d without workspace), ask one concise clarifying question using Thought + Answer (do not call tools).\n- If a tool returns an error, include the error under Observation, analyze root cause in Thought, and either retry with corrected parameters or ask the user for missing info.\n\n---\n\nFollow this prompt structure for every user request. Always keep actions minimal and explicit, and never invent Asana state \u2014 rely on tool Observations for facts.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";
````

Set the following environment variables in a `.env` file:

````bash
ARCADE_API_KEY=your-arcade-api-key
ARCADE_USER_ID=your-arcade-user-id
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
````

## Implementing the `tools.ts` module

The `tools.ts` module fetches Arcade tool definitions and converts them to LangChain-compatible tools using Arcade's Zod schema conversion:

### Create the file and import the dependencies

Create a `tools.ts` file, and add import the following. These will allow you to build the helper functions needed to convert Arcade tool definitions into a format that LangChain can execute. Here, you also define which tools will require human-in-the-loop confirmation. This is very useful for tools that may have dangerous or undesired side-effects if the LLM hallucinates the values in the parameters. You will implement the helper functions to require human approval in this module.

````typescript
import { Arcade } from "@arcadeai/arcadejs";
import {
  type ToolExecuteFunctionFactoryInput,
  type ZodTool,
  executeZodTool,
  isAuthorizationRequiredError,
  toZod,
} from "@arcadeai/arcadejs/lib/index";
import { type ToolExecuteFunction } from "@arcadeai/arcadejs/lib/zod/types";
import { tool } from "langchain";
import {
  interrupt,
} from "@langchain/langgraph";
import readline from "node:readline/promises";

// This determines which tools require human in the loop approval to run
const TOOLS_WITH_APPROVAL = ['Asana_AttachFileToTask', 'Asana_CreateTag', 'Asana_CreateTask', 'Asana_MarkTaskAsCompleted', 'Asana_UpdateTask'];
````

### Create a confirmation helper for human in the loop

The first helper that you will write is the `confirm` function, which asks a yes or no question to the user, and returns `true` if theuser replied with `"yes"` and `false` otherwise.

````typescript
// Prompt user for yes/no confirmation
export async function confirm(question: string, rl?: readline.Interface): Promise<boolean> {
  let shouldClose = false;
  let interface_ = rl;

  if (!interface_) {
      interface_ = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
      });
      shouldClose = true;
  }

  const answer = await interface_.question(`${question} (y/n): `);

  if (shouldClose) {
      interface_.close();
  }

  return ["y", "yes"].includes(answer.trim().toLowerCase());
}
````

Tools that require authorization trigger a LangGraph interrupt, which pauses execution until the user completes authorization in their browser.

### Create the execution helper

This is a wrapper around the `executeZodTool` function. Before you execute the tool, however, there are two logical checks to be made:

1. First, if the tool the agent wants to invoke is included in the `TOOLS_WITH_APPROVAL` variable, human-in-the-loop is enforced by calling `interrupt` and passing the necessary data to call the `confirm` helper. LangChain will surface that `interrupt` to the agentic loop, and you will be required to "resolve" the interrupt later on. For now, you can assume that the reponse of the `interrupt` will have enough information to decide whether to execute the tool or not, depending on the human's reponse.
2. Second, if the tool was approved by the human, but it doesn't have the authorization of the integration to run, then you need to present an URL to the user so they can authorize the OAuth flow for this operation. For this, an execution is attempted, that may fail to run if the user is not authorized. When it fails, you interrupt the flow and send the authorization request for the harness to handle. If the user authorizes the tool, the harness will reply with an `{authorized: true}` object, and the system will retry the tool call without interrupting the flow.

````typescript
export function executeOrInterruptTool({
  zodToolSchema,
  toolDefinition,
  client,
  userId,
}: ToolExecuteFunctionFactoryInput): ToolExecuteFunction<any> {
  const { name: toolName } = zodToolSchema;

  return async (input: unknown) => {
    try {

      // If the tool is on the list that enforces human in the loop, we interrupt the flow and ask the user to authorize the tool

      if (TOOLS_WITH_APPROVAL.includes(toolName)) {
        const hitl_response = interrupt({
          authorization_required: false,
          hitl_required: true,
          tool_name: toolName,
          input: input,
        });

        if (!hitl_response.authorized) {
          // If the user didn't approve the tool call, we throw an error, which will be handled by LangChain
          throw new Error(
            `Human in the loop required for tool call ${toolName}, but user didn't approve.`
          );
        }
      }

      // Try to execute the tool
      const result = await executeZodTool({
        zodToolSchema,
        toolDefinition,
        client,
        userId,
      })(input);
      return result;
    } catch (error) {
      // If the tool requires authorization, we interrupt the flow and ask the user to authorize the tool
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: toolName,
          user_id: userId,
        });

        // We interrupt the flow here, and pass everything the handler needs to get the user's authorization
        const interrupt_response = interrupt({
          authorization_required: true,
          authorization_response: response,
          tool_name: toolName,
          url: response.url ?? "",
        });

        // If the user authorized the tool, we retry the tool call without interrupting the flow
        if (interrupt_response.authorized) {
          const result = await executeZodTool({
            zodToolSchema,
            toolDefinition,
            client,
            userId,
          })(input);
          return result;
        } else {
          // If the user didn't authorize the tool, we throw an error, which will be handled by LangChain
          throw new Error(
            `Authorization required for tool call ${toolName}, but user didn't authorize.`
          );
        }
      }
      throw error;
    }
  };
}
````

### Create the tool retrieval helper

The last helper function of this module is the `getTools` helper. This function will take the configurations you defined in the `main.ts` file, and retrieve all of the configured tool definitions from Arcade. Those definitions will then be converted to LangGraph `Function` tools, and will be returned in a format that LangChain can present to the LLM so it can use the tools and pass the arguments correctly. You will pass the `executeOrInterruptTool` helper you wrote in the previous section so all the bindings to the human-in-the-loop and auth handling are programmed when LancChain invokes a tool.


````typescript
// Initialize the Arcade client
export const arcade = new Arcade();

export type GetToolsProps = {
  arcade: Arcade;
  toolkits?: string[];
  tools?: string[];
  userId: string;
  limit?: number;
}


export async function getTools({
  arcade,
  toolkits = [],
  tools = [],
  userId,
  limit = 100,
}: GetToolsProps) {

  if (toolkits.length === 0 && tools.length === 0) {
      throw new Error("At least one tool or toolkit must be provided");
  }

  // Todo(Mateo): Add pagination support
  const from_toolkits = await Promise.all(toolkits.map(async (tkitName) => {
      const definitions = await arcade.tools.list({
          toolkit: tkitName,
          limit: limit
      });
      return definitions.items;
  }));

  const from_tools = await Promise.all(tools.map(async (toolName) => {
      return await arcade.tools.get(toolName);
  }));

  const all_tools = [...from_toolkits.flat(), ...from_tools];
  const unique_tools = Array.from(
      new Map(all_tools.map(tool => [tool.qualified_name, tool])).values()
  );

  const arcadeTools = toZod({
    tools: unique_tools,
    client: arcade,
    executeFactory: executeOrInterruptTool,
    userId: userId,
  });

  // Convert Arcade tools to LangGraph tools
  const langchainTools = arcadeTools.map(({ name, description, execute, parameters }) =>
    (tool as Function)(execute, {
      name,
      description,
      schema: parameters,
    })
  );

  return langchainTools;
}
````

## Building the Agent

Back on the `main.ts` file, you can now call the helper functions you wrote to build the agent.

### Retrieve the configured tools

Use the `getTools` helper you wrote to retrieve the tools from Arcade in LangChain format:

````typescript
const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});
````

### Write an interrupt handler

When LangChain is interrupted, it will emit an event in the stream that you will need to handle and resolve based on the user's behavior. For a human-in-the-loop interrupt, you will call the `confirm` helper you wrote earlier, and indicate to the harness whether the human approved the specific tool call or not. For an auth interrupt, you will present the OAuth URL to the user, and wait for them to finishe the OAuth dance before resolving the interrupt with `{authorized: true}` or `{authorized: false}` if an error occurred:

````typescript
async function handleInterrupt(
  interrupt: Interrupt,
  rl: readline.Interface
): Promise<{ authorized: boolean }> {
  const value = interrupt.value;
  const authorization_required = value.authorization_required;
  const hitl_required = value.hitl_required;
  if (authorization_required) {
    const tool_name = value.tool_name;
    const authorization_response = value.authorization_response;
    console.log("⚙️: Authorization required for tool call", tool_name);
    console.log(
      "⚙️: Please authorize in your browser",
      authorization_response.url
    );
    console.log("⚙️: Waiting for you to complete authorization...");
    try {
      await arcade.auth.waitForCompletion(authorization_response.id);
      console.log("⚙️: Authorization granted. Resuming execution...");
      return { authorized: true };
    } catch (error) {
      console.error("⚙️: Error waiting for authorization to complete:", error);
      return { authorized: false };
    }
  } else if (hitl_required) {
    console.log("⚙️: Human in the loop required for tool call", value.tool_name);
    console.log("⚙️: Please approve the tool call", value.input);
    const approved = await confirm("Do you approve this tool call?", rl);
    return { authorized: approved };
  }
  return { authorized: false };
}
````

### Create an Agent instance

Here you create the agent using the `createAgent` function. You pass the system prompt, the model, the tools, and the checkpointer. When the agent runs, it will automatically use the helper function you wrote earlier to handle tool calls and authorization requests.

````typescript
const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});
````

### Write the invoke helper

This last helper function handles the streaming of the agent’s response, and captures the interrupts. When the system detects an interrupt, it adds the interrupt to the `interrupts` array, and the flow interrupts. If there are no interrupts, it will just stream the agent’s to your console.

````typescript
async function streamAgent(
  agent: any,
  input: any,
  config: any
): Promise<Interrupt[]> {
  const stream = await agent.stream(input, {
    ...config,
    streamMode: "updates",
  });
  const interrupts: Interrupt[] = [];

  for await (const chunk of stream) {
    if (chunk.__interrupt__) {
      interrupts.push(...(chunk.__interrupt__ as Interrupt[]));
      continue;
    }
    for (const update of Object.values(chunk)) {
      for (const msg of (update as any)?.messages ?? []) {
        console.log("🤖: ", msg.toFormattedString());
      }
    }
  }

  return interrupts;
}
````

### Write the main function

Finally, write the main function that will call the agent and handle the user input.

Here the `config` object configures the `thread_id`, which tells the agent to store the state of the conversation into that specific thread. Like any typical agent loop, you:

1. Capture the user input
2. Stream the agent's response
3. Handle any authorization interrupts
4. Resume the agent after authorization
5. Handle any errors
6. Exit the loop if the user wants to quit

````typescript
async function main() {
  const config = { configurable: { thread_id: threadID } };
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.green("Welcome to the chatbot! Type 'exit' to quit."));
  while (true) {
    const input = await rl.question("> ");
    if (input.toLowerCase() === "exit") {
      break;
    }
    rl.pause();

    try {
      let agentInput: any = {
        messages: [{ role: "user", content: input }],
      };

      // Loop until no more interrupts
      while (true) {
        const interrupts = await streamAgent(agent, agentInput, config);

        if (interrupts.length === 0) {
          break; // No more interrupts, we're done
        }

        // Handle all interrupts
        const decisions: any[] = [];
        for (const interrupt of interrupts) {
          decisions.push(await handleInterrupt(interrupt, rl));
        }

        // Resume with decisions, then loop to check for more interrupts
        // Pass single decision directly, or array for multiple interrupts
        agentInput = new Command({ resume: decisions.length === 1 ? decisions[0] : decisions });
      }
    } catch (error) {
      console.error(error);
    }

    rl.resume();
  }
  console.log(chalk.red("👋 Bye..."));
  process.exit(0);
}

// Run the main function
main().catch((err) => console.error(err));
````

## Running the Agent

### Run the agent

```bash
bun run main.ts
```

You should see the agent responding to your prompts like any model, as well as handling any tool calls and authorization requests.

## Next Steps

- Clone the [repository](https://github.com/arcade-agents/ts-langchain-Asana) and run it
- Add more toolkits to the `toolkits` array to expand capabilities
- Customize the `systemPrompt` to specialize the agent's behavior
- Explore the [Arcade documentation](https://docs.arcade.dev) for available toolkits

