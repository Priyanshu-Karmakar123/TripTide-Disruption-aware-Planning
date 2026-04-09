import json
import os
from collections import defaultdict

def count_local_constraints(file_path):
    level_counts = defaultdict(int)
    constraint_counts = defaultdict(int)

    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    json_data = data.get("JSON", {})
                    level = json_data.get("level")
                    local_constraints = json_data.get("local_constraint", {})

                    if level and local_constraints:
                        non_null_count = sum(1 for value in local_constraints.values() if value is not None and value != '-')
                        
                        level_counts[level] += 1
                        constraint_counts[level] += non_null_count

                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from a line in {file_path}")
                    continue
    
    except FileNotFoundError:
        print(f"Error: The file was not found at {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return constraint_counts, level_counts

def main():
    folder_path = '/scratch/sg/Priyanshu/TripCraft-main/'
    files = ['/scratch/sg/Priyanshu/TripCraft-main/revised_3day_tripcraft_gpt5.jsonl','/scratch/sg/Priyanshu/TripCraft-main/GPT5_results/5day.jsonl', '/scratch/sg/Priyanshu/TripCraft-main/GPT5_results/7day_1.jsonl']

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        print(f"\n--- Results for {file_name} ---")
        
        constraint_counts, level_counts = count_local_constraints(file_path)
        
        if not constraint_counts:
            print("No constraints found or file could not be processed.")
            continue

        for level in sorted(constraint_counts.keys()):
            constraint_count = constraint_counts[level]
            plan_count = level_counts[level]
            average = constraint_count / plan_count if plan_count > 0 else 0
            print(f"  Level: {level.capitalize()}")
            print(f"    Total non-null local constraints: {constraint_count}")
            print(f"    Total number of plans: {plan_count}")
            print(f"    Average constraints per plan: {average:.2f}")
if __name__ == '__main__':
    main()
