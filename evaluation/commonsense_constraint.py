"""
from utils.func import get_valid_name_city,extract_before_parenthesis,extract_numbers_from_filenames
from tools.flights.apis import Flights
from tools.accommodations.apis import Accommodations
from tools.restaurants.apis import Restaurants
from tools.googleDistanceMatrix.apis import GoogleDistanceMatrix
from tools.attractions.apis import Attractions
from tools.events.apis import Events
import math
import json
import re   
import os
import sys
from tqdm import tqdm
import argparse
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

flight = Flights()
accommodation = Accommodations()
restaurants = Restaurants()
googleDistanceMatrix = GoogleDistanceMatrix()
attractions = Attractions()
events = Events()
pois = pd.read_csv('/scratch/sg/Priyanshu/TripCraft-main/ATP_database/all_poi_nearest_stops.csv')

city_state_set = open('/scratch/sg/Priyanshu/TripCraft-main/ATP_database/background/citySet_with_states_140.txt','r').read().split('\n')
city_state_map = {x:y for x,y in [unit.split('\t') for unit in city_state_set]}


def load_line_json_data(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f.read().strip().split('\n'):
            unit = json.loads(line)
            data.append(unit)
    return data


def count_consecutive_values(lst):
    if not lst:
        return []

    result = []
    current_string = lst[0]
    count = 1

    for i in range(1, len(lst)):
        if lst[i] == current_string:
            count += 1
        else:
            result.append((current_string, count))
            current_string = lst[i]
            count = 1

    result.append((current_string, count))  # Add the last group of values
    return result


def transportation_match(text: str):

    if 'taxi' in text.lower():
        return 'Taxi'
    
    elif 'self-driving' in text.lower():
        return 'Self-driving'
    
    elif 'flight' in text.lower():
        return 'Flight'


def extract_from_to(text: str):
    
    #Extracts 'A' and 'B' from the format "from A to B" in the given text, with B ending at a comma or the end of the string.
    
    #Args:
    #- text (str): The input string.
    
    #Returns:
    #- tuple: A tuple containing 'A' and 'B'. If no match is found, returns (None, None).
    
    pattern = r"from\s+(.+?)\s+to\s+([^,]+)(?=[,\s]|$)"
    matches = re.search(pattern, text)
    return matches.groups() if matches else (None, None)



def is_valid_city_sequence(city_list):
    
    #Checks if the city sequence is valid. A valid sequence has every city (except the first and last) 
    #appearing consecutively, and no city should appear again once its sequence is over.
    
    #Args:
    #- city_list (list): List of cities.
    
    #Returns:
    #- bool: True if the sequence is valid, False otherwise.
    
    
    # If the list has less than 3 cities, it's invalid.
    if len(city_list) < 3:
        return False
    
    # Set to keep track of visited cities
    visited_cities = set()
    
    i = 0
    while i < len(city_list):
        city = city_list[i]
        
        # If the city was already visited, it's invalid.
        if city in visited_cities and (i != 0 and i != len(city_list) - 1):
            return False
        
        # Count the consecutive occurrences of the city
        count = 0
        while i < len(city_list) and city_list[i] == city:
            count += 1
            i += 1
        
        # If the city appeared only once in the medium, it's invalid.
        if count == 1 and 0 < i - 1 < len(city_list) - 1:
            return False
        
        visited_cities.add(city)
    
    return True



def is_reasonable_visiting_city(question, tested_data):

    city_list = []
    
    # print(tested_data)
    for i in range(min(question['days'],len(tested_data))):
        city_value = tested_data[i]['current_city']

        if 'from' in city_value:
            city1, city2 = extract_from_to(city_value)
            # city1 = extract_before_parenthesis(city1)
            # city2 = extract_before_parenthesis(city2)
            if i==0 and  city1 != question['org']:
                return False, f"The first day's city should be {question['org']}."

            city_list += [city1, city2]

        else:
            city_list.append(extract_before_parenthesis(city_value))
    
    if city_list[0] != city_list[-1]:
        return False, "The trip should be a closed circle."

    if not is_valid_city_sequence(city_list):
        return False, "The city sequence is invalid."
    
    for idx, city in enumerate(city_list):
        if city not in city_state_map:
            return False, f"{city} is not a valid city."
        if idx not in [0,len(city_list)-1] and question['days'] >3 and city_state_map[city] != question['dest']:
            return False, f"{city} is not in {question['dest']}."
    
    return True, None


def is_valid_restaurants(question, tested_data):

    restaurants_list = []

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'breakfast' in unit and unit['breakfast'] and unit['breakfast'] != '-':
            if unit['breakfast'] not in restaurants_list:
                restaurants_list.append(unit['breakfast'])
            else:
                return False, f"The restaurant in day {i+1} breakfast is repeated."
        # elif 'breakfast' not in unit :
        #     return False, f"No Breakfast Info."
            
        if 'lunch' in unit and unit['lunch'] and unit['lunch'] != '-':
            if unit['lunch'] not in restaurants_list:
                restaurants_list.append(unit['lunch'])
            else:
                return False, f"The restaurant in day {i+1} lunch {unit['lunch']} is repeated."
        # elif 'lunch' not in unit:
        #     return False, f"No Lunch Info."
        
        if 'dinner' in unit and unit['dinner'] and unit['dinner'] != '-':
            if unit['dinner'] not in restaurants_list:
                restaurants_list.append(unit['dinner'])
            else:
                return False, f"The restaurant in day {i+1} dinner is repeated."
        # elif 'dinner' not in unit:
        #     return False, f"No Dinner Info."

    return True, None
            
def is_valid_attractions(question, tested_data):

    attractions_list = []

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'attraction' in unit and unit['attraction'] and unit['attraction'] != '-':
            for attraction in unit['attraction'].split(';'):
                if attraction not in attractions_list:
                    attractions_list.append(attraction)
                else:
                    return False, f"The attraction '{attraction}' in day {i+1} is repeated."
                
        # elif 'attraction' not in unit:
        #     return False, f"No Attraction Info."
        
    return True, None

def is_valid_event(question, tested_data):

    events_list = []

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'event' in unit and unit['event'] and unit['event'] != '-':
            for event in unit['event'].split(';'):
                if event not in events_list:
                    events_list.append(event)
                else:
                    return False, f"The event '{event}' in day {i+1} is repeated."
                
        # elif 'attraction' not in unit:
        #     return False, f"No Attraction Info."
        
    return True, None

def is_time_difference_valid(time1, time2, min_difference):
    from datetime import datetime, timedelta
    fmt = "%H:%M"
    # Extract just the HH:MM part using regex or split
    clean_time1 = re.match(r'\d{1,2}:\d{2}', time1)
    if not clean_time1:
        return False  # or raise a more meaningful error

    time1 = datetime.strptime(clean_time1.group(), fmt)
    clean_time2 = re.match(r'\d{1,2}:\d{2}', time2)
    if not clean_time2:
        return False

    time2 = datetime.strptime(clean_time2.group(), fmt)

    return abs((time2 - time1).total_seconds()) / 60 >= min_difference

def is_valid_poi_sequence(question, tested_data):
    current_accommodation = "abc"
    prev_accommodation = None
    
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        
        # Determine current accommodation
        if unit["accommodation"] != "-":
            current_accommodation = unit["accommodation"]

        # Parse city if present
        if "," in current_accommodation:
            current_accommodation, city = current_accommodation.rsplit(",", 1)
            current_accommodation = current_accommodation.strip()
            city = city.strip()
        else:
            current_accommodation = current_accommodation.strip()
            city = ""

        poi_list = unit["point_of_interest_list"].split(";")

        # Day-specific logic for transitions (e.g., day 3 or day 5)
        if question['days']==7:
            if i+1 in [3,5] and prev_accommodation:
                if not (prev_accommodation.strip() in poi_list[0] and current_accommodation.strip() in poi_list[-1]):
                    return False, f"Day {i+1} PoI list must start with previous day's accommodation and end with current day's accommodation."
        elif question['days']==5:
            if i+1 in [3] and prev_accommodation:
                if not (prev_accommodation.strip() in poi_list[0] and current_accommodation.strip() in poi_list[-1]):
                    return False, f"Day {i+1} PoI list must start with previous day's accommodation and end with current day's accommodation."

        # Normal check: start and end with current accommodation if specified
        elif unit["accommodation"] != "-":
            if current_accommodation.strip() in poi_list[0] and current_accommodation.strip() in poi_list[-1]:
                pass
            else:
                return False, f"The PoI list for day {i+1} doesn't start and end with an accommodation."
        else:
            if current_accommodation.strip() in poi_list[0]:
                pass
            else:
                return False, f"The PoI list for day {i+1} doesn't start with an accommodation."

        # Check events
        if 'event' in unit and unit['event'] and unit['event'] != '-':
            events_list = list({e.rsplit(",", 1)[0].strip() for e in unit['event'].split(';') if e})
            for et in events_list:
                if et in unit["point_of_interest_list"]:
                    return False, f"The PoI list for day {i+1} shouldn't contain events."

        # Check attractions
        if 'attraction' in unit and unit['attraction'] and unit['attraction'] != '-':
            attractions_list = list({attr.rsplit(",", 1)[0].strip() for attr in unit['attraction'].split(';') if attr})
            for attr in attractions_list:
                if attr not in unit["point_of_interest_list"]:
                    return False, f"The PoI list for day {i+1} doesn't contain all attractions."

        # Check meals
        for meal in ['breakfast', 'lunch', 'dinner']:
            if meal in unit and unit[meal] and unit[meal] != '-':
                food_place = unit[meal].rsplit(",", 1)[0].strip()
                if food_place not in unit["point_of_interest_list"]:
                    return False, f"The PoI list for day {i+1} doesn't contain {meal}."

        # Check flight timing constraints
        if 'transportation' in unit and all(x in unit['transportation'].lower() for x in ['flight', 'departure', 'arrival']):
            transport_info = unit['transportation'].split(', ')
            departure_time = arrival_time = None
            for info in transport_info:
                if 'Departure Time' in info:
                        if ': ' not in info or len(info.split(': ')) < 2:
                            print(f"[SKIP] Invalid info format, skipping plan: {info}")
                            return False  # or continue depending on the logic
                        departure_time = info.split(': ')[1]

                elif 'Arrival Time' in info:
                    arrival_time = info.split(': ')[1]

            if i == 0 and poi_list[0] not in ['-', '']:
                for time_phrase in poi_list[0].split(','):
                    if 'stay from' in time_phrase or 'visit from' in time_phrase:
                        first_poi_time = time_phrase.split('from ')[1].split(' to ')[0].strip()
                        if not is_time_difference_valid(arrival_time, first_poi_time, 30):
                            return False, f"First PoI on day {i+1} starts too soon after the flight arrival."
                            
            if question['days'] > 3:            
                if i == 2 and poi_list[0] not in ['-', '']:
                    for time_phrase in poi_list[0].split(','):
                        if 'stay from' in time_phrase or 'visit from' in time_phrase:
                            first_poi_time = time_phrase.split('from ')[1].split(' to ')[0].strip()
                            if not is_time_difference_valid(arrival_time, first_poi_time, 30):
                                return False, f"First PoI on day {i+1} starts too soon after the flight arrival."

            if question['days'] > 5:
                if i == 4 and poi_list[0] not in ['-', '']:
                    for time_phrase in poi_list[0].split(','):
                        if 'stay from' in time_phrase or 'visit from' in time_phrase:
                            first_poi_time = time_phrase.split('from ')[1].split(' to ')[0].strip()
                            if not is_time_difference_valid(arrival_time, first_poi_time, 30):
                                return False, f"First PoI on day {i+1} starts too soon after the flight arrival."

            if i == len(tested_data) - 1 and poi_list[-1] not in ['-', '']:
                for time_phrase in poi_list[-1].split(','):
                    if 'stay from' in time_phrase or 'visit from' in time_phrase:
                        last_poi_time = time_phrase.split('from ')[1].split(' to ')[-1].strip()
                        if not is_time_difference_valid(last_poi_time, departure_time, 30):
                            return False, f"Last PoI on day {i+1} ends too close to the flight departure."

        # Update prev_accommodation only if a new one is provided
        if unit["accommodation"] != "-":
            prev_accommodation = current_accommodation

    return True, None

def is_valid_meal_gaps(question, tested_data):
    for i in range(min(question['days'], len(tested_data))):
        day_plan = tested_data[i]
        # Store meal start and end times
        meal_times = {}
        for meal in ["breakfast", "lunch", "dinner"]:
            if meal in day_plan and day_plan[meal] != "-":
                poi_info = day_plan["point_of_interest_list"].split(";")
                for poi in poi_info:
                    if "," in day_plan[meal]:
                        day_plan_meal = day_plan[meal]
                        day_plan_meal, city = day_plan_meal.rsplit(",", 1)
                        day_plan_meal = day_plan_meal.strip()
                        city = city.strip()
                    else:
                        # Fallback if no city is mentioned
                        day_plan_meal = day_plan[meal]
                        day_plan_meal = day_plan_meal.strip()
                        city = ""

                    if day_plan_meal in poi and poi not in ['-','']:
                        try:
                            # Extract the "from" and "to" times
                            time_info = poi.split("from")[1].split("to")
                            start_time = time_info[0].strip()
                            end_time = time_info[1].split(",")[0].strip()
                        except:
                            try:
                                time_info = poi.rsplit("from", 1)[1].split("to")
                                start_time = time_info[0].strip()
                                end_time = time_info[1].split(",")[0].strip()
                            except:
                                return False, f"Incorrect format."   
                        # Convert times to decimal hours
                        # print(time_info)
                        try:
                            start_hour = int(start_time.split(":")[0]) + int(start_time.split(":")[1]) / 60
                            end_hour = int(end_time.split(":")[0]) + int(end_time.split(":")[1]) / 60
                        except:
                            return False, f"PoI time intervals are not in correct format."

                        # Save meal start and end times
                        meal_times[meal] = (start_hour, end_hour)
                        break

        # Validate meal time gaps
        sorted_meals = ["breakfast", "lunch", "dinner"]
        for j in range(len(sorted_meals) - 1):
            meal1 = sorted_meals[j]
            meal2 = sorted_meals[j + 1]
            if meal1 in meal_times and meal2 in meal_times:
                _, meal1_end = meal_times[meal1]
                meal2_start, _ = meal_times[meal2]
                # Check if the gap is at least 4 hours
                if meal2_start - meal1_end < 4:
                    return False, f"Not sufficient time gap between {meal1} and {meal2} of day {i+1}"  # Invalid gap

    return True, None  # All meal gaps are valid

    
def is_valid_transportation(question, tested_data):
    
    if tested_data[0]['transportation'] and tested_data[0]['transportation'] != '-':
        transportation_list = [transportation_match(tested_data[0]['transportation'])]
    
    else:
        return False, "The transportation in day 1 should not be empty."

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'transportation' in unit and unit['transportation'] and unit['transportation'] != '-':
            transportation_list.append(transportation_match(unit['transportation']))
        # elif 'transportation' not in unit:
        #     return False, f"No Transportation Info."
    
    if (('Self-driving' in transportation_list) and ('Flight' in transportation_list)) or (('Taxi' in transportation_list) and ('Self-driving' in transportation_list)):
        return False, "The transportation is conflicting."

    return True, None

def is_valid_information_in_current_city(question, tested_data):

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]
        current_city = unit['current_city']
        final_city_list = []

        if 'from' in current_city:
            city1, city2 = extract_from_to(current_city)
            # city1 = extract_before_parenthesis(city1)
            # city2 = extract_before_parenthesis(city2)
            final_city_list = [city1, city2]
        else:
            return False, f"Invalid current city format."
            # final_city_list = extract_before_parenthesis(current_city)

        if 'transportation' in unit and unit['transportation'] and unit['transportation'] != '-':
            for city in final_city_list:
                if ('Self-driving' not in unit['transportation'] and 'Taxi' not in unit['transportation']) and (city not in unit['transportation']):
                    # print(city)
                    return False, f"The transportation in day {i+1} is invalid city choice."
        # elif 'transportation' not in unit:
        #     return False, f"No Transportation Info."
        
        if 'breakfast' in unit and unit['breakfast'] and unit['breakfast'] != '-':
            flag = False

            for city in final_city_list:
                if city  in unit['breakfast']:
                    flag = True

            if not flag:
                return False, f"The breakfast in day {i+1} is invalid city choice."
        # elif 'breakfast' not in unit:
        #     return False, f"No Breakfast Info."
        
        if 'lunch' in unit and unit['lunch'] and unit['lunch'] != '-':
            flag = False

            for city in final_city_list:
                if city  in unit['lunch']:
                    flag = True
            
            if not flag:
                return False, f"The lunch in day {i+1} is invalid city choice."
        # elif 'lunch' not in unit:
        #     return False, f"No Lunch Info."
            
        if 'dinner' in unit and unit['dinner'] and unit['dinner'] != '-':
            flag = False

            for city in final_city_list:
                if city  in unit['dinner']:
                    flag = True
            
            if not flag:
                return False, f"The dinner in day {i+1} is invalid city choice."
        # elif 'dinner' not in unit:
        #     return False, f"No Dinner Info."
        
        if 'attraction' in unit and unit['attraction'] and unit['attraction'] != '-':
            
            attraction_list = unit['attraction'].split(';')

            for attraction in attraction_list:
                flag = False
                for city in final_city_list:
                    if city  in attraction:
                        flag = True
                if not flag:
                    return False, f"The attraction in day {i+1} is invalid city choice."
                
        # elif 'attraction' not in unit:
        #     return False, f"No Attraction Info."
            
            
        if 'accommodation' in unit and unit['accommodation'] and unit['accommodation'] != '-':
            
            if final_city_list[-1] not in unit['accommodation']:
                return False, f"The accommodation in day {i+1} is invalid city choice."
            
        # elif 'accommodation' not in unit:
        #     return False, f"No Accommodation Info."
    
    return True, None
        
# hallucination 
def is_valid_information_in_sandbox(question, tested_data):
    
    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]
        
        if unit['transportation'] and unit['transportation'] != '-':
            value = unit['transportation']
            # org_city, dest_city = extract_from_to(value)
            # if org_city == None or dest_city == None:
            # print(unit['current_city'], type(unit['current_city']))
            org_city, dest_city = extract_from_to(unit['current_city'])
            if 'flight number' in value.lower():
                try:
                    # print("(",org_city, dest_city,")")
                    org_city = extract_before_parenthesis(org_city)
                    dest_city = extract_before_parenthesis(dest_city)
                except TypeError:
                    org_city, dest_city = extract_from_to(unit['transportation'])
                    # raise ValueError("The transportation {} in day {} can not be parsed.".format(value,i+1))
                # print(value)
                try:
                    if len(flight.data[(flight.data['Flight Number'] == value.split('Flight Number: ')[1].split(',')[0]) & (flight.data['OriginCityName']==org_city) & (flight.data['DestCityName']==dest_city)]) < 1:
                        return False, f"The flight number in day {i+1} is invalid in the sandbox."
                except:
                    return False, f"Incorrect Flight format."
            
            elif 'self-driving' in value.lower() or 'taxi' in value.lower():
                try:
                    org_city = extract_before_parenthesis(org_city)
                    dest_city = extract_before_parenthesis(dest_city)
                except TypeError:
                    org_city = '-'
                    dest_city = '-'
                    print("The transportation {} in day {} can not be parsed and '-' will be used instead.".format(value,i+1))
                
                if 'self-driving' in value.lower():
                    if googleDistanceMatrix.run_for_evaluation(org_city, dest_city, mode='self-driving')['cost'] == None:
                        return False, f"The self-driving in day {i+1} is invalid in the sandbox."
                else:
                    if googleDistanceMatrix.run_for_evaluation(org_city, dest_city, mode='taxi')['cost'] == None:
                        return False, f"The taxi in day {i+1} is invalid in the sandbox."

        if 'breakfast' in unit and unit['breakfast'] and unit['breakfast'] != '-':
            name, city = get_valid_name_city(unit['breakfast'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) & (restaurants.data['City'] == city)]) < 1:
                return False, f"The breakfast in day {i+1} is invalid in the sandbox."
        elif 'breakfast' not in unit:
            return False, f"No Breakfast Info."
        
        if 'lunch' in unit and unit['lunch'] and unit['lunch'] != '-':
            name, city = get_valid_name_city(unit['lunch'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) & (restaurants.data['City'] == city)]) < 1:
                return False, f"The lunch in day {i+1} is invalid in the sandbox."
        elif 'lunch' not in unit:
            return False, f"No Lunch Info."
        
        if 'dinner' in unit and unit['dinner'] and unit['dinner'] != '-':
            name, city = get_valid_name_city(unit['dinner'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) & (restaurants.data['City'] == city)]) < 1:
                return False, f"The dinner in day {i+1} is invalid in the sandbox."
        elif 'dinner' not in unit:
            return False, f"No Dinner Info."
            
        if 'attraction' in unit and unit['attraction'] and unit['attraction'] != '-':
            attractions_list = unit['attraction'].split(';')
            for attraction in attractions_list:
                name, city = get_valid_name_city(attraction)
                
                if len(attractions.data[(attractions.data['name'].astype(str).str.contains(re.escape(name))) & (attractions.data['City'] == city)]) < 1:
                    return False, f"The attraction {attraction} in day {i+1} is invalid in the sandbox."
        

        if 'event' in unit and unit['event'] and unit['event'] != '-':
            events_list = unit['event'].split(';')
            for event in events_list:
                # name, city = get_valid_name_city(event)
                name = event.rsplit(',',1)[0].strip()
                # city = question['dest'] 
                city = event.rsplit(",",1)[-1].strip()
                if len(events.data[(events.data['name'].astype(str).str.contains(re.escape(name))) & (events.data['city'] == city)]) < 1:
                    return False, f"The event {event} in day {i+1} is invalid in the sandbox."
                
        if 'accommodation' in unit and unit['accommodation'] and unit['accommodation'] != '-':
            name, city = get_valid_name_city(unit['accommodation'])
            # print(name,city)
            # print(accommodation.data[accommodation.data['NAME'].astype(str).str.contains(re.escape(name))])
            if len(accommodation.data[(accommodation.data['name'].astype(str).str.contains(re.escape(name))) & (accommodation.data['City'] == city)]) < 1:
                return False, f"The accommodation in day {i+1} is invalid in the sandbox."
        elif 'accommodation' not in unit:
            return False, f"No Accommodation Info."

        if 'point_of_interest_list' in unit and unit['point_of_interest_list'] and unit['point_of_interest_list'] != '-':
            poi_info = unit["point_of_interest_list"].split(";")
            for poi in poi_info:
                if "nearest transit:" in poi:
                    transit_info = poi.split("nearest transit:")[1].strip()
                    poi_name = poi.split("nearest transit:")[0].strip()[:-1].rsplit(",",1)[0].strip()
                    transit_stop = transit_info.rsplit(",", 1)[0].strip()
                    if "," in transit_info:
                        # print(transit_info)
                        transit_value = transit_info.rsplit(",", 1)[-1].strip().split("m")[0].strip()  
                        try:
                            stop_distance = float(transit_value)
                        except:
                            stop_distance = 0
                    else:
                        return False, f"PoI list is not formatted correctly."

                    try:
                        if question['days']==3:
                            if ((i+1)==3):
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            else:
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                        if question['days']==5:
                            if ((i+1)==3):
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == org_city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == dest_city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            elif ((i+1)==5):
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            else:
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                        if question['days']==7:
                            if ((i+1)==3) or ((i+1)==5):
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == org_city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == dest_city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            elif ((i+1)==7):
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            else:
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) & (pois['PoI'] == poi_name) & (pois['City'] == city) & (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                        return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                    except Exception as e:
                        return False, f"Incorrect format. Error: {str(e)}"
    return True, None

def is_valid_accommodaton(question, tested_data):
    data = []
    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'accommodation' not in unit:
            return False, f"No Accommodation Info."
        
        data.append(unit['accommodation'])
    # data = [unit['accommodation'] for unit in tested_data]
    consectutive_accommodation = count_consecutive_values(data)
    for unit in consectutive_accommodation:
        # print(unit)
        if unit and unit[0] not in  ['-',''] :
            name, city = get_valid_name_city(unit[0])
            # print(unit[0],name,city)
            # try:
            if len(accommodation.data[(accommodation.data['name'].astype(str).str.contains(re.escape(name))) & (accommodation.data['City'] == city)]) == 1 and unit[1] <  accommodation.data[(accommodation.data['name'].astype(str).str.contains(re.escape(name))) & (accommodation.data['City'] == city)].iloc[0]['minimum nights']:
                return False, f"The accommodation {unit[0]} do not obey the minumum nights rule."
            # can not parse data
            # except re.error:
            #     continue
            
    return True, None

def is_valid_visiting_city_number(question, tested_data):

    city_set = set()
    

    for i in range(min(question['days'],len(tested_data))):
        city_value = tested_data[i]['current_city']

        if 'from' in city_value:
            city1, city2 = extract_from_to(city_value)
            city1 = extract_before_parenthesis(city1)
            city2 = extract_before_parenthesis(city2)
            if i==0 and  city1 != question['org']:
                return False, f"The first day's city should be {question['org']}."

            city_set.add(city1)
            city_set.add(city2)

        else:
            city_set.add(extract_before_parenthesis(city_value))
    
    city_set.discard(question['org'])

    if len(city_set) != question['visiting_city_number']:
        return False, f"The number of visiting cities should be {question['visiting_city_number']}."
    
    return True, None

def is_valid_days(question, tested_data):
    lens = 0
    for i in range(min(question['days'],len(tested_data))):
        if tested_data[i] != {} and tested_data[i]['current_city'] != "You don't need to fill in the information for this or later days.":
            lens += 1
        
    if lens != question['days']:
        # print(lens)
        return False, f"The number of days should be {question['days']}."
    else:
        return True, None

def is_not_absent(question, tested_data):
    needed_info = 8 * question['days']
    total_valid_info = 0

    if not is_valid_days(question, tested_data)[0]:
        return False, "Invalid Days"
    
    if not is_valid_visiting_city_number(question, tested_data)[0]:
        return False, "Invalid City Number"

    for i in range(min(question['days'],len(tested_data))):
        unit = tested_data[i]

        if 'transportation' not in unit:
            return False, f"No Transportation Info."
        
        if 'breakfast' not in unit:
            return False, f"No Breakfast Info."
        
        if 'lunch' not in unit:
            return False, f"No Lunch Info."
        
        if 'dinner' not in unit:
            return False, f"No Dinner Info."
        
        if 'attraction' not in unit:
            return False, f"No Attraction Info."
        
        if 'accommodation' not in unit:
            return False, f"No Accommodation Info."
        
        if 'event' not in unit:
            return False, f"No Event Info."
        
        if 'point_of_interest_list' not in unit:
            return False, f"No PoI Info."
        
        if 'point_of_interest_list' in unit and unit['point_of_interest_list'] and unit['point_of_interest_list'] != '-':
            poi_info = unit["point_of_interest_list"].split(";")
            for poi in poi_info:
                if "nearest transit:" in poi:
                    transit_info = poi.split("nearest transit:")[1].strip()
                    transit_stop = transit_info.rsplit(",", 1)[0].strip()
                    if "," in transit_info:
                        # print(transit_info)
                        transit_value = transit_info.rsplit(",", 1)[-1].strip().split("m")[0].strip()  
                        if transit_value == '-' or not transit_value:
                            return False, f"No transit stop distance mentioned."
        
        if ('from ' in unit['current_city'] or 'to ' in unit['current_city']) and unit['transportation'] in ['','-']:
            return False, f"No transportation in day {i+1} is not allowed."
        
        if ('from ' not in unit['current_city'] and  ' to ' not in unit['current_city']) and unit['attraction'] in ['','-']:
            return False, f"No attaction in day {i+1} is not allowed."

        if i != question['days'] - 1 and unit['accommodation'] in ['','-']:
            return False, f"No accommodation in day {i+1} is not allowed."

        if (unit['breakfast'] in ['','-'] or unit['lunch'] in ['','-'] or unit['dinner'] in ['','-']) and 'from ' not in unit['current_city']:
            return False, f"No meal in day {i+1} is not allowed."
        
        if (unit['point_of_interest_list'] in ['','-']):
            return False, f"Point of Interest list will never be empty."
        

        for key in unit:
            if unit[key] and unit[key] != '-':
                total_valid_info += 1


    if total_valid_info * 1.0 / needed_info < 0.5:
        return False, f"The absent information is more than 50%."
    
    return True, None


def evaluation(query_data, tested_data):
    return_info = {}
    return_info['is_reasonable_visiting_city'] = is_reasonable_visiting_city(query_data, tested_data)
    return_info['is_valid_restaurants'] = is_valid_restaurants(query_data, tested_data)
    return_info['is_valid_attractions'] = is_valid_attractions(query_data, tested_data)
    # return_info['is_valid_accommodation'] = is_valid_accommodaton(query_data, tested_data)
    return_info['is_valid_transportation'] = is_valid_transportation(query_data, tested_data)
    return_info['is_valid_event'] = is_valid_event(query_data, tested_data) 
    return_info['is_valid_meal_gaps'] = is_valid_meal_gaps(query_data, tested_data)
    return_info['is_valid_poi_sequence'] = is_valid_poi_sequence(query_data, tested_data)
    return_info['is_valid_information_in_sandbox'] = is_valid_information_in_sandbox(query_data, tested_data) 
    return_info['is_valid_information_in_current_city'] = is_valid_information_in_current_city(query_data, tested_data) 
    return_info['is_not_absent'] = is_not_absent(query_data, tested_data)  
    return return_info

def boolean_evaluation(query_data, tested_data):
    return_info = {}
    return_info['is_reasonable_visiting_city'] = is_reasonable_visiting_city(query_data, tested_data)
    return_info['is_valid_restaurants'] = is_valid_restaurants(query_data, tested_data)
    return_info['is_valid_accommodation'] = is_valid_accommodaton(query_data, tested_data)
    return_info['is_valid_attractions'] = is_valid_attractions(query_data, tested_data)
    return_info['is_valid_transportation'] = is_valid_transportation(query_data, tested_data)
    return_info['is_valid_information_in_current_city'] = is_valid_information_in_current_city(query_data, tested_data)
    return_info['is_valid_information_in_sandbox'] = is_valid_information_in_sandbox(query_data, tested_data)
    return_info['is_not_absent'] = is_not_absent(query_data, tested_data)
    for key in return_info:
        if return_info[key][0] == False:
            print(return_info[key][1])
            return False
    return True
"""

from utils.func import get_valid_name_city, extract_before_parenthesis, extract_numbers_from_filenames
from tools.flights.apis import Flights
from tools.accommodations.apis import Accommodations
from tools.restaurants.apis import Restaurants
from tools.googleDistanceMatrix.apis import GoogleDistanceMatrix
from tools.attractions.apis import Attractions
from tools.events.apis import Events
import json
import re
import os
import sys
from tqdm import tqdm
import argparse
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import re
from datetime import datetime

_TIME_RE = re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b')

def _first_time(text: str):
    """Return 'HH:MM' or 'HH:MM:SS' from arbitrary text, or None."""
    if not text:
        return None
    m = _TIME_RE.search(str(text))
    return m.group(1) if m else None

def _parse_time(text: str):
    """Parse HH:MM or HH:MM:SS to a datetime.time, or None if not found/invalid."""
    s = _first_time(text)
    if not s:
        return None
    fmt = "%H:%M:%S" if s.count(":") == 2 else "%H:%M"
    try:
        return datetime.strptime(s, fmt).time()
    except Exception:
        return None

def _minutes_between(a_text: str, b_text: str):
    """Return minutes from a->b if both parse, else None."""
    a = _parse_time(a_text)
    b = _parse_time(b_text)
    if a is None or b is None:
        return None
    # Use a dummy date to subtract times
    A = datetime(2000,1,1, a.hour, a.minute, getattr(a, 'second', 0))
    B = datetime(2000,1,1, b.hour, b.minute, getattr(b, 'second', 0))
    return (B - A).total_seconds() / 60.0

def is_time_difference_valid(after_time, before_time, min_minutes):
    """
    Keep your original semantics: 'before_time' must be at least min_minutes
    AFTER 'after_time'. If either time can't be parsed, skip (return True).
    """
    mins = _minutes_between(after_time, before_time)
    if mins is None:
        # Can't parse → don't fail the plan just because of annotation noise
        return True
    return mins >= min_minutes

flight = Flights()
accommodation = Accommodations()
restaurants = Restaurants()
googleDistanceMatrix = GoogleDistanceMatrix()
attractions = Attractions()
events = Events()
pois = pd.read_csv('/scratch/sg/Priyanshu/TripCraft-main/ATP_database/all_poi_nearest_stops.csv')

city_state_set = open('/scratch/sg/Priyanshu/TripCraft-main/ATP_database/background/citySet_with_states_140.txt','r').read().split('\n')
city_state_map = {x: y for x, y in [unit.split('\t') for unit in city_state_set]}


def load_line_json_data(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f.read().strip().split('\n'):
            unit = json.loads(line)
            data.append(unit)
    return data


def count_consecutive_values(lst):
    if not lst:
        return []
    result = []
    current_string = lst[0]
    count = 1
    for i in range(1, len(lst)):
        if lst[i] == current_string:
            count += 1
        else:
            result.append((current_string, count))
            current_string = lst[i]
            count = 1
    result.append((current_string, count))
    return result


def transportation_match(text: str):
    tl = text.lower()
    if 'taxi' in tl:
        return 'Taxi'
    if 'self-driving' in tl:
        return 'Self-driving'
    if 'flight' in tl:
        return 'Flight'
    return None


def extract_from_to(text: str):
    """
    Extract 'A' and 'B' from 'from A to B' (B ends at comma or end).
    """
    pattern = r"from\s+(.+?)\s+to\s+([^,]+)(?=[,\s]|$)"
    matches = re.search(pattern, text)
    return matches.groups() if matches else (None, None)


def is_valid_city_sequence(city_list):
    # needs at least 3 entries (A B A)
    if len(city_list) < 3:
        return False
    visited = set()
    i = 0
    while i < len(city_list):
        city = city_list[i]
        if city in visited and (i != 0 and i != len(city_list) - 1):
            return False
        count = 0
        while i < len(city_list) and city_list[i] == city:
            count += 1
            i += 1
        if count == 1 and 0 < i - 1 < len(city_list) - 1:
            return False
        visited.add(city)
    return True


def is_reasonable_visiting_city(question, tested_data):
    city_list = []
    for i in range(min(question['days'], len(tested_data))):
        city_value = tested_data[i]['current_city']
        if 'from' in city_value and ' to ' in city_value:
            city1, city2 = extract_from_to(city_value)
            if i == 0 and city1 != question['org']:
                return False, f"The first day's city should be {question['org']}."
            city_list += [city1, city2]
        else:
            city_list.append(extract_before_parenthesis(city_value))

    if city_list[0] != city_list[-1]:
        return False, "The trip should be a closed circle."

    if not is_valid_city_sequence(city_list):
        return False, "The city sequence is invalid."

    for idx, city in enumerate(city_list):
        if city not in city_state_map:
            return False, f"{city} is not a valid city."
        if idx not in [0, len(city_list) - 1] and question['days'] > 3 and city_state_map[city] != question['dest']:
            return False, f"{city} is not in {question['dest']}."
    return True, None


def is_valid_restaurants(question, tested_data):
    restaurants_list = []
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        if unit.get('breakfast') and unit['breakfast'] != '-':
            if unit['breakfast'] in restaurants_list:
                return False, f"The restaurant in day {i+1} breakfast is repeated."
            restaurants_list.append(unit['breakfast'])
        if unit.get('lunch') and unit['lunch'] != '-':
            if unit['lunch'] in restaurants_list:
                return False, f"The restaurant in day {i+1} lunch {unit['lunch']} is repeated."
            restaurants_list.append(unit['lunch'])
        if unit.get('dinner') and unit['dinner'] != '-':
            if unit['dinner'] in restaurants_list:
                return False, f"The restaurant in day {i+1} dinner is repeated."
            restaurants_list.append(unit['dinner'])
    return True, None


def is_valid_attractions(question, tested_data):
    seen = set()
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        if unit.get('attraction') and unit['attraction'] != '-':
            for attraction in unit['attraction'].split(';'):
                attraction = attraction.strip()
                if attraction in seen:
                    return False, f"The attraction '{attraction}' in day {i+1} is repeated."
                seen.add(attraction)
    return True, None


def is_valid_event(question, tested_data):
    seen = set()
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        if unit.get('event') and unit['event'] != '-':
            for event in unit['event'].split(';'):
                event = event.strip()
                if event in seen:
                    return False, f"The event '{event}' in day {i+1} is repeated."
                seen.add(event)
    return True, None


def is_time_difference_valid(after_time, before_time, min_minutes):
    """
    Ensure 'before_time' occurs at least min_minutes after 'after_time'.
    (Directional; not absolute.)
    """
    from datetime import datetime
    fmt = "%H:%M"
    a = datetime.strptime(after_time, fmt)
    b = datetime.strptime(before_time, fmt)
    return (b - a).total_seconds() / 60 >= min_minutes


# def is_valid_poi_sequence(question, tested_data):
#     current_accommodation = "abc"
#     prev_accommodation = None

#     transition_days = set()
#     if question['days'] == 7:
#         transition_days = {3, 5, 7}
#     elif question['days'] == 5:
#         transition_days = {3, 5}
#     elif question['days'] == 3:
#         transition_days = {3}

#     for i in range(min(question['days'], len(tested_data))):
#         unit = tested_data[i]
#         if unit.get("accommodation") and unit["accommodation"] != "-":
#             current_accommodation = unit["accommodation"]

#         if "," in current_accommodation:
#             current_accommodation, city = current_accommodation.rsplit(",", 1)
#             current_accommodation = current_accommodation.strip()
#             city = city.strip()
#         else:
#             current_accommodation = current_accommodation.strip()
#             city = ""

#         poi_list = unit["point_of_interest_list"].split(";") if unit.get("point_of_interest_list") else []

#         # Transition-day rule (needs prior accom known)
#         if (i + 1) in transition_days and prev_accommodation:
#             if not (poi_list and prev_accommodation.strip() in poi_list[0] and current_accommodation.strip() in poi_list[-1]):
#                 return False, f"Day {i+1} PoI list must start with previous day's accommodation and end with current day's accommodation."
#         else:
#             # Standard daily start/end checks
#             if unit.get("accommodation") and unit["accommodation"] != "-":
#                 if not (poi_list and current_accommodation.strip() in poi_list[0] and current_accommodation.strip() in poi_list[-1]):
#                     return False, f"The PoI list for day {i+1} doesn't start and end with an accommodation."
#             else:
#                 if not (poi_list and current_accommodation.strip() in poi_list[0]):
#                     return False, f"The PoI list for day {i+1} doesn't start with an accommodation."

#         # Events should not appear in PoI list
#         if unit.get('event') and unit['event'] != '-':
#             events_list = list({e.rsplit(",", 1)[0].strip() for e in unit['event'].split(';') if e})
#             for et in events_list:
#                 if et and et in unit["point_of_interest_list"]:
#                     return False, f"The PoI list for day {i+1} shouldn't contain events."

#         # All attractions should appear in PoI list
#         if unit.get('attraction') and unit['attraction'] != '-':
#             attractions_list = list({attr.rsplit(",", 1)[0].strip() for attr in unit['attraction'].split(';') if attr})
#             for attr in attractions_list:
#                 if attr not in unit["point_of_interest_list"]:
#                     return False, f"The PoI list for day {i+1} doesn't contain all attractions."

#         # Meals should appear in PoI list
#         for meal in ['breakfast', 'lunch', 'dinner']:
#             if unit.get(meal) and unit[meal] != '-':
#                 food_place = unit[meal].rsplit(",", 1)[0].strip()
#                 if food_place not in unit["point_of_interest_list"]:
#                     return False, f"The PoI list for day {i+1} doesn't contain {meal}."

#         # Flight arrival/departure spacing (directional)
#         if unit.get('transportation') and all(x in unit['transportation'].lower() for x in ['flight', 'departure', 'arrival']):
#            tval = unit['transportation']
#         departure_time = None
#         arrival_time = None

#         # Try label-targeted extraction first:
#         m_dep = re.search(r'Departure\s*Time\s*:\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', tval, flags=re.IGNORECASE)
#         m_arr = re.search(r'Arrival\s*Time\s*:\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', tval, flags=re.IGNORECASE)
#         if m_dep:
#             departure_time = m_dep.group(1)
#         if m_arr:
#             arrival_time = m_arr.group(1)

#         # Fallback: just pick the first two clock times if labels aren’t present/clean
#         if not (departure_time and arrival_time):
#             times = _TIME_RE.findall(tval)
#             if times:
#                 if not departure_time and len(times) >= 1:
#                     departure_time = times[0]
#                 if not arrival_time and len(times) >= 2:
#                     arrival_time = times[1]

#             # First day's first PoI must be >= 30 mins after arrival
#             if i == 0 and poi_list and poi_list[0] not in ['-', '']:
#                 for part in poi_list[0].split(','):
#                     if 'stay from' in part or 'visit from' in part:
#                         first_start = part.split('from ')[1].split(' to ')[0].strip()
#                         if not is_time_difference_valid(arrival_time, first_start, 30):
#                             return False, f"First PoI on day {i+1} starts too soon after the flight arrival."

#             # For 3/5/7-day mid-arrival days (day 3, 5)
#             if question['days'] > 3 and i == 2 and poi_list and poi_list[0] not in ['-', '']:
#                 for part in poi_list[0].split(','):
#                     if 'stay from' in part or 'visit from' in part:
#                         first_start = part.split('from ')[1].split(' to ')[0].strip()
#                         if not is_time_difference_valid(arrival_time, first_start, 30):
#                             return False, f"First PoI on day {i+1} starts too soon after the flight arrival."

#             if question['days'] > 5 and i == 4 and poi_list and poi_list[0] not in ['-', '']:
#                 for part in poi_list[0].split(','):
#                     if 'stay from' in part or 'visit from' in part:
#                         first_start = part.split('from ')[1].split(' to ')[0].strip()
#                         if not is_time_difference_valid(arrival_time, first_start, 30):
#                             return False, f"First PoI on day {i+1} starts too soon after the flight arrival."

#             # Last day's last PoI must end >= 30 mins before departure
#             if i == len(tested_data) - 1 and poi_list and poi_list[-1] not in ['-', '']:
#                 for part in poi_list[-1].split(','):
#                     if 'stay from' in part or 'visit from' in part:
#                         last_end = part.split(' to ')[-1].strip()
#                         if not is_time_difference_valid(last_end, departure_time, 30):
#                             return False, f"Last PoI on day {i+1} ends too close to the flight departure."

#         if unit.get("accommodation") and unit["accommodation"] != "-":
#             prev_accommodation = current_accommodation

#     return True, None

import re

# Compile once; supports HH:MM or HH:MM:SS (24h)
_TIME_RE = re.compile(r'\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b', re.IGNORECASE)

def _norm_name(s: str) -> str:
    """Strip trailing ', City' etc. and whitespace."""
    if not s or s == '-':
        return ''
    return s.rsplit(',', 1)[0].strip()

def _first_start_time(poi_item: str):
    """Extract the first 'from HH:MM' time in a PoI entry, if present."""
    if not poi_item:
        return None
    m = re.search(r'from\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', poi_item, flags=re.IGNORECASE)
    return m.group(1) if m else None

def _last_end_time(poi_item: str):
    """Extract the last 'to HH:MM' time in a PoI entry, if present."""
    if not poi_item:
        return None
    m = re.search(r'to\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', poi_item, flags=re.IGNORECASE)
    return m.group(1) if m else None

def is_valid_poi_sequence(question, tested_data):
    """
    Softer, disruption-aware checks:
      - Uses substring matches with normalized accommodation names.
      - Treats missing PoI lists / missing accommodation as N/A (skip), not fail.
      - Ensures events aren't embedded in PoIs; attractions/meals that exist appear in PoIs.
      - Handles flight arrival/departure spacing if times are available (labels or plain times).
    """
    days = int(question.get('days', len(tested_data)))
    transition_days = {3} if days == 3 else ({3, 5} if days == 5 else ({3, 5, 7} if days == 7 else set()))

    prev_accommodation = ''
    current_accommodation = ''

    for i in range(min(days, len(tested_data))):
        unit = tested_data[i]

        # Track/normalize accommodation
        raw_acc = unit.get("accommodation")
        if raw_acc and raw_acc != "-":
            current_accommodation = raw_acc
        cur_acc_norm = _norm_name(current_accommodation)
        prev_acc_norm = _norm_name(prev_accommodation)

        # PoI list (gracefully handle missing/empty)
        poi_raw = unit.get("point_of_interest_list") or ''
        poi_list = [p.strip() for p in poi_raw.split(";") if p.strip()]
        if not poi_list:
            # Not enough info to judge -> skip this day
            if raw_acc and raw_acc != "-":
                prev_accommodation = current_accommodation
            continue

        # ---- Start/End accommodation rules ----
        day_no = i + 1
        if (day_no in transition_days) and prev_acc_norm:
            # On transition days, expect start with previous acc and end with current acc.
            start_ok = prev_acc_norm and (prev_acc_norm in poi_list[0])
            end_ok = cur_acc_norm and (cur_acc_norm in poi_list[-1])
            # Soften for disruptions: accept if at least one side matches; fail only if neither does.
            if not (start_ok or end_ok):
                return False, f"Day {day_no}: PoIs should start with previous accommodation or end with current accommodation."
        else:
            # Regular day: require start OR end with today's accommodation (softened)
            if cur_acc_norm:
                start_ok = cur_acc_norm in poi_list[0]
                end_ok = cur_acc_norm in poi_list[-1]
                if not (start_ok or end_ok):
                    return False, f"Day {day_no}: PoIs should start or end with the accommodation."
            # If no accommodation known for the day -> skip this check

        # ---- Events must not appear in PoIs ----
        ev_raw = unit.get('event')
        if ev_raw and ev_raw != '-':
            ev_names = {e.rsplit(",", 1)[0].strip() for e in ev_raw.split(';') if e.strip()}
            for ev in ev_names:
                if ev and any(ev in poi for poi in poi_list):
                    return False, f"Day {day_no}: PoI list contains event '{ev}'."

        # ---- All attractions (if listed) should appear in PoIs ----
        at_raw = unit.get('attraction')
        if at_raw and at_raw != '-':
            at_names = {a.rsplit(",", 1)[0].strip() for a in at_raw.split(';') if a.strip()}
            for at in at_names:
                if at and not any(at in poi for poi in poi_list):
                    return False, f"Day {day_no}: attraction '{at}' missing from PoIs."

        # ---- Meals listed should appear in PoIs ----
        for meal in ['breakfast', 'lunch', 'dinner']:
            m_raw = unit.get(meal)
            if m_raw and m_raw != '-':
                food = m_raw.rsplit(",", 1)[0].strip()
                if food and not any(food in poi for poi in poi_list):
                    return False, f"Day {day_no}: {meal} '{food}' missing from PoIs."

        # ---- Flight arrival / departure spacing ----
        # Always define tval, and parse both labeled and unlabeled times
        tval = unit.get('transportation') or ''
        dep_match = re.search(r'Departure\s*Time\s*:\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', tval, flags=re.IGNORECASE)
        arr_match = re.search(r'Arrival\s*Time\s*:\s*([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)', tval, flags=re.IGNORECASE)
        departure_time = dep_match.group(1) if dep_match else None
        arrival_time = arr_match.group(1) if arr_match else None

        # Fallback: pull the first two clock-like times if labels are missing
        if not (departure_time or arrival_time):
            times = _TIME_RE.findall(tval)
            if len(times) >= 1 and not departure_time:
                departure_time = times[0]
            if len(times) >= 2 and not arrival_time:
                arrival_time = times[1]

        # First day's first PoI should be >= 30 min after arrival, if we have arrival time
        if i == 0 and arrival_time and poi_list:
            first_start = _first_start_time(poi_list[0])
            if first_start and not is_time_difference_valid(arrival_time, first_start, 30):
                return False, f"Day {day_no}: first PoI starts too soon after flight arrival."

        # Mid-arrival checks for 5d/7d templates (day 3 and 5 if times known)
        if days >= 5 and i == 2 and arrival_time and poi_list:
            first_start = _first_start_time(poi_list[0])
            if first_start and not is_time_difference_valid(arrival_time, first_start, 30):
                return False, f"Day {day_no}: first PoI starts too soon after flight arrival."
        if days >= 7 and i == 4 and arrival_time and poi_list:
            first_start = _first_start_time(poi_list[0])
            if first_start and not is_time_difference_valid(arrival_time, first_start, 30):
                return False, f"Day {day_no}: first PoI starts too soon after flight arrival."

        # Last day's last PoI should end >= 30 min before departure, if we have departure time
        is_last_day = (i == min(days, len(tested_data)) - 1)
        if is_last_day and departure_time and poi_list:
            last_end = _last_end_time(poi_list[-1])
            if last_end and not is_time_difference_valid(last_end, departure_time, 30):
                return False, f"Day {day_no}: last PoI ends too close to flight departure."

        # Update previous accommodation for next day
        if raw_acc and raw_acc != "-":
            prev_accommodation = current_accommodation

    return True, None

def is_valid_meal_gaps(question, tested_data):
    for i in range(min(question['days'], len(tested_data))):
        day_plan = tested_data[i]
        meal_times = {}
        if not day_plan.get("point_of_interest_list"):
            continue
        poi_info = day_plan["point_of_interest_list"].split(";")
        for meal in ["breakfast", "lunch", "dinner"]:
            if meal in day_plan and day_plan[meal] != "-":
                for poi in poi_info:
                    meal_name = day_plan[meal]
                    if "," in meal_name:
                        meal_name, _city = meal_name.rsplit(",", 1)
                        meal_name = meal_name.strip()
                    else:
                        meal_name = meal_name.strip()
                    if meal_name in poi and poi not in ['-', '']:
                        try:
                            time_info = poi.split("from")[1].split("to")
                        except Exception:
                            try:
                                time_info = poi.rsplit("from", 1)[1].split("to")
                            except Exception:
                                return False, f"Incorrect format."
                        try:
                            start_time = time_info[0].strip()
                            end_time = time_info[1].split(",")[0].strip()
                            sh = int(start_time.split(":")[0]) + int(start_time.split(":")[1]) / 60
                            eh = int(end_time.split(":")[0]) + int(end_time.split(":")[1]) / 60
                        except Exception:
                            return False, f"PoI time intervals are not in correct format."
                        meal_times[meal] = (sh, eh)
                        break

        order = ["breakfast", "lunch", "dinner"]
        for j in range(len(order) - 1):
            m1, m2 = order[j], order[j + 1]
            if m1 in meal_times and m2 in meal_times:
                _, end1 = meal_times[m1]
                start2, _ = meal_times[m2]
                if start2 - end1 < 4:
                    return False, f"Not sufficient time gap between {m1} and {m2} of day {i+1}"
    return True, None


def is_valid_transportation(question, tested_data):
    if not tested_data[0].get('transportation') or tested_data[0]['transportation'] == '-':
        return False, "The transportation in day 1 should not be empty."
    for i in range(min(question['days'], len(tested_data))):
        t = tested_data[i].get('transportation')
        if not t or t == '-':
            continue
        modes = set()
        tl = t.lower()
        for m in ('flight', 'taxi', 'self-driving'):
            if m in tl:
                modes.add(m)
        # conflict only within the same day (taxi vs self-driving)
        if 'taxi' in modes and 'self-driving' in modes:
            return False, f"The transportation is conflicting on day {i+1}."
    return True, None


def is_valid_information_in_current_city(question, tested_data):
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        current_city = unit['current_city'].strip()
        final_city_list = []
        if 'from' in current_city and ' to ' in current_city:
            city1, city2 = extract_from_to(current_city)
            final_city_list = [city1, city2]
        else:
            # Accept single-city days
            final_city_list = [extract_before_parenthesis(current_city)]

        # Transportation sanity (if not ground, at least mention one of the cities)
        if unit.get('transportation') and unit['transportation'] != '-':
            val = unit['transportation']
            if ('Self-driving' not in val and 'Taxi' not in val):
                if not any(c and c in val for c in final_city_list):
                    return False, f"The transportation in day {i+1} is invalid city choice."

        # Meals must reference the day's city/cities
        for meal in ('breakfast', 'lunch', 'dinner'):
            if unit.get(meal) and unit[meal] != '-':
                if not any(c and c in unit[meal] for c in final_city_list):
                    return False, f"The {meal} in day {i+1} is invalid city choice."

        # Attractions must reference the day's city/cities
        if unit.get('attraction') and unit['attraction'] != '-':
            for attraction in unit['attraction'].split(';'):
                if not any(c and c in attraction for c in final_city_list):
                    return False, f"The attraction in day {i+1} is invalid city choice."

        # Accommodation should be in the *last* city that day
        if unit.get('accommodation') and unit['accommodation'] != '-':
            if final_city_list[-1] not in unit['accommodation']:
                return False, f"The accommodation in day {i+1} is invalid city choice."
    return True, None


def is_valid_information_in_sandbox(question, tested_data):
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]

        # ---- transportation ----
        if unit.get('transportation') and unit['transportation'] != '-':
            value = unit['transportation']
            org_city, dest_city = extract_from_to(unit['current_city'])
            if 'flight number' in value.lower():
                try:
                    org_city = extract_before_parenthesis(org_city)
                    dest_city = extract_before_parenthesis(dest_city)
                except TypeError:
                    org_city, dest_city = extract_from_to(unit['transportation'])
                try:
                    if len(flight.data[(flight.data['Flight Number'] == value.split('Flight Number: ')[1].split(',')[0]) &
                                       (flight.data['OriginCityName'] == org_city) &
                                       (flight.data['DestCityName'] == dest_city)]) < 1:
                        return False, f"The flight number in day {i+1} is invalid in the sandbox."
                except Exception:
                    return False, f"Incorrect Flight format."
            elif 'self-driving' in value.lower() or 'taxi' in value.lower():
                try:
                    org_city = extract_before_parenthesis(org_city)
                    dest_city = extract_before_parenthesis(dest_city)
                except TypeError:
                    org_city = '-'
                    dest_city = '-'
                mode = 'self-driving' if 'self-driving' in value.lower() else 'taxi'
                res = googleDistanceMatrix.run_for_evaluation(org_city, dest_city, mode=mode)
                if res.get('cost') is None:
                    return False, f"The {mode} in day {i+1} is invalid in the sandbox."

        # ---- meals ----
        if 'breakfast' in unit and unit['breakfast'] and unit['breakfast'] != '-':
            name, city = get_valid_name_city(unit['breakfast'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) &
                                    (restaurants.data['City'] == city)]) < 1:
                return False, f"The breakfast in day {i+1} is invalid in the sandbox."
        elif 'breakfast' not in unit:
            return False, f"No Breakfast Info."

        if 'lunch' in unit and unit['lunch'] and unit['lunch'] != '-':
            name, city = get_valid_name_city(unit['lunch'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) &
                                    (restaurants.data['City'] == city)]) < 1:
                return False, f"The lunch in day {i+1} is invalid in the sandbox."
        elif 'lunch' not in unit:
            return False, f"No Lunch Info."

        if 'dinner' in unit and unit['dinner'] and unit['dinner'] != '-':
            name, city = get_valid_name_city(unit['dinner'])
            if len(restaurants.data[(restaurants.data['name'].astype(str).str.contains(re.escape(name))) &
                                    (restaurants.data['City'] == city)]) < 1:
                return False, f"The dinner in day {i+1} is invalid in the sandbox."
        elif 'dinner' not in unit:
            return False, f"No Dinner Info."

        # ---- attractions ----
        if unit.get('attraction') and unit['attraction'] != '-':
            for attraction in unit['attraction'].split(';'):
                name, city = get_valid_name_city(attraction)
                if len(attractions.data[(attractions.data['name'].astype(str).str.contains(re.escape(name))) &
                                        (attractions.data['City'] == city)]) < 1:
                    return False, f"The attraction {attraction} in day {i+1} is invalid in the sandbox."

        # ---- events ----
        if unit.get('event') and unit['event'] != '-':
            for event in unit['event'].split(';'):
                name = event.rsplit(',', 1)[0].strip()
                city = event.rsplit(",", 1)[-1].strip()
                if len(events.data[(events.data['name'].astype(str).str.contains(re.escape(name))) &
                                   (events.data['city'] == city)]) < 1:
                    return False, f"The event {event} in day {i+1} is invalid in the sandbox."

        # ---- accommodation ----
        if 'accommodation' in unit and unit['accommodation'] and unit['accommodation'] != '-':
            name, city = get_valid_name_city(unit['accommodation'])
            if len(accommodation.data[(accommodation.data['name'].astype(str).str.contains(re.escape(name))) &
                                      (accommodation.data['City'] == city)]) < 1:
                return False, f"The accommodation in day {i+1} is invalid in the sandbox."
        elif 'accommodation' not in unit:
            return False, f"No Accommodation Info."

        # ---- PoI nearest transit ----
        if unit.get('point_of_interest_list') and unit['point_of_interest_list'] != '-':
            poi_info = unit["point_of_interest_list"].split(";")
            for poi in poi_info:
                if "nearest transit:" in poi:
                    transit_info = poi.split("nearest transit:")[1].strip()
                    poi_name = poi.split("nearest transit:")[0].strip()[:-1].rsplit(",", 1)[0].strip()
                    transit_stop = transit_info.rsplit(",", 1)[0].strip()
                    if "," in transit_info:
                        transit_value = transit_info.rsplit(",", 1)[-1].strip().split("m")[0].strip()
                        try:
                            stop_distance = float(transit_value)
                        except Exception:
                            stop_distance = 0.0
                    else:
                        return False, f"PoI list is not formatted correctly."

                    try:
                        days = question['days']
                        if days == 3:
                            if (i + 1) == 3:
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                            else:
                                city = unit['current_city'].split(" to ")[-1].strip() if ' to ' in unit['current_city'] else extract_before_parenthesis(unit['current_city'])
                            if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                        (pois['PoI'] == poi_name) &
                                        (pois['City'] == city) &
                                        (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                        if days == 5:
                            if (i + 1) == 3:
                                org_city, dest_city = extract_from_to(unit['current_city'])
                                ok = len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                              (pois['PoI'] == poi_name) &
                                              (pois['City'] == extract_before_parenthesis(org_city)) &
                                              (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) >= 1
                                if not ok:
                                    ok = len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                                  (pois['PoI'] == poi_name) &
                                                  (pois['City'] == extract_before_parenthesis(dest_city)) &
                                                  (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) >= 1
                                if not ok:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            elif (i + 1) == 5:
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                            (pois['PoI'] == poi_name) &
                                            (pois['City'] == city) &
                                            (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            else:
                                city = extract_before_parenthesis(unit['current_city'].split(" to ")[-1]) if ' to ' in unit['current_city'] else extract_before_parenthesis(unit['current_city'])
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                            (pois['PoI'] == poi_name) &
                                            (pois['City'] == city) &
                                            (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                        if days == 7:
                            org_city, dest_city = extract_from_to(unit['current_city'])
                            if (i + 1) in (3, 5):
                                ok = len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                              (pois['PoI'] == poi_name) &
                                              (pois['City'] == extract_before_parenthesis(org_city)) &
                                              (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) >= 1
                                if not ok:
                                    ok = len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                                  (pois['PoI'] == poi_name) &
                                                  (pois['City'] == extract_before_parenthesis(dest_city)) &
                                                  (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) >= 1
                                if not ok:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            elif (i + 1) == 7:
                                city = unit['current_city'].split("from ")[-1].split(" to ")[0].strip()
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                            (pois['PoI'] == poi_name) &
                                            (pois['City'] == city) &
                                            (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                            else:
                                city = extract_before_parenthesis(unit['current_city'].split(" to ")[-1]) if ' to ' in unit['current_city'] else extract_before_parenthesis(unit['current_city'])
                                if len(pois[(pois['nearest_stop_name'].astype(str).str.contains(re.escape(transit_stop))) &
                                            (pois['PoI'] == poi_name) &
                                            (pois['City'] == city) &
                                            (abs(pois['nearest_stop_distance'] - stop_distance) <= 5)]) < 1:
                                    return False, f"The PoI nearest stops in day {i+1} have hallucinated data."
                    except Exception as e:
                        return False, f"Incorrect format. Error: {str(e)}"
    return True, None


def is_valid_accommodaton(question, tested_data):
    data = []
    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]
        if 'accommodation' not in unit:
            return False, f"No Accommodation Info."
        data.append(unit['accommodation'])
    consecutive = count_consecutive_values(data)
    for name_city, nights in consecutive:
        if name_city and name_city not in ['-', '']:
            name, city = get_valid_name_city(name_city)
            rows = accommodation.data[(accommodation.data['name'].astype(str).str.contains(re.escape(name))) &
                                      (accommodation.data['City'] == city)]
            if len(rows) == 1 and nights < rows.iloc[0]['minimum nights']:
                return False, f"The accommodation {name_city} does not obey the minimum nights rule."
    return True, None


def is_valid_visiting_city_number(question, tested_data):
    city_set = set()
    for i in range(min(question['days'], len(tested_data))):
        city_value = tested_data[i]['current_city']
        if 'from' in city_value and ' to ' in city_value:
            city1, city2 = extract_from_to(city_value)
            city1 = extract_before_parenthesis(city1)
            city2 = extract_before_parenthesis(city2)
            if i == 0 and city1 != question['org']:
                return False, f"The first day's city should be {question['org']}."
            city_set.add(city1)
            city_set.add(city2)
        else:
            city_set.add(extract_before_parenthesis(city_value))
    city_set.discard(question['org'])
    if len(city_set) != question['visiting_city_number']:
        return False, f"The number of visiting cities should be {question['visiting_city_number']}."
    return True, None


def is_valid_days(question, tested_data):
    lens = 0
    for i in range(min(question['days'], len(tested_data))):
        if tested_data[i] != {} and tested_data[i]['current_city'] != "You don't need to fill in the information for this or later days.":
            lens += 1
    if lens != question['days']:
        return False, f"The number of days should be {question['days']}."
    return True, None


def is_not_absent(question, tested_data):
    needed_info = 8 * question['days']
    total_valid_info = 0

    ok, _ = is_valid_days(question, tested_data)
    if not ok:
        return False, "Invalid Days"

    ok, _ = is_valid_visiting_city_number(question, tested_data)
    if not ok:
        return False, "Invalid City Number"

    for i in range(min(question['days'], len(tested_data))):
        unit = tested_data[i]

        for field, msg in [
            ('transportation', "No Transportation Info."),
            ('breakfast', "No Breakfast Info."),
            ('lunch', "No Lunch Info."),
            ('dinner', "No Dinner Info."),
            ('attraction', "No Attraction Info."),
            ('accommodation', "No Accommodation Info."),
            ('event', "No Event Info."),
            ('point_of_interest_list', "No PoI Info."),
        ]:
            if field not in unit:
                return False, msg

        if unit['point_of_interest_list'] and unit['point_of_interest_list'] != '-':
            for poi in unit["point_of_interest_list"].split(";"):
                if "nearest transit:" in poi:
                    transit_info = poi.split("nearest transit:")[1].strip()
                    if "," in transit_info:
                        transit_value = transit_info.rsplit(",", 1)[-1].strip().split("m")[0].strip()
                        if transit_value == '-' or not transit_value:
                            return False, f"No transit stop distance mentioned."

        if ('from ' in unit['current_city'] or ' to ' in unit['current_city']) and unit['transportation'] in ['', '-']:
            return False, f"No transportation in day {i+1} is not allowed."

        if ('from ' not in unit['current_city'] and ' to ' not in unit['current_city']) and unit['attraction'] in ['', '-']:
            return False, f"No attaction in day {i+1} is not allowed."

        if i != question['days'] - 1 and unit['accommodation'] in ['', '-']:
            return False, f"No accommodation in day {i+1} is not allowed."

        if (unit['breakfast'] in ['', '-'] or unit['lunch'] in ['', '-'] or unit['dinner'] in ['', '-']) and 'from ' not in unit['current_city']:
            return False, f"No meal in day {i+1} is not allowed."

        if (unit['point_of_interest_list'] in ['', '-']):
            return False, f"Point of Interest list will never be empty."

        for key in unit:
            if unit[key] and unit[key] != '-':
                total_valid_info += 1

    if total_valid_info / float(needed_info) < 0.5:
        return False, f"The absent information is more than 50%."
    return True, None


def evaluation(query_data, tested_data):
    return_info = {}
    return_info['is_reasonable_visiting_city'] = is_reasonable_visiting_city(query_data, tested_data)
    return_info['is_valid_restaurants'] = is_valid_restaurants(query_data, tested_data)
    return_info['is_valid_attractions'] = is_valid_attractions(query_data, tested_data)
    # return_info['is_valid_accommodation'] = is_valid_accommodaton(query_data, tested_data)
    return_info['is_valid_transportation'] = is_valid_transportation(query_data, tested_data)
    return_info['is_valid_event'] = is_valid_event(query_data, tested_data)
    return_info['is_valid_meal_gaps'] = is_valid_meal_gaps(query_data, tested_data)
    return_info['is_valid_poi_sequence'] = is_valid_poi_sequence(query_data, tested_data)
    return_info['is_valid_information_in_sandbox'] = is_valid_information_in_sandbox(query_data, tested_data)
    return_info['is_valid_information_in_current_city'] = is_valid_information_in_current_city(query_data, tested_data)
    return_info['is_not_absent'] = is_not_absent(query_data, tested_data)
    return return_info


def boolean_evaluation(query_data, tested_data):
    return_info = {}
    return_info['is_reasonable_visiting_city'] = is_reasonable_visiting_city(query_data, tested_data)
    return_info['is_valid_restaurants'] = is_valid_restaurants(query_data, tested_data)
    return_info['is_valid_accommodation'] = is_valid_accommodaton(query_data, tested_data)
    return_info['is_valid_attractions'] = is_valid_attractions(query_data, tested_data)
    return_info['is_valid_transportation'] = is_valid_transportation(query_data, tested_data)
    return_info['is_valid_information_in_current_city'] = is_valid_information_in_current_city(query_data, tested_data)
    return_info['is_valid_information_in_sandbox'] = is_valid_information_in_sandbox(query_data, tested_data)
    return_info['is_not_absent'] = is_not_absent(query_data, tested_data)
    for key in return_info:
        if return_info[key][0] is False:
            print(return_info[key][1])
            return False
    return True
