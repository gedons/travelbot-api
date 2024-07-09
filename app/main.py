from flask import Blueprint, request, jsonify
import json
import requests
from flask_cors import CORS
from dateutil.parser import parse as parse_date

main = Blueprint('main', __name__)
CORS(main)

# Replace with your actual Paystack secret key
PAYSTACK_SECRET_KEY = 'sk_test_73d239b922a8dbe050ada4b7f453580c0c8e5a86'

with open('app/data.json', 'r') as f:
    destinations_data = json.load(f)

current_state = {}

@main.route('/chat', methods=['POST'])
def chat():
    global current_state
    user_message = request.json['message']
    response = ""

    if not current_state:
        if any(phrase in user_message.lower() for phrase in ["recommend a destination", "where should i go", "suggest a travel destination"]):
            response = "Great! Let's start by exploring some travel destinations. What are your preferences? beaches, Adventure trip, Cultural experience, Surprise me"
            current_state['step'] = 'preferences'
        else:
            response = "Hello! How can I assist you with your travel plans today?"

    elif current_state.get('step') == 'preferences':
        preferences = ["beaches", "adventure trip", "cultural experience", "surprise me"]
        if any(pref in user_message.lower() for pref in preferences):
            response = "Excellent choice! Here are the available destinations:\n"
            for i, destination in enumerate(destinations_data):
                response += f"{i+1}. {destination['destination']} {destination['imageUrl']}\n"
            response += "Please select the number or type the name corresponding to your desired destination."
            current_state['step'] = 'select_destination'
        else:
            response = "Please choose from the available options: beaches, Adventure trip, Cultural experience, Surprise me"

    elif current_state.get('step') == 'select_destination':
        destination_choice = user_message.strip().lower()
        try:
            destination_num = int(destination_choice)
            if 1 <= destination_num <= len(destinations_data):
                selected_destination = destinations_data[destination_num - 1]
                current_state['destination'] = selected_destination
                response = "Excellent choice! Let's start by providing your departure and arrival travel dates."
                current_state['step'] = 'travel_dates'
            else:
                response = "Please choose a valid destination number from the list."
        except ValueError:
            selected_destination = next((dest for dest in destinations_data if dest['destination'].lower() == destination_choice), None)
            if selected_destination:
                current_state['destination'] = selected_destination
                response = "Excellent choice! Let's start by providing your departure and arrival travel dates."
                current_state['step'] = 'travel_dates'
            else:
                response = "Please choose a valid destination from the list."

    elif current_state.get('step') == 'travel_dates':
        try:
            dates = user_message.split(" and ")
            if len(dates) == 2:
                departure_date = parse_date(dates[0])
                arrival_date = parse_date(dates[1])
                current_state['departure_date'] = departure_date
                current_state['arrival_date'] = arrival_date
                response = "Perfect! Let's explore lodging options. When do you plan to check in and check out?"
                current_state['step'] = 'lodging_dates'
            else:
                response = "Please provide your travel dates in the format: [departure_date] to [arrival_date]"
        except ValueError:
            response = "Please provide valid travel dates."

    elif current_state.get('step') == 'lodging_dates':
        try:
            dates = user_message.split(" and ")
            if len(dates) == 2:
                check_in_date = parse_date(dates[0])
                check_out_date = parse_date(dates[1])
                current_state['check_in_date'] = check_in_date
                current_state['check_out_date'] = check_out_date
                response = "Thank you for providing your accommodation dates. What type of lodging are you interested in? (e.g., hotel, resort, Airbnb)"
                current_state['step'] = 'lodging_type'
            else:
                response = "Please provide your lodging dates in the format: [check_in_date] and [check_out_date]"
        except ValueError:
            response = "Please provide valid lodging dates."

    elif current_state.get('step') == 'lodging_type':
        lodging_types = ["hotel", "resort", "airbnb"]
        if any(lodging in user_message.lower() for lodging in lodging_types):
            current_state['lodging_type'] = user_message
            response = "Noted. Please provide your name and email."
            current_state['step'] = 'user_details'
        else:
            response = "Please choose a valid lodging type: hotel, resort, Airbnb"

    elif current_state.get('step') == 'user_details':
        user_details = user_message.split(" ")
        if len(user_details) >= 2:
            current_state['user_name'] = " ".join(user_details[:-1])
            current_state['user_email'] = user_details[-1]
            selected_package = current_state['destination']['packages'][0]  # Assuming the user selects the first package
            package_price = selected_package['prices'][0]['price']  # Assuming the user selects the first price option
            package_details = selected_package['prices'][0]['details']
            package_image = selected_package['prices'][0]['imageUrl']
            current_state['price'] = package_price
            response = f"Thank you {current_state['user_name']}! Here are your travel details:\n"
            response += f"Destination: {current_state['destination']['destination']}\n"
            response += f"Departure Date: {current_state['departure_date'].strftime('%d %B %Y')}\n"
            response += f"Arrival Date: {current_state['arrival_date'].strftime('%d %B %Y')}\n"
            response += f"Check-in Date: {current_state['check_in_date'].strftime('%d %B %Y')}\n"
            response += f"Check-out Date: {current_state['check_out_date'].strftime('%d %B %Y')}\n"
            response += f"Lodging Type: {current_state['lodging_type']}\n"
            response += f"Price: ${current_state['price']}\n"
            response += f"Package Details: {package_details}\n"
            response += f"Destination Picture: {package_image}\n"
            response += "Please proceed with the payment by choosing either card or transfer"
            current_state['step'] = 'payment'
        else:
            response = "Please provide your name and email."

    elif current_state.get('step') == 'payment':
        if "card" in user_message.lower() or "transfer" in user_message.lower():
            try:
                email = current_state['user_email']
                amount = current_state['price']
                brand = "Travel Package"  # Replace with a meaningful description
                payment_link = initialize_paystack_transaction(email, amount, brand)
                response = f"Please proceed with the payment payment method: {payment_link}"
                current_state = {}  # Clear current state after successful payment initiation
            except Exception as e:
                response = f"An error occurred while initializing the payment: {str(e)}"
        else:
            response = "Please choose a valid payment method: card or transfer"
    else:
        response = "I'm sorry, I didn't understand that selection. Try again."

    return jsonify({"response": response})

def initialize_paystack_transaction(email, amount, brand):
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": amount * 100,
        "metadata": {
            "custom_fields": [
                {
                    "display_name": "Travel Bot",
                    "variable_name": "brand",
                    "value": brand
                }
            ]
        }
    }
    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()
    if response_data['status']:
        return response_data['data']['authorization_url']
    else:
        raise Exception(response_data['message'])
