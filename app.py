# app.py
#
# 前端改造版：马卡龙轻奢视觉 + 卡片化输出 + 交互反馈
# 只改界面层，src/ 后端与生成逻辑未动

import os
import sys
import json
import html as html_lib
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
from src.generator import ContentGenerator
from src.config import PLATFORMS


# 全局实例
generator = ContentGenerator()

# 历史记录（内存存储）
history_records = []

# 平台名称映射
PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "ecommerce": "电商",
    "wechat": "公众号"
}

# 平台展示元信息（马卡龙配色）
PLATFORM_META = {
    "douyin":      {"name": "抖音",   "bg": "#E4EEF7", "fg": "#5E86B3", "border": "#D3E2F0"},
    "xiaohongshu": {"name": "小红书", "bg": "#F7E4E8", "fg": "#C4707F", "border": "#F2DDE3"},
    "ecommerce":   {"name": "电商",   "bg": "#F8EFE0", "fg": "#A98E6A", "border": "#EFE2CC"},
    "wechat":      {"name": "公众号", "bg": "#E6F0E7", "fg": "#6E9C78", "border": "#DCEADF"},
}

# 调性选项
TONE_OPTIONS = [
    "自动匹配",
    "科技感极简风",
    "治愈系温暖风",
    "高端商务风",
    "活力潮流风",
    "亲民平价风"
]

# HTML 转义（防注入 / 防样式破坏）
def esc(s):
    return html_lib.escape(str(s), quote=True)


# ============ 前端渲染函数 ============

def brand_bar_html():
    return f"""
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;background:#FFFFFF;border:1px solid #F0E6EA;border-radius:14px;padding:12px 18px;box-shadow:0 6px 20px rgba(196,141,152,0.07);">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#E3B5BA,#C68D98);"></div>
    <div style="font-weight:700;font-size:16px;letter-spacing:0.5px;color:#4B4453;">AI Marketing Copilot</div>
    <div style="color:#9C8F9E;font-size:11px;border-left:1px solid #F0E6EA;padding-left:10px;">跨平台智能营销内容工作台</div>
  </div>
  <div style="color:#B77F8B;font-size:11px;">为品牌方一键生成 · 抖音 / 小红书 / 电商 / 公众号</div>
</div>
"""


def section_title(num, text):
    return f"""
<div style="font-size:13px;font-weight:600;color:#C68D98;margin:0 0 12px;display:flex;align-items:center;gap:6px;">
  <span style="width:18px;height:18px;border-radius:50%;background:#F4E3E6;color:#C68D98;font-size:11px;display:flex;align-items:center;justify-content:center;font-weight:700;">{num}</span>
  {esc(text)}
</div>
"""


def status_html(text, kind="info"):
    """状态徽章：kind in info / progress / success / error"""
    styles = {
        "info":     ("#FDF9F7", "#F3E9EC", "#8C7F86"),
        "progress": ("#F4E3E6", "#E8C9D0", "#B06878"),
        "success":  ("#EAF2EB", "#D8E5DB", "#5F8A6A"),
        "error":    ("#FDF6F7", "#F0D9DE", "#B06878"),
    }
    bg, bd, fg = styles.get(kind, styles["info"])
    return '<div style="background:{0};border:1px solid {1};border-radius:10px;padding:9px 12px;font-size:12px;color:{2};text-align:center;">{3}</div>'.format(bg, bd, fg, text)


def empty_state_html():
    return """
<div style="border:1.5px dashed #EADCE1;border-radius:12px;padding:30px 18px;text-align:center;">
  <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#F7E7EA,#EFD9DE);margin:0 auto 12px;display:flex;align-items:center;justify-content:center;font-size:22px;color:#C68D98;">✦</div>
  <div style="font-size:14px;font-weight:600;margin-bottom:6px;color:#4B4453;">填写产品信息，一键生成营销内容</div>
  <div style="font-size:11px;color:#9C8F9E;">生成后在此预览 4 平台内容卡片 · 支持一键复制</div>
</div>
"""


def meta_bar_html(elapsed, total_chars, tone_name, ok_count, total_count):
    tone = tone_name if tone_name else "自动匹配"
    return f"""
<div style="display:flex;flex-wrap:wrap;gap:6px;background:#FDF9F7;border:1px solid #F3E9EC;border-radius:10px;padding:9px 12px;font-size:11px;color:#8C7F86;margin-bottom:12px;">
  <span style="color:#5F8A6A;font-weight:600;">✓ 生成完成</span>
  <span style="color:#D8C9CF;">|</span><span>耗时 {elapsed:.1f}s</span>
  <span style="color:#D8C9CF;">|</span><span>总字数 {total_chars}</span>
  <span style="color:#D8C9CF;">|</span><span>调性 {esc(tone)}</span>
  <span style="color:#D8C9CF;">|</span><span>{ok_count}/{total_count} 平台成功</span>
</div>
"""


def platform_card_html(platform, r):
    meta = PLATFORM_META.get(platform, {"name": platform, "fg": "#8C7F86", "border": "#F0E6EA"})
    if "error" in r:
        return '<div style="border:1px solid #F0D9DE;border-radius:12px;padding:12px 14px;margin-bottom:8px;background:#FDF6F7;color:#B06878;font-size:12px;">⚠ {0} 生成失败：{1}</div>'.format(esc(meta["name"]), esc(r["error"]))
    title = r.get("title", "")
    content = r.get("content", "")
    chars = len(content)
    copy_payload = json.dumps("标题：{0}\n\n正文：\n{1}".format(title, content), ensure_ascii=False)
    return f"""
<div style="border:1px solid {meta['border']};border-radius:12px;padding:12px 14px;margin-bottom:8px;background:#FFFFFF;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:8px;">
    <div style="font-size:13px;font-weight:700;color:#4B4453;flex:1;">{esc(title)}</div>
    <button onclick="window.__mkt.copy(this)" data-copy="{esc(copy_payload)}" style="font-size:10px;color:{meta['fg']};border:1px solid {meta['border']};border-radius:6px;padding:3px 9px;background:#fff;cursor:pointer;flex-shrink:0;">复制</button>
  </div>
  <div style="font-size:12px;color:#6A5F68;line-height:1.7;white-space:pre-wrap;">{esc(content)}</div>
  <div style="font-size:10px;color:#C8B8BE;margin-top:6px;"><span style="color:{meta['fg']};">{esc(meta['name'])}</span> · {chars}字</div>
</div>"""


def results_html(selected_platforms, results):
    pills = "".join(
        '<span style="background:{0};color:{1};border-radius:9px;padding:6px 14px;font-size:12px;font-weight:600;">{2}</span>'.format(
            PLATFORM_META[p]["bg"], PLATFORM_META[p]["fg"], esc(PLATFORM_META[p]["name"]))
        for p in selected_platforms if p in PLATFORM_META
    )
    cards = "".join(platform_card_html(p, results[p]) for p in selected_platforms if p in results)
    return '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">{0}</div>\n{1}'.format(pills, cards)


def render_history():
    if not history_records:
        return '<div style="font-size:12px;color:#B9ABB2;text-align:center;padding:14px 0;">暂无生成记录，去试试吧 ✨</div>'
    items = []
    for rec in reversed(history_records[-8:]):
        platforms = rec.get("platforms", [])
        tone = rec.get("tone_name") or "自动匹配"
        total = rec.get("total_chars", "-")
        elapsed = rec.get("elapsed", "-")
        fill = json.dumps({
            "product": rec.get("product_name", ""),
            "benefits": rec.get("core_benefits", ""),
            "audience": rec.get("target_audience", ""),
            "promotion": rec.get("promotion_info", ""),
            "tone": rec.get("tone_choice", "自动匹配"),
            "platforms": rec.get("platform_keys", []),
        }, ensure_ascii=False)
        tag_html = " ".join(
            '<span style="background:{0};color:{1};border-radius:999px;padding:2px 9px;font-size:10px;">{2}</span>'.format(
                PLATFORM_META[p]["bg"], PLATFORM_META[p]["fg"], esc(PLATFORM_META[p]["name"]))
            for p in platforms if p in PLATFORM_META
        )
        items.append(f"""
<div style="border:1px solid #F0E6EA;border-radius:9px;padding:9px 11px;font-size:12px;background:#FDFBFC;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
  <div style="flex:1;min-width:140px;color:#4B4453;">{esc(rec.get('product_name',''))}<div style="margin-top:4px;">{tag_html}</div></div>
  <div style="text-align:right;color:#B9ABB2;font-size:11px;">
    <div>{esc(rec.get('time',''))}</div>
    <div style="color:#C8B8BE;">{esc(tone)} · {esc(str(total))}字 · {esc(str(elapsed))}s</div>
  </div>
  <button onclick="window.__mkt.fill(this)" data-fill="{esc(fill)}" style="font-size:10px;color:#C68D98;border:1px solid #F0D9DE;border-radius:6px;padding:3px 9px;background:#fff;cursor:pointer;">↺ 回填</button>
</div>""")
    return "".join(items)


def clear_history():
    history_records.clear()
    return '<div style="font-size:12px;color:#B9ABB2;text-align:center;padding:14px 0;">历史记录已清空</div>'


# ============ 主流程（生成，yield 逐平台进度） ============

def generate_content(product_name, core_benefits, target_audience, tone_choice, promotion_info, selected_platforms):
    # 输入校验（与改造前一致）
    if not product_name.strip():
        yield status_html("请填写产品名称", "error"), None, gr.skip()
        return
    if not core_benefits.strip():
        yield status_html("请填写核心卖点", "error"), None, gr.skip()
        return
    if not target_audience.strip():
        yield status_html("请填写目标人群", "error"), None, gr.skip()
        return
    if not selected_platforms:
        yield status_html("请至少选择一个平台", "error"), None, gr.skip()
        return

    tone_name = None if tone_choice == "自动匹配" else tone_choice
    results = {}
    total = len(selected_platforms)
    t_start = time.time()

    for i, platform in enumerate(selected_platforms, 1):
        yield status_html("正在生成 {0}/{1}：{2}…".format(i, total, PLATFORM_NAMES.get(platform, platform)), "progress"), None, gr.skip()
        try:
            r = generator.generate(
                product_name=product_name,
                core_benefits=core_benefits,
                target_audience=target_audience,
                platform=platform,
                tone_name=tone_name,
                promotion_info=promotion_info
            )
            results[platform] = r
        except Exception as e:
            results[platform] = {"error": str(e)}

    elapsed = time.time() - t_start
    ok_count = sum(1 for p in selected_platforms if p in results and "error" not in results[p])
    total_chars = sum(len(results[p].get("content", "")) for p in selected_platforms if p in results and "error" not in results[p])

    # 记录历史
    history_records.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "product_name": product_name,
        "core_benefits": core_benefits,
        "target_audience": target_audience,
        "promotion_info": promotion_info,
        "tone_name": tone_name,
        "tone_choice": tone_choice,
        "platform_keys": list(selected_platforms),
        "platforms": [PLATFORM_NAMES.get(p, p) for p in selected_platforms],
        "elapsed": round(elapsed, 1),
        "total_chars": total_chars,
        "results": results,
    })

    meta = meta_bar_html(elapsed, total_chars, tone_name, ok_count, total)
    ok = status_html("✓ 生成完成 · 共 {0} 个平台".format(total), "success")
    yield meta + ok, results_html(selected_platforms, results), render_history()


# ============ 前端注入 JS（复制 / 历史回填） ============

HEAD_JS = """
<script>
window.__mkt = window.__mkt || {};

window.__mkt._fbCopy = function(text) {
  var ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
};

window.__mkt.copy = function(btn) {
  var raw = btn.getAttribute('data-copy'); if (!raw) return;
  var text; try { text = JSON.parse(raw); } catch (e) { return; }
  var label = btn.textContent;
  var done = function() { btn.textContent = '已复制 ✓'; setTimeout(function() { btn.textContent = label; }, 1500); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, function() { window.__mkt._fbCopy(text); done(); });
  } else { window.__mkt._fbCopy(text); done(); }
};

window.__mkt._set = function(id, val) {
  var box = document.getElementById(id); if (!box) return;
  var node = box.querySelector('textarea') || box.querySelector('input');
  if (!node) return;
  node.value = val || '';
  node.dispatchEvent(new Event('input', { bubbles: true }));
};

window.__mkt.fill = function(el) {
  var raw = el.getAttribute('data-fill'); if (!raw) return;
  var o; try { o = JSON.parse(raw); } catch (e) { return; }
  window.__mkt._set('in_name', o.product);
  window.__mkt._set('in_benefits', o.benefits);
  window.__mkt._set('in_audience', o.audience);
  window.__mkt._set('in_promo', o.promotion);
  var toneBox = document.getElementById('in_tone');
  if (toneBox) {
    var node = toneBox.querySelector('select') || toneBox.querySelector('input');
    if (node) { node.value = o.tone || ''; node.dispatchEvent(new Event('change', { bubbles: true })); node.dispatchEvent(new Event('input', { bubbles: true })); }
  }
  var group = document.getElementById('platform_group');
  if (group && o.platforms && o.platforms.length) {
    group.querySelectorAll('input[type=checkbox]').forEach(function(cb) {
      var want = o.platforms.indexOf(cb.value) >= 0;
      if (cb.checked !== want) { cb.checked = want; cb.dispatchEvent(new Event('change', { bubbles: true })); }
    });
  }
};
</script>
"""


# ============ 界面样式（马卡龙轻奢） ============

CSS = """
:root {
  --bg: #FBF7F6; --card: #FFFFFF; --line: #F0E6EA; --line-soft: #EFE5E9;
  --primary: #C68D98; --primary-2: #DCA9B1; --primary-soft: #F4E3E6;
  --text: #4B4453; --text-2: #8C7F86; --text-3: #B9ABB2;
  --shadow: 0 6px 20px rgba(196,141,152,0.07); --radius: 14px;
}
.gradio-container {
  max-width: 100% !important; width: 100% !important; margin: 0 auto !important;
  background: var(--bg) !important; padding: 22px 20px 30px !important;
  font-family: 'Microsoft YaHei', system-ui, sans-serif !important;
}
.gradio-container .wrap { background: transparent !important; }
label { color: var(--text) !important; font-weight: 600 !important; font-size: 12px !important; }
.gradio-container input, .gradio-container textarea {
  font-family: 'Microsoft YaHei', system-ui, sans-serif !important;
}
.gradio-container textarea, .gradio-container input {
  border: 1px solid var(--line-soft) !important; border-radius: 9px !important;
  background: #FDFBFC !important; font-size: 13px !important; color: var(--text) !important;
}
.gradio-container textarea:focus, .gradio-container input:focus {
  border-color: #E3B5BA !important; box-shadow: 0 0 0 1px #F0D9DE !important;
}
.gradio-container ::placeholder { color: var(--text-3) !important; font-size: 12px !important; }
.gradio-container select { border: 1px solid var(--line-soft) !important; border-radius: 9px !important; background: #FDFBFC !important; font-size: 13px !important; color: var(--text) !important; }

#generate_btn {
  background: linear-gradient(135deg, #DCA9B1, #C68D98) !important; color: #FFFFFF !important;
  border: none !important; border-radius: 10px !important;
  font-size: 14px !important; font-weight: 600 !important; letter-spacing: 1px !important;
  box-shadow: 0 6px 14px rgba(198,141,152,0.30) !important; padding: 12px !important;
  cursor: pointer !important; transition: transform .15s ease, box-shadow .15s ease !important;
}
#generate_btn:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(198,141,152,0.38) !important; }

#btn_example1, #btn_example2 {
  background: #FFFFFF !important; border: 1px solid var(--line) !important; color: var(--text-2) !important;
  border-radius: 999px !important; font-size: 11px !important; padding: 6px 12px !important; cursor: pointer !important;
}

#platform_group { display: flex !important; flex-wrap: wrap !important; gap: 8px !important; }
#platform_group label {
  border: 1px solid var(--line) !important; border-radius: 999px !important;
  padding: 5px 14px !important; font-size: 12px !important; background: #FFFFFF !important;
  color: var(--text-2) !important; cursor: pointer !important; margin: 0 !important;
}
#platform_group input[type="checkbox"] { display: none !important; }
#platform_group label:has(input:checked) { background: #F4E3E6 !important; border-color: #E8C9D0 !important; color: #C68D98 !important; font-weight: 600 !important; }
#platform_group label:nth-of-type(1):has(input:checked) { background: #E4EEF7 !important; border-color: #D3E2F0 !important; color: #5E86B3 !important; }
#platform_group label:nth-of-type(2):has(input:checked) { background: #F7E4E8 !important; border-color: #F2DDE3 !important; color: #C4707F !important; }
#platform_group label:nth-of-type(3):has(input:checked) { background: #F8EFE0 !important; border-color: #EFE2CC !important; color: #A98E6A !important; }
#platform_group label:nth-of-type(4):has(input:checked) { background: #E6F0E7 !important; border-color: #DCEADF !important; color: #6E9C78 !important; }

#refresh_btn, #clear_btn {
  background: #FFFFFF !important; border: 1px solid var(--line) !important; color: var(--text-2) !important;
  border-radius: 999px !important; font-size: 11px !important; padding: 5px 12px !important; cursor: pointer !important;
}
"""


# ============ 界面构建 ============

with gr.Blocks(title="跨平台智能营销内容生成系统", css=CSS, head=HEAD_JS) as demo:
    gr.HTML(brand_bar_html())

    with gr.Row():
        # 左侧输入区
        with gr.Column(scale=4):
            with gr.Group(elem_id="input_card"):
                gr.HTML(section_title(1, "产品信息"))
                product_name = gr.Textbox(label="产品名称", placeholder="例如：云朵冷萃咖啡", elem_id="in_name")
                core_benefits = gr.Textbox(label="核心卖点", placeholder="例如：深烘醇厚、冷萃清爽不酸涩", lines=3, elem_id="in_benefits")
                target_audience = gr.Textbox(label="目标人群", placeholder="例如：上班族、咖啡爱好者", elem_id="in_audience")
                tone_choice = gr.Dropdown(label="品牌调性", choices=TONE_OPTIONS, value="自动匹配", elem_id="in_tone")
                promotion_info = gr.Textbox(label="促销信息（选填）", placeholder="例如：限时买一送一，赠价值99元小样套装", lines=2, elem_id="in_promo")

            with gr.Group():
                gr.HTML(section_title(2, "目标平台"))
                platform_checkboxes = gr.CheckboxGroup(
                    label="选择要生成的平台",
                    choices=[
                        ("抖音", "douyin"),
                        ("小红书", "xiaohongshu"),
                        ("电商", "ecommerce"),
                        ("公众号", "wechat")
                    ],
                    value=["douyin", "xiaohongshu"],
                    elem_id="platform_group"
                )
                generate_btn = gr.Button("✦ 生成营销内容", variant="primary", size="lg", elem_id="generate_btn")
                status_display = gr.HTML("")

        # 右侧输出区
        with gr.Column(scale=6):
            with gr.Group():
                gr.HTML(section_title(3, "生成结果"))
                results_display = gr.HTML(empty_state_html())

            with gr.Accordion("历史记录", open=False):
                history_display = gr.HTML(render_history())
                with gr.Row():
                    refresh_history_btn = gr.Button("刷新历史", size="sm", elem_id="refresh_btn")
                    clear_history_btn = gr.Button("清空历史", size="sm", elem_id="clear_btn")

    # 绑定事件
    generate_btn.click(
        fn=generate_content,
        inputs=[
            product_name, core_benefits, target_audience,
            tone_choice, promotion_info, platform_checkboxes
        ],
        outputs=[status_display, results_display, history_display]
    )

    refresh_history_btn.click(fn=render_history, outputs=history_display)
    clear_history_btn.click(fn=clear_history, outputs=history_display)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
