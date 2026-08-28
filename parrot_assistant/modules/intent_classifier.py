import re

class IntentClassifier:
    """
    Lightweight rule-based intent classifier.
    Categorizes the user request before passing it to an LLM.
    """

    INTENTS = {
        "SYS_CMD": [r"(?i)\b(?:open|close|launch|start|kill)\b", r"(?i)\b(?:file|directory|folder)\b"],
        "SEARCH": [r"(?i)\b(?:search|lookup|find|who is|what is the weather)\b"],
        "SHELL": [r"(?i)\b(?:run|execute|bash|script|command)\b"],
        "CHAT": [] # Fallback
    }

    @staticmethod
    def classify(query: str) -> str:
        """Classifies the query into one of the predefined intents."""
        for intent, patterns in IntentClassifier.INTENTS.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return intent
        return "CHAT"
