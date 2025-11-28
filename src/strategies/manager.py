import os
import json
from typing import Dict, List, Optional
from src.config.settings import settings

class StrategyManager:
    def __init__(self, filepath: str = str(settings.USER_STRATEGIES_PATH)):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the storage file exists, create if not."""
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump({}, f)

    def _load_data(self) -> Dict[str, str]:
        """Load strategies from JSON file."""
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_data(self, data: Dict[str, str]):
        """Save strategies to JSON file using atomic write."""
        temp_filepath = f"{self.filepath}.tmp"
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_filepath, self.filepath)
        except Exception as e:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            raise e

    def save(self, name: str, code: str):
        """Save a strategy by name."""
        if not name or len(name) > 100:
            raise ValueError("Strategy name must be 1-100 characters.")
        if len(code) > 1_000_000: # 1MB limit
            raise ValueError("Strategy code exceeds size limit (1MB).")

        data = self._load_data()
        data[name] = code
        self._save_data(data)

    def get(self, name: str) -> Optional[str]:
        """Retrieve a strategy's code by name."""
        data = self._load_data()
        return data.get(name)

    def delete(self, name: str):
        """Delete a strategy by name."""
        data = self._load_data()
        if name in data:
            del data[name]
            self._save_data(data)

    def list_all(self) -> List[str]:
        """List all stored strategy names."""
        data = self._load_data()
        return list(data.keys())
