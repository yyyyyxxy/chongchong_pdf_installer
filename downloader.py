import os
import requests
import base64
import time
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin

# 配置常量
EDGE_DRIVER_NAME = "msedgedriver.exe"

def get_html_and_extract(link):
    """提取乐谱详情页中的 iframe 地址"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
        }
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', id='ai-score')
        if iframe and 'src' in iframe.attrs:
            # 自动处理相对/绝对路径
            return urljoin(link, iframe['src'])
        return None
    except Exception as e:
        print(f"❌ 网页解析失败: {e}")
        return None

def init_driver():
    """初始化 Edge 浏览器驱动"""
    edge_options = Options()
    edge_options.add_argument("--headless")  # 无头模式
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    # 隐藏无用的控制台日志
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # 在当前目录、drivers子目录或脚本目录下寻找驱动
    paths = [
        EDGE_DRIVER_NAME,
        os.path.join("drivers", EDGE_DRIVER_NAME),
        os.path.join(os.path.dirname(__file__), EDGE_DRIVER_NAME)
    ]
    
    driver_path = next((p for p in paths if os.path.exists(p)), EDGE_DRIVER_NAME)
    
    try:
        service = Service(driver_path)
        return webdriver.Edge(service=service, options=edge_options)
    except Exception as e:
        print(f"❌ 启动 Edge 驱动失败: {e}")
        print(f"请确保 {EDGE_DRIVER_NAME} 版本正确并位于脚本同级目录。")
        exit(1)

def save_score_as_pdf(driver, url, suffix):
    """利用 CDP 将页面打印为 PDF"""
    try:
        driver.get(url)
        # 显式等待：直到乐谱的 SVG 文字元素加载
        wait = WebDriverWait(driver, 15)
        target_xpath = "//*[name()='text' and @text-anchor='middle']"
        elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, target_xpath)))
        
        # 获取乐谱标题并清理非法字符
        title = elements[0].text.strip()
        clean_title = ''.join(c if c not in '/\\:*?"<>|' else '_' for c in title)
        
        # 注入 CSS：隐藏网页按钮，并强制页边距为 0
        script = """
        var style = document.createElement('style');
        style.innerHTML = '@page { margin: 0; } .print { display: none !important; }';
        document.head.appendChild(style);
        """
        driver.execute_script(script)

        # CDP 打印参数 (A4 纸张)
        print_options = {
            'paperWidth': 8.27,
            'paperHeight': 11.69,
            'marginTop': 0, 
            'marginBottom': 0, 
            'marginLeft': 0, 
            'marginRight': 0,
            'printBackground': True
        }

        # 执行打印
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        filename = f"{clean_title}_{suffix}.pdf"
        
        # 保存文件
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(pdf_data['data']))
        print(f"✅ 保存成功: {filename}")
        
    except Exception as e:
        print(f"❌ 打印失败 ({suffix}): {e}")

def main():
    print("=" * 60)
    print("🎹 虫虫钢琴乐谱下载器 (全能版)")
    print("=" * 60)

    # 参数解析
    parser = argparse.ArgumentParser(description="虫虫钢琴乐谱下载工具")
    parser.add_argument('-u', '--url', help='单个乐谱详情页链接')
    parser.add_argument('-f', '--file', help='包含多个链接的文本文件')
    args = parser.parse_args()

    links = []

    # 获取输入链接
    if args.url:
        links.append(args.url)
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ 找不到文件: {args.file}")
            return
    else:
        print("提示：请输入链接，每行一个，输入空行结束。")
        while True:
            u = input("请输入链接: ").strip()
            if not u: break
            links.append(u)

    if not links:
        print("❌ 没有可处理的链接。")
        return

    # 初始化浏览器（仅初始化一次，复用实例提高效率）
    driver = init_driver()
    
    try:
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}] 正在解析: {link}")
            iframe_url = get_html_and_extract(link)
            
            if iframe_url:
                # 1. 下载五线谱版
                print(f"   >>> 正在下载五线谱版本...")
                save_score_as_pdf(driver, iframe_url, "五线谱")
                
                # 2. 下载简谱版 (通过修改 URL 参数)
                print(f"   >>> 正在下载简谱版本...")
                jianpu_url = iframe_url.replace('jianpuMode=0', 'jianpuMode=1')
                save_score_as_pdf(driver, jianpu_url, "简谱")
            else:
                print("   ❌ 解析失败：未能在页面中找到乐谱资源。")
                
    finally:
        driver.quit()
        print("\n" + "=" * 60)
        print("🎉 所有任务处理完毕！")
        print("=" * 60)

if __name__ == "__main__":
    main()
