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
MAX_RESULTS_PER_QUERY = 50  # 可自由调整：10（日常）、50（周报）、100（调研）

# 是否只抓取最近 N 天的论文？
DAYS_AGO = 7           # ← 设置为 7 表示“最近一周”
ONLY_TODAY = True      # ← 设为 True 表示启用时间过滤
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
    f.write(f"📅 文献抓取日志\n")
    f.write(f"⏰ 执行时间: {TIMESTAMP}\n")
    f.write(f"📅 抓取范围: 最近 {DAYS_AGO} 天（从 {CUTOFF_DATE} 开始）\n")
    f.write(f"🔍 查询类别数: {len(QUERIES)}\n")
    f.write(f"📥 每类最多下载: {MAX_RESULTS_PER_QUERY} 篇\n")
    f.write(f"{'='*80}\n\n")

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
    print(f"📁 分类文件夹: {folder_name}")

    # 构建搜索对象
    search = arxiv.Search(
        query=query,
        max_results=MAX_RESULTS_PER_QUERY,           # 控制总请求数
        sort_by=arxiv.SortCriterion.SubmittedDate,   # 按提交时间排序
        sort_order=arxiv.SortOrder.Descending,       # 最新的在前
    )

    # 创建客户端
    client = arxiv.Client(
        page_size=min(MAX_RESULTS_PER_QUERY, 100),   # 每页请求数
        delay_seconds=3,                             # 请求间隔，尊重服务器
        num_retries=3                                # 网络失败时重试次数
    )

    downloaded = 0
    try:
        for result in client.results(search):
            # 时间过滤：只保留最近 N 天的论文
            if ONLY_TODAY and not is_within_time_window(result):
                continue  # 跳过太早的论文

            # 防止超限
            if downloaded >= MAX_RESULTS_PER_QUERY:
                break

            # 第一次下载时创建分类文件夹
            if downloaded == 0:
                os.makedirs(category_dir, exist_ok=True)

            # 下载设置
            short_id = result.get_short_id()
            filename = f"{short_id}.pdf"
            filepath = os.path.join(category_dir, filename)

            try:
                result.download_pdf(dirpath=category_dir, filename=filename)
                print(f"✅ {short_id}: {result.title[:70]}...")

                # 写入日志
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"📄 论文ID: {short_id}\n")
                    f.write(f"   标题: {result.title}\n")
                    f.write(f"   作者: {', '.join(str(author) for author in result.authors)}\n")
                    f.write(f"   提交时间: {result.published.strftime('%Y-%m-%d %H:%M')} (UTC)\n")
                    f.write(f"   链接: {result.entry_id}\n")
                    f.write(f"   保存路径: {filepath}\n")
                    f.write(f"{'-'*80}\n")

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
    print(f"📁 本次结果将保存在: ./{SESSION_DIR}/")

    total_downloaded = 0
    for query in QUERIES:
        count = fetch_papers(query)
        total_downloaded += count

    # 更新日志头部统计
    with open(LOG_FILE, "r+", encoding="utf-8") as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f"📊 总计下载: {total_downloaded} 篇论文\n")
        f.write(f"{'='*80}\n\n")
        f.write(content)

    print(f"\n🎉 抓取完成！共下载 {total_downloaded} 篇新论文。")
    print(f"📝 详细日志已保存: {LOG_FILE}")