# xbrl_parser.py
import pandas as pd
import xml.etree.ElementTree as ET
import yaml
import os
from datetime import datetime
import logging

def parse_xbrl(xml_path):
    
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ns_uri = root.tag.split("}")[0].strip("{")
    ns = {"us-gaap": ns_uri}

    records = []
    for elem in root.iter():
        tag_full = elem.tag.split("}")[1] if "}" in elem.tag else elem.tag
        xbrl_tag = f"us-gaap:{tag_full}"
        value = elem.text
        contextRef = elem.attrib.get("contextRef", "")
        unitRef = elem.attrib.get("unitRef", "")
        records.append({
            "XBRL_Tag": xbrl_tag,
            "Value": value,
            "contextRef": contextRef,
            "unitRef": unitRef
        })

    raw_df = pd.DataFrame(records)
    
    return raw_df

def extract_context_periods(xml_path):
    
    tree = ET.parse(xml_path)
    root = tree.getroot()

    context_info = []
    for elem in root.findall(".//{*}context"):
        context_id = elem.attrib.get("id", "")
        period = elem.find("{*}period")
        if period is not None:
            if period.find("{*}instant") is not None:
                instant = period.find("{*}instant").text
                context_info.append({
                    "contextRef": context_id,
                    "Period_Type": "instant",
                    "Period": instant
                })
            elif period.find("{*}startDate") is not None and period.find("{*}endDate") is not None:
                start = period.find("{*}startDate").text
                end = period.find("{*}endDate").text
                context_info.append({
                    "contextRef": context_id,
                    "Period_Type": "duration",
                    "Period": f"{start} to {end}"
                })

    return pd.DataFrame(context_info)

def load_mapping_from_yaml(ticker=None, cik=None, mapping_dir="mapping"):
    """
    加载映射表 YAML，优先使用 ticker 命名文件，其次尝试 CIK。
    如果都失败，可选加载 default.yaml。
    """
    yaml_path = None

    if ticker:
        yaml_path = os.path.join(mapping_dir, f"{ticker.lower()}.yaml")
        if not os.path.exists(yaml_path):
            logging.warning(f"Mapping file for ticker '{ticker}' not found at {yaml_path}")
            yaml_path = None

    if not yaml_path and cik:
        yaml_path = os.path.join(mapping_dir, f"{cik}.yaml")
        if not os.path.exists(yaml_path):
            logging.warning(f"Mapping file for CIK '{cik}' not found at {yaml_path}")
            yaml_path = None

    if not yaml_path:
        # 可选 fallback（默认文件）
        default_path = os.path.join(mapping_dir, "default.yaml")
        if os.path.exists(default_path):
            logging.info("Fallback to default.yaml mapping")
            yaml_path = default_path
        else:
            raise FileNotFoundError("No valid mapping file found for ticker/CIK and no default.yaml provided.")

    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)

def extract_normalized_fields_from_dict(xbrl_df, field_mapping, context_df):
    results = []
    for norm_field, cfg in field_mapping.items():
        tags = cfg.get("tags", [])
        context_type = cfg.get("context", "").strip().lower()

        if context_type in ["instant", "duration"]:
            context_refs = context_df[context_df["Period_Type"] == context_type]["contextRef"].tolist()
        else:
            context_refs = context_df["contextRef"].tolist()

        value_found = None
        context_used = None

        for tag in tags:
            sub_df = xbrl_df[(xbrl_df["XBRL_Tag"] == tag) & (xbrl_df["contextRef"].isin(context_refs))].copy()
            sub_df["Value"] = pd.to_numeric(sub_df["Value"], errors="coerce")
            sub_df = sub_df.dropna(subset=["Value"])
            if not sub_df.empty:
                value_found = sub_df.iloc[0]["Value"]
                context_used = sub_df.iloc[0]["contextRef"]
                break

        results.append({
            "Normalized_Name": norm_field,
            "Value": value_found,
            "Context_Used": context_used
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    # Example usage
    xbrl_path = "filings/gs_20241231_10-K.xml"
    cik = "0000886982"
    xbrl_df = parse_xbrl(xbrl_path)
    context_df = extract_context_periods(xbrl_path)
    mapping = load_mapping_from_yaml(cik=cik)
    field_mapping = mapping["fields"]

    normalized_df = extract_normalized_fields_from_dict(xbrl_df, field_mapping, context_df)
    
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/{cik}_{date_str}.xlsx"
    
    with pd.ExcelWriter(output_path) as writer:
        xbrl_df.to_excel(writer, sheet_name="XBRL Data", index=False)
        context_df.to_excel(writer, sheet_name="Context Periods", index=False)
        pd.DataFrame.from_dict(field_mapping, orient="index").to_excel(writer, sheet_name="Field Mapping")
        normalized_df.to_excel(writer, sheet_name="Normalized Fields", index=False)
        
        print(f"✅ Output written to {output_path}")