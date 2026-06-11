import json
import os
import shutil


class RecipeManager:
    def __init__(self, filepath='recipes.json'):
        self.filepath = filepath
        self.recipes = {}
        self.load_recipes()

    def load_recipes(self):
        """Loads recipes from JSON file."""
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                self.recipes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(
                f"WARNING: Could not load recipes from '{self.filepath}'. creating empty.")
            self.recipes = {}

    def save_recipes(self):
        """Persists recipes to JSON."""
        try:
            # Backup
            if os.path.exists(self.filepath):
                shutil.copy(self.filepath, f"{self.filepath}.bak")

            with open(self.filepath, 'w', encoding='utf-8-sig') as f:
                json.dump(self.recipes, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"ERROR: Failed to save recipes: {e}")

    def get_all_recipes(self):
        return self.recipes

    def get_recipe(self, recipe_id):
        return self.recipes.get(recipe_id)

    def add_recipe(self, recipe_id, data):
        self.recipes[recipe_id] = data
        self.save_recipes()

    def delete_recipe(self, recipe_id):
        if recipe_id in self.recipes:
            del self.recipes[recipe_id]
            self.save_recipes()
