import base64
from xml.etree import ElementTree as ET


def extract_glyphs_from_base64_svg(svg_path):
    # 解析 SVG 文件
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # 定义命名空间
    namespaces = {'svg': 'http://www.w3.org/2000/svg', 'xlink': 'http://www.w3.org/1999/xlink'}

    # 查找 <image> 标签
    for image in root.findall('.//svg:image', namespaces):
        xlink_href = image.attrib.get('{http://www.w3.org/1999/xlink}href')
        if xlink_href and xlink_href.startswith('data:'):
            # 提取 Base64 数据
            data = xlink_href.split(',')[1]  # 获取 ',' 后面的部分
            try:
                # 解码 Base64 数据
                decoded_data = base64.b64decode(data)
                print(decoded_data)
                exit(111)
                # 检查数据头以确认格式
                # 解析解码后的 SVG
                decoded_tree = ET.ElementTree(ET.fromstring(decoded_data))
                # 提取路径（<path>）数据
                paths = decoded_tree.findall('.//svg:path', namespaces)
                glyph_outlines = []
                for path in paths:
                    d = path.attrib.get('d')
                    glyph_outlines.append(d)

                return glyph_outlines

            except Exception as e:
                print(f"Error decoding Base64 data: {e}")


import cv2
import numpy as np
from PIL import Image


def extract_glyphs_from_png(png_path):
    # 读取图像
    img = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)

    # 转为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 二值化图像
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # 提取轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 保存轮廓路径
    glyph_outlines = []
    for contour in contours:
        # 转换为路径字符串
        path = 'M ' + ' '.join(f"{point[0][0]} {point[0][1]}" for point in contour)
        glyph_outlines.append(path)

    return glyph_outlines


# 使用示例
glyphs = extract_glyphs_from_png('svg/jin_19418_1.jpg')
for glyph in glyphs:
    print(glyph)