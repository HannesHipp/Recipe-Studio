import json
import os
import shutil


class DataManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.db = {}
        self.load_data()

    def load_data(self):
        """Loads, lowercases, sorts, and maintains the ingredients JSON."""
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            # Ensure keys are lowercase for consistent lookup
            lowercase_data = {key.lower(): value for key,
                              value in data.items()}
            # Sort data
            self.db = dict(sorted(lowercase_data.items()))
            # Save back to ensure formatting/consistency (optional, but requested in original)
            self.save_data()
        except FileNotFoundError:
            print(f"WARNING: '{self.filepath}' not found. Creating empty DB.")
            self.db = {}
        except json.JSONDecodeError:
            print(
                f"WARNING: Could not decode JSON from '{self.filepath}'. Creating empty DB.")
            self.db = {}

    def save_data(self):
        """Persists the current state of self.db to disk."""
        try:
            # Create backup before writing
            if os.path.exists(self.filepath):
                shutil.copy(self.filepath, f"{self.filepath}.bak")

            with open(self.filepath, 'w', encoding='utf-8-sig') as f:
                json.dump(self.db, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"ERROR: Failed to save data: {e}")

    def get_all_ingredients(self):
        """Returns the raw dictionary."""
        return self.db

    def get_ingredient(self, name):
        """Safe lookup by name (case-insensitive)."""
        if not name:
            return None
        return self.db.get(name.lower())

    def update_database(self, new_data_list):
        """
        Updates the internal DB from a list of dicts (e.g. from DataTable).
        Format: [{'name': 'Chicken', 'cal_d': 100, ...}, ...]
        """
        new_db = {}
        for item in new_data_list:
            name = item.get('name')
            if name:
                # Remove 'name' key from the values dict
                values = {k: v for k, v in item.items() if k != 'name'}
                new_db[name.lower()] = values

        self.db = dict(sorted(new_db.items()))
        self.save_data()

    def get_table_data(self):
        """Returns list of dicts suitable for Dash DataTable."""
        return [{'name': key, **value} for key, value in self.db.items()]
