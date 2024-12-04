from bson import ObjectId  # Import to handle ObjectId serialization
from flask import Flask, render_template, request, jsonify
from facebook_page_scraper import FacebookPageScraper
from pymongo import MongoClient
import datetime

# Initialize Flask app
app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")  # Replace with your MongoDB connection string
db = client["facebook_scraper_db"]  # Database name
collection = db["scraped_data"]  # Collection name

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get the URL input from the form
        page_url = request.form.get("page_url")

        # Validate the URL
        if not page_url:
            return jsonify({"error": "Page URL is required"}), 400

        try:
            # Scrape the Facebook page
            page_info = FacebookPageScraper.PageInfo(page_url)

            # Add a timestamp to the scraped data
            page_info["scraped_at"] = datetime.datetime.now()

            # Save to MongoDB
            result = collection.insert_one(page_info)

            # Add the inserted ID to the response
            page_info["_id"] = str(result.inserted_id)

        except Exception as e:
            # Handle any scraping or other errors
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    # Retrieve all data from the database
    all_data = list(collection.find({}))
    for item in all_data:
        item["_id"] = str(item["_id"])  # Convert ObjectId to string for JSON serialization

        # Aggregate category counts and total followers
    category_counts = {}
    total_followers = 0
    top_pages = []

    def clean_followers(value):
        try:
            # Remove unnecessary characters, handle M (millions) and K (thousands)
            value = value.split(" ")[0].replace(",", "").replace("M", "000000").replace("K", "000")
            return int(float(value))
        except (ValueError, TypeError):
            return 0  # Return 0 if conversion fails

    # Aggregate category counts and total followers
    for item in all_data:
        category = item.get("page_category", "Unknown")
        category_counts[category] = category_counts.get(category, 0) + 1

        followers = clean_followers(item.get("page_followers", "0"))
        total_followers += followers

    # Get top 5 pages by followers
    all_data_sorted = sorted(all_data, key=lambda x: clean_followers(x.get("page_followers", "0")), reverse=True)
    top_pages = [{"name": item["page_name"] or "Unknown", "followers": clean_followers(item.get("page_followers", "0"))} for item in all_data_sorted[:5]]

    # Prepare chart data
    chart_data = {
        "labels": list(category_counts.keys()),
        "values": list(category_counts.values())
    }

    top_pages_chart = {
        "labels": [page["name"] for page in top_pages],
        "values": [page["followers"] for page in top_pages]
    }

    # Debugging outputs
    print("Chart Data for Pie Chart:", chart_data)
    print("Chart Data for Bar Chart:", top_pages_chart)


    # Render the HTML form and table
    return render_template(
        "index.html",
        data=all_data,
        total_pages=len(all_data),
        unique_categories=len(category_counts),
        total_followers=total_followers,
        chart_data=chart_data,
        top_pages=top_pages_chart,
    )



@app.route("/delete", methods=["POST"])
def delete():
    try:
        # Get the ID from the form
        item_id = request.form.get("id")

        # Remove the item from the database
        result = collection.delete_one({"_id": ObjectId(item_id)})

        if result.deleted_count == 1:
            return jsonify({"message": "Successfully deleted!"}), 200
        else:
            return jsonify({"error": "No such item found."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/delete_all", methods=["POST"])
def delete_all():
    try:
        # Delete all items in the database
        collection.delete_many({})
        return jsonify({"message": "All data successfully deleted!"}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(debug=True)
