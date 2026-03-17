"""
60장면 이미지 검수 도구
HTML 갤러리 생성 → 브라우저에서 한눈에 확인 가능
"""

import json, base64
from pathlib import Path

EPISODE_DIR = Path("output/episodes/2026-03-17_Mommy_Became_the_Warm_Sun")
IMAGES_DIR = EPISODE_DIR / "images_v3"
CHARS_PATH = EPISODE_DIR / "characters.json"

with open(EPISODE_DIR / "images_v2" / "scenario_v2_60.json", "r", encoding="utf-8") as f:
    scenario = json.load(f)

with open(CHARS_PATH, "r", encoding="utf-8") as f:
    characters = json.load(f)

scenes = scenario["scenes"]

# 캐릭터 정보
char_info = f"""<b>주인공:</b> {characters['main_character']['name_kr']} - {characters['main_character']['description_en'][:80]}...<br>"""
for sc in characters.get("supporting_characters", []):
    char_info += f"""<b>{sc['name_kr']}:</b> {sc['description_en'][:80]}...<br>"""

# 이미지를 base64로 인코딩 (HTML에 임베드)
rows_html = ""
for i, scene in enumerate(scenes):
    img_up = IMAGES_DIR / f"scene_{i:02d}_up.png"
    img_raw = IMAGES_DIR / f"scene_{i:02d}.png"
    img_path = img_up if img_up.exists() else img_raw

    if img_path.exists():
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{b64}" class="scene-img" onclick="toggleFlag(this, {i})">'
    else:
        img_tag = '<div class="no-img">이미지 없음</div>'

    # 어떤 그리드에서 나왔는지
    grid_idx = i // 4

    rows_html += f"""
    <div class="scene-card" id="card-{i}" data-grid="{grid_idx}">
        <div class="scene-header">
            <span class="scene-num">#{i+1}</span>
            <span class="grid-badge">그리드 {grid_idx}</span>
            <button class="flag-btn" onclick="toggleFlag(document.querySelector('#card-{i} img'), {i})">문제 표시</button>
        </div>
        {img_tag}
        <div class="scene-text">
            <div class="narration">{scene['narration_kr']}</div>
            <div class="prompt">{scene['image_prompt_en']}</div>
        </div>
    </div>
    """

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>60장면 이미지 검수</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 10px; color: #ffd700; }}
.info {{ text-align: center; margin-bottom: 20px; color: #aaa; font-size: 14px; line-height: 1.6; }}
.char-info {{ background: #16213e; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; line-height: 1.6; }}
.controls {{ text-align: center; margin-bottom: 20px; }}
.controls button {{ padding: 8px 16px; margin: 0 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }}
.btn-all {{ background: #4a4a8a; color: white; }}
.btn-flagged {{ background: #e74c3c; color: white; }}
.btn-export {{ background: #2ecc71; color: white; }}
.stats {{ text-align: center; margin-bottom: 20px; font-size: 16px; color: #ffd700; }}

.grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }}
.scene-card {{ background: #16213e; border-radius: 10px; overflow: hidden; border: 2px solid transparent; transition: border-color 0.3s; }}
.scene-card.flagged {{ border-color: #e74c3c; background: #2c1a1a; }}
.scene-header {{ display: flex; align-items: center; gap: 10px; padding: 10px 15px; background: #0f3460; }}
.scene-num {{ font-weight: bold; font-size: 18px; color: #ffd700; }}
.grid-badge {{ background: #4a4a8a; padding: 2px 8px; border-radius: 10px; font-size: 12px; }}
.flag-btn {{ margin-left: auto; padding: 4px 10px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }}
.scene-img {{ width: 100%; cursor: pointer; transition: opacity 0.2s; }}
.scene-img:hover {{ opacity: 0.9; }}
.no-img {{ width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; background: #333; }}
.scene-text {{ padding: 10px 15px; }}
.narration {{ font-size: 14px; line-height: 1.6; margin-bottom: 8px; color: #ddd; }}
.prompt {{ font-size: 12px; color: #888; line-height: 1.4; font-style: italic; }}

.hidden {{ display: none !important; }}

/* 그리드 뷰 */
.grid-section {{ margin-bottom: 30px; }}
.grid-title {{ font-size: 18px; color: #ffd700; margin-bottom: 10px; padding: 5px 10px; background: #0f3460; border-radius: 5px; }}
</style>
</head>
<body>

<h1>60장면 이미지 검수</h1>
<div class="info">
    이미지를 클릭하거나 "문제 표시" 버튼을 눌러 재생성이 필요한 장면을 표시하세요.<br>
    같은 그리드(4컷)는 함께 재생성됩니다.
</div>
<div class="char-info">{char_info}</div>

<div class="controls">
    <button class="btn-all" onclick="showAll()">전체 보기</button>
    <button class="btn-flagged" onclick="showFlagged()">문제 장면만</button>
    <button class="btn-export" onclick="exportFlagged()">문제 목록 내보내기</button>
</div>

<div class="stats" id="stats">문제 표시: 0 / 60</div>

<div class="grid-container" id="gallery">
{rows_html}
</div>

<script>
let flagged = new Set();

function toggleFlag(imgEl, idx) {{
    const card = document.getElementById('card-' + idx);
    if (flagged.has(idx)) {{
        flagged.delete(idx);
        card.classList.remove('flagged');
    }} else {{
        flagged.add(idx);
        card.classList.add('flagged');
    }}
    updateStats();
}}

function updateStats() {{
    document.getElementById('stats').textContent =
        '문제 표시: ' + flagged.size + ' / 60 (그리드 ' +
        new Set([...flagged].map(i => Math.floor(i/4))).size + '개 재생성 필요)';
}}

function showAll() {{
    document.querySelectorAll('.scene-card').forEach(c => c.classList.remove('hidden'));
}}

function showFlagged() {{
    document.querySelectorAll('.scene-card').forEach((c, idx) => {{
        if (flagged.has(idx)) {{
            c.classList.remove('hidden');
        }} else {{
            c.classList.add('hidden');
        }}
    }});
}}

function exportFlagged() {{
    if (flagged.size === 0) {{
        alert('문제 표시된 장면이 없습니다.');
        return;
    }}

    let grids = {{}};
    flagged.forEach(idx => {{
        let g = Math.floor(idx / 4);
        if (!grids[g]) grids[g] = [];
        grids[g].push(idx + 1);
    }});

    let text = '=== 재생성 필요 목록 ===\\n\\n';
    for (let g of Object.keys(grids).sort((a,b) => a-b)) {{
        text += '그리드 ' + g + ' (장면 ' + grids[g].join(', ') + ')\\n';
    }}
    text += '\\n총 ' + Object.keys(grids).length + '개 그리드 재생성 필요';

    // 클립보드 복사
    navigator.clipboard.writeText(text).then(() => {{
        alert('클립보드에 복사되었습니다!\\n\\n' + text);
    }}).catch(() => {{
        prompt('아래 내용을 복사하세요:', text);
    }});
}}
</script>

</body>
</html>"""

output_path = EPISODE_DIR / "review_images.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"검수 페이지 생성 완료!")
print(f"파일: {output_path}")
print(f"\n브라우저에서 열어서 확인하세요.")
print(f"- 이미지 클릭 or '문제 표시' → 빨간 테두리로 표시")
print(f"- '문제 장면만' 필터")
print(f"- '문제 목록 내보내기' → 재생성할 그리드 목록 복사")
