from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
from PIL import Image
import io
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})\

# --- Model Paths ---
PEACH_MODEL_PATH = "peach_ripeness_v1.h5"
# Make sure you have this file in the same directory as app.py
APPLE_MODEL_PATH = "peach_ripeness_v2.9.h5"

# --- Load Models ---
# Check if peach model exists
if not os.path.exists(PEACH_MODEL_PATH):
    raise FileNotFoundError(f"Peach model dosyası bulunamadı: {PEACH_MODEL_PATH}")
peach_model = load_model(PEACH_MODEL_PATH)
peach_classes = ['Unripe', 'Ripe', 'Overripe']

# Check if apple model exists. If not, print a warning and set model to None.
# In a production environment, you might want to raise an error or handle this differently.
apple_model = None
if not os.path.exists(APPLE_MODEL_PATH):
    print(f"UYARI: Apple model dosyası bulunamadı: {APPLE_MODEL_PATH}. Bu modelin tahminleri devre dışı bırakılacak.")
else:
    try:
        apple_model = load_model(APPLE_MODEL_PATH)
        apple_classes = ['Overripe', 'Ripe', 'Unripe'] # Define classes for your apple model
    except Exception as e:
        print(f"UYARI: Apple modeli yüklenirken bir hata oluştu: {e}. Bu modelin tahminleri devre dışı bırakılacak.")
        apple_model = None

# --- Prediction Function for both models ---
def predict_image_all_models(img_bytes):
    try:
        # Preprocess image for models
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((224, 224))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # --- Predict with Peach Model ---
        peach_predictions_raw = peach_model.predict(img_array)[0]
        # Apply the original swap for peach predictions (Unripe with Overripe)
        swapped_peach_predictions = peach_predictions_raw.copy()
        swapped_peach_predictions[0] = peach_predictions_raw[2]
        swapped_peach_predictions[2] = peach_predictions_raw[0]
        peach_results = {peach_classes[i]: float(swapped_peach_predictions[i]) for i in range(len(peach_classes))}

        # --- Predict with Apple Model (if available) ---
        apple_results = None
        if apple_model:
            apple_predictions_raw = apple_model.predict(img_array)[0]
            # Assuming no custom swapping logic for the apple model unless you have one
            apple_results = {apple_classes[i]: float(apple_predictions_raw[i]) for i in range(len(apple_classes))}

        return {
            "peach_results": peach_results,
            "apple_results": apple_results # Will be None if apple_model was not loaded
        }
    except Exception as e:
        # Catch any errors during prediction or preprocessing
        raise ValueError(f"Görsel tahmini başarısız oldu: {str(e)}")

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'İstek dosya içermiyor'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi'}), 400

    try:
        results = predict_image_all_models(file.read())
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Tahmin sırasında beklenmedik bir hata oluştu: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)