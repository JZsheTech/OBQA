import arxiv

# 创建客户端（默认：每页 100 结果，3 秒延迟，3 次重试）
client = arxiv.Client(page_size=10, delay_seconds=3, num_retries=3)

# 搜索查询
search = arxiv.Search(
    query="all:electron",  # 或 "au:John Smith AND cat:cs.LG"
    max_results=5,
    sort_by=arxiv.SortCriterion.Relevance,  # 或 LastUpdatedDate, SubmittedDate
    sort_order=arxiv.SortOrder.Descending
)

# 获取结果（生成器，避免大结果集加载）
results = client.results(search)
for result in results:
    print(f"标题: {result.title}")
    print(f"作者: {', '.join(author.name for author in result.authors)}")
    print(f"摘要: {result.summary[:100]}...")  # 前 100 字符
    print(f"PDF: {result.pdf_url}")
    print("---")

search_by_id = arxiv.Search(id_list=["2506.05176v3"])
result = next(client.results(search_by_id))
print(result.title)


import arxiv
import requests

client = arxiv.Client()
search = arxiv.Search(query="all:electron", max_results=1)
result = next(client.results(search))

# 下载 PDF
pdf_url = result.pdf_url
response = requests.get(pdf_url)
with open("paper.pdf", "wb") as f:
    f.write(response.content)
print("PDF 下载完成！")