import json
from scipy.optimize import minimize, LinearConstraint
import numpy as np
from functools import partial


def read_and_sort_ingredients(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    sorted_data = dict(sorted(data.items()))
    with open(path, 'w', encoding='utf-8-sig') as f:
        json.dump(sorted_data, f, indent=4, ensure_ascii=False)
    return sorted_data

def find_optimized_recipe(ingredients, orig_recipe, nutrients, num_portions, consider_size):
    recipe_vector = np.asarray(list(orig_recipe.values()), dtype=float)
    cal_constr = get_nutrients_constraint('cal', ingredients, orig_recipe, nutrients, num_portions)
    prot_constr = get_nutrients_constraint('prot', ingredients, orig_recipe, nutrients, num_portions)
    constraints = [cal_constr, prot_constr]
    sol = solve_optimization(recipe_vector, constraints)
    if consider_size:
        for index, ingredient in enumerate(orig_recipe):
            if ingredient in consider_size:
                size = ingredients[ingredient]['size']
                amount = round(sol[index]/size) * size
                constraints.append(get_mass_constraint(ingredient, orig_recipe, amount))
        sol = solve_optimization(recipe_vector, constraints)
    sol = np.round(sol)
    cal = round(np.dot(cal_constr.A, sol)[0]/num_portions)
    prot = round(np.dot(prot_constr.A, sol)[0]/num_portions)
    print_output(orig_recipe, sol, cal, prot, num_portions)

def get_nutrients_constraint(type, ingredients, orig_recipe, nutrients, num_portions):
    a = []
    for ingredient in orig_recipe:
        a.append(ingredients[ingredient][f'{type}_d']/100)
    a = np.array(a)

    eps = nutrients[f'delta_{type}']
    b = nutrients[type]*num_portions

    return LinearConstraint(A=a, lb=b-eps, ub=b+eps)

def solve_optimization(recipe_vector, constraints):
    result = minimize(
        partial(distance, recipe=recipe_vector), 
        recipe_vector, 
        method='SLSQP', 
        constraints=constraints
    )
    if not result.success:
        raise Exception(f'Etwas ist numerisch schiefgegangen: {result.message}')
    return result.x

def distance(x, recipe):
    direction_norm = recipe / np.linalg.norm(recipe)
    projection = np.dot(x, direction_norm) * direction_norm
    distance = np.linalg.norm(x - projection)
    return distance

def get_mass_constraint(constr_ingredient, orig_recipe, amount):
    a = []
    for ingredient in orig_recipe:
        if ingredient == constr_ingredient:
            a.append(1)
        else:
            a.append(0)
    a = np.array(a)
    return LinearConstraint(A=a, lb=amount, ub=amount)

def print_output(orig_recipe, sol, cal, prot, num_portions):
    # print('')
    # print(f'Nährwerte pro Portion:')
    # print(f'Kalorien: {cal}')
    # print(f'Proteine: {prot}')
    print('')
    print(f'Pro Portion:    {cal}kcal   {prot}g Protein')
    print('')
    print(f'Neues Rezept für {num_portions} Portionen:')
    print('')
    print('Zutat                Menge[g]       Originalrezept[g]: ')
    print('---------------------------------------------------------------------')
    projection = calc_projection(orig_recipe, sol)
    for index, ingredient in enumerate(orig_recipe):
        print("{:<20} {:<14} {:<20}".format(ingredient, sol[index], projection[index]))
        # print(f"{ingredient}: {sol[index]} (orig: {recipe_vector[index]*num_portions})")
    print('---------------------------------------------------------------------')
    print(f'Maximale Abweichung einer Zutat vom Originalrezept: {round(np.max(sol/num_portions-projection/num_portions))}')
    print('')

def calc_projection(orig_recipe, solution):
    recipe_vector = np.asarray(list(orig_recipe.values()), dtype=float)
    direction_norm = recipe_vector / np.linalg.norm(recipe_vector)
    projection = np.dot(solution, direction_norm) * direction_norm
    return np.round(projection)

recipe = {
    'Haferflocken': 450,
    'Skyr': 1500,
    'Apfel': 413,
    'Milch': 850,
    'Mandeln': 200,
    'Honig': 320
}

# recipe = {
#     'Zwiebel': 170,
#     'Paprika': 154,
#     'Kartoffeln': 300,
#     'Linsen (rot)': 113,
#     'Kokosmilch light': 150
# }

# recipe = {
#     'Hähnchenbrustfilet': 700,
#     'Basmati-Reis': 380,
#     'Brokkoli': 300,
#     'Kokosmilch': 400,
#     'Olivenöl': 200,
# }

# recipe = {
#     'Brot': 165,
#     'Körniger Frischkäse': 150,
#     'Milch': 200,
#     'Isolat': 25
# }


nutrients = {
    'cal': 930,
    'prot': 60,
    'delta_cal': 50,
    'delta_prot': 10
} 

num_portions = 6

consider_size = ['Skyr']

ingredients = read_and_sort_ingredients('ingredients.json')

find_optimized_recipe(ingredients, recipe, nutrients, num_portions, consider_size)