"""Fixed choices used across the app (muscles, meals, activities, ...).

Units: body and lifting weight in pounds, height in inches, distance in
miles. Food amounts are stored in grams because nutrition data is published
per 100 g; the UI shows servings/ounces.
"""

# Muscle key -> display label. Fine-grained so the body map can color
# individual muscles.
MUSCLES: dict[str, str] = {
    "chest": "Chest",
    "front_delts": "Front Delts",
    "side_delts": "Side Delts",
    "rear_delts": "Rear Delts",
    "lats": "Lats",
    "upper_back": "Upper Back & Traps",
    "lower_back": "Lower Back",
    "biceps": "Biceps",
    "triceps": "Triceps",
    "forearms": "Forearms",
    "abs": "Abs",
    "obliques": "Obliques",
    "glutes": "Glutes",
    "quads": "Quads",
    "hamstrings": "Hamstrings",
    "adductors": "Adductors",
    "calves": "Calves",
}

# Coarse regions for summaries ("Legs: 18 sets this week").
MUSCLE_REGIONS: dict[str, list[str]] = {
    "Chest": ["chest"],
    "Back": ["lats", "upper_back", "lower_back"],
    "Shoulders": ["front_delts", "side_delts", "rear_delts"],
    "Arms": ["biceps", "triceps", "forearms"],
    "Core": ["abs", "obliques"],
    "Legs": ["glutes", "quads", "hamstrings", "adductors", "calves"],
}

EQUIPMENT: dict[str, str] = {
    "barbell": "Barbell",
    "dumbbell": "Dumbbell",
    "machine": "Machine",
    "cable": "Cable",
    "bodyweight": "Bodyweight",
    "kettlebell": "Kettlebell",
    "band": "Band",
    "other": "Other",
}

# Cardio activity -> (label, MET value). MET values are typical moderate
# efforts from the Compendium of Physical Activities; used to estimate
# calories burned when the user doesn't enter them.
CARDIO_ACTIVITIES: dict[str, tuple[str, float]] = {
    "walk": ("Walking", 3.5),
    "run": ("Running", 9.8),
    "cycle": ("Cycling", 7.5),
    "row": ("Rowing", 7.0),
    "elliptical": ("Elliptical", 5.0),
    "stairs": ("Stair Climber", 9.0),
    "swim": ("Swimming", 7.0),
    "other": ("Other", 6.0),
}

MEALS: dict[str, str] = {
    "breakfast": "Breakfast",
    "lunch": "Lunch",
    "dinner": "Dinner",
    "snack": "Snacks",
}

FOOD_SOURCES: dict[str, str] = {
    "usda": "USDA FoodData Central",
    "off": "Open Food Facts",
    "custom": "Custom",
    "ai": "AI estimate",
}

SEXES: dict[str, str] = {"male": "Male", "female": "Female"}

# Activity level -> (label, TDEE multiplier)
ACTIVITY_LEVELS: dict[str, tuple[str, float]] = {
    "sedentary": ("Sedentary (desk job, little exercise)", 1.2),
    "light": ("Light (exercise 1-3 days/week)", 1.375),
    "moderate": ("Moderate (exercise 3-5 days/week)", 1.55),
    "active": ("Active (exercise 6-7 days/week)", 1.725),
    "very_active": ("Very active (hard training + physical job)", 1.9),
}

GOALS: dict[str, str] = {
    "cut": "Lose fat",
    "maintain": "Maintain",
    "bulk": "Build muscle",
}

CHAT_ROLES = ("user", "assistant", "tool")
