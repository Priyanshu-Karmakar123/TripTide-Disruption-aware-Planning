#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import argparse
from typing import Any, Dict

import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


JUDGE_PROMPT = """You are a strict evaluator of travel plans. 
You are given:
1. The original travel plan
2. The disruption description
3. The revised plan
4. ALL 344 plans must have NOT NULL SCORES
Return EXACTLY ONE LINE of MINIFIED JSON, no code fences, no extra text:
{{"score":<INT 1-5>,"explanation":"<one-sentence reason and penalties applied>"}}
⚠️"score": null is NOT ALLOWED
---

### Traveler Type Definitions
- **Planbound** = Must follow the original plan exactly, unless absolutely forced by disruption.  
  *Step-level disruption → only that step may change.  
  Day-level disruption → only that day may change.  
  Plan-level disruption → broader edits allowed.  
  Any change outside this scope = automatic penalty (max score 2–3).*

- **Flexiventurer** = Allows more flexibility, but even here, unrelated or unnecessary changes = penalty.  

---

### Mandatory Penalties
- **If disruption not clearly addressed** → score = 1.  
- **If disrupted POI still appears** → score = 1.  
- **If plan unchanged** → score = 1.  
- **If disruption only “acknowledged” but not actually mitigated in itinerary** → score = 2.  
- **If Planbound constraint violated (edits outside allowed scope)** → score = max 2–3.  
- **If sequencing is unrealistic (impossible times, locations, overlaps)** → score = max 3.  

---







### Scoring Rubric (strict)
- **5 (Excellent)**: Disruption handled perfectly, only necessary change(s), constraints fully respected, plan coherent.  
- **4 (Good)**: Disruption handled correctly AND traveler is Flexiventurer, but one small unnecessary edit (e.g., shifting a meal time slightly).  
- **3 (Average)**: Disruption handled, BUT traveler is Planbound and extra edits were made outside allowed scope, OR noticeable unnecessary edits exist.  
- **2 (Poor)**: Disruption barely handled, or major scope violations, or incoherence.  
- **1 (Very Poor)**: Disruption not addressed at all.  


⚠️ Default to lower scores if there is *any doubt*.  
⚠️ Scores 4 and 5 should be *rare exceptions*, only for near-perfect plans.

---

### Examples

**Case A (Very Poor – 1)**  
Original Plan: Dinner at "Bone's Restaurant, Atlanta".  
Disruption: Restaurant closed due to private event.  
Revised Plan: Still lists "Bone's Restaurant" for dinner.  
→ Score = 1 ("Disruption ignored, POI unchanged.")  

**Case B (Good – 4)**  
Original Plan: Lunch at 12:30 at "South City Kitchen Midtown, Atlanta", Dinner at 20:45 at " Mc Donalds, Atlanta"  
Disruption: Restaurant unavailable due to supply chain issues.  
Revised Plan: Lunch replaced with "Mary Mac’s Tea Room"(same time, same city),  Dinner at 20:15 at " Mc Donalds, Atlanta"  
But also unnecessarily moved dinner 30 minutes earlier.  
→ Score = 4 ("Disruption correctly handled, but one unnecessary timing edit.")  

**Case C (Poor – 2)**  
Original Plan: Day 3 visit to "Lenox Square, Atlanta".  
Disruption: Mall closed due to security incident.  
Revised Plan: Starts with acknowledgement but still lists Lenox Square in itinerary.  
→ Score = 2 ("Disruption noted but not properly mitigated; POI remains.")  

---

Now evaluate:

Original Plan:
{initial_plan}

Disruption:
{disruption_info}

Revised Plan:
{mitigated_plan}

Answer ONLY in JSON:
{{
  "score": X,
  "explanation": "<explicit reasoning, listing penalties applied and why>"
}}
"""






def build_generator(model_name: str = "meta-llama/Llama-3.1-8B-Instruct"):
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map={"": 0},  # put model fully on cuda:0
    )

    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.eos_token_id

    gen = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        pad_token_id=model.config.pad_token_id,
    )

    if torch.cuda.is_available():
        try:
            torch.cuda.synchronize()
            used_gb = torch.cuda.memory_allocated(0) / (1024**3)
            reserved_gb = torch.cuda.memory_reserved(0) / (1024**3)
            print(f"[GPU] memory_allocated={used_gb:.2f} GB, memory_reserved={reserved_gb:.2f} GB")
        except Exception:
            pass

    return gen


def safe_json_load(line: str) -> Any:
    s = str(line).strip()
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        try:
            s2 = s.rstrip(",")
            return json.loads(s2)
        except Exception:
            return {"raw_text": s}


def extract_json_from_response(text: str) -> Dict[str, Any]:
    try:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            candidate = m.group(0)
            return json.loads(candidate)
    except Exception:
        pass
    return {"score": None, "explanation": text.strip()}


def evaluate_csv(csv_file: str, output_file: str = "judge_results.jsonl",
                 max_new_tokens: int = 300,
                 initial_col: str = "annotation_plan",
                 disruption_col: str = "disruption_info",
                 mitigated_col: str = "revised_plan"):
    """
    Reads CSV row-by-row, extracts original plan, disruption, and revised plan,
    prompts the judge LLM, extracts JSON safely, and writes results JSONL.
    """
    generator = build_generator()
    df = pd.read_csv(csv_file)

    total = 0
    parsed = 0

    with open(output_file, "w", encoding="utf-8") as fout:
        for idx, row in df.iterrows():
            total += 1
            init_data = safe_json_load(row[initial_col])
            disruption_info = str(row[disruption_col])
            mit_data = safe_json_load(row[mitigated_col])

            initial_plan = json.dumps(init_data, ensure_ascii=False, indent=2)
            mitigated_plan = json.dumps(mit_data, ensure_ascii=False, indent=2)

            prompt = JUDGE_PROMPT.format(
                initial_plan=initial_plan,
                disruption_info=disruption_info,
                mitigated_plan=mitigated_plan
            )

            out = generator(
                prompt,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                return_full_text=False
            )[0]["generated_text"]

            judge_json = extract_json_from_response(out)
            if judge_json.get("score") is not None:
                parsed += 1

            record = {
                "row_index": int(idx),
                "initial_plan": init_data,
                "disruption_info": disruption_info,
                "mitigated_plan": mit_data,
                "judge_output": judge_json
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✅ Saved judge evaluations to {output_file}")
    print(f"Stats: {parsed}/{total} responses parsed with non-null score.")


def main():
    parser = argparse.ArgumentParser(description="LLM Judge for Disrupted vs Mitigated Travel Plans (CSV input)")
    parser.add_argument("--csv_file", type=str, required=True,
                        help="CSV file with annotation_plan, disruption_info, revised_plan")
    parser.add_argument("--output_file", type=str, default="judge_results.jsonl",
                        help="Path to write judge results JSONL")
    parser.add_argument("--max_new_tokens", type=int, default=300,
                        help="Max new tokens for judge output generation")
    parser.add_argument("--initial_col", type=str, default="annotation_plan",
                        help="Column name for initial/original plan")
    parser.add_argument("--disruption_col", type=str, default="disruption_info",
                        help="Column name for disruption description")
    parser.add_argument("--mitigated_col", type=str, default="revised_plan",
                        help="Column name for mitigated/revised plan")
    args = parser.parse_args()

    os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))

    if torch.cuda.is_available():
        print(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA not available. Running on CPU will be slow.")

    evaluate_csv(
        csv_file=args.csv_file,
        output_file=args.output_file,
        max_new_tokens=args.max_new_tokens,
        initial_col=args.initial_col,
        disruption_col=args.disruption_col,
        mitigated_col=args.mitigated_col
    )


if __name__ == "__main__":
    main()
