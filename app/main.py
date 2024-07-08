from flask import Blueprint, request, jsonify
import json
import requests
from flask_cors import CORS

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
    
    if "destination" not in current_state:
        for destination in destinations_data:
            if destination['destination'].lower() in user_message.lower():
                current_state['destination'] = destination['destination']
                response = f"How many days do you plan to spend on your vacation?"
                break
        else:
            response = "Please choose a destination from the available options."
    
    elif "days" not in current_state:
        days = [int(s) for s in user_message.split() if s.isdigit()]
        if days:
            current_state['days'] = days[0]
            response = "How many persons will be traveling?"
        else:
            response = "Please specify the number of days."
    
    elif "persons" not in current_state:
        persons = [int(s) for s in user_message.split() if s.isdigit()]
        if persons:
            current_state['persons'] = persons[0]
            destination = next(d for d in destinations_data if d['destination'] == current_state['destination'])
            packages = destination['packages']
            response = "Here are the available packages:\n"
            for i, pkg in enumerate(packages):
                response += f"{i+1}. {pkg['name']}\n"
            response += "Please select the number or type the name corresponding to your desired package."
        else:
            response = "Please specify the number of persons."
    
    elif "package" not in current_state:
        package_choice = user_message.strip().lower()
        destination = next(d for d in destinations_data if d['destination'] == current_state['destination'])
        packages = destination['packages']
        
        # Check if user input is a number
        try:
            package_num = int(package_choice)
            if 1 <= package_num <= len(packages):
                selected_package = packages[package_num - 1]
                current_state['package'] = selected_package['name']
                response = f"Here are the details and prices of the {current_state['package']} package in {current_state['destination']}:\n"
                for i, price in enumerate(selected_package['prices']):
                    response += f"{i+1}. Amenities: {price['amenities']}\n Price: ${price['price']}\n Details: {price['details']}\n"
                response += "Please select the number corresponding to your desired amenities."
            else:
                response = "Please choose a valid package number from the list."
        
        # If input is not a number, search by package name
        except ValueError:
            selected_package = next((pkg for pkg in packages if pkg['name'].lower() == package_choice), None)
            if selected_package:
                current_state['package'] = selected_package['name']
                response = f"Here are the details and prices of the {current_state['package']} package in {current_state['destination']}:\n"
                for i, price in enumerate(selected_package['prices']):
                    response += f"{i+1}. Amenities:\n- {price['amenities']}\n- Price: ${price['price']}\n- Details: {price['details']}\n"
                response += "Please select the number corresponding to your desired amenities."
            else:
                response = "Please choose a valid package from the list."
    
    elif "amenities" not in current_state:
        try:
            amenities_choice = int(user_message.strip())
            destination = next(d for d in destinations_data if d['destination'] == current_state['destination'])
            selected_package = next(p for p in destination['packages'] if p['name'] == current_state['package'])
            selected_amenities = selected_package['prices'][amenities_choice - 1]
            current_state['amenities'] = selected_amenities['amenities']
            current_state['price'] = selected_amenities['price']
            current_state['details'] = selected_amenities['details']
            response = f"Package Details:\n- Amenities: {current_state['amenities']}\n- Price: ${current_state['price']}\n- Details: {current_state['details']}\n"
            response += f"{current_state['package']} package {selected_amenities['imageUrl']}\n"
            response += "Please make the payment to proceed with your order.\n Payment Type: Card or Transfer"
        except (IndexError, ValueError):
            response = "Please choose a valid number corresponding to your desired amenities."
      
    elif "card" in user_message.lower() or "transfer" in user_message.lower():
        try:
            email = "customer@email.com"  # Replace with customer's email
            amount = current_state['price']
            brand = "Travel Package"  # Replace with a meaningful description
            payment_link = initialize_paystack_transaction(email, amount, brand)
            response = f"Please proceed with the payment by clicking on this link: {payment_link}"
            current_state = {}  # Clear current state after successful payment initiation
        except Exception as e:
            response = f"An error occurred while initializing the payment: {str(e)}"
    
    else:
        response = "I'm sorry, I didn't understand that selection. Try Again!!!'."

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
