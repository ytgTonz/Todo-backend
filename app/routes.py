from flask import Blueprint, request, jsonify, render_template, redirect
from bson.objectid import ObjectId
from app.database import mongo
from app.models import Item, User
from datetime import datetime
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    verify_password = data.get("verify_password")

    if not username or not password or not verify_password or not email:
        return jsonify({"error": "Username, password, verify_password, and email are required"}), 400

    if password != verify_password:
        return jsonify({"error": "Passwords do not match"}), 400

    if User.find_by_email(email):
        return jsonify({"error": "User already exists"}), 409

    User.create_user(username, email, password)
    return jsonify({"message": "Registration successful"}), 201

@api_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = User.find_by_email(email)
    if not user or not User.verify_password(user, password):
        return jsonify({"error": "Invalid credentials"}), 401
    access_token = create_access_token(identity=email)
    return jsonify({"access_token": access_token}), 200

# Protect todo routes:
@api_bp.route("/api/todo_entries", methods=["POST"])
@jwt_required()
def create_item():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Invalid input, 'name' is required and JSON must be sent"}), 400
    name = data["name"]
    timestamp = datetime.now().isoformat()
    user_email = get_jwt_identity()
    item = {"name": name, "time": timestamp, "user_email": user_email}
    result = mongo.db.todo_entries.insert_one(item)
    objId = str(result.inserted_id)
    return jsonify({"id": objId, "name": name, "time": timestamp}), 201

@api_bp.route("/api/todo_entries", methods=["GET"])
@jwt_required()
def get_items():
    user_email = get_jwt_identity()
    items = mongo.db.todo_entries.find({"user_email": user_email})
    return jsonify([Item.to_dict(item) for item in items])

@api_bp.route("/api/todo_entries/<string:item_id>", methods=["PUT"])
@jwt_required()
def update_item(item_id):
    user_email = get_jwt_identity()
    data = request.get_json()
    update_data = {"$set": {"name": data.get("name"), "description": data.get("description")}}
    # Only update if the item belongs to the user
    result = mongo.db.todo_entries.update_one({"_id": ObjectId(item_id), "user_email": user_email}, update_data)
    if result.matched_count:
        updated_item = mongo.db.todo_entries.find_one({"_id": ObjectId(item_id)})
        return jsonify(Item.to_dict(updated_item))
    return jsonify({"error": "Item not found or not authorized"}), 404

@api_bp.route("/api/todo_entries/<string:item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id):
    user_email = get_jwt_identity()
    # Only delete if the item belongs to the user
    result = mongo.db.todo_entries.delete_one({"_id": ObjectId(item_id), "user_email": user_email})
    if result.deleted_count:
        return jsonify({"message": "Item delete is successful"})
    return jsonify({"error": "Item wasnt found or not authorized"}), 404