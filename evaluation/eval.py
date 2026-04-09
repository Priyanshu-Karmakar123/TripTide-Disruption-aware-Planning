import os, sys
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
from commonsense_constraint import evaluation as commonsense_eval
from hard_constraint import evaluation as hard_eval
import json
from tqdm import tqdm
import argparse


# ---------------- utils ----------------

def load_line_json_data(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def count_true_false(data):
    if data is None:
        return 0, 0
    if isinstance(data, bool):
        return (1, 0) if data else (0, 1)
    if isinstance(data, (list, tuple)):
        vals = [data[0]] if isinstance(data, tuple) else data
        return vals.count(True), vals.count(False)
    return 0, 0


def statistics(statistic):
    result = {lvl: {d: {} for d in statistic[lvl]} for lvl in statistic}
    for lvl, days in statistic.items():
        for d, records in days.items():
            for rec in records:
                if not rec:
                    continue
                for k, v in rec.items():
                    t, f = count_true_false(v)
                    result[lvl][d].setdefault(k, {"true": 0, "false": 0})
                    result[lvl][d][k]["true"] += t
                    result[lvl][d][k]["false"] += f
    return result


# ---------------- mapping ----------------

def paper_term_mapping(cs, hd):
    mapping = {
        'is_valid_information_in_current_city':'Within Current City',
        'is_valid_information_in_sandbox':'Within Sandbox',
        'is_reasonable_visiting_city':'Reasonable City Route',
        'is_valid_restaurants':'Diverse Restaurants',
        'is_valid_transportation':'Non-conf. Transportation',
        'is_valid_attractions':'Diverse Attractions',
        'is_not_absent':'Complete Information',
        'is_valid_meal_gaps':'Sufficient Time between meals',
        'is_valid_event':'No Reapeated Events',
        'is_valid_poi_sequence':'PoI sequence starts and ends with accommodation',
        'valid_cost':'Budget',
        'valid_room_rule':'Room Rule',
        'valid_cuisine':'Cuisine',
        'valid_room_type':'Room Type',
        'valid_transportation':'Transportation',
        'valid_event_type':'Event Type',
        'valid_attraction_type':'Attraction Type'
    }

    def remap(src):
        return {
            lvl: {
                d: {mapping.get(k, k): v for k, v in src[lvl][d].items()}
                for d in src[lvl]
            }
            for lvl in src
        }

    return remap(cs), remap(hd)


# ---------------- main eval ----------------

def eval_score(set_type: str, file_path: str):

    tested_plans = load_line_json_data(file_path)
    query_data_list = [x["JSON"] for x in tested_plans]

    commonsense_stat = {l:{d:[] for d in [3,5,7]} for l in ['easy','medium','hard']}
    hard_stat = {l:{d:[] for d in [3,5,7]} for l in ['easy','medium','hard']}

    delivery_cnt = 0
    plan_store = []

    for i in tqdm(range(len(query_data_list))):
        q = query_data_list[i]
        p = tested_plans[i]

        if isinstance(q, str): q = eval(q)
        if isinstance(p, str): p = eval(p)
        if isinstance(q.get("local_constraint"), str):
            q["local_constraint"] = eval(q["local_constraint"])

        if len(p["plan"]) <= 2:
            plan_store.append({"commonsense_constraint": None, "hard_constraint": None})
            continue

        delivery_cnt += 1
        cs = commonsense_eval(q, p["plan"])

        if cs and cs["is_not_absent"][0] and cs["is_valid_information_in_sandbox"][0]:
            hd = hard_eval(q, p["plan"])
        else:
            hd = None

        plan_store.append({"commonsense_constraint": cs, "hard_constraint": hd})
        commonsense_stat[q["level"]][q["days"]].append(cs)
        hard_stat[q["level"]][q["days"]].append(hd)

    # ---------- aggregation ----------
    cs_proc = statistics(commonsense_stat)
    hd_proc = statistics(hard_stat)

    final_cs = 0
    final_hd = 0
    final_all = 0

    for i, rec in enumerate(plan_store):
        cs, hd = rec["commonsense_constraint"], rec["hard_constraint"]

        cs_pass = True
        if cs:
            for v in cs.values():
                if isinstance(v, (list, tuple)) and v[0] is False:
                    cs_pass = False
                    break
        else:
            cs_pass = False

        hd_pass = True
        if hd:
            for v in hd.values():
                if isinstance(v, (list, tuple)) and v[0] is False:
                    hd_pass = False
                    break
        else:
            hd_pass = False

        if cs_pass: final_cs += 1
        if hd_pass: final_hd += 1
        if cs_pass and hd_pass: final_all += 1

    # ---------- final metrics ----------
    if set_type == '3d':
        N = 343
        cs_micro = 3430
        hd_micro = 813
    elif set_type == '5d':
        N = 50
        cs_micro = 500
        hd_micro = 119
    else:
        N = 329
        cs_micro = 3290
        hd_micro = 686

    result = {
        "Delivery Rate": delivery_cnt / N,
        "Commonsense Constraint Micro Pass Rate": sum(v["true"] for l in cs_proc.values() for d in l.values() for v in d.values()) / cs_micro,
        "Commonsense Constraint Macro Pass Rate": final_cs / N,
        "Hard Constraint Micro Pass Rate": sum(v["true"] for l in hd_proc.values() for d in l.values() for v in d.values()) / hd_micro,
        "Hard Constraint Macro Pass Rate": final_hd / N,
        "Final Pass Rate": final_all / N
    }

    cs_remap, hd_remap = paper_term_mapping(cs_proc, hd_proc)
    return result, {"Commonsense Constraint": cs_remap, "Hard Constraint": hd_remap}


# ---------------- CLI ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--set_type", type=str, required=True)
    parser.add_argument("--evaluation_file_path", type=str, required=True)
    args = parser.parse_args()

    scores, details = eval_score(args.set_type, args.evaluation_file_path)

    for k, v in scores.items():
        print(f"{k}: {v*100:.2f}%")
