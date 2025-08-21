from flask import Flask, request, jsonify
from vllm import LLM, SamplingParams
from modelscope import AutoModelForCausalLM, AutoTokenizer
import torch # require torch==2.2.2,accelerate>=0.26.0,numpy=2.2.3,modelscope


model_name = 'XGenerationLab/XiYanSQL-QwenCoder-3B-2502'
llm = LLM(
    model=model_name,
    trust_remote_code=True,      # 因为是自定义模型，需要开启
    dtype='float16',             # 推荐使用 float16 加速
    gpu_memory_utilization=0.9,  # 控制显存使用
    max_model_len=4096           # 根据实际需求调整
)

base_sampling_params = SamplingParams(
    temperature=0.1,
    top_p=0.8,
    max_tokens=1024,
    # stop_token_ids=[],  # 可选：添加停止 token
)
local_tokenizer = llm.get_tokenizer()



app = Flask(__name__)

@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    # 获取请求中的数据
    input_data = request.json

    # 提取提示（prompt）
    messages = input_data.get('messages', [])

    if not messages:
        return jsonify({'error': 'No messages provided'})

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    outputs = llm.generate(prompt, base_sampling_params, request_id=str(time.time()))
    generated_text = outputs[0].outputs[0].text


    # 生成响应格式
    response = {
        'id': 'xiyan',
        'object': 'chat.completion',
        'created': 1234567890,
        'model': model_name,
        'choices': [{
            'index': 0,
            'message': {
                "content":generated_text
            },
            'finish_reason': 'length'
        }]
    }
    print(generated_text)
    return jsonify(response)


if __name__ == '__main__':
    # this flask server runs on http://localhost:5090
    app.run(host='0.0.0.0', port=4090)

