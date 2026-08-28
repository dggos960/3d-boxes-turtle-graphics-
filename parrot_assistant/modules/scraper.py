from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests

class WebScraper:
    """
    Web Search using DuckDuckGo and BeautifulSoup for dynamic data fetching.
    """
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 3) -> str:
        """Performs a web search and returns formatted results."""
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            if not results:
                return "No search results found."

            formatted = []
            for r in results:
                formatted.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}")
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Search error: {e}"

    def extract_webpage(self, url: str) -> str:
        """Extracts text content from a given webpage."""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract paragraph text to limit token usage
                paragraphs = soup.find_all('p')
                text = "\n".join([p.get_text() for p in paragraphs])
                # Truncate to reasonable length for LLM
                return text[:2000] + ("..." if len(text) > 2000 else "")
            return f"Failed to fetch webpage. HTTP {response.status_code}"
        except Exception as e:
            return f"Error extracting webpage: {e}"
