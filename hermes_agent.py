import os
import subprocess
import json
import urllib.request
import urllib.error

# --- Tool Functions ---

def create_directory(path):
    """Creates a directory and all parent directories."""
    try:
        os.makedirs(path, exist_ok=True)
        return f"Directory {path} created successfully."
    except Exception as e:
        return f"Error creating directory {path}: {str(e)}"

def write_file(path, content):
    """Writes content to a file, overwriting it if it exists."""
    try:
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File {path} written successfully."
    except Exception as e:
        return f"Error writing to file {path}: {str(e)}"

def append_file(path, content):
    """Appends content to a file."""
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
        return f"Content appended to {path} successfully."
    except Exception as e:
        return f"Error appending to file {path}: {str(e)}"

def read_file(path):
    """Reads the content of a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

def execute_command(command):
    """Executes a bash command and returns the output (stdout and stderr)."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode

        output = f"Exit code: {exit_code}\n"
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
            output += f"STDERR:\n{stderr}\n"

        return output.strip()
    except Exception as e:
        return f"Error executing command: {str(e)}"


# --- API Interaction ---

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:7b"

def chat_with_ollama(messages, model=DEFAULT_MODEL, tools=None):
    """Sends a chat request to the Ollama API."""
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1 # Keep it somewhat deterministic for tool calling
        }
    }

    if tools:
        data["tools"] = tools

    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('message', {})
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama: {e}")
        return None

# --- Agent Loop ---

def run_agent(task, model=DEFAULT_MODEL, max_iterations=20):
    """Runs the agent loop."""
    print(f"Starting agent with task: {task}\nModel: {model}")

    # Define available tools according to Ollama's tool format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_directory",
                "description": "Creates a directory and all parent directories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path of the directory to create."
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Writes content to a file, overwriting it if it exists. Creates parent directories if they don't exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path of the file to write."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file."
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "append_file",
                "description": "Appends content to an existing file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path of the file to append to."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to append to the file."
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Reads the content of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path of the file to read."
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_command",
                "description": "Executes a bash command and returns the output (stdout and stderr). Useful for running scripts, tests, or system commands.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute."
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Marks the task as completed. Call this when you have fulfilled the user's request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "A final message summarizing what was done."
                        }
                    },
                    "required": ["message"]
                }
            }
        }
    ]

    system_prompt = """You are an autonomous AI software engineer agent.
You have access to tools that let you read/write files, create directories, and execute terminal commands.
Your job is to accomplish the task given by the user by using these tools.
You can write code, run it to see if it works, and fix errors if it doesn't.
Continue working in a loop until the task is complete.
Once you are confident the task is fully complete, call the `finish` tool.
Always verify your work (e.g. by reading the file you wrote or executing the code you wrote)."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        response_message = chat_with_ollama(messages, model, tools)

        if not response_message:
            print("Failed to get response from model. Exiting.")
            break

        messages.append(response_message)

        if response_message.get("content"):
            print(f"Agent reasoning: {response_message['content']}")

        tool_calls = response_message.get("tool_calls")

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                print(f"Tool Call: {function_name}({json.dumps(arguments)})")

                if function_name == "finish":
                    print(f"\nTask completed! Agent final message: {arguments.get('message')}")
                    return

                # Execute tool
                result = None
                if function_name == "create_directory":
                    result = create_directory(arguments["path"])
                elif function_name == "write_file":
                    result = write_file(arguments["path"], arguments["content"])
                elif function_name == "append_file":
                    result = append_file(arguments["path"], arguments["content"])
                elif function_name == "read_file":
                    result = read_file(arguments["path"])
                elif function_name == "execute_command":
                    result = execute_command(arguments["command"])
                else:
                    result = f"Unknown function {function_name}"

                print(f"Tool Result:\n{result}")

                # Append tool result to messages
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(result)
                })
        else:
            # If the model didn't call a tool and just replied, we prompt it again to either call a tool or finish
            print("No tool call made. Prompting model to continue or finish.")
            messages.append({
                "role": "user",
                "content": "Please continue with the task by calling appropriate tools, or call the 'finish' tool if the task is complete."
            })

    print(f"\nReached maximum iterations ({max_iterations}). Stopping.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hermes-like Agent using Ollama")
    parser.add_argument("task", help="The task for the agent to accomplish")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="The Ollama model to use")

    args = parser.parse_args()
    run_agent(args.task, args.model)
