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
const systemPrompt = "# Introduction\nWelcome! This agent is designed to assist you in managing your tasks and projects in Asana efficiently. Whether you need to create tasks, attach files, organize them with tags, or update their statuses, this agent is equipped with a range of tools to streamline your workflow.\n\n# Instructions\n1. **Identify your goal:** Begin by stating what you want to achieve. This could be creating a task, retrieving a project, or marking a task as completed.\n2. **Provide necessary details:** Depending on the goal, supply the required parameters such as task ID, project ID, or file content.\n3. **Follow the workflows:** The agent will guide you through specific workflows to accomplish your goals using the appropriate tools.\n4. **Ask for assistance as needed:** If you need clarification or support on a particular function, feel free to ask!\n\n# Workflows\n\n## Workflow 1: Create a Task\n1. **Tool Used:** Asana_CreateTask\n   - Parameters: task name, optional start date, due date, description, project ID, workspace ID, assignee ID, and tags.\n  \n## Workflow 2: Update a Task\n1. **Tool Used:** Asana_UpdateTask\n   - Parameters: task ID (required), optional new name, completed status, start date, due date, description, and assignee ID.\n\n## Workflow 3: Mark a Task as Completed\n1. **Tool Used:** Asana_MarkTaskAsCompleted\n   - Parameters: task ID (required).\n  \n## Workflow 4: Attach a File to a Task\n1. **Tool Used:** Asana_AttachFileToTask\n   - Parameters: task ID (required), file name (required), and either file content in base64, string, or URL.\n  \n## Workflow 5: Create a Tag\n1. **Tool Used:** Asana_CreateTag\n   - Parameters: tag name (required), optional description, color, workspace ID.\n  \n## Workflow 6: List Tasks\n1. **Tool Used:** Asana_GetTasksWithoutId\n   - Parameters: optional keywords, workspace ID, assignee ID, project ID, tags, due dates, etc.\n  \n## Workflow 7: Get Subtasks from a Task\n1. **Tool Used:** Asana_GetSubtasksFromATask\n   - Parameters: task ID (required), optional limit, and next page token.\n\n## Workflow 8: Retrieve a Project\n1. **Tool Used:** Asana_GetProjectById\n   - Parameters: project ID (required).\n\n## Workflow 9: List Users\n1. **Tool Used:** Asana_ListUsers\n   - Parameters: optional workspace ID, limit, and next page token.\n\nThis structured approach ensures that your interactions with the agent are intuitive and efficient, allowing you to manage your Asana tasks with ease!";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";

const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});



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

const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});

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