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


import threading
import queue
import time

# --- Agent Loop ---

def run_agent_worker(task, model, msg_queue, max_iterations=20):
    """Runs the agent loop in a background thread, reporting to msg_queue."""

    def emit(type, content):
        msg_queue.put({"type": type, "content": content})

    emit("log", f"Starting agent with task: {task}\nModel: {model}")
    emit("status", "Initializing...")

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
        emit("log", f"\n--- Iteration {iteration + 1} ---")
        emit("status", f"Thinking (Iter {iteration+1})...")

        response_message = chat_with_ollama(messages, model, tools)

        if not response_message:
            emit("log", "Failed to get response from model. Exiting.")
            emit("status", "Error: Connection Failed")
            emit("done", True)
            return

        messages.append(response_message)

        if response_message.get("content"):
            emit("log", f"Agent reasoning: {response_message['content']}")

        tool_calls = response_message.get("tool_calls")

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                emit("log", f"Tool Call: {function_name}({json.dumps(arguments)})")
                emit("status", f"Executing {function_name}...")

                if function_name == "finish":
                    emit("log", f"\nTask completed! Agent final message: {arguments.get('message')}")
                    emit("status", "Task Completed!")
                    emit("done", True)
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

                emit("log", f"Tool Result:\n{result}")
                # Append tool result to messages
                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": str(result)
                })
        else:
            emit("log", "No tool call made. Prompting model to continue or finish.")
            messages.append({
                "role": "user",
                "content": "Please continue with the task by calling appropriate tools, or call the 'finish' tool if the task is complete."
            })

    emit("log", f"\nReached maximum iterations ({max_iterations}). Stopping.")
    emit("done", True)

def run_agent(task, model=DEFAULT_MODEL, max_iterations=20):
    """CLI fallback wrapper for the agent loop."""
    msg_queue = queue.Queue()
    t = threading.Thread(target=run_agent_worker, args=(task, model, msg_queue, max_iterations), daemon=True)
    t.start()

    while t.is_alive() or not msg_queue.empty():
        try:
            msg = msg_queue.get(timeout=0.1)
            if msg["type"] == "log":
                print(msg["content"])
            elif msg["type"] == "done":
                break
        except queue.Empty:
            continue



# --- UI Integration ---

import customtkinter as ctk

class HermesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hermes Agent UI")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Layout configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar (Status and Settings) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Hermes Agent", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.status_label_title = ctk.CTkLabel(self.sidebar_frame, text="Current Status:", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label_title.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Idle", text_color="#00FF00", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")

        self.model_label = ctk.CTkLabel(self.sidebar_frame, text="Ollama Model:")
        self.model_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["qwen2.5-coder:7b", "llama3:latest", "mistral:latest"])
        self.model_optionemenu.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="n")

        # --- Main Chat/Log Window ---
        self.log_textbox = ctk.CTkTextbox(self, width=250)
        self.log_textbox.grid(row=0, column=1, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.log_textbox.insert("0.0", "Welcome to Hermes Agent.\nEnter a task below and press Start.\n\n")
        self.log_textbox.configure(state="disabled")

        # --- Input Area ---
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.task_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter your task here...")
        self.task_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")
        self.task_entry.bind("<Return>", lambda event: self.start_task())

        self.start_button = ctk.CTkButton(self.input_frame, text="Start Task", command=self.start_task)
        self.start_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        # State variables
        self.msg_queue = queue.Queue()
        self.is_running = False

    def update_status(self, text, color="#00FF00"):
        self.status_label.configure(text=text, text_color=color)

    def append_log(self, text):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_task(self):
        if self.is_running:
            return

        task = self.task_entry.get()
        if not task.strip():
            return

        model = self.model_optionemenu.get()

        self.append_log(f"==================================================")
        self.append_log(f"New Task: {task}")
        self.task_entry.delete(0, 'end')
        self.is_running = True
        self.start_button.configure(state="disabled")

        # Start worker thread
        t = threading.Thread(target=run_agent_worker, args=(task, model, self.msg_queue, 20), daemon=True)
        t.start()

        # Start polling the queue
        self.poll_queue()

    def poll_queue(self):
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                if msg["type"] == "log":
                    self.append_log(msg["content"])
                elif msg["type"] == "status":
                    self.update_status(msg["content"])
                elif msg["type"] == "done":
                    self.is_running = False
                    self.start_button.configure(state="normal")
                    self.update_status("Idle", "#00FF00")
        except queue.Empty:
            pass

        if self.is_running:
            self.after(100, self.poll_queue) # Poll again in 100ms


if __name__ == "__main__":
    import sys
    # If run with arguments, fallback to CLI mode
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser(description="Hermes-like Agent using Ollama")
        parser.add_argument("task", help="The task for the agent to accomplish")
        parser.add_argument("--model", default=DEFAULT_MODEL, help="The Ollama model to use")

        args = parser.parse_args()
        run_agent(args.task, args.model)
    else:
        # Launch GUI
        app = HermesApp()
        app.mainloop()
