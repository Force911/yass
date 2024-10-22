import os
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
import pandas as pd
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'txt'}
app.secret_key = 'supersecretkey'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def determine_sleep_stage(hr, spo2, temp):
    """
    Determines the sleep stage based on heart rate, SpO2, and temperature.
    :param hr: Heart rate value.
    :param spo2: SpO2 value.
    :param temp: Body temperature value.
    :return: String indicating the sleep stage.
    """
    # Define typical ranges for each stage
    HR_AWAKE = 70  # bpm
    HR_LIGHT = 50
    HR_DEEP = 40
    HR_REM = 60
    
    SPO2_NORMAL = 95  # %
    
    TEMP_AWAKE = 36.6  # Celsius
    TEMP_SLEEP = 36.0
    
    if hr >= HR_AWAKE and spo2 >= SPO2_NORMAL and temp >= TEMP_AWAKE:
        return "Awake"
    elif HR_LIGHT < hr < HR_AWAKE and spo2 >= SPO2_NORMAL and TEMP_SLEEP <= temp < TEMP_AWAKE:
        return "Light Sleep"
    elif hr <= HR_DEEP and spo2 >= SPO2_NORMAL and temp <= TEMP_SLEEP:
        return "Deep Sleep"
    elif HR_REM <= hr < HR_AWAKE and spo2 >= SPO2_NORMAL and temp >= TEMP_SLEEP:
        return "REM Sleep"
    else:
        return "Light Sleep"  # Default to light sleep if no clear stage is found

# Group sleep data into blocks based on consecutive sleep stages
def group_sleep_cycles(df):
    df['Sleep Stage'] = df.apply(lambda row: determine_sleep_stage(row['HR'], row['SpO2'], row['Temp']), axis=1)
    
    grouped_stages = []
    current_stage = None
    current_start = None
    current_duration = 0
    
    for index, row in df.iterrows():
        if row['Sleep Stage'] != current_stage:
            if current_stage:
                grouped_stages.append({
                    'stage': current_stage,
                    'start': current_start,
                    'duration': current_duration * 90  # 90 seconds per row
                })
            current_stage = row['Sleep Stage']
            current_start = row['Timestamp']
            current_duration = 1
        else:
            current_duration += 1
    
    # Append the final stage
    grouped_stages.append({
        'stage': current_stage,
        'start': current_start,
        'duration': current_duration * 90
    })
    
    return grouped_stages

# Upload .txt file from ESP32 or manually
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Process the uploaded file
        df = pd.read_csv(filepath, delimiter="\t", names=["Timestamp", "HR", "SpO2", "Temp"])
        sleep_data = group_sleep_cycles(df)
        
        return jsonify(sleep_data)  # Return the grouped sleep data in JSON for charting
    else:
        flash('Allowed file type is .txt')
        return redirect(request.url)

# Render the index page
@app.route('/')
def index():
    return render_template('Main.html')

if __name__ == '__main__':
    app.run(debug=True)
