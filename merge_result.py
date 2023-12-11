import argparse
import json
import os
import openai

def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", type=str, default='korea')
    parser.add_argument("--file_path", type=str, default='./image')
    return parser


def parse_args():
    parser = init_args()
    return parser.parse_args()


def IoU(box1, box2):
    # box = (x1, y1, x2, y2)
    box1_area = abs((box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1))
    box2_area = abs((box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1))

    # obtain x1, y1, x2, y2 of the intersection
    x1 = max(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = max(box1[3], box2[3])

    # compute the width and height of the intersection
    w = max(0, x2 - x1 + 1)
    h = max(0, y1 - y2 + 1)
    inter = w * h
    iou = inter / (box1_area + box2_area - inter)
    return iou


def get_completion(Query):
    secret_file = os.path.join('./secrets.json')

    with open(secret_file) as f:
        secrets = json.loads(f.read())
        OPENAI_API_KEY = secrets['OPENAI_API_KEY']

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    temperature=0.1,
    max_tokens=24,
    messages=[
        {"role": "system", "content": "한국 요리를 입력로 받을거야. 무슨 단어로 구성된거야? 설명은 하지말고 단어들만 얘기해줘. /로 구분해서 답변해줘"},
        {"role": "user", "content": Query},
    ]
    )
    return response.choices[0].message.content

def error_completion(Query, Language):
    secret_file = os.path.join('./secrets.json')

    with open(secret_file) as f:
        secrets = json.loads(f.read())
        OPENAI_API_KEY = secrets['OPENAI_API_KEY']

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    temperature=0.1,
    max_tokens=24,
    messages=[
        {"role": "system", "content": f"한국어에서 {Language}로 설명은 하지말고 번역만 해줘."},
        {"role": "user", "content": Query},
    ]
    )
    return response.choices[0].message.content


def chg_trans(text_info, language):
    dict_language_txt = open('./doc/dict.txt', 'r', encoding='utf8')
    dict_language = json.load(dict_language_txt)

    len_text = len(text_info)
    
    for i in range(len_text):
        except_list = []

        origin = text_info[i]['transcription']
        origin = origin.replace(' ', '')
        text_info[i]['origin'] = origin
        
        try:
            trans = dict_language[origin][language]
            text_info[i]['transcription'] = trans
        except KeyError:
            trans = get_completion(origin)
            trans_list = trans.split('/')

            for word in trans_list:
                try:
                    except_list.append(dict_language[word][language])
                except KeyError:
                    except_list.append(error_completion(word, language))

            text_info[i]['transcription'] = ' '.join(except_list)

    return text_info


def get_final_info(number_info, text_info, args):
    len_number = len(number_info)
    len_text = len(text_info)
    x = []
    for n in range(len_number):
        for t in range(len_text):
            box1 = number_info[n]['points'][3] + number_info[n]['points'][1]
            box2 = text_info[t]['points'][3] + text_info[t]['points'][1]
    
            iou_result = IoU(box1,box2)
            if iou_result == 0:
                #print(iou_result)
                x.append(number_info[n])
                break
    final = chg_trans(text_info, args.language) + x
    return final


def make_final(args):
    image_path = os.path.join(args.file_path, "inference_results/menu")
    image_list = os.listdir(image_path)
    num_image = len(image_list) - 1
    number_path = os.path.join(args.file_path, "inference_results/number/system_results.txt")
    number = open(number_path, 'r')
    line_number = number.readlines()
    text_path = os.path.join(args.file_path, "inference_results/menu/system_results.txt")
    text = open(text_path, 'r')
    line_text = text.readlines()

    result_path = os.path.join(args.file_path, "inference_results/final_results.txt")
    result = open(result_path, 'w')

    for i in range(num_image):
        number_line = line_number[i].split('\t')
        img_name_number = number_line[0]
        number_info = json.loads(number_line[1])

        text_line = line_text[i].split('\t')
        img_name_text = text_line[0]
        text_info = json.loads(text_line[1])

        final = get_final_info(number_info, text_info, args)
        final = json.dumps(final, ensure_ascii=False)
        final = img_name_text + '\t' +final + '\n'
        result.write(final)

    result.close()
    number.close()
    text.close()

if __name__ == "__main__":
    args = parse_args()
    make_final(args)
    print('done')