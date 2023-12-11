if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <path>"
    exit 1
fi

path="$1"
lang="$2"

python3 ./predict_system.py \
    --image_dir="$path"/image \
    --det_algorithm="DB++" \
    --det_model_dir="../model/detection" \
    --rec_model_dir="../model/recognition" \
    --rec_image_shape="3, 48, 320" \
    --draw_img_save_dir="$path"/inference_results/menu \
    --rec_char_dict_path="./ppocr/utils/korean_dict.txt" \
    --use_gpu=False

python3 ./predict_system_num.py  \
    --image_dir="$path"/image \
    --det_model_dir='../model/det_nummodel_dir/' \
    --rec_model_dir='../model/rec_nummodel_dir/' \
    --rec_image_shape="3, 48, 320" \
    --draw_img_save_dir="$path"/inference_results/number \
    --rec_char_dict_path="./ppocr/utils/en_dict.txt" \
    --use_gpu=False

python3 ./merge_result.py \
    --language=$lang \
    --file_path="$path" \
