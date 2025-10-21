# main.py
from datetime import datetime, timezone, timedelta
import arxiv
import os

# ==================== 配置区 ====================
# 从 queries.txt 读取查询语句
with open("queries.txt", "r", encoding="utf-8") as file:
    QUERIES = [line.strip() for line in file.readlines() if line.strip()]

# 根下载目录
ROOT_DOWNLOAD_DIR = "./pdf"

# 每个查询最多下载多少篇论文
MAX_RESULTS_PER_QUERY = 20  # 精简：只下载20篇

# 抓取最近1天的论文
DAYS_AGO = 1
# ===============================================

# 计算时间窗口：只抓从这个日期之后提交的论文
CUTOFF_DATE = (datetime.now(timezone.utc).date() - timedelta(days=DAYS_AGO))

# 创建时间戳目录（格式：YYYY-MM-DD_HH-MM-SS）
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
SESSION_DIR = os.path.join(ROOT_DOWNLOAD_DIR, TIMESTAMP)
LOG_FILE = os.path.join(SESSION_DIR, "log.txt")

# 创建会话目录
os.makedirs(SESSION_DIR, exist_ok=True)

# 写日志头
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"📅 文献抓取日志 - {TIMESTAMP}\n")
    f.write(f"📥 每类最多下载: {MAX_RESULTS_PER_QUERY} 篇\n")
    f.write(f"{'='*50}\n")

def is_within_time_window(paper):
    """
    判断论文是否在设定的时间窗口内（即最近 DAYS_AGO 天内）
    """
    paper_date = paper.published.date()
    return paper_date >= CUTOFF_DATE

def sanitize_folder_name(query):
    """
    将查询语句映射为简短的分类文件夹名
    """
    q = query.lower()
    if "graph" in q or "gnn" in q or "geometric" in q or "equivariant" in q or "diffusion" in q:
        return "gnn-diffusion"
    if "causal" in q or "invariant" in q or "disentanglement" in q:
        return "causal-representation"
    if "time" in q or "temporal" in q or "dynamics" in q or "kinetic" in q:
        return "time-series-dynamics"
    if "large language" in q or "llm" in q or "reinforcement" in q or "molecule generation" in q:
        return "llm-rl-generation"
    if "agent" in q or "continual" in q or "lifelong" in q or "autonomous" in q or "closed-loop" in q:
        return "agent-cl-autonomous"
    return "others"

def fetch_papers(query):
    """
    抓取单个查询语句下的论文
    """
    folder_name = sanitize_folder_name(query)
    category_dir = os.path.join(SESSION_DIR, folder_name)

    print(f"\n🔍 搜索: {query}")

    # 构建搜索对象
    search = arxiv.Search(
        query=query,
        max_results=MAX_RESULTS_PER_QUERY,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    # 创建客户端
    client = arxiv.Client(
        page_size=min(MAX_RESULTS_PER_QUERY, 100),
        delay_seconds=2,  # 精简：减少延迟
        num_retries=2     # 精简：减少重试次数
    )

    downloaded = 0
    try:
        for result in client.results(search):
            # 时间过滤：只保留最近1天的论文
            if not is_within_time_window(result):
                continue

            # 防止超限
            if downloaded >= MAX_RESULTS_PER_QUERY:
                break

            # 第一次下载时创建分类文件夹
            if downloaded == 0:
                os.makedirs(category_dir, exist_ok=True)

            # 下载设置
            short_id = result.get_short_id()
            filename = f"{short_id}.pdf"

            try:
                result.download_pdf(dirpath=category_dir, filename=filename)
                print(f"✅ {short_id}: {result.title[:50]}...")

                # 精简日志
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{short_id} | {result.title[:60]} | {result.published.strftime('%m-%d %H:%M')}\n")

                downloaded += 1
            except Exception as e:
                print(f"❌ 下载失败 {short_id}: {e}")

    except Exception as e:
        print(f"❌ 查询执行出错: {e}")

    print(f"✅ 本类别共下载 {downloaded} 篇")
    return downloaded

# ========== 主程序 ==========
if __name__ == "__main__":
    print(f"📅 开始抓取【最近 {DAYS_AGO} 天】的新论文...")

    total_downloaded = 0
    for query in QUERIES:
        count = fetch_papers(query)
        total_downloaded += count

    print(f"\n🎉 抓取完成！共下载 {total_downloaded} 篇新论文。")
