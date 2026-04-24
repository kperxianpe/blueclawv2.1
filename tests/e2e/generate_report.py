#!/usr/bin/env python3
"""
Generate HTML report from screenshot test results.
"""
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
REPORT_DIR = PROJECT_ROOT / "tests" / "e2e" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def find_screenshots(module_name: str, case_id: str) -> list:
    """Find latest screenshots for a test case, deduplicated by checkpoint name."""
    module_dir = SCREENSHOT_DIR / module_name
    if not module_dir.exists():
        return []
    
    pattern = f"{case_id}_*.png"
    files = list(module_dir.glob(pattern))
    # Sort by mtime descending (newest first)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Deduplicate by checkpoint name, keeping only the newest for each
    seen = set()
    result = []
    for f in files:
        # Parse checkpoint name: CASE-001_checkpoint_name_123456.png
        parts = f.stem.split('_')
        if len(parts) >= 3:
            # checkpoint name is everything between case_id and timestamp
            checkpoint = '_'.join(parts[1:-1])
            if checkpoint not in seen:
                seen.add(checkpoint)
                result.append(f)
    
    # Return in chronological order (oldest first) for narrative flow
    result.reverse()
    return result


def generate_report():
    """Generate HTML report from all screenshots."""
    
    # Test case definitions
    modules = [
        ("Module 1: Thinking Blueprint", [
            ("TB-001", "基础意图理解 - 公众号选题", "PASS", "基础思考流程验证通过"),
            ("TB-002", "复杂意图拆解 - 旅行规划", "GAP", "约束标签/并行分支/AI推断未实现"),
            ("TB-003", "回溯与重新思考", "GAP", "重新思考按钮/历史存档/路径对比未实现"),
        ]),
        ("Module 2: Execution Blueprint", [
            ("EB-001", "基础执行流程 - 信息检索", "PASS", "执行节点状态动画验证通过"),
            ("EB-002", "并行执行 - 多渠道采集", "GAP", "独立进度条/分支分组/等待状态未实现"),
            ("EB-003", "失败与自愈 - 网页抓取", "GAP", "自愈触发/橙色状态/自愈日志未实现"),
        ]),
        ("Module 3: Adapter Visualization", [
            ("AD-001", "Web Adapter - 自动搜索", "GAP", "Web浏览器/视图切换/操作动画未实现"),
            ("AD-002", "IDE Adapter - 代码生成", "GAP", "IDE标签/文件树编辑器终端/打字机效果未实现"),
            ("AD-003", "混合执行 - API+Web", "GAP", "多视图切换/过渡动画/数据传递未实现"),
        ]),
        ("Module 4: Freeze Annotation", [
            ("FR-001", "主动冻结 - Web标注", "GAP", "冻结按钮/遮罩/框选/标注输入未实现"),
            ("FR-002", "自动冻结 - 元素未找到", "GAP", "自动触发/错误提示/截图/元素库更新未实现"),
            ("FR-003", "IDE冻结 - 代码位置", "GAP", "IDE视图/代码截图/行号映射/回滚未实现"),
        ]),
        ("Module 5: Intervention", [
            ("IV-001", "重新执行 - 步骤重试", "GAP", "Retry按钮/重试计数/确认弹窗/自动重试未实现"),
            ("IV-002", "重新规划 - 策略调整", "GAP", "真实重新思考/蓝图对比/废弃存档未实现"),
            ("IV-003", "组合干预 - 冻结+重规划", "GAP", "组合流程/数据流/标注传递未实现"),
        ]),
        ("Module 6: Loop Protection", [
            ("LP-001", "正常循环 - 翻页抓取", "GAP", "循环计数器/页码标签/完成状态未实现"),
            ("LP-002", "循环超限 - 无限滚动", "GAP", "max_iterations/颜色警告/自动暂停/干预选项未实现"),
            ("LP-003", "循环异常 - 轮询超时", "GAP", "轮询间隔/超时暂停/诊断信息未实现"),
        ]),
        ("Batch 2: Advanced Scenarios (LLM-driven)", [
            ("Q7", "智能旅行行程优化 - 多轮干预", "PASS", "Real LLM thinking + execution flow verified"),
            ("Q8", "PDF批量处理 - 并行步骤", "GAP", "Parallel step visual grouping not implemented"),
            ("Q9", "多语言翻译+排版 - 多阶段", "GAP", "Stage boundary checkpoint UI not implemented"),
            ("Q10", "数据可视化报表 - 自适应干预", "GAP", "Local intervention (per-chart) not implemented"),
            ("Q11", "自动化测试脚本 - 工具分层", "GAP", "Tool binding visual indicators not fully implemented"),
            ("Q12", "智能邮件处理 - 边界条件", "GAP", "High-risk email forced checkpoint not implemented"),
            ("Q13", "Chrome插件开发 - 长流程恢复", "GAP", "Long flow state recovery not implemented"),
            ("Q14", "跨平台内容发布 - Adapter验证", "GAP", "Adapter visual distinction not implemented"),
        ]),
    ]
    
    total = sum(len(cases) for _, cases in modules)
    passed = sum(1 for _, cases in modules for _, _, s, _ in cases if s == "PASS")
    gaps = sum(1 for _, cases in modules for _, _, s, _ in cases if s == "GAP")
    
    # Count actual screenshots
    screenshot_count = sum(1 for f in SCREENSHOT_DIR.rglob("*.png") if f.name.startswith(("TB-", "EB-", "AD-", "FR-", "IV-", "LP-", "Q")))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Blueclaw v2.5 E2E Test Report</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f0f2f5; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 40px; }}
.header h1 {{ margin: 0 0 10px 0; font-size: 28px; }}
.header p {{ margin: 0; opacity: 0.8; }}
.stats {{ display: flex; gap: 15px; margin-top: 25px; flex-wrap: wrap; }}
.stat {{ padding: 12px 24px; border-radius: 10px; font-weight: 600; font-size: 14px; }}
.stat.pass {{ background: #28a745; color: white; }}
.stat.gap {{ background: #ffc107; color: #333; }}
.stat.total {{ background: rgba(255,255,255,0.15); color: white; }}
.content {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
.module {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.module h2 {{ margin: 0 0 20px 0; color: #1a1a2e; font-size: 20px; display: flex; align-items: center; gap: 10px; }}
.case {{ border-left: 4px solid #ddd; padding: 15px 20px; margin: 12px 0; background: #fafbfc; border-radius: 0 8px 8px 0; }}
.case.pass {{ border-left-color: #28a745; }}
.case.gap {{ border-left-color: #ffc107; }}
.case h3 {{ margin: 0 0 8px 0; font-size: 16px; display: flex; align-items: center; gap: 10px; }}
.case p {{ margin: 0; color: #666; font-size: 14px; }}
.badge {{ padding: 3px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.badge-pass {{ background: #d4edda; color: #155724; }}
.badge-gap {{ background: #fff3cd; color: #856404; }}
.gap-reason {{ background: #fff8e1; border: 1px solid #ffe082; padding: 12px 15px; border-radius: 8px; margin-top: 10px; font-size: 13px; color: #5d4037; }}
.gap-reason strong {{ color: #e65100; }}
.screenshots {{ display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }}
.screenshots img {{ max-width: 240px; max-height: 150px; border-radius: 6px; border: 1px solid #e0e0e0; cursor: pointer; transition: transform 0.2s; }}
.screenshots img:hover {{ transform: scale(1.05); }}
.summary {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.summary h2 {{ margin: 0 0 15px 0; }}
.summary-table {{ width: 100%; border-collapse: collapse; }}
.summary-table th, .summary-table td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
.summary-table th {{ background: #f8f9fa; font-weight: 600; color: #555; }}
.footer {{ text-align: center; padding: 30px; color: #999; font-size: 13px; }}
</style>
</head>
<body>
<div class="header">
<h1>Blueclaw v2.5 E2E Test Report</h1>
<p>Run at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Total Screenshots: {screenshot_count}</p>
<div class="stats">
<div class="stat pass">PASS: {passed}</div>
<div class="stat gap">GAP: {gaps}</div>
<div class="stat total">TOTAL: {total}</div>
<div class="stat total">Coverage: {passed}/{total} ({passed*100//total}%)</div>
</div>
</div>
<div class="content">
"""
    
    # Add summary table
    html += """
<div class="summary">
<h2>Summary by Module</h2>
<table class="summary-table">
<tr><th>Module</th><th>Tests</th><th>Pass</th><th>Gap</th><th>Status</th></tr>
"""
    for module_name, cases in modules:
        mod_pass = sum(1 for _, _, s, _ in cases if s == "PASS")
        mod_gap = sum(1 for _, _, s, _ in cases if s == "GAP")
        status = "PASS" if mod_gap == 0 else "PARTIAL" if mod_pass > 0 else "NOT STARTED"
        status_color = "#28a745" if status == "PASS" else "#ffc107" if status == "PARTIAL" else "#dc3545"
        html += f"<tr><td>{module_name}</td><td>{len(cases)}</td><td>{mod_pass}</td><td>{mod_gap}</td><td style='color:{status_color};font-weight:600'>{status}</td></tr>"
    
    html += "</table></div>"
    
    # Add detailed modules
    for module_name, cases in modules:
        html += f'<div class="module"><h2>{module_name}</h2>'
        for case_id, title, status, reason in cases:
            status_class = status.lower()
            badge = f'<span class="badge badge-{status_class}">{status}</span>'
            gap_html = f'<div class="gap-reason"><strong>Gap Analysis:</strong> {reason}</div>' if status == "GAP" else ""
            
            # Find screenshots
            mod_dir_part = module_name.split(":")[0].replace(" ", "").lower()
            if mod_dir_part.startswith("batch"):
                mod_dir = "batch2"
            else:
                mod_dir = mod_dir_part
            screenshots = find_screenshots(mod_dir, case_id)
            img_html = ""
            if screenshots:
                img_html = '<div class="screenshots">'
                for img in screenshots[:6]:  # Limit to 6 screenshots
                    rel_path = img.relative_to(PROJECT_ROOT).as_posix()
                    img_html += f'<img src="../../{rel_path}" title="{img.name}" loading="lazy">'
                img_html += '</div>'
            
            html += f"""
<div class="case {status_class}">
<h3>{case_id}: {title} {badge}</h3>
{gap_html}
{img_html}
</div>"""
        html += "</div>"
    
    html += f"""
<div class="footer">
Blueclaw v2.5 E2E Test Suite | Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
</div>
</div>
</body>
</html>"""
    
    report_path = REPORT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"[Report] Generated: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_report()
