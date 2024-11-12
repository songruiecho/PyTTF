import os
import traceback

from fontTools.ttLib import TTFont, newTable
import fontTools.ttx
import fontTools.fontBuilder
import pandas as pd
from tqdm import tqdm
import xml.etree.ElementTree as ET
import array
from tqdm import tqdm
from xml.dom import minidom

ttf_name_maping = {
    'CHANT': 'chant',
    '金文宋體': 'ZKing(1)',
    '中间字库宋体0C平面': 'MidPlane0C_20190122_1024.xml'
}

def font_resize():
    ''' 将集大字库2中的字体进行resize
    :return:
    '''
    # 首先对全部的字形进行平移，尽量保证所有字形不存在y<0的情况
    tree = ET.parse('xml/集大字库2.xml')
    root = tree.getroot()

    # 遍历所有的TTGlyph标签
    for ttglyph in tqdm(root.findall('.//TTGlyph')):
        pt_nodes = ttglyph.findall('.//pt')
        if len(pt_nodes) != 0:
            y_values = []
            yMax = int(ttglyph.get('yMax'))
            for pt in pt_nodes:
                y_value = pt.get('y')  # 假设 y 值是作为属性存储
                if y_value is not None:
                    y_values.append(int(y_value))
            if yMax - min(y_values) < 1024:
                move_ = 0 - min(y_values)
            else:
                move_ = 1024 - yMax
            # 移动pt_nodes中的所有y值
            for pt in pt_nodes:
                y = int(pt.get('y')) + move_  # 向上移动
                pt.set('y', str(int(y * 0.92)))  # 成比例缩放
            # 修改yMax、yMin值
            ttglyph.set('yMin', str(int(min(y_values) * 0.92 + move_ * 0.92)))  # 注意这里要减去move_up来反映新的最小值
            ttglyph.set('yMax', str(int((max(y_values) * 0.92 + move_ * 0.92))))  # 注意这里也要减去move_up来反映新的最大值

    # 遍历所有的TTGlyph标签，对于Max<500的数据进行向1000缩放
    for ttglyph in tqdm(root.findall('.//TTGlyph')):
        pt_nodes = ttglyph.findall('.//pt')
        if len(pt_nodes) != 0:
            yMax = int(ttglyph.get('yMax'))
            xMax = int(ttglyph.get('xMax'))
            if xMax < 500 and yMax < 500:
                xScale, yScale = 950 / xMax, 950 / yMax
                x_values, y_values = [], []
                for pt in pt_nodes:
                    x = int(float(pt.get('x'))*xScale)  # 等比缩放
                    x_values.append(x)
                    pt.set('x', str(x))
                    y = int(float(pt.get('y'))*xScale)  # 等比缩放
                    y_values.append(y)
                    pt.set('y', str(y))
                # 修改yMax、yMin值
                ttglyph.set('xMin', str(min(x_values)))
                ttglyph.set('xMax', str(max(x_values)))
                ttglyph.set('yMin', str(min(y_values)))
                ttglyph.set('yMax', str(max(y_values)))

    font = TTFont()
    tree.write('new_xml/集大字库2.1.xml')
    font.importXML('new_xml/集大字库2.1.xml')
    font.save('new_ttf/集大字库2.1.ttf')

# font_resize()


# 根据name属性获取对应的value
def get_mtc_value_by_name(name, mtc_elements):
    for mtc in mtc_elements:
        if mtc.get('name') == name:
            return mtc
    return None

def prettify(elem):
    """将 XML 元素转换为字符串，并进行格式化"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def add_char_to_font():
    # 尝试向集大字库中添加新字体
    tree = ET.parse('new_xml/集大字库2.1.xml')
    root = tree.getroot()
    # 首先获取所有数据的coding，以便我们能够分配给样本编码，glyph6971，coding需要另行计算
    names, ids = [], []  # 一一对应
    GlyphIDs = root.findall('.//GlyphOrder/GlyphID')
    GlyphOrder = root.find('.//GlyphOrder')
    cmap = root.find('.//cmap/cmap_format_12/')
    hmtx = root.find('.//hmtx')
    glyf = root.find('.//glyf')
    extraNames = root.find('.//post/extraNames')

    for each in GlyphIDs:
        names.append(each.get('name'))
        ids.append(each.get('id'))
    codings = [-1]*len(names)
    Maps = root.findall('.//cmap/cmap_format_12/map')
    for each in Maps:
        name = each.get('name')
        code = each.get('code')
        idx = names.index(name)   # 注意coding并不是按顺序的
        codings[idx] = code
    max_code, max_name = codings[-1], names[-1]
    mapping_frame = pd.read_excel('mapping/20240919字形对照v2备注.xlsx')
    filtered_df = mapping_frame[mapping_frame['集大字库2字形'] == '未找到']
    filtered_df_groups = filtered_df.groupby('fontName_x')

    for group in filtered_df_groups:
        if group[0] == '中间字库宋体0C平面':   # 以中间字库宋体0C平面为例
            ori_codes = list(group[1]['16进制原字体文件中编码'].values)
            group_tree = ET.parse('xml/{}'.format(ttf_name_maping[group[0]]))
            group_root = group_tree.getroot()
            count = 0
            for ori_code in tqdm(ori_codes):
                ori_code = 'u'+ori_code
                # # 首先根据code找到GlyphID的id
                # glyph_id = group_root.find(f".//GlyphID[@name='{ori_code}']")
                # print(glyph_id)
                # 找到code对应的mtc tag
                mtc_elements = group_root.findall('.//hmtx/mtx')
                mtc_element = get_mtc_value_by_name(ori_code, mtc_elements)
                if mtc_element is not None:
                    int_number = int(max_code, 16)
                    # code + 1
                    int_number += count
                    new_code = hex(int_number)
                    # 对应的name也需要＋1
                    new_name = 'glyph' + str(len(names) + count)

                    # 接下来查找 cmap/cmap_format_12/map
                    map_elements = group_root.findall('.//cmap/cmap_format_12/map')
                    map_element = get_mtc_value_by_name(ori_code, map_elements)
                    # 接下来查找glyf/TTGlyph，这个是关键，代表了字形
                    glyph_elements = group_root.findall('.//glyf/TTGlyph')
                    glyph_element = get_mtc_value_by_name(ori_code, glyph_elements)
                    # 将找到的字形加入到集大字库中，需要添加的内容为：GlyphID、hmtx、cmap cmap_format_12、以及glyf中的TTGlyph
                    # 【注意所有】name\code出现的部分都需要进行修改，改成new_code\new_name
                    # print(glyph_element, map_element, mtc_element.attrib['name'])
                    for tag in [glyph_element, map_element, mtc_element]:
                        if 'name' in tag.attrib:
                            tag.attrib['name'] = new_name
                            # 修改code属性（如果存在）
                        if 'code' in tag.attrib:
                            tag.attrib['code'] = new_code
                    # 再新建符合集大字库的 GlyphOrder/GlyphID
                    new_glyph_id = ET.Element('GlyphID')
                    new_glyph_id.set('id', str(len(names) + count))
                    new_glyph_id.set('name', new_name)
                    # 再新加入pdNames
                    new_psName = ET.Element('psName')
                    new_psName.set('name', new_name)
                    # 添加元素
                    GlyphOrder.append(new_glyph_id)
                    extraNames.append(new_psName)
                    hmtx.append(mtc_element)
                    cmap.append(map_element)
                    glyf.append(glyph_element)
                    # 加入成功后count更新
                    count += 1
    with open('new_xml/集大字库2.2.xml', 'w', encoding='utf-8') as f:
        f.write(prettify(root))

# add_char_to_font()

# font = TTFont()
# font.importXML('new_xml/集大字库2.2.xml')
# font.save('new_ttf/集大字库2.2.ttf')