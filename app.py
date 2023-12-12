from flask import Flask, request, jsonify, send_file
import subprocess
import os
import shutil
import time
from flask_cors import CORS
import json
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO

app = Flask(__name__)
CORS(app)

ALLOWED_LANGUAGES = {"english", "japanese", "chinese"}
route = []


def create_directory_structure(base_dir):
    # 디렉토리 생성
    os.makedirs(os.path.join(base_dir, 'image'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'inference_results/number'), exist_ok=True)
    route.append(os.path.join(base_dir))

    # 필요한 빈 파일 생성
    open(os.path.join(base_dir, 'inference_results/final_results.txt'), 'a').close()
    open(os.path.join(base_dir, 'inference_results/system_results.txt'), 'a').close()
    open(os.path.join(base_dir, 'inference_results/number/system_results.txt'), 'a').close()

    # txt 파일 생성
    open(os.path.join(base_dir, 'inference_results/number/txt'), 'a').close()

@app.route('/translate/<language>', methods=['POST'])
def run_model(language):
    if language.lower() not in ALLOWED_LANGUAGES:
        return jsonify({'error': 'Invalid language'}), 400

    print("Received language:", language)

    if 'imageName' not in request.form:
        return jsonify({'error': 'No imageName provided'}), 400
    image_name = request.form['imageName']

    if 'imageFile' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    base_dir = os.path.join('.', image_name)
    create_directory_structure(base_dir)
    
    image_file = request.files['imageFile']
    image_path = os.path.join(base_dir, 'image', image_name)
    try:
        image_file.save(image_path)
    except Exception as e:
        return jsonify({'error': f'Failed to save image: {str(e)}'}), 500

    try:
        subprocess.run(['bash', 'run.sh', image_name, language], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Failed to run model: {str(e)}'}), 500

    results_path = os.path.join(base_dir, 'inference_results/final_results.txt')
    while not is_model_done(results_path):
        time.sleep(1)

    try:
        with open(results_path, 'r') as file:
            results = file.read()
            parts = results.split('\t', 1)
            image_name_result = parts[0]

            json_string = parts[1].strip()
            if not (json_string.startswith('[') or json_string.startswith('{')):
                return jsonify({'error': 'Invalid JSON format'}), 500

            translated_txt_result = json.loads(json_string)

            menuName = []
            price = []
            for item in translated_txt_result:
                if item['transcription'].isdigit():
                    price_item = {'priceValue': item['transcription'], 'points': item['points']}
                    price.append(price_item)
                else:
                    menuName.append(item)

            shutil.rmtree(base_dir)

            
            return {
                "imageName": image_name_result,
                "menuName": menuName,
                "price": price
            }

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to read results: {str(e)}'}), 500

def is_model_done(results_path):
    return os.path.exists(results_path) and os.path.getsize(results_path) > 0


### 워드클라우드
# final_results.txt 매핑
def read_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def parse_text_content(text_content):
    data = eval(text_content)
    menu_entries = data.get('menuName', [])
    mapping = {entry['origin']: entry['transcription'] for entry in menu_entries}
    return mapping

# 번역된 메뉴이름 key값으로 옮김
def replace_keys_with_transcription(mapping, input_json):
    result = {mapping[key]: value for key, value in input_json.items()}
    return result

#워드클라우드
def wordcloud(data, save_path=None):
    wordcloud = WordCloud(
        font_path='doc/fonts/HANDotum.ttf',
        width=800, height=400, background_color='white',
        colormap='autumn'
    ).generate_from_frequencies(data)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')

    if save_path:
        plt.savefig(save_path, format='png')

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)

    return img_buffer

@app.route('/wordcloud', methods=['POST'])
def get_mapping():
    try:
        input_json = request.get_json()
        
        base_dir = input_json.get('imageName', route[-1])
        file_path = os.path.join(base_dir, 'inference_results/final_results.txt')
        text_content = read_text_file(file_path)
        mapping = parse_text_content(text_content)

        result = replace_keys_with_transcription(mapping, input_json)
        save_path = 'static/wordcloud.png'
            
        img_buffer = wordcloud(result, save_path)
        return send_file(img_buffer, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port, debug=True)

