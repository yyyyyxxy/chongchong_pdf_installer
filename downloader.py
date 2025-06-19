import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time
import base64
import argparse


def get_html_and_extract(link):
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
    edge_options = Options()
    edge_options.use_chromium = True
    edge_options.add_argument("--headless")  # 无头模式
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")

    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36")
    edge_options.add_argument("referer=")
    edge_options.add_argument("accept-language=en-US,en;q=0.9")

    # 检查驱动文件
    driver_path = "msedgedriver.exe"
    if not os.path.exists(driver_path):
        print(f"错误: 找不到Edge驱动文件 {driver_path}")
        print("请下载msedgedriver.exe并放在脚本同目录下")
        print("下载地址: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
        return

    service = Service(driver_path)
    driver = webdriver.Edge(service=service, options=edge_options)

    try:
        print(f"正在加载乐谱页面...")
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
            elements = driver.find_elements(By.XPATH, "//*[name()='text' and @text-anchor='middle']")
            if elements:
                title = elements[0].text.strip()
                folder_name = title if title else "Unknown"
                # 清理文件名中的非法字符
                folder_name = ''.join(c if c not in '/\\:*?"<>|' else '_' for c in folder_name)
                os.makedirs(folder_name, exist_ok=True)

                print_options = {
                    'paperWidth': 8.27,
                    'paperHeight': 11.69,
                    'marginTop': 0,
                    'marginBottom': 0,
                    'marginLeft': 0,
                    'marginRight': 0,
                    'printBackground': True,
                    'landscape': False
                }

                print(f"正在生成PDF: {output_pdf}")
                pdf_data = driver.execute_cdp_cmd("Page.printToPDF", print_options)
                output_pdf_path = os.path.join(folder_name, f"{title}-{output_pdf}.pdf")
                with open(output_pdf_path, 'wb') as f:
                    f.write(base64.b64decode(pdf_data['data']))
                print(f"✅ PDF保存成功: {output_pdf_path}")
                return
            else:
                print(f"❌ 第{attempt + 1}次尝试失败，正在重试...")

        print("❌ 无法加载乐谱内容，请检查链接是否正确")
    except Exception as e:
        print(f"处理过程中出错: {e}")
    finally:
        driver.quit()


def main():
    print("=" * 60)
    print("虫虫钢琴乐谱下载器")
    print("=" * 60)
    print("使用说明:")
    print("1. 确保已安装 msedgedriver.exe 在当前目录")
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
            print(f"❌ 文件不存在: {args.file}")
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
        print("❌ 没有输入任何链接")
        return

    base_url = "https://www.gangqinpu.com"
    total = len(links)
    
    for i, link in enumerate(links, 1):
        print(f"\n处理第 {i}/{total} 个链接: {link}")
        src_value = get_html_and_extract(link)
        if src_value:
            full_url = base_url + src_value

            # 五线谱模式
            print("下载五线谱版本...")
            save_page_as_pdf(full_url, "五线谱")

            # 简谱模式
            print("下载简谱版本...")
            simplified_url = full_url.replace('jianpuMode=0', 'jianpuMode=1')
            save_page_as_pdf(simplified_url, "简谱")
        else:
            print(f"❌ 无法处理链接: {link}")
    
    print(f"\n🎉 处理完成! 共处理了 {total} 个链接")


if __name__ == "__main__":
    main()
