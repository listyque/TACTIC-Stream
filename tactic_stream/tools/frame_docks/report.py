"""Build the dock evidence page, rejecting stale native/browser sources."""

import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).resolve().parent / "output"
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from native_capture import source_hashes


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    shared, sources = source_hashes(ROOT, TH, list(native["nativeSources"]))
    assert shared == native["sha256"] and sources == native["nativeSources"], (
        "Stale dock captures"
    )
    for name, expected in browser["sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert len(browser["captures"]) == len(native["samples"]) == 24
    sections = []
    for sample in native["samples"]:
        originals = [row for row in native["captures"] if row["id"] == sample["id"]]
        current = next(row for row in browser["captures"] if row["id"] == sample["id"])
        pictures = []
        for label, row in zip(
            ["Исходный ТХ", "Frame ТХ", "Frame ТС"], originals + [current]
        ):
            assert (OUT / row["image"]).is_file()
            pictures.append(
                f'<figure><figcaption>{label}</figcaption><a href="{row["image"]}"><img src="{row["image"]}" alt="{html.escape(sample["id"])}"></a></figure>'
            )
        sections.append(
            f'<details open><summary>{html.escape(sample["id"])} · {sample["height"]} px</summary><div class="pictures">{"".join(pictures)}</div></details>'
        )
    page = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · деревья доков</title><style>body{{background:#1c2022;color:#eee;font:15px/1.5 Segoe UI,sans-serif;margin:24px}}a{{color:#8abbd5}}.pictures{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}figure{{margin:0}}img{{width:100%;height:auto}}figcaption{{padding:8px}}details{{margin:24px 0}}summary{{cursor:pointer}}p{{max-width:1100px}}@media(max-width:760px){{.pictures{{grid-template-columns:1fr}}}}</style>
<h1>Деревья доков: исходный ТХ → Frame ТХ → Frame ТС</h1>
<p>24 полные раскладки, {browser["comparisons"]} сравнений координат и размеров. Вложенные сплиты, скрытые панели, максимум вкладки стека, плавающее окно, очередь отправки; 1800×1000, 1100×800, 760×640. Изображения используют настоящие DockPanel/DockWorkspace с пустым предметным содержимым. Проверяется геометрия оболочки, а не функциональность содержимого панелей.</p>
<p>Эталон дерева и минимумов взят из независимого архива <code>{native["reference"]}</code>. Исходный QML снят отдельно; отличия платформенных кнопок сохранены. Проверки пальцем/мышью/клавиатурой, отмены, восьми краёв, сохранения и возврата размеров выполняются отдельными сценариями. Тела экранов и системные окна Windows не объявляются идентичными.</p>
<p>Полный публичный путь проекции ТХ с преобразованием Python↔Qt JS: {native["projectionMs"]:.3f} мс/обновление, среднее 200 повторов данного стенда. Это не FPS и не замер композитора.</p>
<p><a href="../../../docs/shared_ui_foundation_plan.md">План и оставшиеся блоки</a> · <a href="native.json">Нативные измерения и отпечатки</a> · <a href="browser.json">Веб-измерения</a></p>{"".join(sections)}</html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
