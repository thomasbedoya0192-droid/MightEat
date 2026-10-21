# Constantes para cálculo de metas
GOAL_LOSE_WEIGHT_DEFICIT = 0.15  # 15% caloric deficit
GOAL_LOSE_FAT_DEFICIT = 0.18    # 15-20% caloric deficit with high protein
GOAL_GAIN_WEIGHT_SURPLUS = 0.10  # 10-15% caloric surplus
GOAL_MAINTAIN = 1.0  # Maintenance

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}

MIN_CALORIES_FLOOR = 1200  # Calories floor recommendation


def calc_bmr(sex, weight_kg, height_cm, age):
    """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
    
    Args:
        sex: "male" or "female"
        weight_kg: weight in kilograms
        height_cm: height in centimeters
        age: age in years
    
    Returns:
        BMR in kcal/day
    """
    if sex.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return bmr


def calc_tdee(bmr, activity_level):
    """Calculate Total Daily Energy Expenditure.
    
    Args:
        bmr: Basal Metabolic Rate from calc_bmr()
        activity_level: one of "sedentary", "light", "moderate", "active"
    
    Returns:
        TDEE in kcal/day
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.2)
    return bmr * multiplier


def calc_targets(user):
    """Calculate nutritional targets based on user profile and goal.
    
    Args:
        user: dict with user profile (age, sex, weight_kg, height_cm, activity_level, goal)
    
    Returns:
        dict with kcal_goal and macro targets in grams
    """
    bmr = calc_bmr(user["sex"], user["weight_kg"], user["height_cm"], user["age"])
    tdee = calc_tdee(bmr, user["activity_level"])
    
    goal = user["goal"].lower()
    weight_kg = user["weight_kg"]
    
    if goal == "lose_weight":
        kcal_goal = tdee * (1 - GOAL_LOSE_WEIGHT_DEFICIT)
        protein_grams = weight_kg * 1.5  # Moderate protein for weight loss
    elif goal == "lose_fat":
        kcal_goal = tdee * (1 - GOAL_LOSE_FAT_DEFICIT)
        protein_grams = weight_kg * 2.0  # High protein for fat loss
    elif goal == "gain_weight":
        kcal_goal = tdee * (1 + GOAL_GAIN_WEIGHT_SURPLUS)
        protein_grams = weight_kg * 1.5  # Moderate protein for weight gain
    else:  # maintain
        kcal_goal = tdee
        protein_grams = weight_kg * 1.2  # Maintenance protein
    
    # Apply minimum calorie floor
    kcal_goal = max(kcal_goal, MIN_CALORIES_FLOOR)
    
    # Calculate other macros based on protein and standard ratios
    # 4 kcal/g for carbs and protein, 9 kcal/g for fat
    remaining_kcal = kcal_goal - (protein_grams * 4)
    fat_grams = remaining_kcal / 9 / 2.5  # Rough estimate, adjust as needed
    carbs_grams = (remaining_kcal - (fat_grams * 9)) / 4
    fiber_grams = carbs_grams * 0.25  # Rough fiber estimate
    
    return {
        "kcal_goal": round(kcal_goal, 1),
        "protein_grams": round(protein_grams, 1),
        "carbs_grams": round(carbs_grams, 1),
        "fat_grams": round(fat_grams, 1),
        "fiber_grams": round(fiber_grams, 1),
    }