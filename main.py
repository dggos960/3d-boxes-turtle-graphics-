import json
import os
import subprocess
import threading
import customtkinter as ctk
from llama_cpp import Llama

# --- CONFIGURATION ---
MODEL_PATH = "/home/dggos/llm-models/qwen2.5-3b-instruct-q8_0.gguf"

# Set up UI Theme
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")

# --- DEFINE DESKTOP TOOLS (FUNCTIONS) ---
def open_browser(url: str = "https://www.google.com"):
    """Opens the default web browser to a specific URL."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        if os.name == 'posix':
            subprocess.Popen(['xdg-open', url])
        elif os.name == 'nt':
            os.startfile(url)
        return f"Successfully opened browser to {url}"
    except Exception as e:
        return f"Failed to open browser: {str(e)}"

def list_files(directory_path: str = "."):
    """Lists all files and folders in the specified directory path."""
    try:
        files = os.listdir(directory_path)
        return json.dumps(files)
    except Exception as e:
        return f"Error reading directory: {str(e)}"

available_tools = {
    "open_browser": open_browser,
    "list_files": list_files
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "open_browser",
            "description": "Open the web browser to a website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The website URL to open."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a local directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "The folder path to check. Defaults to current directory."}
                },
            },
        },
    }
]


class DesktopAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("GGUF Desktop Assistant")
        self.geometry("850x650")
        self.minsize(600, 500)

        # Configure grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- SIDEBAR FRAME ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AI Agent 🤖", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Loading Model...", text_color="orange", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=1, column=0, padx=20, pady=10)

        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Dark", "Light"], command=self.change_appearance_mode)
        self.appearance_mode_menu.grid(row=5, column=0, padx=20, pady=20, sticky="s")

        # --- MAIN CHAT AREA ---
        self.chat_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Chat History Text Box
        self.chat_box = ctk.CTkTextbox(self.chat_frame, wrap="word", font=ctk.CTkFont(size=14))
        self.chat_box.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        self.chat_box.configure(state="disabled")

        # Bottom Input Area Frame
        self.input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.user_input_field = ctk.CTkEntry(self.input_frame, placeholder_text="Ask your assistant to do something...", height=45, font=ctk.CTkFont(size=14))
        self.input_field = self.user_input_field
        self.input_field.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_field.bind("<Return>", self.on_enter_press)

        self.send_button = ctk.CTkButton(self.input_frame, text="Send", width=100, height=45, command=self.process_user_input)
        self.send_button.grid(row=0, column=1, sticky="e")

        # Initialize LLM in a background thread so UI doesn't freeze on startup
        self.messages = [{"role": "system", "content": "You are a helpful desktop assistant with access to tools to control the computer, browse the web, and manage files."}]
        self.llm = None
        threading.Thread(target=self.init_llm, daemon=True).start()

    def init_llm(self):
        try:
            self.llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=4096,
                verbose=False
            )
            self.status_label.configure(text="Status: Ready ✅", text_color="green")
            self.append_to_chat("System", "Assistant is loaded and ready. How can I help you control your PC today?\n")
        except Exception as e:
            self.status_label.configure(text="Status: Error ❌", text_color="red")
            self.append_to_chat("System", f"Failed to load model: {str(e)}\n")

    def append_to_chat(self, sender, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{sender}: {text}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def on_enter_press(self, event):
        self.process_user_input()

    def process_user_input(self):
        if not self.llm:
            self.append_to_chat("System", "Please wait, model is still loading...\n")
            return

        user_text = self.input_field.get().strip()
        if not user_text:
            return

        self.input_field.delete(0, "end")
        self.append_to_chat("You", user_text)

        # Run inference in a background thread to keep the UI smooth and responsive
        threading.Thread(target=self.run_agent_loop, args=(user_text,), daemon=True).start()

    def run_agent_loop(self, user_text):
        try:
            self.messages.append({"role": "user", "content": user_text})

            response = self.llm.create_chat_completion(
                messages=self.messages,
                tools=tools_schema,
                tool_choice="auto"
            )

            response_message = response["choices"][0]["message"]
            self.messages.append(response_message)

            if response_message.get("tool_calls"):
                for tool_call in response_message["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])

                    self.append_to_chat("Agent Action", f"Executing `{func_name}` with args {func_args}...")

                    if func_name in available_tools:
                        tool_output = available_tools[func_name](**func_args)
                    else:
                        tool_output = f"Error: Tool {func_name} not found."

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": func_name,
                        "content": str(tool_output)
                    })

                second_response = self.llm.create_chat_completion(messages=self.messages)
                final_reply = second_response["choices"][0]["message"]["content"]
                self.messages.append(second_response["choices"][0]["message"])

                self.append_to_chat("AI", final_reply + "\n")
            else:
                self.append_to_chat("AI", response_message["content"] + "\n")

        except Exception as e:
            self.append_to_chat("System", f"An error occurred: {str(e)}\n")


if __name__ == "__main__":
    app = DesktopAssistantApp()
    app.mainloop()
