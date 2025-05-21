import os
import logging
import pandas as pd
from datetime import datetime
from modules.xbrl_parser import (
    parse_xbrl,
    extract_context_periods,
    extract_normalized_fields_from_dict,
    load_mapping_from_yaml  # ✅ 修改为按 ticker 加载
)
from modules.qa_utils import run_all_qa_checks

# 日志配置
logging.basicConfig(
    filename='xbrl_batch.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_single_file(ticker, xml_path, output_dir="output"):
    logging.info(f"Start processing file: {xml_path} for ticker: {ticker}")
    print(f"📄 Processing {xml_path} ...")

    try:
        # 加载基于 ticker 命名的 YAML
        mapping = load_mapping_from_yaml(ticker=ticker)
        field_mapping = mapping["fields"]

        # Parse and normalize
        xbrl_df = parse_xbrl(xml_path)
        context_df = extract_context_periods(xml_path)
        normalized_df = extract_normalized_fields_from_dict(xbrl_df, field_mapping, context_df)
        filename = os.path.basename(xml_path)
        parts = filename.replace(".xml", "").split("_")
        fiscal_year = parts[1][:4]  # 取 "20221231" 的前4位
        form_type = parts[2] if len(parts) > 2 else "10-K"  # 容错
        
        # Run QA
        value_dict = dict(zip(normalized_df["Normalized_Name"], normalized_df["Value"]))
        qa_results = run_all_qa_checks(value_dict, pd.DataFrame({
            "QA Group": [field_mapping[f].get("qa_group", "") for f in field_mapping]
        }))

        # Output
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"output_{ticker}_{fiscal_year}_{form_type}_{date_str}.xlsx")
        
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            xbrl_df.to_excel(writer, sheet_name="Raw_XBRL", index=False)
            context_df.to_excel(writer, sheet_name="Context_Info", index=False)
            pd.DataFrame.from_dict(field_mapping, orient="index").to_excel(writer, sheet_name="Field Mapping")
            normalized_df.to_excel(writer, sheet_name="Normalized_Values", index=False)
            pd.DataFrame(list(qa_results.items()), columns=["QA Check", "Pass?"]).to_excel(writer, sheet_name="QA_Summary", index=False)

        logging.info(f"✅ Successfully processed {xml_path}, output saved to {output_path}")
        print(f"✅ Output saved to {output_path}\n")
        return output_path

    except Exception as e:
        logging.error(f"❌ Failed to process {xml_path}: {e}")
        print(f"❌ Error processing {xml_path}: {e}")
        return None

def batch_process(folder_path):
    for file in os.listdir(folder_path):
        if file.endswith(".xml"):
            xml_path = os.path.join(folder_path, file)

            # 提取 ticker（文件名第一个下划线前）
            ticker = file.split("_")[0].lower()
            process_single_file(ticker, xml_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch XBRL Processor using ticker-based YAML mapping")
    parser.add_argument("--folder", required=True, help="Folder containing multiple XBRL XML files")
    args = parser.parse_args()

    batch_process(args.folder)