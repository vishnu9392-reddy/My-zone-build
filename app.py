from flask import Flask, render_template, request, redirect, session, jsonify, Response, abort
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import os

from werkzeug.utils import secure_filename
import csv
complaints = [] 

# Initialize Firebase
import firebase_admin
from firebase_admin import credentials, firestore
import json, os

firebase_app = None
db = None

import firebase_admin
from firebase_admin import credentials, firestore
import os, json

firebase_app = None
db = None

def get_firestore():
    global firebase_app, db
    if not firebase_app:
        cred_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        cred = credentials.Certificate(cred_dict)
        firebase_app = firebase_admin.initialize_app(cred)
        db = firestore.client()
    return db

# ✅ Use this
db = get_firestore()


app = Flask(__name__)
app.secret_key = "supersecretkey"

# Home Page Route
@app.route("/")
def home():
    return render_template("home.html")

# Admin Registration Route


# Resident Registration Route


# Login Page Route
@app.route("/login_page")
def login_page():
    return render_template("home.html")


# Admin Dashboard Route
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if "user" not in session or session["role"] != "admin":
        return redirect("/login_page")

    apartment_code = session.get("apartment_code")

    # Fetch apartment details
    apartment_ref = db.collection("apartments").document(apartment_code).get()
    apartment = apartment_ref.to_dict() if apartment_ref.exists else None

    # Fetch residents
    residents_ref = db.collection("users") \
        .where("role", "==", "resident") \
        .where("apartment_code", "==", apartment_code) \
        .stream()

    residents = [resident.to_dict() for resident in residents_ref]

    # Fetch maintainers
    maintainers_ref = db.collection("maintainers") \
        .where("apartment_code", "==", apartment_code) \
        .stream()

    maintainers = [maintainer.to_dict() for maintainer in maintainers_ref]

    # Fetch maintenance records
    maintenance_ref = db.collection("maintenance") \
        .where("apartment_code", "==", apartment_code) \
        .stream()

    maintenance_records = [record.to_dict() for record in maintenance_ref]

    # Handle Form Submissions
    if request.method == "POST":
        form_type = request.form.get("form_type")  # Identify which form was submitted

        if form_type == "add_maintainer":
            maintainer_name = request.form["maintainer_name"]
            maintainer_contact = request.form["maintainer_contact"]

            try:
                db.collection("maintainers").add({
                    "name": maintainer_name,
                    "contact": maintainer_contact,
                    "apartment_code": apartment_code
                })
            except Exception as e:
                print(f"Error adding maintainer: {e}")

        elif form_type == "add_maintenance":
            resident_name = request.form["resident_name"]
            flat_number = request.form["flat_number"]
            amount = request.form["amount"]

            try:
                db.collection("maintenance").add({
                    "resident_name": resident_name,
                    "flat_number": flat_number,
                    "amount_paid": amount,
                    "apartment_code": apartment_code
                })
            except Exception as e:
                print(f"Error adding maintenance: {e}")

        return redirect("/admin_dashboard")

    return render_template(
        "admin_dashboard.html",
        apartment=apartment,
        residents=residents,
        maintainers=maintainers,
        maintenance_records=maintenance_records
    )

from datetime import datetime
@app.route('/admin_residents')
def admin_residents():
    if "user" not in session or session.get("role") != "admin":
        return redirect(("login"))  # Ensure only admins can access

    apartment_code = session.get("apartment_code")  # Fetch the admin's apartment code

    # Fetch only residents of the same apartment
    users_ref = db.collection("users") \
        .where("role", "==", "resident") \
        .where("apartment_code", "==", apartment_code) \
        .stream()

    residents = [
        {
            "name": user.to_dict().get("name"),
            "flat_number": user.to_dict().get("flat_number"),
            "email": user.to_dict().get("email"),

            "apartment_code": user.to_dict().get("apartment_code")
        }
        for user in users_ref
    ]

    return render_template("admin_residents.html", residents=residents)


@app.route('/maintenance_records')
def maintenance_records():
    if "user" in session and session["role"] == "admin":
        return render_template("admin_maintenance.html")
    return jsonify({"message": "Unauthorized"}), 403

from datetime import datetime


@app.route('/add_maintenance', methods=['POST'])
def add_maintenance():
    try:
        data = request.get_json()
        required_fields = ["name", "flat_number", "apartment_code", "amount_paid", "month", "year"]

        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        apartment_code = data["apartment_code"]
        flat_number = data["flat_number"]
        month = data["month"]
        year = data["year"]

        # Reference to Firestore document
        doc_ref = db.collection("maintenance_records").document(f"{apartment_code}_{flat_number}_{month}_{year}")

        # Check if the record exists
        existing_record = doc_ref.get()
        if existing_record.exists:
            # Update the existing record
            doc_ref.update({
                "amount_paid": data["amount_paid"],
                "status": "Paid"
            })
        else:
            # Create a new record
            doc_ref.set({
                "name": data["name"],
                "flat_number": flat_number,
                "apartment_code": apartment_code,
                "amount_paid": data["amount_paid"],
                "month": month,
                "year": year,
                "status": "Paid"
            })

        return jsonify({"message": "Payment recorded successfully"}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"message": "Internal Server Error", "error": str(e)}), 500


@app.route("/admin_complaints")
def admin_complaints():
    if "user" in session and session["role"] == "admin":
        return render_template("admin_complaints.html")
    return redirect("/login_page")
   
   
# API to fetch all maintenance records

@app.route('/get_maintenance', methods=['GET'])
def get_maintenance():
    apartment_code = session.get("apartment_code")  
    month = request.args.get("month", "all")
    year = request.args.get("year", str(datetime.now().year))

    if not apartment_code:
        return jsonify({"error": "Apartment code not found in session"}), 400

    try:
        records_ref = db.collection("maintenance_records") \
                        .where("apartment_code", "==", apartment_code) \
                        .stream()

        records = []
        total_amount = 0

        for record in records_ref:
            data = record.to_dict()

            flat_number = str(data.get("flat_number", ""))
            record_month = str(data.get("month", ""))
            record_year = str(data.get("year", ""))
            amount_paid = float(data.get("amount_paid", 0))
            status = data.get("status", "Unpaid")

            # Month & Year Filtering
            if (month == "all" or record_month == month) and (year == "all" or record_year == year):
                if status == "Paid":
                    total_amount += amount_paid  

                records.append({
                    "flat_number": flat_number,
                    "apartment_code": apartment_code,
                    "amount_paid": amount_paid,
                    "month": record_month,
                    "year": record_year,
                    "status": status,
                })

        return jsonify({"records": records, "total_collected": total_amount})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/residents")
def residents_list():
    if "user" in session and session["role"] == "admin":
        apartment_code = session.get("apartment_code")  # Admin's apartment code
        
        # Fetch only residents from the same apartment
        residents_ref = db.collection("users") \
            .where("role", "==", "resident") \
            .where("apartment_code", "==", apartment_code) \
            .stream()

        residents = []
        for resident in residents_ref:
            resident_data = resident.to_dict()
            residents.append(resident_data)

        return render_template("residents.html", residents=residents)
    
    return redirect("/login_page")


# Add Maintainer Route
@app.route("/add_maintainer", methods=["POST"])
def add_maintainer():
    if "user" in session and session["role"] == "admin":
        data = request.json
        name = data.get("name")
        contact = data.get("contact")
        job_title = data.get("job_title")
        apartment_code = session.get("apartment_code")

        if not name or not contact or not job_title:
            return jsonify({"message": "All fields (name, contact, job_title) are required!"}), 400

        try:
            # Add maintainer and get the document ID
            maintainer_ref = db.collection("maintainers").add({
                "name": name,
                "contact": contact,
                "job_title": job_title,
                "apartment_code": apartment_code
            })
            maintainer_id = maintainer_ref[1].id  # Get document ID

            return jsonify({"message": "Maintainer added successfully!", "id": maintainer_id}), 200
        except Exception as e:
            return jsonify({"message": str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403



@app.route("/get_admin_maintainers", methods=["GET"])
def get_admin_maintainers():
    if "user" in session and session.get("role") == "admin":
        apartment_code = session.get("apartment_code")  # Get admin's apartment code
        
        # Fetch maintainers from Firestore based on apartment_code
        maintainers_ref = db.collection("maintainers").where("apartment_code", "==", apartment_code).stream()
        maintainers = [{"id": maintainer.id, **maintainer.to_dict()} for maintainer in maintainers_ref]

        return jsonify({"maintainers": maintainers}), 200

    return jsonify({"message": "Unauthorized"}), 403

# Resident Dashboard Route
@app.route("/resident_dashboard")
def resident_dashboard():
    if "user" in session and session["role"] == "resident":
        email = session["user"]

        # Fetch resident details
        residents_ref = db.collection("users").where("email", "==", email).stream()
        resident_data = None
        for resident in residents_ref:
            resident_data = resident.to_dict()
            break

        if resident_data:
            apartment_code = resident_data["apartment_code"]

            # Fetch maintainers for the resident's apartment
            maintainers_ref = db.collection("maintainers").where("apartment_code", "==", apartment_code).stream()
            maintainers = [maintainer.to_dict() for maintainer in maintainers_ref]

            # Fetch maintenance records
            maintenance_ref = db.collection("maintenance").where("apartment_code", "==", apartment_code).stream()
            maintenance_records = [maintenance.to_dict() for maintenance in maintenance_ref]

            print(f"Found {len(maintainers)} maintainers for apartment code {apartment_code}")  # Debugging
            print(f"Found {len(maintenance_records)} maintenance records fro apartment code {apartment_code}")  # Debugging

            return render_template(
                "resident_dashboard.html",
                resident=resident_data,
                maintainers=maintainers,
                maintenance_records=maintenance_records  # Passing maintenance records to the template
            )
        else:
            return redirect("/login_page")
    
    return redirect("/login_page")
@app.route('/get_resident_maintenance', methods=['GET'])
def get_resident_maintenance():
    if "user" not in session or session["role"] != "resident":
        return jsonify({"message": "Unauthorized"}), 403

    email = session["user"]

    # Default month and year if not provided
    month = request.args.get("month", "all")
    year = request.args.get("year", str(datetime.now().year))

    # 🔹 Fetch the logged-in resident's details
    resident_query = db.collection("users").where("email", "==", email).stream()
    resident_data = next((r.to_dict() for r in resident_query), None)

    if not resident_data:
        return jsonify({"message": "Resident not found"}), 404

    apartment_code = resident_data.get("apartment_code")

    # 🔹 Fetch all residents in the same apartment & create a {flat_number: resident_name} mapping
    residents_query = db.collection("users").where("apartment_code", "==", apartment_code).stream()
    flat_to_resident = {res.to_dict().get("flat_number"): res.to_dict().get("name", "Unknown") for res in residents_query}

    # 🔹 Fetch all maintenance records for the apartment
    records_query = db.collection("maintenance_records").where("apartment_code", "==", apartment_code).stream()

    records = []
    for record in records_query:
        data = record.to_dict()
        record_flat = data.get("flat_number")

        # 🔹 Get resident name using the flat number mapping
        resident_name = flat_to_resident.get(record_flat, "Unknown")

        # 🔹 Filter by month & year
        if (month == "all" or data.get("month") == month) and data.get("year") == year:
            records.append({
                "resident_name": resident_name,  # 🔹 Correctly mapped name
                "flat_number": record_flat,
                "amount_paid": data.get("amount_paid"),
                "status": data.get("status", "Paid")  # Default to "Paid" if missing
            })

    return jsonify(records), 200
# 🔹 Configure Upload Folder (Local Storage)
UPLOAD_FOLDER = "uploads/receipts"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
@app.route('/submit_maintenance_payment', methods=['POST'])
def submit_maintenance_payment():
    if "user" not in session or session["role"] != "resident":
        return jsonify({"message": "Unauthorized"}), 403

    email = session["user"]

    # 🔹 Retrieve form data
    month_year = request.form.get("month_year")  # Format: YYYY-MM
    amount_paid = request.form.get("amount_paid")
    receipt = request.files.get("receipt")

    if not month_year or not amount_paid or not receipt:
        return jsonify({"message": "All fields are required"}), 400

    # 🔹 Extract month & year
    year, month = month_year.split("-")

    # 🔹 Fetch Resident Data
    resident_query = db.collection("users").where("email", "==", email).stream()
    resident_data = next((r.to_dict() for r in resident_query), None)

    if not resident_data:
        return jsonify({"message": "Resident not found"}), 404

    resident_name = resident_data.get("name")
    flat_number = resident_data.get("flat_number")
    apartment_code = resident_data.get("apartment_code")

    # 🔹 Check for existing maintenance payment (to prevent duplicates)
    existing_payments = db.collection("maintenance_records").where(
        "flat_number", "==", flat_number
    ).where(
        "month", "==", month
    ).where(
        "year", "==", year
    ).stream()

    if any(existing_payments):  # If any record exists, reject the submission
        return jsonify({"message": "Payment already submitted for this month!"}), 400

    # 🔹 Save Receipt Locally
    filename = secure_filename(f"{flat_number}_{month}_{year}.pdf")
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    receipt.save(file_path)

    # 🔹 Save to Firestore
    db.collection("maintenance_records").add({
        "resident_name": resident_name,
        "flat_number": flat_number,
        "apartment_code": apartment_code,
        "month": month,
        "year": year,
        "amount_paid": amount_paid,
        "status": "Pending",  # Admin will confirm
        "receipt_path": file_path,  # 🔹 Store local path instead of URL
        "timestamp": datetime.now()
    })

    return jsonify({"message": "Payment submitted successfully!"}), 200

@app.route("/confirm_maintenance", methods=["POST"])
def confirm_maintenance():
    try:
        data = request.get_json()
        flat_number = data.get("flat_number")
        apartment_code = data.get("apartment_code")
        month = data.get("month")
        year = data.get("year")

        if not flat_number or not apartment_code or not month or not year:
            return jsonify({"message": "Missing required fields"}), 400  # <-- This prevents 400 errors

        # Find the record in Firestore
        query = db.collection("maintenance_records").where("flat_number", "==", flat_number)\
            .where("apartment_code", "==", apartment_code).where("month", "==", month)\
            .where("year", "==", year).stream()

        records = list(query)

        if not records:
            return jsonify({"message": "Record not found"}), 404  # <-- If no record exists

        # Update record to "Paid"
        for record in records:
            db.collection("maintenance_records").document(record.id).update({"status": "Paid"})

        return jsonify({"message": "Payment confirmed successfully!"}), 200

    except Exception as e:
        return jsonify({"message": "Error processing request", "error": str(e)}), 500
@app.route("/get_maintainers", methods=["GET"])
def get_maintainers():
    if "user" in session:
        apartment_code = session.get("apartment_code")  # Get apartment code from session
        
        # Fetch maintainers from Firestore for the same apartment
        maintainers_ref = db.collection("maintainers").where("apartment_code", "==", apartment_code).stream()
        maintainers = [maintainer.to_dict() for maintainer in maintainers_ref]

        return jsonify({"maintainers": maintainers}), 200

    return jsonify({"message": "Unauthorized"}), 403


@app.route("/add_announcement", methods=["POST"])
def add_announcement():
    if "user" in session and session["role"] == "admin":
        try:
            data = request.json
            message = data.get("message")
            date = data.get("date")  # Ensure date is provided
            apartment_code = session.get("apartment_code")

            # ✅ Validation: Ensure all fields are present
            if not message or not date:
                return jsonify({"message": "Both message and date are required!"}), 400

            print(f"Adding announcement: {message}, Date: {date}, Apartment: {apartment_code}")  # Debugging Log

            db.collection("announcements").add({
                "message": message,
                "date": date,
                "apartment_code": apartment_code  # ✅ Store announcement with apartment code
            })

            return jsonify({"message": "Announcement posted successfully!"}), 200
        
        except Exception as e:
            print(f"Error adding announcement: {e}")  # ✅ Log error for debugging
            return jsonify({"message": str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403




@app.route("/get_announcements", methods=["GET"])
def get_announcements():
    if "user" in session:
        apartment_code = request.args.get("apartment_code")  # Get from URL parameter
        date = request.args.get("date")  # Get date from query parameter

        if not date:
            return jsonify({"message": "Date is required"}), 400

        # Fetch announcements from Firestore for the selected date and apartment
        announcements_ref = (
            db.collection("announcements")
            .where("apartment_code", "==", apartment_code)
            .where("date", "==", date)  # ✅ Filter by date
            .stream()
        )

        announcements = [announcement.to_dict() for announcement in announcements_ref]
        return jsonify({"announcements": announcements}), 200

    return jsonify({"message": "Unauthorized"}), 403

# Admin Registration Route
@app.route("/admin_register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        data = request.json
        email = data["email"]
        password = data["password"]
        apartment_code = data["apartment_code"]
        name = data["name"]  # Apartment Name
        location = data["location"]  # Apartment Location
        total_flats = data["total_flats"]  # Total Flats
        established = data["established"]  # Established Year

        try:
            # Ensure apartment code is unique
            db = get_firestore()
            apartment = db.collection("apartments").document(apartment_code).get()

            if apartment.exists:
                return jsonify({"message": "Apartment code already exists! Choose a different code."}), 400

            # Create Firebase user
            user = auth.create_user(email=email, password=password)

            # Store apartment details in Firestore
            db.collection("apartments").document(apartment_code).set({
                "admin": email,
                "name": name,
                "location": location,
                "total_flats": total_flats,
                "established": established
            })

            # Store user details with role as admin
            user_data = {
                "name": data["name"],  # Admin Name
                "email": email,
                "role": "admin",
                "apartment_code": apartment_code
            }
            db.collection("users").document(user.uid).set(user_data)

            session["user"] = email
            session["role"] = "admin"
            session["apartment_code"] = apartment_code

            return jsonify({"message": "Admin registered successfully!", "redirect_url": "/admin_dashboard"}), 201

        except Exception as e:
            return jsonify({"message": str(e)}), 400

    return render_template("admin_register.html")


# Resident Registration Route
@app.route("/resident_register", methods=["GET", "POST"])
def resident_register():
    if request.method == "POST":
        data = request.json
        email = data.get("email")
        password = data.get("password")
        flat_number = data.get("flat_number")
        apartment_code = data.get("apartment_code")

        try:
            # Check if the apartment exists
            apartment = db.collection("apartments").document(apartment_code).get()
            if not apartment.exists:
                return jsonify({"message": "Invalid apartment code! Please enter a valid code."}), 400

            # Check if the flat number already exists in the same apartment
            existing_flat = db.collection("users").where("apartment_code", "==", apartment_code).where("flat_number", "==", flat_number).get()
            if existing_flat:
                return jsonify({"message": "Flat number already registered!"}), 400

            # Create Firebase user
            user = auth.create_user(email=email, password=password)

            # Store resident details in Firestore
            user_data = {
                "name": data.get("name"),
                "email": email,
                "role": "resident",
                "flat_number": flat_number,
                "apartment_code": apartment_code
            }
            db.collection("users").document(user.uid).set(user_data)

            # Store user session details
            session["user"] = email
            session["role"] = "resident"
            session["flat_number"] = flat_number
            session["apartment_code"] = apartment_code

            # Add maintenance record without a date
            db.collection("maintenance_records").add({
                "resident_name": data["name"],
                "flat_number": data["flat_number"],
                "apartment_code": data["apartment_code"],
                "amount_paid": 0,  # Default to 0, since payment isn't made yet
                "status": "Pending"  # You can later update status when payment is made
            })

            return jsonify({"message": "Resident registered successfully!", "redirect_url": "/resident_dashboard"}), 201

        except Exception as e:
            return jsonify({"message": str(e)}), 400

    return render_template("resident_register.html")


# View Complaints Route (Admin)
@app.route("/view_complaints")
def view_complaints():
    if "user" in session and session["role"] == "admin":
        apartment_code = session["apartment_code"]

        complaints_ref = db.collection("complaints").where("apartment_code", "==", apartment_code).stream()
        complaints = [complaint.to_dict() for complaint in complaints_ref]

        return jsonify({"complaints": complaints}), 200

    return jsonify({"message": "Unauthorized"}), 403

@app.route("/update_complaint_status", methods=["POST"])
def update_complaint_status():
    data = request.json
    complaint_id = data.get("id")
    new_status = data.get("status")

    if not complaint_id or not new_status:
        return jsonify({"success": False, "message": "Invalid request data"}), 400

    # Update the complaint status in Firestore
    complaint_ref = db.collection("complaints").document(complaint_id)
    complaint_ref.update({"status": new_status})

    return jsonify({"success": True, "message": "Complaint status updated"})
@app.route('/get_complaints', methods=['GET'])
def get_complaints():
    docs = db.collection("complaints").stream()  # Fetch from Firestore
    complaints_list = []

    for doc in docs:
        complaints_list.append(doc.to_dict())

    
    return jsonify({"complaints": complaints_list})
# Add Complaint Route (Resident)
@app.route("/add_resident_complaints", methods=["POST"])
def add_resident_complaint():
    if "user" in session and session["role"] == "resident":
        complaint_text = request.json["complaint"]
        resident_email = session["user"]
        apartment_code = session["apartment_code"]
        flat_number = session.get("flat_number")
        complaint_data = {
            "text": complaint_text,  # Changed from "complaint" to "text" for consistency
            "status": "Pending",
            "resident_email": resident_email,
            "apartment_code": apartment_code,
            "flat_number": flat_number 
        }

        db.collection("complaints").add(complaint_data)
        return jsonify({"success": True, "message": "Complaint added successfully!"}), 201

    return jsonify({"success": False, "message": "Unauthorized"}), 403

@app.route("/get_resident_complaints", methods=["GET"])
def get_resident_complaints():
    if "user" in session and session["role"] == "resident":
        apartment_code = session["apartment_code"]

        complaints_ref = db.collection("complaints").where("apartment_code", "==", apartment_code).stream()
        complaints_list = []

        for complaint in complaints_ref:
            complaint_data = complaint.to_dict()
            complaints_list.append({
                "text": complaint_data.get("text", ""),
                "status": complaint_data.get("status", "Pending")
            })

        return jsonify({"success": True, "complaints": complaints_list}), 200

    return jsonify({"success": False, "message": "Unauthorized"}), 403

@app.route('/get_residents', methods=['GET'])
def get_residents():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized, admin role required"}), 403  # Admin only access

    apartment_code = session.get("apartment_code")
    if not apartment_code:
        return jsonify({"message": "No apartment code found in session"}), 400  # Ensure apartment code is in session

    try:
        # Query users where the role is 'resident' and match apartment_code
        users_ref = db.collection("users") \
            .where("role", "==", "resident") \
            .where("apartment_code", "==", apartment_code) \
            .stream()

        residents = [
            {
                "name": user.to_dict().get("name"),
                "flat_number": user.to_dict().get("flat_number"),
                "email": user.to_dict().get("email"),
                "apartment_code": user.to_dict().get("apartment_code")
            }
            for user in users_ref
        ]

        if not residents:
            return jsonify({"message": "No residents found for this apartment"}), 404  # No residents found

        return jsonify(residents), 200

    except Exception as e:
        # Handle any unexpected errors
        return jsonify({"message": str(e)}), 500

from flask import send_from_directory

@app.route('/uploads/receipts/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Remove Resident Route
@app.route("/remove_resident", methods=["POST"])
def remove_resident():
    if "user" in session and session["role"] == "admin":
        data = request.json
        resident_email = data.get("email")

        try:
            # Query for the resident with the given email
            residents_ref = db.collection("users").where("email", "==", resident_email).stream()
            for resident in residents_ref:
                db.collection("users").document(resident.id).delete()
                return jsonify({"message": "Resident removed successfully!"}), 200
            
            return jsonify({"message": "Resident not found!"}), 404

        except Exception as e:
            return jsonify({"message": str(e)}), 500
    
    return jsonify({"message": "Unauthorized"}), 403


@app.route("/remove_maintainer", methods=["POST"])
def remove_maintainer():
    if "user" not in session or session["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data = request.json  # Get JSON data from the request
    print("Received data:", data)  # Debugging line
    
    maintainer_id = data.get("maintainer_id")

    if not maintainer_id:
        return jsonify({"message": "Maintainer ID is required!"}), 400

    try:
        maintainer_ref = db.collection("maintainers").document(maintainer_id)
        
        # Check if maintainer exists
        if not maintainer_ref.get().exists:
            return jsonify({"message": "Maintainer not found!"}), 404

        maintainer_ref.delete()
        return jsonify({"message": "Maintainer removed successfully!"}), 200

    except Exception as e:
        print(f"Error removing maintainer: {e}")
        return jsonify({"message": "Error removing maintainer"}), 500

@app.route('/maintenance')
def maintenance_page():
    if "user" in session and session["role"] == "resident":
        return render_template("maintenance.html")
    return redirect("/login_page")
@app.route('/expenses')
def expenses_page():
    if "user" in session and session["role"] == "resident":
        return render_template("resident_expenses.html")
    return redirect("/login_page")
@app.route('/admin_events')
def admin_events():
    if "user" in session and session["role"] == "admin":
        return render_template("admin_events.html")
    return redirect("/login_page")
@app.route('/resident_events')
def events_page():
    if "user" in session and session["role"] == "resident":
        return render_template("resident_events.html")
    return redirect("/login_page")




@app.route("/get_expenses", methods=["GET"])
def get_expenses():
    """Resident API: Fetches resident's monthly expenses."""
    if "user" in session and session["role"] == "resident":
        apartment_code = session.get("apartment_code")

        # Fetch total maintenance budget
        payments_ref = db.collection("maintenance_records").where(
            "apartment_code", "==", apartment_code
        ).stream()
        total_budget = sum(doc.to_dict().get("amount", 0) for doc in payments_ref)

        # Fetch resident's expenses
        expenses_ref = db.collection("expenses").where(
            "apartment_code", "==", apartment_code
        ).stream()

        expenses = []
        total_expenses = 0

        for doc in expenses_ref:
            data = doc.to_dict()
            expenses.append({
                "month": data.get("month", "Unknown"),
                "description": data.get("description", "No Description"),
                "amount": data.get("amount", 0)
            })
            total_expenses += data.get("amount", 0)

        remaining_budget = total_budget - total_expenses

        return jsonify({
            "total_budget": total_budget,
            "total_expenses": total_expenses,
            "remaining_budget": remaining_budget,
            "expenses": expenses
        })

    return jsonify({"error": "Unauthorized"}), 403


@app.route("/get_admin_expenses", methods=["GET"])
def get_admin_expenses():
    """Admin API: Fetches all monthly expenses grouped by month."""
    if "user" in session and session["role"] == "admin":
        apartment_code = session.get("apartment_code")

        # Fetch total maintenance budget
        payments_ref = db.collection("maintenance_records").where(
            "apartment_code", "==", apartment_code
        ).stream()
        total_budget = sum(doc.to_dict().get("amount", 0) for doc in payments_ref)

        # Fetch all expenses
        expenses_ref = db.collection("expenses").where(
            "apartment_code", "==", apartment_code
        ).stream()

        expenses = {}
        total_expenses = 0

        for doc in expenses_ref:
            data = doc.to_dict()
            month = data.get("month", "Unknown")
            amount = data.get("amount", 0)
            description = data.get("description", "No Description")

            if month not in expenses:
                expenses[month] = []

            expenses[month].append({
                "description": description,
                "amount": amount
            })
            total_expenses += amount

        remaining_budget = total_budget - total_expenses

        return jsonify({
            "total_budget": total_budget,
            "total_expenses": total_expenses,
            "remaining_budget": remaining_budget,
            "expenses": expenses  # ✅ Grouped by month
        })

    return jsonify({"error": "Unauthorized"}), 403

from flask import request, jsonify

@app.route("/add_event", methods=["POST"])
def add_event():
    if "user" in session and session["role"] == "admin":
        try:
            data = request.get_json()
            if not data:
                return jsonify({"message": "Invalid request, JSON expected"}), 400

            title = data.get("title")
            description = data.get("description")
            date = data.get("date")
            apartment_code = session.get("apartment_code")

            if not title or not description or not date:
                return jsonify({"message": "All fields are required!"}), 400

            # Store in Firestore
            db.collection("events").add({
                "title": title,
                "description": description,
                "date": date,
                "apartment_code": apartment_code
            })
            return jsonify({"message": "Event added successfully!"}), 200

        except Exception as e:
            print("Error:", str(e))  # ✅ Print the error for debugging
            return jsonify({"message": "Server error: " + str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403


@app.route("/get_events", methods=["GET"])
def get_events():
    if "user" in session:
        apartment_code = session.get("apartment_code")

        try:
            events_ref = db.collection("events").where("apartment_code", "==", apartment_code).stream()
            events = [{"id": event.id, **event.to_dict()} for event in events_ref]
            return jsonify(events), 200
        except Exception as e:
            return jsonify({"message": str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403


# ✅ VOTE EVENT (Residents can vote)
@app.route("/vote_event/<event_id>/<vote_type>", methods=["POST"])
def vote_event(event_id, vote_type):
    if "user" in session:  # Ensure user is logged in
        try:
            user_flat_number = session.get("flat_number")  # Fetch flat number from session
            if not user_flat_number:
                return jsonify({"message": "Flat number not found in session"}), 403

            event_ref = db.collection("events").document(event_id)
            event = event_ref.get()

            if event.exists:
                event_data = event.to_dict()

                # Fetch previous votes
                yes_voters = event_data.get("yes_voters", [])
                no_voters = event_data.get("no_voters", [])

                # Check if user has already voted
                if user_flat_number in yes_voters or user_flat_number in no_voters:
                    return jsonify({"message": "You have already voted!"}), 400

                # Update votes
                if vote_type == "yes":
                    yes_voters.append(user_flat_number)
                else:
                    no_voters.append(user_flat_number)

                # Update Firestore
                event_ref.update({
                    "yes_voters": yes_voters,
                    "no_voters": no_voters,
                    "yes_votes": len(yes_voters),
                    "no_votes": len(no_voters),
                })

                return jsonify({
                    "message": "Vote submitted successfully!",
                    "yes_votes": len(yes_voters),
                    "no_votes": len(no_voters),
                    "yes_voters": yes_voters,
                    "no_voters": no_voters
                }), 200

            else:
                return jsonify({"message": "Event not found"}), 404

        except Exception as e:
            return jsonify({"message": str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403

@app.route("/delete_event", methods=["POST"])
def delete_event():
    data = request.json
    event_id = data.get("event_id")

    if event_id:
        db.collection("events").document(event_id).delete()
        return jsonify({"message": "Event deleted successfully!", "success": True})
    return jsonify({"message": "Event not found!", "success": False})

@app.route("/edit_event", methods=["POST"])
def edit_event():
    data = request.json
    event_id = data.get("event_id")
    new_title = data.get("title")
    new_date = data.get("date")
    new_description = data.get("description")

    if event_id and new_title and new_date and new_description:
        db.collection("events").document(event_id).update({
            "title": new_title,
            "date": new_date,
            "description": new_description
        })
        return jsonify({"message": "Event updated successfully!", "success": True})
    return jsonify({"message": "Error updating event!", "success": False})

@app.route('/complaints')
def complaints_page():
    if "user" in session and session["role"] == "resident":
        return render_template("complaints.html")
    return redirect("/login_page")

@app.route("/get_admin_complaints", methods=["GET"])
def get_admin_complaints():
    if "user" in session and session["role"] == "admin":
        apartment_code = session["apartment_code"]

        complaints_ref = db.collection("complaints").where("apartment_code", "==", apartment_code).stream()
        complaints_list = []

        for complaint in complaints_ref:
            complaint_data = complaint.to_dict()
            complaints_list.append({
                "id": complaint.id,
                "text": complaint_data.get("text", ""),
                "resident": complaint_data.get("resident_email", "Unknown"),
                "status": complaint_data.get("status", "Pending"),
                "flat_number": complaint_data.get("flat_number", "Unknown")
                
            })

        return jsonify({"success": True, "complaints": complaints_list}), 200

    return jsonify({"success": False, "message": "Unauthorized"}), 403

@app.route('/download_maintenance', methods=['GET'])
def download_maintenance():
    if "user" in session and session["role"] == "resident":
        try:
            month = request.args.get("month")
            year = request.args.get("year")

            if not month or not year:
                return jsonify({"error": "Month and Year are required"}), 400

            month_year = f"{year}-{month.zfill(2)}"

            records_ref = db.collection("maintenance").where("date", ">=", f"{month_year}-01")\
                                                     .where("date", "<=", f"{month_year}-31")\
                                                     .stream()
            
            csv_data = [["Resident Name", "Flat No", "Amount Paid", "Date"]]
            found_records = False  # Flag to check if records exist
            
            for record in records_ref:
                data = record.to_dict()
                csv_data.append([
                    data.get("resident_name", ""),
                    data.get("flat_number", ""),
                    data.get("amount_paid", ""),
                    data.get("date", "")
                ])
                found_records = True
            
            if not found_records:
                return jsonify({"error": "No records found for this month"}), 404
            
            # Create CSV response
            response = Response()
            response.status_code = 200
            response.headers["Content-Disposition"] = f"attachment; filename=maintenance_{month}_{year}.csv"
            response.headers["Content-Type"] = "text/csv"

            writer = csv.writer(response.stream)
            writer.writerows(csv_data)
            return response

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Unauthorized"}), 403
@app.route('/admin_gallery')
def admin_gallery():
    if "user" in session and session["role"] == "admin":
        return render_template("admin_gallery.html")
    return redirect("/login_page")
@app.route('/admin_amounts')
def amount():
    if "user" not in session or session.get("role") != "admin":
        return redirect("login")

    apartment_code = session.get("apartment_code")

    # Fetch expenses from Firestore
    expenses_ref = db.collection("expenses").where("apartment_code", "==", apartment_code).stream()

    expenses = [{"description": exp.to_dict().get("description"), "amount": exp.to_dict().get("amount")} for exp in expenses_ref]

    return render_template("admin_amount.html", expenses=expenses)

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    apartment_code = session.get("apartment_code")  # Get apartment code from session

    # Create a new expense record
    new_expense = {
        "month": data.get("month"),
        "description": data.get("description"),
        "amount": data.get("amount"),
        "apartment_code": apartment_code
    }

    # Add to Firestore
    db.collection("expenses").add(new_expense)

    return jsonify({"success": True, "message": "Expense added successfully!"})
from flask import request, jsonify
@app.route('/get_total_expenses')
def get_total_expenses():
    apartment_code = request.args.get("apartment_code")

    if not apartment_code:
        return jsonify({"total_amount": 0, "remaining_amount": 0})

    # Fetch total maintenance budget from Firestore
    maintenance_doc = db.collection("maintenance_records").document(apartment_code).get()
    total_budget = maintenance_doc.to_dict().get("total_amount", 0) if maintenance_doc.exists else 0

    # Fetch total expenses from Firestore
    expenses = db.collection("expenses").where("apartment_code", "==", apartment_code).stream()
    total_expenses = sum(expense.to_dict().get("amount", 0) for expense in expenses)

    # Calculate remaining amount
    remaining_amount = max(total_budget - total_expenses, 0)

    return jsonify({"total_amount": total_expenses, "remaining_amount": remaining_amount})




@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data["email"]

    user_data = next((doc.to_dict() for doc in db.collection("users").where("email", "==", email).stream()), None)
    if not user_data:
        return jsonify({"message": "User not found!"}), 401

    session.update({
        "user": email,
        "role": user_data.get("role"),
        "apartment_code": user_data.get("apartment_code"),
        "flat_number": user_data.get("flat_number", "Not Assigned")  # ✅ Default if missing
    })
    redirect_url = "/admin_dashboard" if user_data["role"] == "admin" else "/resident_dashboard"

    return jsonify({"message": "Login successful!", "redirect_url": redirect_url}), 200

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login_page")

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
