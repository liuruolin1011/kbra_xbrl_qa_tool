# import xml.etree.ElementTree as ET
# import pandas as pd

# tree = ET.parse('filings/aapl_20240928_10-K.xml')
# root = tree.getroot()

# context_dict = {}
# for context in root.findall('{http://www.xbrl.org/2003/instance}context'):
#     cid = context.get('id')
#     period = context.find('{http://www.xbrl.org/2003/instance}period')
#     instant = period.find('{http://www.xbrl.org/2003/instance}instant')
#     if period is not None:
#         start = period.find('{http://www.xbrl.org/2003/instance}startDate')
#         end = period.find('{http://www.xbrl.org/2003/instance}endDate')
#         if start is not None and end is not None:
#             context_dict[cid] = (start.text, end.text)
#         elif instant is not None:
#             context_dict[cid] = (instant.text, instant.text) 

# records = []
# for elem in root:
#     if elem.tag.startswith('{http://fasb.org/us-gaap/'):
#         tag = elem.tag.split('}')[1]
#         value = elem.text
#         contextRef = elem.attrib.get('contextRef')
#         unitRef = elem.attrib.get('unitRef')
#         start_end = context_dict.get(contextRef, (None, None))
#         records.append({
#             'tag': tag,
#             'value': value,
#             'contextRef': contextRef,
#             'unitRef': unitRef,
#             'startDate': start_end[0],
#             'endDate': start_end[1]
#         })

# # 1. 从 records 构建 DataFrame
# df = pd.DataFrame(records)
# print(df.head())

# # 2. 读取映射表
# mapping = pd.read_excel('mapping/mapping.xlsx')

# # 3. 合并映射字段（left join）
# df_merged = df.merge(mapping, left_on='tag', right_on='XBRL_Tag', how='left')

# df_clean = df_merged.dropna(subset=['Normalized_Name'])

# # 5. 将 DataFrame 转换为 Excel 文件
# df_merged.to_excel('output/aapl_20240928_10-K.xlsx', index=False)

import pandas as pd
import numpy as np

raw_data = pd.DataFrame({
    'tag': ['us-gaap:Assets', 'us-gaap:Liabilities', 'us-gaap:StockholdersEquity', 'us-gaap:Assets', 'us-gaap:Liabilities', 'us-gaap:StockholdersEquity'],
    'value': [11000000, 700000, 300000, 2000000, 1200000, 800000],
    'contextRef': ["c1", "c1", "c1", "c2", "c2", "c2"],
    'unitRef': ['USD', 'USD', 'USD', 'USD', 'USD', 'USD'],
    'startDate': ['2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01'],
    'endDate': ['2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31']
})

mapping_table = pd.DataFrame({
    "tag": [
        "us-gaap:Assets", 
        "us-gaap:Liabilities", 
        "us-gaap:StockholdersEquity"
    ],
    "normalized_name": [
        "Total Assets", 
        "Total Liabilities", 
        "Equity"
    ]
})

merged_df = raw_data.merge(mapping_table, left_on='tag', right_on='tag', how='left')
merged_df = merged_df.dropna(subset=['normalized_name'])

pivot = merged_df.pivot_table(
    index="contextRef",
    columns="normalized_name",
    values="value",
    aggfunc="first"
).reset_index()

pivot["QA_Result"] = np.isclose(
    pivot["Total Assets"],
    pivot["Total Liabilities"] + pivot["Equity"],
    atol=1e-5
)

print("❌ QA failed rows:")
print(pivot[~pivot["QA_Result"]])