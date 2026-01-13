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
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'}
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', id='ai-score')
        if iframe and 'src' in iframe.attrs:
            return urljoin(link, iframe['src']) # 自动处理相对/绝对路径
        return None
    except Exception as e:
        print(f"❌ 网页解析失败: {e}")
        return None

def init_driver():
    edge_options = Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging']) # 减少控制台杂讯

    # 自动寻找驱动
    paths = [EDGE_DRIVER_NAME, os.path.join("drivers", EDGE_DRIVER_NAME), os.path.join(os.path.dirname(__file__), EDGE_DRIVER_NAME)]
    driver_path = next((p for p in paths if os.path.exists(p)), EDGE_DRIVER_NAME)
    
    service = Service(driver_path)
    return webdriver.Edge(service=service, options=edge_options)

def save_score_as_pdf(driver, url, suffix):
    try:
        driver.get(url)
        # 等待乐谱的核心元素加载 (使用显式等待)
        wait = WebDriverWait(driver, 15)
        # 假设标题元素出现代表页面加载完成
        target_xpath = "//*[name()='text' and @text-anchor='middle']"
        elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, target_xpath)))
        
        title = elements[0].text.strip()
        clean_title = ''.join(c if c not in '/\\:*?"<>|' else '_' for c in title)
        
        # 注入CSS隐藏打印时的干扰项并调整页边距
        script = """
        var style = document.createElement('style');
        style.innerHTML = '@page { margin: 0; } .print { display: none !important; }';
        document.head.appendChild(style);
        """
        driver.execute_script(script)

        print_options = {
            'paperWidth': 8.27,
            'paperHeight': 11.69,
            'marginTop': 0, 'marginBottom': 0, 'marginLeft': 0, 'marginRight': 0,
            'printBackground': True
        }

        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        filename = f"{clean_title}_{suffix}.pdf"
        output_path = os.path.abspath(filename)

        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(pdf_data['data']))
        print(f"✅ 保存成功: {filename}")
        
    except Exception as e:
        print(f"❌ 打印失败 ({suffix}): {e}")

def main():
    # ... (前面的 argparse 部分保持不变) ...
    
    # 获取链接后
    if not links: return

    driver = init_driver()
    try:
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}] 正在处理: {link}")
            iframe_url = get_html_and_extract(link)
            
            if iframe_url:
                # 五线谱
                save_score_as_pdf(driver, iframe_url, "五线谱")
                # 简谱 (切换模式)
                jianpu_url = iframe_url.replace('jianpuMode=0', 'jianpuMode=1')
                save_score_as_pdf(driver, jianpu_url, "简谱")
            else:
                print("❌ 未能找到乐谱资源")
    finally:
        driver.quit()
        print("\n🎉 所有任务处理完毕")

if __name__ == "__main__":
    main()
