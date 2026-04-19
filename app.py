from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import Counter

load_dotenv()

app = Flask(__name__)

def get_weather(city):
    api_key = os.getenv('API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        print("ERROR: API key not set or still has placeholder value")
        return None
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        print(f"API Response Status: {response.status_code}")
        print(f"API Response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            # Convert Unix timestamps to readable time format
            sunrise_time = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%I:%M %p')
            sunset_time = datetime.fromtimestamp(data['sys']['sunset']).strftime('%I:%M %p')
            
            weather = {
                'temp': round(data['main']['temp']),
                'description': data['weather'][0]['description'].capitalize(),
                'icon': data['weather'][0]['icon'],
                'humidity': data['main']['humidity'],
                'feels_like': round(data['main']['feels_like']),
                'wind_speed': round(data['wind']['speed'], 1),
                'sunrise': sunrise_time,
                'sunset': sunset_time,
                'sunrise_24': sunrise_time.replace(' AM', '').replace(' PM', ''),  # Will be converted by JS
                'sunset_24': sunset_time.replace(' AM', '').replace(' PM', '')     # Will be converted by JS
            }
            return weather
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Request Exception: {e}")
        return None

def get_clothing_suggestions(weather):
    """Generate clothing suggestions based on weather conditions"""
    temp = weather['feels_like']  # Use feels_like for more accurate suggestions
    description = weather['description'].lower()
    humidity = weather['humidity']
    wind_speed = weather['wind_speed']
    
    suggestions = []
    
    # Temperature-based suggestions
    if temp < 0:
        suggestions.extend(['Heavy winter coat', 'Thermal underwear', 'Warm hat', 'Gloves', 'Scarf', 'Winter boots'])
    elif temp < 5:
        suggestions.extend(['Winter coat', 'Sweater', 'Hat', 'Gloves', 'Warm pants', 'Boots'])
    elif temp < 10:
        suggestions.extend(['Light coat or jacket', 'Long-sleeve shirt', 'Jeans or warm pants', 'Closed-toe shoes'])
    elif temp < 15:
        suggestions.extend(['Light jacket or sweater', 'Long-sleeve shirt', 'Jeans', 'Comfortable shoes'])
    elif temp < 20:
        suggestions.extend(['Light sweater or hoodie', 'T-shirt', 'Jeans or chinos', 'Sneakers'])
    elif temp < 25:
        suggestions.extend(['T-shirt', 'Light pants or shorts', 'Sandals or sneakers'])
    elif temp < 30:
        suggestions.extend(['Light T-shirt', 'Shorts', 'Sandals', 'Sunglasses'])
    else:
        suggestions.extend(['Very light clothing', 'Tank top', 'Shorts', 'Sandals', 'Hat for sun protection'])
    
    # Weather condition adjustments
    if 'rain' in description or 'drizzle' in description:
        suggestions.extend(['Umbrella', 'Rain jacket or poncho', 'Water-resistant shoes', 'Rain boots'])
    elif 'snow' in description:
        suggestions.extend(['Snow boots', 'Snow pants', 'Warm waterproof gloves'])
    elif 'sunny' in description or 'clear' in description:
        suggestions.extend(['Sunglasses', 'Sunscreen', 'Hat or cap'])
    elif 'cloudy' in description:
        suggestions.append('Light jacket (just in case)')
    
    # Humidity and wind considerations
    if humidity > 80:
        suggestions.append('Breathable clothing')
    if wind_speed > 10:
        suggestions.extend(['Windbreaker', 'Hat to keep hair in place'])
    
    # Remove duplicates and limit to most relevant suggestions
    unique_suggestions = []
    seen = set()
    for item in suggestions:
        if item not in seen:
            unique_suggestions.append(item)
            seen.add(item)
    
    return unique_suggestions[:8]  # Limit to 8 suggestions


def get_day_vibe(description, temp):
    """Return a short mood phrase for the day."""
    desc = description.lower()
    if 'storm' in desc or 'thunder' in desc:
        return "stay in, stay warm"
    elif 'rain' in desc or 'drizzle' in desc:
        return "a soft, slow kind of day"
    elif 'snow' in desc:
        return "a cosy, quiet kind of day"
    elif 'clear' in desc or 'sunny' in desc:
        return "bright and open skies" if temp > 22 else "crisp and clear out there"
    elif 'cloud' in desc:
        return "gentle light, easy pace"
    else:
        return "a calm, unhurried day"


def get_activity_suggestion(description, temp, humidity, wind_speed):
    """Return one specific activity to remove the decision of what to do."""
    import random
    desc = description.lower()

    # Storm / thunder — stay in, low energy
    if 'storm' in desc or 'thunder' in desc:
        return random.choice([
            "Put on a documentary and let your mind wander",
            "Make a warm drink and work through a jigsaw puzzle",
            "Write down three things you want to do this week",
        ])

    # Rain or drizzle — indoor calm
    if 'rain' in desc or 'drizzle' in desc:
        if temp < 10:
            return random.choice([
                "Curl up with a book and a blanket",
                "Try a 20-minute guided meditation",
                "Do a slow, full-body stretch — 15 minutes is enough",
            ])
        else:
            return random.choice([
                "Put on music and do some watercolour or doodling",
                "Pick up a book you've been meaning to start",
                "Work on a puzzle — no time limit, no pressure",
            ])

    # Snow — gentle indoor or outdoor
    if 'snow' in desc:
        return random.choice([
            "Take a slow walk in the snow if it's safe — 10 minutes is plenty",
            "Make something warm from scratch — soup, porridge, tea",
            "Settle in with a long book or a film you've been saving",
        ])

    # Hot and sunny (above 28°C) — avoid midday heat
    if ('clear' in desc or 'sunny' in desc) and temp >= 28:
        return random.choice([
            "Go outside early morning or after 5pm — avoid the midday heat",
            "Find a shaded spot and read outside for 30 minutes",
            "Do a light swim or cool-down walk in the evening",
        ])

    # Warm and clear (20–28°C) — get outside
    if ('clear' in desc or 'sunny' in desc) and temp >= 20:
        return random.choice([
            "Take a 20-minute walk with no destination in mind",
            "Sit outside with a drink and just observe — no phone",
            "Go for a gentle cycle or an easy jog",
        ])

    # Cool and clear (10–20°C) — brisk outdoor
    if ('clear' in desc or 'sunny' in desc) and temp >= 10:
        return random.choice([
            "Bundle up and take a brisk 15-minute walk",
            "Visit a park or green space — even briefly",
            "Do some light stretching outdoors in the fresh air",
        ])

    # Cloudy and mild — flexible
    if 'cloud' in desc and 10 <= temp <= 22:
        return random.choice([
            "Go for a slow walk — overcast light is actually very easy on the eyes",
            "Find a café, order something warm, and read or sketch",
            "Do a 20-minute body-weight stretch or yoga flow",
        ])

    # Cold (below 10°C) — indoor warmth
    if temp < 10:
        return random.choice([
            "Do a slow 15-minute stretch to warm up your body",
            "Make something with your hands — cook, draw, write",
            "Take a nap if you need one — cold days are made for rest",
        ])

    # Windy — short outdoor or indoor
    if wind_speed > 10:
        return random.choice([
            "Keep outdoor time short — a quick 10-minute walk is enough",
            "Stay in and do something creative with your hands",
            "Do a home workout — bodyweight exercises, no equipment needed",
        ])

    # High humidity — easy indoors
    if humidity > 80:
        return random.choice([
            "Keep it light — try reading, sketching, or listening to a podcast",
            "Do a gentle stretch inside where it's cool",
            "Take a cool shower then rest — humidity drains energy quietly",
        ])

    # Default
    return random.choice([
        "Take a 15-minute walk and notice three things you haven't seen before",
        "Spend 20 minutes on something creative — no pressure, no goal",
        "Make a warm drink and sit without a screen for 10 minutes",
    ])


def get_meal_drink_nudge(description, temp, humidity, wind_speed):
    """Return one specific meal/drink nudge for light meal-prep planning."""
    import random
    desc = description.lower()

    if 'storm' in desc or 'thunder' in desc:
        return random.choice([
            "Meal prep: one-pot lentil soup + ginger tea",
            "Meal prep: baked potatoes + veggie chili",
            "Drink nudge: hot cocoa or cinnamon tea",
        ])

    if 'rain' in desc or 'drizzle' in desc:
        if temp < 12:
            return random.choice([
                "Meal prep: tomato soup + grilled cheese",
                "Meal prep: chickpea curry + rice",
                "Drink nudge: masala chai or peppermint tea",
            ])
        return random.choice([
            "Meal prep: pasta salad + boiled eggs",
            "Meal prep: wrap fillings (beans, greens, hummus)",
            "Drink nudge: warm lemon water",
        ])

    if 'snow' in desc:
        return random.choice([
            "Meal prep: hearty stew for 2 days",
            "Meal prep: oatmeal jars + mixed nuts",
            "Drink nudge: ginger-honey tea",
        ])

    if ('clear' in desc or 'sunny' in desc) and temp >= 28:
        return random.choice([
            "Meal prep: cold noodle bowls + cucumber",
            "Meal prep: watermelon + yogurt cups",
            "Drink nudge: water + electrolytes",
        ])

    if ('clear' in desc or 'sunny' in desc) and temp >= 20:
        return random.choice([
            "Meal prep: grain bowls + roasted veggies",
            "Meal prep: chicken/tofu wraps",
            "Drink nudge: iced green tea",
        ])

    if temp < 10:
        return random.choice([
            "Meal prep: overnight oats + fruit",
            "Meal prep: soup + toast combo",
            "Drink nudge: warm herbal tea",
        ])

    if humidity > 80:
        return random.choice([
            "Meal prep: light rice bowl + steamed veg",
            "Meal prep: yogurt parfait jars",
            "Drink nudge: extra water all day",
        ])

    if wind_speed > 10:
        return random.choice([
            "Meal prep: easy stir-fry boxes",
            "Meal prep: sandwich kit + fruit",
            "Drink nudge: one thermos of tea",
        ])

    return random.choice([
        "Meal prep: simple protein + veg + carb box",
        "Meal prep: burrito bowl batch",
        "Drink nudge: keep a water bottle nearby",
    ])


def apply_batch_prep_hints(daily):
    """Add batch-prep notes for similar back-to-back forecast days."""

    def weather_family(description):
        desc = description.lower()
        if 'storm' in desc or 'thunder' in desc:
            return 'storm'
        if 'rain' in desc or 'drizzle' in desc:
            return 'rain'
        if 'snow' in desc:
            return 'snow'
        if 'clear' in desc or 'sunny' in desc:
            return 'sun'
        if 'cloud' in desc:
            return 'cloud'
        return 'mixed'

    for day in daily:
        day['batch_note'] = ''

    for idx in range(len(daily) - 1):
        current_day = daily[idx]
        next_day = daily[idx + 1]

        current_family = weather_family(current_day['description'])
        next_family = weather_family(next_day['description'])
        temp_close = abs(current_day['feels_like'] - next_day['feels_like']) <= 4
        same_family = current_family == next_family

        current_is_meal = current_day.get('meal_nudge', '').startswith('Meal prep:')
        next_is_meal = next_day.get('meal_nudge', '').startswith('Meal prep:')

        if same_family and temp_close and current_is_meal and next_is_meal:
            if not current_day['batch_note']:
                current_day['batch_note'] = f"Batch tip: cook double and use leftovers on {next_day['weekday_short']}."
            if not next_day['batch_note']:
                next_day['batch_note'] = f"Batch tip: leftover day from {current_day['weekday_short']}."

    for day in daily:
        if not day['batch_note'] and day.get('meal_nudge', '').startswith('Meal prep:'):
            day['batch_note'] = 'Batch tip: make 2 extra portions for an easier next day.'

    return daily


def get_daily_briefing(weather, clothing_suggestions, activity_suggestion, meal_nudge):
    """Build a compact low-decision daily briefing."""
    desc = weather['description'].lower()
    carry_item = 'Sunglasses'
    if 'rain' in desc or 'drizzle' in desc:
        carry_item = 'Umbrella'
    elif 'snow' in desc:
        carry_item = 'Gloves'
    elif weather['wind_speed'] > 10:
        carry_item = 'Windbreaker'

    wear_now = clothing_suggestions[0] if clothing_suggestions else 'Comfortable layered outfit'

    return {
        'headline': 'Here is your low-decision plan.',
        'wear_now': wear_now,
        'carry_item': carry_item,
        'activity': activity_suggestion,
        'meal': meal_nudge,
    }


def get_wind_down_bag_plan(tomorrow):
    """Create a simple tomorrow bag checklist based on forecast cues."""
    if not tomorrow:
        return {
            'headline': 'Wind-down briefing: set up your bag for tomorrow.',
            'tomorrow_weekday': 'tomorrow',
            'items': [
                'Wear (tomorrow): set out one ready-to-wear outfit.',
                'Carry (tomorrow): choose one weather item.',
                'Add a reusable water bottle.',
                'Pack one snack so you are not running on empty.'
            ]
        }

    desc = tomorrow.get('description', '').lower()
    carry = 'Sunglasses'
    if 'rain' in desc or 'drizzle' in desc:
        carry = 'Umbrella'
    elif 'snow' in desc:
        carry = 'Gloves'
    elif tomorrow.get('wind_speed', 0) > 10:
        carry = 'Windbreaker'

    top_clothing = tomorrow.get('clothing', [])
    outfit = top_clothing[0] if top_clothing else 'Comfortable layered outfit'

    meal_nudge = tomorrow.get('meal_nudge', '')
    fuel_item = 'Pack one snack so you are not running on empty.'
    if meal_nudge.startswith('Meal prep:'):
        fuel_item = f"Bring leftovers: {meal_nudge.replace('Meal prep:', '').strip()}"
    elif meal_nudge.startswith('Drink nudge:'):
        fuel_item = 'Pack your water bottle and refill once tomorrow.'

    return {
        'headline': f"Wind-down briefing for {tomorrow.get('weekday', 'tomorrow')}: set up your bag now.",
        'tomorrow_weekday': tomorrow.get('weekday', 'tomorrow'),
        'items': [
            f"Wear (tomorrow): {outfit}",
            f"Carry (tomorrow): {carry}",
            'Essentials: keys, wallet, ID, charger.',
            fuel_item,
        ]
    }


def get_commute_briefing(home_weather, work_weather, home_city, work_city,
                         leave_home_time='08:00', leave_work_time='17:00'):
    """Build a merged commute-aware briefing comparing home and work city weather."""
    home_desc = home_weather['description'].lower()
    work_desc = work_weather['description'].lower()

    home_rain = any(k in home_desc for k in ('rain', 'drizzle', 'storm', 'thunder'))
    work_rain = any(k in work_desc for k in ('rain', 'drizzle', 'storm', 'thunder'))
    home_snow = 'snow' in home_desc
    work_snow = 'snow' in work_desc

    home_temp = home_weather['temp']
    work_temp = work_weather['temp']
    temp_delta = round(work_temp - home_temp)

    # --- Wear baseline ---
    if (home_rain or work_rain) and (home_temp < 12 or work_temp < 12):
        wear = 'Waterproof jacket with warm layers underneath — rain and cooler air at one or both ends.'
    elif home_rain or work_rain:
        wear = 'Light rain jacket or waterproof layer — at least one location has rain today.'
    elif home_snow or work_snow:
        wear = 'Warm waterproof coat — snow conditions at one of your locations.'
    elif abs(temp_delta) >= 7:
        cooler = min(home_temp, work_temp)
        if cooler < 12:
            wear = f'Warm layered outfit — there is a {abs(temp_delta)}°C gap between your locations. Dress for the cooler end.'
        else:
            wear = f'Layered outfit with a removable outer piece — {abs(temp_delta)}°C difference between home and work.'
    elif max(home_temp, work_temp) >= 28:
        wear = 'Light breathable clothing — warm at both ends of your day.'
    elif min(home_temp, work_temp) < 10:
        wear = 'Light coat or jacket — cooler temperatures at one or both locations.'
    else:
        wear = 'Comfortable everyday outfit — conditions are fairly similar at both ends.'

    # --- Carry list ---
    carry_list = []
    if home_rain or work_rain:
        carry_list.append('Umbrella')
    if home_snow or work_snow:
        carry_list.append('Gloves')
    if abs(temp_delta) >= 5 and not (home_rain or work_rain):
        carry_list.append('Extra layer in bag')
    if home_weather.get('wind_speed', 0) > 10 or work_weather.get('wind_speed', 0) > 10:
        carry_list.append('Windbreaker')
    if home_weather.get('humidity', 0) > 80 or work_weather.get('humidity', 0) > 80:
        carry_list.append('Extra water')
    if not carry_list:
        has_sun = any(k in home_desc + work_desc for k in ('clear', 'sunny'))
        carry_list.append('Sunglasses' if has_sun else 'Your usual daily bag')

    carry = ', '.join(carry_list)

    # --- Commute watch flags ---
    flags = []
    if home_rain:
        flags.append(f'Rain in {home_city.title()} — leave home with an umbrella ({leave_home_time} commute).')
    if work_rain:
        flags.append(f'Rain in {work_city.title()} — your return journey may be wet ({leave_work_time} commute).')
    if home_snow:
        flags.append(f'Snow in {home_city.title()} — allow extra travel time leaving home.')
    if work_snow:
        flags.append(f'Snow in {work_city.title()} — check transport before heading back.')
    if abs(temp_delta) >= 5:
        direction = 'warmer' if temp_delta > 0 else 'cooler'
        flags.append(
            f'{work_city.title()} is {abs(temp_delta)}°C {direction} than {home_city.title()} today '
            f'({home_temp}°C → {work_temp}°C) — layers help.'
        )
    if home_weather.get('wind_speed', 0) > 10:
        flags.append(f'Windy in {home_city.title()} this morning — hat recommended.')
    if work_weather.get('wind_speed', 0) > 10:
        flags.append(f'Windy in {work_city.title()} this evening — windbreaker useful.')
    if not flags:
        flags.append('Conditions are similar at both locations — smooth commute expected.')

    return {
        'headline': 'Here is your commute-aware plan.',
        'home_city': home_city.title(),
        'work_city': work_city.title(),
        'wear': wear,
        'carry': carry,
        'carry_list': carry_list,
        'commute_flags': flags,
        'home': {
            'label': home_city.title(),
            'temp': home_temp,
            'description': home_weather['description'],
            'icon': home_weather['icon'],
            'humidity': home_weather['humidity'],
            'wind_speed': home_weather['wind_speed'],
        },
        'work': {
            'label': work_city.title(),
            'temp': work_temp,
            'description': work_weather['description'],
            'icon': work_weather['icon'],
            'humidity': work_weather['humidity'],
            'wind_speed': work_weather['wind_speed'],
        },
        'leave_home': leave_home_time,
        'leave_work': leave_work_time,
        'temp_delta': temp_delta,
    }


def get_forecast(city):
    """Fetch 5-day / 3-hour forecast and return daily summaries."""
    api_key = os.getenv('API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        return None
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()

        # Group 3-hour entries by date
        days = {}
        for entry in data['list']:
            date = entry['dt_txt'].split(' ')[0]
            if date not in days:
                days[date] = []
            days[date].append(entry)

        today_str = datetime.now().strftime('%Y-%m-%d')
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        daily = []
        for date_str, entries in sorted(days.items()):
            if date_str == today_str:
                continue  # today already handled by get_weather()

            temps = [e['main']['temp'] for e in entries]
            feels = [e['main']['feels_like'] for e in entries]
            descriptions = [e['weather'][0]['description'] for e in entries]
            humidities = [e['main']['humidity'] for e in entries]
            winds = [e['wind']['speed'] for e in entries]

            # Prefer noon slot for icon, else first entry
            noon = next((e for e in entries if '12:00:00' in e['dt_txt']), entries[0])
            icon = noon['weather'][0]['icon']
            common_desc = Counter(descriptions).most_common(1)[0][0]

            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            summary = {
                'date': date_str,
                'weekday': date_obj.strftime('%A'),
                'weekday_short': date_obj.strftime('%a'),
                'date_display': date_obj.strftime('%b %d'),
                'temp_min': round(min(temps)),
                'temp_max': round(max(temps)),
                'feels_like': round(sum(feels) / len(feels)),
                'description': common_desc.capitalize(),
                'icon': icon,
                'humidity': round(sum(humidities) / len(humidities)),
                'wind_speed': round(sum(winds) / len(winds), 1),
            }
            summary['clothing'] = get_clothing_suggestions({
                'feels_like': summary['feels_like'],
                'description': summary['description'],
                'humidity': summary['humidity'],
                'wind_speed': summary['wind_speed'],
            })
            summary['vibe'] = get_day_vibe(summary['description'], summary['feels_like'])
            summary['activity'] = get_activity_suggestion(
                summary['description'], summary['feels_like'],
                summary['humidity'], summary['wind_speed']
            )
            summary['meal_nudge'] = get_meal_drink_nudge(
                summary['description'], summary['feels_like'],
                summary['humidity'], summary['wind_speed']
            )
            daily.append(summary)

        daily = apply_batch_prep_hints(daily)

        tomorrow = next((d for d in daily if d['date'] == tomorrow_str), None)
        weekend = [d for d in daily if d['weekday'] in ('Saturday', 'Sunday')]

        return {
            'tomorrow': tomorrow,
            'weekend': weekend,
            'week': daily,
        }
    except Exception as e:
        print(f"Forecast error: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        plan_mode = request.form.get('plan_mode', 'single').strip().lower()
        work_city = request.form.get('work_city', '').strip()
        leave_home = request.form.get('leave_home', '08:00').strip() or '08:00'
        leave_work = request.form.get('leave_work', '17:00').strip() or '17:00'
        commute_mode = plan_mode == 'commute' and bool(work_city)

        if not city:
            error = "Please enter a city name."
            return render_template('index.html', error=error)

        weather = get_weather(city)
        if not weather:
            error = "City not found or API error. Please check the city name and your API key."
            return render_template('index.html', error=error)

        clothing_suggestions = get_clothing_suggestions(weather)
        today_vibe = get_day_vibe(weather['description'], weather['feels_like'])
        today_activity = get_activity_suggestion(
            weather['description'], weather['feels_like'],
            weather['humidity'], weather['wind_speed']
        )
        today_meal_nudge = get_meal_drink_nudge(
            weather['description'], weather['feels_like'],
            weather['humidity'], weather['wind_speed']
        )
        daily_brief = get_daily_briefing(
            weather, clothing_suggestions, today_activity, today_meal_nudge
        )
        forecast = get_forecast(city)
        wind_down_plan = get_wind_down_bag_plan(forecast.get('tomorrow') if forecast else None)

        commute_brief = None
        work_weather = None
        if commute_mode:
            work_weather = get_weather(work_city)
            if work_weather:
                commute_brief = get_commute_briefing(
                    weather, work_weather, city, work_city, leave_home, leave_work
                )
            else:
                # Work city not found — fall back to single mode silently
                commute_mode = False
                work_city = ''

        plan_day = datetime.now()

        return render_template(
            'index.html',
            weather=weather,
            city=city.title(),
            clothing_suggestions=clothing_suggestions,
            today_vibe=today_vibe,
            today_activity=today_activity,
            today_meal_nudge=today_meal_nudge,
            daily_brief=daily_brief,
            wind_down_plan=wind_down_plan,
            forecast=forecast,
            commute_brief=commute_brief,
            commute_mode=commute_mode,
            home_city=city.title(),
            work_city=work_city.title() if work_city else '',
            leave_home=leave_home,
            leave_work=leave_work,
            plan_weekday=plan_day.strftime('%A'),
            plan_date=plan_day.strftime('%b %d'),
        )
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)