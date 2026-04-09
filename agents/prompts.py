from langchain.prompts import PromptTemplate

PLANNER_INSTRUCTION_OG = """You are an efficient travel planner agent. You job is to plan the travel itenary and generate the travel itenary based on the reference information and the following constraints. You need to only given a travel itinerary in JSON format, along with user details and a disruption information that affects the travel plan. The disruption has a severity level — step, day, or plan — indicating how much of the itinerary is impacted. The mitigation depends on the "Disruption Tolerance" level- Flexiventurer or Planbound.
If the traveler is identified as “Planbound”, the scope of revision must strictly correspond to the disruption_severity. Specifically, for step-level disruptions, only the affected event should be modified; for day-level disruptions, modifications must be limited to the POIs scheduled for that particular day; and for plan-level disruptions, broader itinerary changes are permitted.
In contrast, for “Flexiventurer” travelers, there is no constraint linking the revision scope to the disruption severity.
Your task is to update the travel itinerary to accommodate the disruption with necessary changes, using the reference information provided to guide your modifications.
Return the complete revised travel plan in the exact same JSON format as the original. 
You must acknowledge the disruption first and then proceed with appropriate revisions based on disruption severity and traveler's disruption tolerance.
Output only the revised travel plan in strict JSON format.

*** Remember that you do not have to include the annotation plan or any explanation or the Reference Info in the output.
Once the entire travel itenary along with POI list of Day 7 ended, do not add any additional text.
Do not add the example or the PLANNER_INSTRUCTION_OG prompt in the outputs.




Given information: {text}
Query: {query}
reference_info: {{reference_info}}

###Output ### (strict JSON only, no explanations):Return only the revised itinerary JSON. Do not repeat the instruction or example."""

PLANNER_INSTRUCTION_DISRUPTION = """"You are given a travel itinerary in JSON format {text}, along with user details and a disruption information {query} that affects the travel plan. The disruption has a severity level — step, day, or plan — indicating how much of the itinerary is impacted. The mitigation depends on the "Disruption Tolerance" level- Flexiventurer or Planbound.
If the traveler is identified as “Planbound”, the scope of revision must strictly correspond to the disruption_severity. Specifically, for step-level disruptions, only the affected event should be modified; for day-level disruptions, modifications must be limited to the POIs scheduled for that particular day; and for plan-level disruptions, broader itinerary changes are permitted.
In contrast, for “Flexiventurer” travelers, there is no constraint linking the revision scope to the disruption severity.
Your task is to update the travel itinerary to accommodate the disruption with necessary changes, using the reference information {reference_info_1}, {reference_info_2} and {reference_info_3} provided to guide your modifications.
Return the complete revised travel plan in the exact same JSON format as the original. 
You must acknowledge the disruption first and then proceed with appropriate revisions based on disruption severity and traveler's disruption tolerance.

-------------------- Chain-of-Thought (Internal) --------------------
IMPORTANT: Perform the following steps internally (silently). DO NOT reveal the step-by-step reasoning.
Only output the final JSON in the required wrapper.

1) Extract & Normalize
   - Parse {text}: trip days, dates, cities, daily schedule objects, POIs, meals, accommodation, transportation.
   - Parse {query}: affected day/step, category, reason, severity (step/day/plan), when it occurs, and any constraints.

2) Determine Traveler Tolerance
   - Identify whether the traveler is "Planbound" or "Flexiventurer" from the input.
   - If missing, default to Planbound (minimal-change policy).

3) Decide Allowed Edit Scope
   - If Planbound: edits must match disruption_severity:
       * step  -> change ONLY the impacted step/event/booking (keep everything else identical)
       * day   -> change ONLY the POIs/schedule on the impacted day
       * plan  -> broader changes allowed (reorder, swap days/cities if needed)
   - If Flexiventurer: you may revise beyond the impacted scope, but still prefer minimal disruption unless necessary.

4) Select Replacements Using  References
   - Use {reference_info_1} , {reference_info_2} and {reference_info_3} to choose alternatives (POIs, restaurants, hotels, transport, timings).
   

5) Apply Changes Consistently
   - If you replace/remove an item, update ALL linked fields (day summary fields + point_of_interest_list entries + time windows).
   - Preserve the original schema, ordering style, and formatting patterns.

6) Self-Check Before Output
   - JSON validity, same schema as original, dates/day counts unchanged unless plan-level disruption requires otherwise.
   - For Planbound: unaffected days must remain byte-for-byte identical in content (except unavoidable dependencies).
   - Ensure the acknowledgement is present and accurate.
--------------------------------------------------------------------

 
Travel Itinerary and User Details:{text}
Disruption Information:{query}
Reference Information:{reference_info_1}
Reference Information: {reference_info_2}
Reference Information: {reference_info_3}

Output the complete travel plan with acknowledgement and the modifications in the exact same JSON template as the original.
Your response must start with "complete_revised_travel_plan"
Output (Updated Travel Plan in JSON format):
 """

planner_agent_prompt_direct_og = PromptTemplate(
                        input_variables=["text","query","reference_info_1","reference_info_2","reference_info_3"],
                        template = PLANNER_INSTRUCTION_DISRUPTION
                        )

# planner_agent_prompt_direct_param = PromptTemplate(
#                         input_variables=["text","query","persona"],
#                         template = PLANNER_INSTRUCTION_PARAMETER_INFO,
#                         )

# cot_planner_agent_prompt = PromptTemplate(
#                         input_variables=["text","query"],
#                         template = COT_PLANNER_INSTRUCTION,
#                         )

# react_planner_agent_prompt = PromptTemplate(
#                         input_variables=["text","query", "scratchpad"],
#                         template = REACT_PLANNER_INSTRUCTION,
#                         )

# reflect_prompt = PromptTemplate(
#                         input_variables=["text", "query", "scratchpad"],
#                         template = REFLECT_INSTRUCTION,
#                         )

# react_reflect_planner_agent_prompt = PromptTemplate(
#                         input_variables=["text", "query", "reflections", "scratchpad"],
#                         template = REACT_REFLECT_PLANNER_INSTRUCTION,
                        # )