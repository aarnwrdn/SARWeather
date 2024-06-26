from flask import Flask, request, jsonify, render_template
import prediction
import requests

app = Flask(__name__)
model_path = "model/my_model.keras"


@app.route("/")
def main():
    return render_template("indexcoba.html")


@app.route("/dashboard")
def dashboard():
    return render_template("indexcoba.html")


@app.route("/location")
def location():
    return render_template("location.html")


@app.route("/history")
def history():
    return render_template("history-data.html")

def get_api_data():
    api_url = "https://3uojc35gb6.execute-api.ap-southeast-2.amazonaws.com/SmartWeather/SmartWeatherSAR2"
    try: 
        response = requests.get(api_url)
        data = response.json()
        
            # Process data to handle null values and round floats using lambda functions
        process_entry = lambda entry: {k: "N/A" if v is None else round(v, 4) if isinstance(v, float) else v for k, v in entry.items()}
        data = [process_entry(entry) for entry in data]

        return data
    except requests.exceptions.RequestException as e:
        return None
    
@app.route("/predict", methods=["GET"])
def predict():
    try:
        data = get_api_data()
        result = prediction.startPrediction(data)
        forecast_df = result["result"]
        # Konversi DataFrame menjadi dictionary atau list
        result_dict = forecast_df.to_dict(orient='records')
        return jsonify(result_dict)
    except Exception as e:
        print(e)
        return jsonify({
            "error": True,
            "message": str(e)
        }), 500

@app.route("/data/latest", methods=["GET"])
def get_latest_data():
    data = get_api_data()
    if data:
        latest_entry = max(data, key=lambda x: x['TS'])
        return jsonify(latest_entry)
    else:
        return jsonify({"error": "Data not available. Please try again later."})    
    

@app.route("/data/history", methods=["GET"])
def get_history_data():
    data = get_api_data()
    if data:
        sorted_data = sorted(data, key=lambda x: x['TS'], reverse=True)
        return jsonify(sorted_data)
    else:
        return jsonify({"error": "Data not available. Please try again later."})
    
if __name__ == "__main__":
    app.run(debug=True, port=5000)
