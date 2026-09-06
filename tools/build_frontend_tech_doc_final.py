from __future__ import annotations

import build_frontend_tech_doc as report
from docx import Document


def main() -> None:
    replacements = {
        "59df1d036747e52b7685d0a36ec48bb9.png": "118f1859de740f2c0eb4b8230530bd66.png",
        "7cecff5698ea020768d43ea15e98f23a.png": "c14682951f35af82313b9b6e9fc92fc6.png",
        "26d06d86c8f7900e08e3f2734cdefae9.png": "1c2890d7fe4a254668976e64f3b91743.png",
    }
    for figure in report.FIGURES:
        source_name = figure["file"]
        if source_name in replacements:
            figure["file"] = replacements[source_name]
        if figure["file"] == "118f1859de740f2c0eb4b8230530bd66.png":
            figure["max_height"] = 4.1
        if figure["file"] == "f4d7e90923e117ad818f001eb077b9aa.png":
            figure.pop("code", None)
            figure.pop("code_title", None)
        if figure["file"] == "1c2890d7fe4a254668976e64f3b91743.png":
            figure["max_height"] = 4.4
            figure.pop("code", None)
            figure.pop("code_title", None)

    expected = {
        "c14682951f35af82313b9b6e9fc92fc6.png",
        "f4d7e90923e117ad818f001eb077b9aa.png",
        "b3de4fe5d6d4e81d789722c8b99e180d.png",
        "1c2890d7fe4a254668976e64f3b91743.png",
        "118f1859de740f2c0eb4b8230530bd66.png",
        "4d7775daea18853668bfe81fc3ef2734.png",
        "4289712f2a993629d2d69e65901289eb.png",
        "38bcbcecb1ae717aa4abf36c77e4d1ed.png",
        "fe4b3e7e1871b431288688985032616b.png",
        "4a646e13ea0dc09dad72c03180b12ab8.png",
        "519b4fc0bfa13382e4edc7d3361ec986.png",
        "1d138370a7a0906423f2b0881153587e.png",
        "018127eeac2cbc94bbaa03af2d146370.png",
        "c813157af2fe09c5918dfdafcfc42002.png",
        "60fa493d69f1185f94168750ec8cbbab.png",
        "bde9ee73c91247bb6b823811c07dc8c8.png",
        "9a8db6c13ee403b68029615723f7c112.png",
        "97ee94cf1559422b09e22fd2564ce8bc.png",
        "df154d72d7135cb368ba2bc3f85da5e1.png",
    }
    actual = {figure["file"] for figure in report.FIGURES}
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise RuntimeError(f"截图清单不一致；缺少={missing}；多余={unexpected}")

    output_path = report.build_document()
    document = Document(output_path)
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            if "18 张系统界面截图" in run.text:
                run.text = run.text.replace("18 张系统界面截图", "19 张系统界面截图")
    document.save(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
