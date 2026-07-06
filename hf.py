# 导入词嵌入模型，将文本转为计算机能理解的向量
from langchain_huggingface import HuggingFaceEmbeddings
# 导入文本分割器，把长文章切成小段方便检索
from langchain_text_splitters import CharacterTextSplitter
# 导入文档类，封装文本数据
from langchain_core.documents import Document
# 导入提示词模板，规范AI回答的格式
from langchain_core.prompts import PromptTemplate
# 导入输出解析器，提取AI返回的有效文字
from langchain_core.output_parsers import StrOutputParser
# 导入直通组件，构建数据处理管道
from langchain_core.runnables import RunnablePassthrough
# 导入模型、分词器、生成流水线的核心库
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
# 导入向量数据库，用于快速查找相似内容
import faiss
# 导入数值计算库，处理向量数据
import numpy as np
# 导入Gradio，制作可视化网页聊天界面
import gradio as gr

# ===================== 1. 加载本地知识库 =====================
file_path = "knowledge.txt"                  # 定义知识库文件路径
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()                          # 读取txt文件里的所有内容
documents = [Document(page_content=text)]    # 把内容封装成标准文档格式

# ===================== 2. 切割长文本 =====================
text_splitter = CharacterTextSplitter(
    chunk_size=200,         # 每一小段文本的最大长度
    chunk_overlap=50,       # 段落之间重叠50个字符，防止语义断裂
    separator="\n"          # 按换行符进行切割
)
chunks = text_splitter.split_documents(documents)  # 执行切割操作

# ===================== 3. 初始化向量模型 =====================
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"  # 轻量、快速、免费的中文向量模型
)

# ===================== 4. 创建向量检索库 =====================
chunk_texts = [c.page_content for c in chunks]  # 提取所有切割后的文本
chunk_embeds = embeddings.embed_documents(chunk_texts)  # 将文本转为向量
index = faiss.IndexFlatL2(len(chunk_embeds[0]))  # 创建向量索引库
index.add(np.array(chunk_embeds).astype("float32"))  # 把向量存入库中

# 定义检索函数：输入问题，返回最相关的知识库内容
def retrieve(question, top_k=2):
    q_embed = embeddings.embed_query(question)  # 把问题转为向量
    dists, idxs = index.search(np.array([q_embed]).astype("float32"), top_k)  # 搜索最相似内容
    return "\n\n".join([chunk_texts[i] for i in idxs[0]])  # 返回找到的内容

# ===================== 5. 加载本地训练好的模型 =====================
model_path = "./model-final-merged"          # 你合并好的最终模型路径
tokenizer = AutoTokenizer.from_pretrained(model_path)  # 加载分词器（文字转数字）
model = AutoModelForCausalLM.from_pretrained(model_path)  # 加载大语言模型

# ===================== 6. 创建生成流水线（极简配置，无警告） =====================
pipe = pipeline(
    task="text-generation",  # 任务类型：文本生成
    model=model,             # 绑定模型
    tokenizer=tokenizer      # 绑定分词器
)

# 生成参数：统一存放，彻底消除版本冲突警告
gen_params = {
    "max_new_tokens": 300,    # 最多生成300个字
    "temperature": 0.1,       # 回答严谨度，0最严谨
    "top_p": 0.9,             # 控制词汇多样性
    "do_sample": True,        # 开启智能采样
    "pad_token_id": tokenizer.eos_token_id  # 填充符号，防止报错
}

# ===================== 7. 构建RAG问答逻辑 =====================
prompt = PromptTemplate(
    template="根据下面的资料，简洁准确地回答问题：\n资料：{context}\n问题：{question}\n回答：",
    input_variables=["context", "question"]
)

# 核心问答函数
def ask_ai(question):
    context = retrieve(question)                # 从知识库找答案
    full_prompt = prompt.format(context=context, question=question)  # 拼接提问内容
    output = pipe(full_prompt, **gen_params)    # 让AI生成回答
    return output[0]["generated_text"].split("回答：")[-1].strip()  # 提取干净结果

# ===================== 8. 多轮聊天逻辑 =====================
def chat(message, history):
    response = ask_ai(message)  # 调用AI获取回答
    history.append((message, response))  # 把对话加入历史记录
    return history

# ===================== 9. 网页界面 =====================
with gr.Blocks(title="AI知识库助手") as demo:
    gr.Markdown("# 🤖 本地AI知识库聊天机器人")
    gr.Markdown("✅ 模型已整合 | ✅ 知识库已加载 | ✅ 多轮对话")
    
    chatbot = gr.Chatbot(height=500)  # 聊天窗口
    msg = gr.Textbox(label="输入问题")  # 输入框
    clear = gr.Button("清空对话")      # 清空按钮

    msg.submit(chat, [msg, chatbot], [chatbot])  # 回车发送
    clear.click(lambda: [], None, chatbot)      # 清空历史

# ===================== 10. 启动项目 =====================
if __name__ == "__main__":
    demo.launch()