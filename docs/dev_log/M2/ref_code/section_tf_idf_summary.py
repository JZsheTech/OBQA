
from nltk.tokenize import sent_tokenize, word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import nltk

from pathlib import Path
import os
import sys
PROJECT_ROOT_PATH = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT_PATH))

nltk_user_path = os.path.join(PROJECT_ROOT_PATH, "model/nltk_data")
nltk.data.path.clear()
nltk.data.path.append(nltk_user_path)  # 将数据路径设置为当前目录下的data文件夹   

def tfidf_summary(text, num_sentences=1):
    sentences = sent_tokenize(text)
    
    # 验证输入
    if not sentences:
        return ""
    
    # 过滤空句子和过短的句子
    valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if not valid_sentences:
        return sentences[0] if sentences else ""
    
    # 如果请求的句子数超过可用句子数，调整数量
    num_sentences = min(num_sentences, len(valid_sentences))
    
    try:
        # 计算TF-IDF
        vectorizer = TfidfVectorizer(
            stop_words='english',
            min_df=1,  # 确保至少出现1次的词被包含
            max_features=1000,  # 限制特征数量
            lowercase=True,
            token_pattern=r'\b[a-zA-Z]{2,}\b'  # 只匹配字母且长度>=2的词
        )
        X = vectorizer.fit_transform(valid_sentences)
        
        # 检查是否生成了有效的特征
        if X.shape[1] == 0:
            # 如果没有有效特征，返回第一个句子
            return valid_sentences[0]
        
        # 计算句子重要性（TF-IDF分数之和）
        sentence_scores = X.sum(axis=1).A1  # .A1 将矩阵转换为1D数组
        
        # 获取最重要的句子
        top_indices = np.argsort(sentence_scores)[-num_sentences:]
        
        # 按原文顺序排序索引
        top_indices = sorted(top_indices)
        
        top_sentences = [valid_sentences[i] for i in top_indices]
        
        return '\n'.join(top_sentences)
        
    except ValueError as e:
        if "empty vocabulary" in str(e):
            # 如果词汇表为空，返回第一个有效句子
            return valid_sentences[0]
        else:
            raise e


if __name__ == "__main__":

    text = """
    Natural language processing (NLP) is a subfield of linguistics, computer science, 
    and artificial intelligence concerned with the interactions between computers and 
    human language, in particular how to program computers to process and analyze 
    large amounts of natural language data. The result is a computer capable of 
    "understanding" the contents of documents, including the contextual nuances of 
    the language within them. The technology can then accurately extract information 
    and insights contained in the documents as well as categorize and organize the 
    documents themselves. Challenges in natural language processing frequently involve 
    speech recognition, natural language understanding, and natural language generation.
    """


    print("\n基于TF-IDF的摘要:")
    print(tfidf_summary(text, num_sentences=2))


