#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
假成功检测器 (Masked Success Detector)

扫描结构化日志（JSONL），识别被 execution_engine 硬编码掩盖的错误记录：
- result 以 "成功执行:" 开头但无明显实质内容
- 或者 actual_output / result 为空字符串、null、none

用法:
    python scripts/detect_masked_errors.py --log-dir tests/e2e/logs/beijing_travel_replan
    python scripts/detect_masked_errors.py --log-dir tests/e2e/logs/ --days 7
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def is_masked_success(record: dict) -> bool:
    """判断一条记录是否为被掩盖的假成功"""
    result = record.get("result") or ""
    actual = record.get("actual_output") or ""
    error = record.get("error") or ""
    
    # 特征 1：硬编码前缀且无实质内容
    if isinstance(result, str) and result.startswith("成功执行:"):
        content_after = result.replace("成功执行:", "").strip()
        if not content_after or content_after == record.get("step_name", ""):
            return True
    
    # 特征 2：result 为空/None 但 success 被标记为 True
    if record.get("success") is True:
        if result.lower() in ["", "none", "null"]:
            return True
        if actual.lower() in ["", "none", "null"]:
            return True
    
    # 特征 3：error 字段有值但 success 仍为 True（旧版掩盖逻辑产物）
    if record.get("success") is True and error:
        return True
    
    return False


def scan_jsonl_file(path: Path) -> list:
    """扫描单个 JSONL 文件"""
    findings = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            payload = record.get("payload") or {}
            # 尝试从 event 结构中提取执行结果信息
            candidates = []
            if isinstance(payload, dict):
                candidates.append(payload)
                if "payload" in payload:
                    candidates.append(payload["payload"])
            
            for cand in candidates:
                if not isinstance(cand, dict):
                    continue
                # 我们只关心真正带有 result 或 success 字段的执行结果事件
                has_execution_data = (
                    cand.get("result") is not None or
                    cand.get("success") is not None or
                    cand.get("actual_output") is not None or
                    cand.get("error") is not None
                )
                if not has_execution_data:
                    continue
                
                test_record = {
                    "step_id": cand.get("step_id"),
                    "step_name": cand.get("name"),
                    "result": cand.get("result"),
                    "actual_output": cand.get("actual_output"),
                    "error": cand.get("error"),
                    "success": cand.get("success", True),
                }
                if is_masked_success(test_record):
                    findings.append({
                        "file": str(path),
                        "line": line_no,
                        "ts": record.get("ts"),
                        "masked_record": test_record,
                        "raw": record,
                    })
    return findings


def scan_text_log(path: Path) -> list:
    """扫描纯文本日志，查找硬编码成功前缀"""
    findings = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if "成功执行:" in line and "[EXEC] Step completed" not in line:
                findings.append({
                    "file": str(path),
                    "line": line_no,
                    "snippet": line.strip(),
                })
    return findings


def main():
    parser = argparse.ArgumentParser(description="假成功检测器")
    parser.add_argument("--log-dir", default="tests/e2e/logs", help="日志根目录")
    parser.add_argument("--days", type=int, default=7, help="扫描最近 N 天的日志")
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    cutoff = datetime.now() - timedelta(days=args.days)
    all_findings = []
    
    for root, _, files in os.walk(log_dir):
        for fname in files:
            fpath = Path(root) / fname
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            if mtime < cutoff:
                continue
            
            if fname.endswith(".jsonl"):
                all_findings.extend(scan_jsonl_file(fpath))
            elif fname.endswith(".log"):
                all_findings.extend(scan_text_log(fpath))
    
    print(f"\n[Masked Success Detector] 扫描完成：共发现 {len(all_findings)} 条可疑记录\n")
    if all_findings:
        for f in all_findings[:50]:
            print(json.dumps(f, ensure_ascii=False, indent=2))
        if len(all_findings) > 50:
            print(f"\n... 还有 {len(all_findings) - 50} 条记录未显示")
        sys.exit(1)
    else:
        print("未发现被掩盖的错误记录，系统健康。")
        sys.exit(0)


if __name__ == "__main__":
    main()
