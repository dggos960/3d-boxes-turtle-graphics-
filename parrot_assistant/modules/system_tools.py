import subprocess
import os
import psutil

class SystemTools:
    """
    Safe Linux file management, application control, process inspection, and bash execution.
    """
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    def run_bash_script(self, script_content: str) -> str:
        """Securely run a bash script and return its output."""
        try:
            # We save it to a temporary script in the workspace to run it
            script_path = os.path.join(self.workspace_dir, "temp_script.sh")
            with open(script_path, "w") as f:
                f.write(script_content)

            os.chmod(script_path, 0o755)

            process = subprocess.Popen(
                ["/bin/bash", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=10)

            if process.returncode != 0:
                return f"Error executing script:\n{stderr}"
            return stdout
        except Exception as e:
            return f"Exception executing script: {e}"

    def open_application(self, app_name: str) -> str:
        """Opens a Linux GUI application via standard process handles."""
        try:
            # Simple approach: use nohup or standard subproccess to launch detatched
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Successfully opened {app_name}."
        except Exception as e:
            return f"Failed to open {app_name}. Error: {e}"

    def close_application(self, app_name: str) -> str:
        """Closes a running application."""
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == app_name:
                try:
                    proc.kill()
                    killed += 1
                except psutil.AccessDenied:
                    pass
        if killed > 0:
            return f"Successfully closed {killed} instances of {app_name}."
        return f"Could not find running instances of {app_name}."

    def list_directory(self, path: str = None) -> str:
        target_dir = path if path else self.workspace_dir
        try:
            items = os.listdir(target_dir)
            return "\n".join(items) if items else "Directory is empty."
        except Exception as e:
            return f"Error listing directory: {e}"
