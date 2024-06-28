from flask import jsonify
import pandas as pd
from pandas import DataFrame
from pandas import concat
import numpy as np
from sklearn import preprocessing
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta
from keras.models import load_model
from keras.layers import Bidirectional, LSTM
import requests


# Path to CSV file
model_path = "model/my_model.keras"

hist_window = 3
horizon = 8

features_col = [
    "RAINFALL",
    "TEMP",
    "WINDDIR",
    "WINDSPEED",
    "HUMIDITY",
    "PRESSURE",
]
features_num = len(features_col)


def startPrediction(data):
    df = get_data(data)
    df_preprocess = preprocess_data(df)
    df_model = model_prediction(df_preprocess, model_path)
    df_result = processing_prediction(df_model)
    return df_result


def FilterRAINFALL(val):
    try:
        val = float(val)
        if val < 0 or val > 1000:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val

def FilterTEMP(val):
    try:
        val = float(val)
        if val < 21 or val > 37:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val

def FilterWINDDIR(val):
    try:
        val = float(val)
        if val < 0 or val > 360:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val

def FilterWINDSPEED(val):
    try:
        val = float(val)
        if val > 24:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val

def FilterHUMIDITY(val):
    try:
        val = float(val)
        if val < 0 or val > 100:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val

def FilterPRESSURE(val):
    try:
        val = float(val)
        if val < 1000 or val > 1018:
            val = np.NaN
    except ValueError:
        val = np.NaN
    return val


def deret_waktu_regresi(dataset, target, start, end, window, horizon):
    X = []
    y = []
    start = start + window
    if end is None:
        end = len(dataset) - horizon

    for i in range(start, end):
        indices = range(i - window, i)
        if i + horizon > len(target):
            continue
        X.append(dataset[indices])

        # indicey = range(i+1, i+1+horizon)
        indicey = range(i, i + horizon)
        y.append(target[indicey])

    return np.array(X), np.array(y)


# Pengkategorian kondisi hujan & arah angin
def classify_rainfall(value):
    if value > 20:
        return "Hujan Sangat Lebat"
    elif value > 10:
        return "Hujan Lebat"
    elif value > 5:
        return "Hujan Sedang"
    elif value > 1:
        return "Hujan Ringan"
    elif value > 0.5:
        return "Hujan Sangat Ringan"
    else:
        return "Tidak Hujan"


def classify_winddir(value):
    if 1 <= value < 90:
        return "Timur Laut (TL)"
    elif value == 90:
        return "Timur (T)"
    elif 90 < value < 180:
        return "Tenggara (TG)"
    elif value == 180:
        return "Selatan (S)"
    elif 180 < value < 270:
        return "Barat Daya (BD)"
    elif value == 270:
        return "Barat (B)"
    elif 270 < value <= 360:
        return "Barat Laut (BL)"
    else:
        return "Utara (U)"


# get data
def get_data(data):
    # Define the date format
    date_format = "%Y-%m-%d %H:%M:%S"

    df = pd.DataFrame(data)
    # Remove all \n from TimeStamp
    df["TimeStamp"] = df["TimeStamp"].str.replace("\n", "")


    # Parse date from Day Month Date Hour:Minute:Second Year to datetime object
    df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], format=date_format)
    df = df.rename(
        columns={
            "Humidity": "HUMIDITY",
            "Pressure": "PRESSURE",
            "Rainfall": "RAINFALL",
            "Temperature": "TEMP",
            "WindDirection": "WINDDIR",
            "WindSpeed": "WINDSPEED",
        }
    )

    df["RAINFALL"] = df.apply(lambda row: FilterRAINFALL(row["RAINFALL"]), axis=1)
    df["TEMP"] = df.apply(lambda row: FilterTEMP(row["TEMP"]), axis=1)
    df["WINDDIR"] = df.apply(lambda row: FilterWINDDIR(row["WINDDIR"]), axis=1)
    df["WINDSPEED"] = df.apply(lambda row: FilterWINDSPEED(row["WINDSPEED"]), axis=1)
    df["HUMIDITY"] = df.apply(lambda row: FilterHUMIDITY(row["HUMIDITY"]), axis=1)
    df["PRESSURE"] = df.apply(lambda row: FilterPRESSURE(row["PRESSURE"]), axis=1)


    # Filter data to the latest 1 week or a maximum of 3 x 3600 data points
    # max_weeks = 1
    max_weeks = 1
    max_data_points = 3 * 60 * 60 /5 #3 hours kirim tiap 10 detik

    max_date = df['TimeStamp'].max()
    min_date_week = max_date - timedelta(days=max_weeks)

    # Filter data to the current week/days
    df_week = df[df['TimeStamp'] >= min_date_week]
    df_week = df_week.sort_values(by='TimeStamp', ascending=False)

    # Calculate the number of data points within the current week
    num_data_points_weeks = len(df_week)

    if num_data_points_weeks > max_data_points:
        # If the number of data points within the current week exceeds the maximum allowed,
        # limit the data to the maximum number of data points
        df = df_week.iloc[:max_data_points]
    else:
        # If the number of data points within the current week is within the maximum allowed,
        # include all data points within the current week
        df = df_week
    
    df = df.reset_index(drop=True)
    
    # If the number of data points is less than the sum of the historical window and horizon,
    # return None
    if len(df) < (hist_window + horizon):
        return None


    return df


def preprocess_data(data):
    df = data

    if df is None:
        return None

    # resample rata-rata di jam dan hari yg sama pada semua tahun
    dfl = df.groupby(
        [df["TimeStamp"].dt.month, df["TimeStamp"].dt.day, df["TimeStamp"].dt.hour],
        as_index=True,
    ).mean()

    # mengisikan rata2 pada jam dan tanggal yg sama pada nilai NaN
    for kolom in list(df):
        index = df.index[df[kolom].apply(np.isnan)]
        for num, val in enumerate(index):
            df.loc[val, kolom] = dfl.loc[
                df["TimeStamp"].dt.month[num],
                df["TimeStamp"].dt.day[num],
                df["TimeStamp"].dt.hour[num],
            ][kolom]

    features = df[features_col]
    col_names = list(features.columns)
    s_scaler = preprocessing.StandardScaler()
    features = s_scaler.fit_transform(features)
    features = pd.DataFrame(features, columns=col_names)

    x_scaler = preprocessing.MinMaxScaler()
    y_scaler = preprocessing.MinMaxScaler()
    dataX = x_scaler.fit_transform(features)

    variabel = ["RAINFALL", "TEMP", "WINDDIR", "WINDSPEED", "HUMIDITY", "PRESSURE"]
    target = []
    for i in range(horizon):
        target += variabel

    dataY = y_scaler.fit_transform(df[target])

    n = int(dataY.shape[1] / horizon)
    TRAIN_SPLIT = int(len(df))

    x_multi, y_multi = deret_waktu_regresi(
        dataX, dataY[:, :n], 0, TRAIN_SPLIT, hist_window, horizon
    )

    output = y_multi.shape[2] * y_multi.shape[1]
    y_multi = y_multi.reshape(-1, output, 1)

    return {
        "x_multi": x_multi,
        "y_scaler": y_scaler,
        "df": df,
    }


def model_prediction(data, filepath=model_path):
    if data is None:
        return None

    # Convert data to DataFrame
    model = load_model(
        filepath, custom_objects={"Bidirectional": Bidirectional, "LSTM": LSTM}
    )

    x_multi = data["x_multi"]
    y_scaler = data["y_scaler"]

    new_columns = []
    for i in range(1, horizon + 1):
        new_columns += [
            x + str(i)
            for x in [
                "RAINFALL",
                "TEMP",
                "WINDDIR",
                "WINDSPEED",
                "HUMIDITY",
                "PRESSURE",
            ]
        ]

    # Make prediction
    pred = model.predict(x_multi)
    preds = y_scaler.inverse_transform(pred)
    predictions_df = pd.DataFrame(preds, columns=new_columns)
    return predictions_df


def processing_prediction(data):
    if data is None:
        return {"result": None, "message": "Data not available"}

    # Calculate the mean for each column
    mean_values = data.mean()
    mean_values_rounded = mean_values.round(4)

    # Convert to a 1 x 48 array
    mean_array = mean_values_rounded.to_numpy().reshape(1, -1)
    forecast = mean_array.flatten()

    # Reshape the forecast array into 2 dimension array
    mean_array_reshaped = forecast.reshape(horizon, features_num)
    current_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    data_list = []
    for i in range(8):
        hour_data = {"timestamp": (current_time + timedelta(hours=i + 8)).strftime('%a, %d %b %Y %H:%M:%S')}
        for j, feature in enumerate(features_col):
            hour_data[feature] = round(float(mean_array_reshaped[i, j]), 4)
            if feature == "RAINFALL":
                hour_data["rainfall_text"] = classify_rainfall(
                    mean_array_reshaped[i, j]
                )
            elif feature == "WINDDIR":
                hour_data["winddir_text"] = classify_winddir(mean_array_reshaped[i, j])
        data_list.append(hour_data)

    forecast_df = pd.DataFrame(data_list)

    result = {
        "result": forecast_df,
    }
    return result
