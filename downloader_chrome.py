import argparse
import base64
import os
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_html_and_extract(link):
    """
    Fetches the HTML content of a given link and extracts the src of an iframe.

    Args:
        link (str): The URL to fetch.

    Returns:
        str: The value of the src attribute of the iframe, or None if not found.
    """
    try:
        response = requests.get(link)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', id='ai-score')
        if iframe and 'src' in iframe.attrs:
            return iframe['src']
        else:
            print("未找到乐谱iframe，可能不是支持的乐谱页面")
            return None
    except requests.RequestException as e:
        print(f"获取页面失败: {e}")
        return None


def save_page_as_pdf(url, output_pdf):
    """
    Saves a web page as a PDF file using Selenium and Chrome.

    Args:
        url (str): The URL of the web page to save.
        output_pdf (str): The name of the output PDF file.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
    )
    chrome_options.add_argument("referer=")
    chrome_options.add_argument("accept-language=en-US,en;q=0.9")

    possible_paths = [
        "chromedriver.exe",
        "drivers/chromedriver.exe",
        os.path.join(os.path.dirname(__file__), "chromedriver.exe"),
    ]
    driver_path = None
    for path in possible_paths:
        if os.path.exists(path):
            driver_path = path
            break

    if not driver_path:
        print("[Error] 错误: 找不到Chrome驱动文件")
        print("请下载chromedriver.exe并放在以下任一位置:")
        for path in possible_paths:
            print(f" - {os.path.abspath(path)}")
        print(
            "下载地址: https://googlechromelabs.github.io/chrome-for-testing/"
        )
        return

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("正在加载乐谱页面...")
        driver.get(url)
        script = """
        (function(){
            'use strict';
            if (!document.referrer) {
                location.href += '';
            }
            var style = document.createElement('style');
            style.innerHTML = '.print{display:none!important}';
            document.head.appendChild(style);
        })();
        """
        driver.execute_script(script)
        retries = 4
        for attempt in range(retries):
            print(f"尝试获取乐谱内容... ({attempt + 1}/{retries})")
            time.sleep(5)
            elements = driver.find_elements(
                By.XPATH, "//*[name()='text' and @text-anchor='middle']"
            )
            if elements:
                title = elements[0].text.strip()
                clean_title = (
                    ''.join(c for c in title if c not in '/\\:*?"<>|')
                    if title
                    else "Unknown"
                )
                print_options = {
                    'paperWidth': 8.27,
                    'paperHeight': 11.69,
                    'marginTop': 0,
                    'marginBottom': 0,
                    'marginLeft': 0,
                    'marginRight': 0,
                    'printBackground': True,
                    'landscape': False,
                }
                print(f"正在生成PDF: {output_pdf}")
                pdf_data = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                output_pdf_path = f"{clean_title}-{output_pdf}.pdf"
                with open(output_pdf_path, 'wb') as f:
                    f.write(base64.b64decode(pdf_data['data']))
                print(f"[Success] PDF保存成功: {output_pdf_path}")
                return
            else:
                print(f"[Failed] 第{attempt + 1}次尝试失败，正在重试...")
        print("[Error] 无法加载乐谱内容，请检查链接是否正确")
    except Exception as e:
        print(f"处理过程中出错: {e}")
    finally:
        driver.quit()


def main():
    """
    Main function to run the piano score downloader.
    """
    print("=" * 60)
    print("虫虫钢琴乐谱下载器 (Chrome版)")
    print("=" * 60)
    print("使用说明:")
    print("1. 确保已安装 chromedriver.exe 在当前目录")
    print("2. 输入虫虫钢琴网站的乐谱链接")
    print("3. 程序会自动下载五线谱和简谱版本的PDF")
    print("=" * 60)
    parser = argparse.ArgumentParser(description="虫虫钢琴乐谱下载器")
    parser.add_argument('-u', '--url', help='单个乐谱链接')
    parser.add_argument('-f', '--file', help='包含多个链接的文本文件')
    args = parser.parse_args()
    links = []
    if args.url:
        links.append(args.url)
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"[Error] 文件不存在: {args.file}")
            return
    else:
        print("请输入要处理的乐谱链接，每行一个，输入空行结束：")
        print("示例: https://www.gangqinpu.com/html/1002952.htm")
        while True:
            link = input("链接: ").strip()
            if not link:
                break
            links.append(link)
    if not links:
        print("[Error] 没有输入任何链接")
        return
    base_url = "https://www.gangqinpu.com"
    total = len(links)
    for i, link in enumerate(links, 1):
        print(f"\n处理第 {i}/{total} 个链接: {link}")
        src_value = get_html_and_extract(link)
        if src_value:
            full_url = base_url + src_value
            print("下载五线谱版本...")
            save_page_as_pdf(full_url, "五线谱")
            print("下载简谱版本...")
            simplified_url = full_url.replace('jianpuMode=0', 'jianpuMode=1')
            save_page_as_pdf(simplified_url, "简谱")
        else:
            print(f"[Error] 无法处理链接: {link}")
    print(f"\n[Done] 处理完成! 共处理了 {total} 个链接")


if __name__ == "__main__":
    main()
