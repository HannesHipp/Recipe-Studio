from typing import List, Dict, Tuple, Any
import numpy as np
from scipy.optimize import minimize, LinearConstraint
from functools import partial
import itertools


def get_nutrients_constraint(type_key, ingredient_db, flattened_vars, targets):
    """
    Constraint: Sum( (Amount_i / 100) * Nutrient_i / Portions_i ) = Daily_Target
    """
    coeffs = []

    # We need to sum contributions from ALL recipes.
    # Contribution of 1g of ingredient X in Recipe R = (Nutrient_X/100) / Portions_R

    db_key = f"{type_key}_d"

    for var in flattened_vars:
        name = var['name']
        portions = max(1.0, float(var.get('portions', 1.0)))

        # Nutrient density per gram
        # (val per 100g) / 100 -> val per 1g
        nut_per_g = ingredient_db.get(name, {}).get(db_key, 0) / 100.0

        coeff = nut_per_g / portions
        coeffs.append(coeff)

    a = np.array(coeffs)
    target = targets[type_key]
    slack = targets.get(f'delta_{type_key}', 0)

    return LinearConstraint(A=a, lb=target - slack, ub=target + slack)


def get_recipe_calorie_constraint(target_indices, ingredient_db, flattened_vars, limit_val, is_min=True):
    """
    Constraint: Sum(Amount_i * Cal_Density_i / 100 / Portions_i) >= Min (or <= Max) per recipe
    """
    num_vars = len(flattened_vars)
    a = np.zeros(num_vars)

    # We sum calories ONLY for the specific indices belonging to this recipe
    for idx in target_indices:
        var = flattened_vars[idx]
        name = var['name']
        portions = max(1.0, float(var.get('portions', 1.0)))

        # Calories per gram of ingredient * 1/Portions
        cal_per_g = ingredient_db.get(name, {}).get('cal_d', 0) / 100.0

        a[idx] = cal_per_g / portions

    # Minimize: Amount >= Min  =>  Amount - Min >= 0  => -Amount <= -Min ❌
    # LinearConstraint: lb <= A*x <= ub

    if is_min:
        return LinearConstraint(A=a, lb=limit_val, ub=np.inf)
    else:
        return LinearConstraint(A=a, lb=-np.inf, ub=limit_val)


def get_mass_constraint(target_index, num_vars, amount):
    a = np.zeros(num_vars)
    a[target_index] = 1.0
    return LinearConstraint(A=a, lb=amount, ub=amount)


def objective_function(x, original_vectors_map, weights):
    """
    Minimize distance to the PROJECTED line for each recipe independently.
    Cost = Sum ( || x_R - proj_R(x_R) ||^2 )

    x: Global vector
    original_vectors_map: { recipe_id: {'indices': [0, 1...], 'vector': np.array([...])} }
    weights: Global weights vector
    """
    total_cost = 0.0

    for r_id, data in original_vectors_map.items():
        indices = data['indices']
        r_vec = data['vector']  # The "Direction"

        # Extract sub-vector for this recipe
        x_sub = x[indices]
        w_sub = weights[indices]

        # Norm of original recipe (direction)
        r_norm_val = np.linalg.norm(r_vec)

        if r_norm_val < 1e-9:
            # If original recipe was all zeros, just minimize magnitude of x?
            # Or assume direction is undefined.
            # Lets minimize magnitude of weighted x
            cost = np.sum(w_sub * (x_sub**2))
            total_cost += cost
            continue

        # Projection of x_sub onto r_vec
        # proj = (x . r / |r|^2) * r
        scalar_proj = np.dot(x_sub, r_vec) / (r_norm_val**2)

        # We enforce positive scaling only? (You can't have negative recipe)
        # If scalar_proj < 0, we imply x is opposing r. Project to 0.
        scalar_proj = max(0.0, scalar_proj)

        projection = scalar_proj * r_vec

        # Weighted Squared Euclidean Distance
        # || sqrt(W) * (x - proj) ||^2
        # = Sum( w_i * (x_i - proj_i)^2 )

        diff = x_sub - projection
        weighted_sq_diff = w_sub * (diff**2)
        total_cost += np.sum(weighted_sq_diff)

    return total_cost


def solve_global_plan(recipes: List[Dict], ingredient_db: Dict, targets: Dict) -> Tuple[Dict, Dict]:
    """
    Globally optimizes recipes.
    Assumes recipes have 'portions' field (default 1).
    """

    # 1. Flatten Variables
    # We need to map global indices to recipes
    flat_vars = []
    x0_list = []
    weights_list = []

    # For constructing the objective map
    recipe_map = {}  # r_id -> {indices: [], vector: []}

    global_idx = 0

    mass_locks = []
    pkg_locks = []

    for r in recipes:
        r_id = r.get('id')
        portions = float(r.get('portions', 1))
        ingredients = r.get('ingredients', [])

        # Temp lists for this recipe to build vector later
        r_indices = []
        r_amounts = []

        for i, ing in enumerate(ingredients):
            name = ing.get('name', '').lower()
            if not name or name not in ingredient_db:
                continue

            amount = float(ing.get('amount') or 0)
            prio = float(ing.get('priority') or 1)
            is_locked = ing.get('locked', False)
            is_pkg_locked = ing.get('pkg_locked', False)

            flat_vars.append({
                'name': name,
                'recipe_id': r_id,
                'row_index': i,
                'portions': portions
            })

            x0_list.append(amount)
            weights_list.append(prio)

            r_indices.append(global_idx)
            r_amounts.append(amount)

            if is_locked:
                mass_locks.append((global_idx, amount))

            if is_pkg_locked:
                p_size = ingredient_db[name].get('pack_size', 0)
                if p_size > 0:
                    pkg_locks.append((global_idx, p_size))

            global_idx += 1

        # Store recipe vector for projection
        recipe_map[r_id] = {
            'indices': r_indices,
            'vector': np.array(r_amounts)
        }

    if not flat_vars:
        return {}, {'error': 'No valid ingredients found'}

    x0 = np.array(x0_list)
    w = np.array(weights_list)
    num_vars = len(x0)

    # 2. Constraints
    constraints = []

    # Nutrient Constraints (Scaled by portions)
    if 'cal' in targets:
        constraints.append(get_nutrients_constraint(
            'cal', ingredient_db, flat_vars, targets))
    if 'prot' in targets:
        constraints.append(get_nutrients_constraint(
            'prot', ingredient_db, flat_vars, targets))

    # Mass Locks
    for idx, val in mass_locks:
        constraints.append(get_mass_constraint(idx, num_vars, val))

    # Recipe Calorie Limits (Min/Max per Recipe)
    min_meal_cal = targets.get('min_meal_cal', 300)
    max_meal_cal = targets.get('max_meal_cal', 1000)

    for r_id, data in recipe_map.items():
        indices = data['indices']
        if not indices:
            continue

        # Add Min Cal Constraint
        constraints.append(get_recipe_calorie_constraint(
            indices, ingredient_db, flat_vars, min_meal_cal, is_min=True))

        # Add Max Cal Constraint
        constraints.append(get_recipe_calorie_constraint(
            indices, ingredient_db, flat_vars, max_meal_cal, is_min=False))

    # 3. Solve (Continuous)

    # To pass extra args to objective, we use partial
    obj_fun = partial(objective_function,
                      original_vectors_map=recipe_map, weights=w)

    res = minimize(
        obj_fun,
        x0,
        method='SLSQP',
        constraints=constraints,
        bounds=[(0, None) for _ in range(num_vars)]
    )

    final_sol = None

    if res.success:
        final_sol = res.x
    else:
        # If fail, we might return None or best effort
        return None, {'error': f'Optimization failed: {res.message}'}

    # 4. Discrete (Package) Logic - Simplified for now
    # We can perform the same branching strategy as before.
    # For brevity in this implementation, I will assume Continuous first.
    # If the user wants package locking, we reuse the branching logic.

    if pkg_locks and final_sol is not None:
        # Use Branching
        branch_opts = []
        # Simple limit logic
        relevant_locks = pkg_locks[:5]  # Max 5 branches to save time

        for idx, p_size in relevant_locks:
            val = final_sol[idx]
            f = np.floor(val/p_size)*p_size
            c = np.ceil(val/p_size)*p_size
            branch_opts.append(list({f, c}))

        scenarios = itertools.product(*branch_opts)
        best_score = np.inf
        best_disc_sol = None

        for scen in scenarios:
            curr_constr = list(constraints)
            for i, val in enumerate(scen):
                t_idx = relevant_locks[i][0]
                curr_constr.append(get_mass_constraint(t_idx, num_vars, val))

            # Re-solve
            s_res = minimize(obj_fun, x0, method='SLSQP', constraints=curr_constr, bounds=[
                             (0, None) for _ in range(num_vars)])
            if s_res.success:
                if s_res.fun < best_score:
                    best_score = s_res.fun
                    best_disc_sol = s_res.x

        if best_disc_sol is not None:
            final_sol = best_disc_sol

    # 5. Output Construction
    updates = {}
    total_cal = 0
    total_prot = 0
    total_fat = 0
    total_carbs = 0

    # We round for display
    final_sol = np.round(final_sol, 1)

    for i, val in enumerate(final_sol):
        fv = flat_vars[i]
        r_id = fv['recipe_id']
        row = fv['row_index']
        name = fv['name']
        portions = fv['portions']

        if r_id not in updates:
            updates[r_id] = {}
        updates[r_id][row] = val

        # Stats Calculation
        # Cal contribution = (Amount/100 * CalPer100) / Portions
        inf = ingredient_db.get(name, {})
        c_100 = inf.get('cal_d', 0)
        p_100 = inf.get('prot_d', 0)
        f_100 = inf.get('fat_d', 0)
        carb_100 = inf.get('carbs_d', 0)

        total_cal += (val/100.0 * c_100) / portions
        total_prot += (val/100.0 * p_100) / portions
        total_fat += (val/100.0 * f_100) / portions
        total_carbs += (val/100.0 * carb_100) / portions

    stats = {
        'calories': total_cal,
        'protein': total_prot,
        'fat': total_fat,
        'carbs': total_carbs
    }

    return updates, stats
