from aiogram.fsm.context import FSMContext

from utils.files import load_costs, save_costs


async def update_user_cost(user_id: int, user_name: str, cost: float):
    """Update the user's total cost and save it with their name to a JSON file."""
    user_costs = load_costs()  # Load current costs

    user_id_str = str(user_id)  # Convert user ID to string for JSON storage

    # Update or create a record for the user
    if user_id_str not in user_costs:
        user_costs[user_id_str] = {"name": user_name, "cost": 0}

    # Add the new cost
    user_costs[user_id_str]["cost"] += cost

    save_costs(user_costs)  # Save updated data back to file