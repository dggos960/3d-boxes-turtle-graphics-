import customtkinter as ctk
import threading
import time
import queue

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SearchApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Global Search Tool - Mock UI")
        self.geometry("900x700")

        self.queue = queue.Queue()

        # --- Grid Layout Configuration ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Sidebar (Inputs) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Search Inputs", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.entry_name = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Name")
        self.entry_name.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.entry_phone = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Phone Number")
        self.entry_phone.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.entry_location = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Location")
        self.entry_location.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.entry_profession = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Profession / Academics")
        self.entry_profession.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.search_button = ctk.CTkButton(self.sidebar_frame, text="Start Search", command=self.start_search)
        self.search_button.grid(row=5, column=0, padx=20, pady=20, sticky="ew")

        # --- Top Output Window ---
        self.output_label = ctk.CTkLabel(self, text="Search Results", font=ctk.CTkFont(size=16, weight="bold"))
        self.output_label.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="w")

        self.output_textbox = ctk.CTkTextbox(self, height=250)
        self.output_textbox.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.output_textbox.insert("0.0", "Results will appear here...\n\nNote: For safety and privacy reasons, this tool does NOT perform actual scraping or data gathering.\n")
        self.output_textbox.configure(state="disabled")

        # --- Bottom Logs Window ---
        self.logs_label = ctk.CTkLabel(self, text="Live Logs", font=ctk.CTkFont(size=16, weight="bold"))
        self.logs_label.grid(row=2, column=1, padx=20, pady=(10, 0), sticky="sw")

        self.logs_textbox = ctk.CTkTextbox(self, height=150)
        self.logs_textbox.grid(row=3, column=1, padx=20, pady=(5, 10), sticky="nsew")
        self.logs_textbox.insert("0.0", "System initialized.\nReady to process requests.\n")
        self.logs_textbox.configure(state="disabled")

        # --- Progress Bar ---
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=4, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")
        self.progress_bar.set(0)

        # Start queue processing
        self.check_queue()

    def log(self, message):
        self.queue.put(("log", message))

    def result(self, message):
        self.queue.put(("result", message))

    def update_progress(self, value):
        self.queue.put(("progress", value))

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "log":
                    self.logs_textbox.configure(state="normal")
                    self.logs_textbox.insert("end", f"> {data}\n")
                    self.logs_textbox.see("end")
                    self.logs_textbox.configure(state="disabled")
                elif msg_type == "result":
                    self.output_textbox.configure(state="normal")
                    self.output_textbox.insert("end", f"{data}\n")
                    self.output_textbox.see("end")
                    self.output_textbox.configure(state="disabled")
                elif msg_type == "progress":
                    self.progress_bar.set(data)
                elif msg_type == "finish":
                    self.search_button.configure(state="normal")
                    self.progress_bar.stop()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def start_search(self):
        # Disable button to prevent multiple searches
        self.search_button.configure(state="disabled")

        # Clear previous outputs
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("0.0", "end")
        self.output_textbox.insert("0.0", "Note: Actual data gathering is disabled for privacy and safety.\n\n")
        self.output_textbox.configure(state="disabled")

        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("0.0", "end")
        self.logs_textbox.configure(state="disabled")

        # Reset progress bar
        self.progress_bar.set(0)
        self.progress_bar.start()

        # Gather inputs
        inputs = {
            "name": self.entry_name.get(),
            "phone": self.entry_phone.get(),
            "location": self.entry_location.get(),
            "profession": self.entry_profession.get()
        }

        # Start background thread
        threading.Thread(target=self.mock_search_worker, args=(inputs,), daemon=True).start()

    def mock_search_worker(self, inputs):
        self.log("Starting mock search sequence...")
        time.sleep(1)

        self.log(f"Inputs received: {', '.join([f'{k}={v}' for k, v in inputs.items() if v])}")
        time.sleep(1.5)

        self.log("Connecting to mock database endpoints...")
        self.update_progress(0.2)
        time.sleep(2)

        self.log("Querying public directories (MOCK)...")
        self.update_progress(0.4)
        time.sleep(2)

        self.log("Parsing simulated results...")
        self.update_progress(0.6)
        time.sleep(2)

        self.log("Cross-referencing mock data...")
        self.update_progress(0.8)
        time.sleep(1.5)

        self.log("Search complete.")
        self.update_progress(1.0)

        self.result("--- MOCK RESULTS ---")
        self.result("No real data was retrieved.")
        self.result("To implement actual search capabilities, you would need to integrate with legitimate APIs (e.g., Clearbit, Pipl, or official social media APIs) in compliance with their Terms of Service and applicable privacy laws (such as GDPR/CCPA).")

        self.queue.put(("finish", None))

if __name__ == "__main__":
    app = SearchApp()
    app.mainloop()
