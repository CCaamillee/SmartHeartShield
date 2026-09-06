from __future__ import annotations

from pathlib import Path

from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = (
    Path(r"D:\Personal\Documents\Tencent Files\1806093469\nt_qq\nt_data\Pic\2026-08\Ori"),
    Path(r"D:\Personal\Documents\Tencent Files\1806093469\nt_qq\nt_data\Pic\2026-09\Ori"),
)
OUTPUT_DIR = PROJECT_ROOT / "deliverables"
OUTPUT_PATH = OUTPUT_DIR / "智能心盾_前端技术实现细节.docx"

PRESET = {
    "name": "compact_reference_guide",
    "page_width": 8.5,
    "page_height": 11.0,
    "margin": 1.0,
    "header_distance": 0.492,
    "footer_distance": 0.492,
    "body_font": "Calibri",
    "east_asia_font": "Microsoft YaHei",
    "body_size": 11,
    "body_after": 6,
    "body_line": 1.25,
    "h1_size": 16,
    "h1_before": 18,
    "h1_after": 10,
    "h2_size": 13,
    "h2_before": 14,
    "h2_after": 7,
    "h3_size": 12,
    "h3_before": 10,
    "h3_after": 5,
    "table_width_dxa": 9360,
    "table_indent_dxa": 120,
    "cell_margin_top": 80,
    "cell_margin_bottom": 80,
    "cell_margin_start": 120,
    "cell_margin_end": 120,
}

NAVY = "0B2545"
BLUE = "176BCE"
DEEP_BLUE = "0B5B91"
LIGHT_BLUE = "E8F1F8"
VERY_LIGHT_BLUE = "F4F8FB"
MUTED = "5F7385"
LIGHT_GRAY = "D8E2EA"
WHITE = "FFFFFF"
INK = "17324A"
GREEN = "1B8A5A"
RED = "C9343A"


FIGURES = [
    {
        "file": "59df1d036747e52b7685d0a36ec48bb9.png",
        "section": "",
        "title": "1.2 关于页与全局可信交互边界",
        "caption": "图 1  关于页面、功能职责与临床使用原则",
        "max_height": 5.6,
        "description": (
            "关于页面以系统定位、主要功能和临床使用原则三个层次解释产品边界，"
            "并将急诊概览、辅助诊断和病情详情的职责并列呈现。views/about.py 负责内容组织，"
            "components/header.py、components/footer.py 与 components/styles.py 提供统一标题、页脚和卡片视觉；"
            "页面特别区分回顾性 label、15 天窗口 cutoff_time 与模型风险结果，使公共说明与各业务页的缺失值、"
            "模型不可用提示共同构成前端可信交互约束。"
        ),
        "details": "",
    },
    {
        "file": "7cecff5698ea020768d43ea15e98f23a.png",
        "section": "2 首页实现",
        "title": "2.1 首页、品牌区与主导航",
        "caption": "图 2  系统首页与全局导航",
        "max_height": 5.4,
        "description": (
            "首页由顶部品牌导航、核心功能说明区、三类功能入口卡片和临床使用边界提示组成。"
            "入口文件 app.py 统一设置宽屏布局并加载全局样式，components/sidebar.py 根据 Session State "
            "维护当前页面，ROUTES 映射再将页面名称分发到 views 目录中的对应 render 函数。"
        ),
        "details": (
            "页面主体使用 st.columns 组织文字与心脏主题视觉素材，功能卡片通过按钮回调写入 pending_page，"
            "从而在不暴露底层路径的情况下完成页面切换。公共导航、页眉和页脚被封装为组件，保证五个页面的"
            "品牌色、图标、间距和交互状态一致；移动端样式则由 components/styles.py 中的媒体查询负责收缩和重排。"
        ),
        "code_title": "首页入口按钮的状态跳转",
        "code": (
            "def _go(page: str) -> None:\n"
            "    st.session_state.pending_page = page\n\n"
            "st.button(\n"
            "    f\"进入{title}\", type=\"primary\", width=\"stretch\",\n"
            "    on_click=_go, args=(page,),\n"
            ")"
        ),
    },
    {
        "file": "f4d7e90923e117ad818f001eb077b9aa.png",
        "section": "3 急诊概览页面",
        "title": "3.1 急诊概览整体页面",
        "caption": "图 3  急诊概览页面整体布局",
        "max_height": 4.65,
        "description": (
            "急诊概览将模型验证结果概括为重点指标、风险分布、当前危急度、分级处置建议和患者结果表。"
            "views/dashboard.py 负责页面编排，services/prediction_api.py 读取并规范化项目根目录中的"
            " heart_break_predict_results.json，使卡片、图表、筛选器和表格使用同一份结果口径。"
        ),
        "details": (
            "页面采用由上到下的阅读顺序：先展示总体结论，再通过图表解释分布，随后给出处置分层，最后进入患者级检索。"
            "这种组织方式减少了使用者在大量结果中直接查找的负担，同时将模型验证样本与工作簿中的真实就诊资料明确区分。"
        ),
        "code_title": "急诊概览的数据装载与分页",
        "code": (
            "overview = get_evaluation_prediction_overview()\n"
            "records = get_evaluation_prediction_records()\n"
            "page = st.pagination(total_pages, key=\"evaluation_patient_page\")\n"
            "start = (page - 1) * ROWS_PER_PAGE\n"
            "_display_evaluation_table(filtered.iloc[start:start + ROWS_PER_PAGE])"
        ),
    },
    {
        "file": "4d7775daea18853668bfe81fc3ef2734.png",
        "section": "",
        "title": "3.2 模型预测重点指标",
        "caption": "图 4  模型预测重点卡片",
        "max_height": 3.0,
        "description": (
            "重点区域以三张指标卡呈现高风险样本数、当前危急样本数和验证样本规模。"
            "后端读取结果文件后先完成字段归一化，再由 _render_prediction_focus 将数值、说明文字和风险色映射到固定卡片结构。"
        ),
        "details": (
            "红色强调高风险与危急状态，蓝色用于统计基数；下方边界说明单独显示。"
            "指标计算与页面 HTML 分离，使结果文件更新后无需修改页面模板。"
        ),
    },
    {
        "file": "4289712f2a993629d2d69e65901289eb.png",
        "section": "",
        "title": "3.3 风险分布与危急度图表",
        "caption": "图 5  风险等级分布与当前危急度",
        "max_height": 3.2,
        "description": (
            "风险等级采用横向条形图展示高、中、低风险样本数量，当前危急度采用环形图展示危急与暂时稳定的比例。"
            "views/dashboard.py 使用 Altair 构造条形图与环形图，页面通过 st.altair_chart 完成响应式渲染。"
        ),
        "details": (
            "图表颜色与患者列表中的风险标识保持一致，图下方同步输出汇总文本，既便于快速比较，也保留精确数值。"
            "数据源发生变化时，图表和文字由同一统计结果重新生成，避免视觉结果与统计卡片不一致。"
        ),
    },
    {
        "file": "38bcbcecb1ae717aa4abf36c77e4d1ed.png",
        "section": "",
        "title": "3.4 分级处置建议",
        "caption": "图 6  高、中、低风险分级处置建议",
        "max_height": 3.1,
        "description": (
            "处置建议按高、中、低风险分为三列，并通过红、橙、绿三种状态色建立清晰的视觉优先级。"
            "views/dashboard.py 将每一级别的标题、说明和要点定义为结构化配置，再循环生成同构卡片。"
        ),
        "details": (
            "该部分只提供分层复核方向，页面同时保留“需结合生命体征、床旁影像和完整病历动态调整”的说明，"
            "使模型分层与临床判断之间保持明确边界。"
        ),
    },
    {
        "file": "fe4b3e7e1871b431288688985032616b.png",
        "section": "",
        "title": "3.5 患者结果筛选、排序与分页",
        "caption": "图 7  患者结果表及组合筛选",
        "max_height": 5.4,
        "description": (
            "患者基本情况区域支持按匿名患者标识、诊断文字、风险等级和当前危急度组合筛选，"
            "并提供风险优先排序。表格以预测破裂时间替代数据集列，通过 column_config 控制字段宽度和状态文本。"
        ),
        "details": (
            "分页由 st.pagination 管理，当前页只渲染对应数据切片，降低长表格一次性加载带来的页面压力。"
            "高风险记录的预测破裂时间使用匿名样本标识生成稳定且有差异的时间范围；"
            "风险行背景与状态标识采用统一色阶，使用者能够先按颜色定位重点对象，再读取破裂判断和危急度等字段。"
        ),
    },
    {
        "file": "b3de4fe5d6d4e81d789722c8b99e180d.png",
        "section": "4 辅助诊断页面",
        "title": "4.1 辅助诊断整体工作区",
        "caption": "图 8  患者筛选与 Agent 问答双栏工作区",
        "max_height": 5.1,
        "description": (
            "辅助诊断页面采用左右双栏结构：左侧负责患者检索、就诊确认和结构化资料查看，右侧负责连续问答与分析过程展示。"
            "两侧容器均设置固定高度，聊天内容在内部滚动，避免长回答持续拉伸整页。"
        ),
        "details": (
            "views/clinical_agent.py 读取上传预测结果的稳定患者映射，将模型判断可能发生心脏破裂的就诊优先排列，"
            "并通过 selected_encounter_key 维护当前就诊；页面切换时仍可保留全局聊天流，"
            "但每条消息标注所属患者与就诊。模型上下文继续按 encounter_key 隔离，从界面连续性和数据安全两个方面"
            "处理跨患者问答场景。"
        ),
        "code_title": "ReAct 事件流与就诊级上下文",
        "code": (
            "response = ClinicalReActAgent().run(\n"
            "    encounter_key, question,\n"
            "    history=prior_history,\n"
            "    event_callback=on_event,\n"
            ")\n"
            "append_chat_message(encounter_key, {\"role\": \"assistant\", **response})"
        ),
    },
    {
        "file": "519b4fc0bfa13382e4edc7d3361ec986.png",
        "section": "",
        "title": "4.2 患者组合筛选器",
        "caption": "图 9  辅助诊断患者筛选条件",
        "max_height": 5.5,
        "description": (
            "左侧筛选器提供编号直查，并可展开年龄、性别、入院日期、诊断名称、诊断科室和手术名称等组合条件。"
            "筛选操作放在 st.form 中，用户完成多项选择后再统一提交，避免每次控件变化都触发完整页面重算。"
        ),
        "details": (
            "清除按钮统一重置筛选状态，应用筛选后再生成就诊下拉列表。列表选项由 regno 与 admno 构成稳定就诊键，"
            "保证同一患者的不同就诊不会被错误合并。"
        ),
    },
    {
        "file": "1d138370a7a0906423f2b0881153587e.png",
        "section": "",
        "title": "4.3 结构化患者资料分组",
        "caption": "图 10  结构化患者资料分组选择",
        "max_height": 3.6,
        "description": (
            "结构化资料采用概览、诊断、检查与检验、治疗与病程、风险信息五类分组。"
            "get_encounter_detail 将原始工作簿字段整理为统一字典，components/records.py 再将各组字段渲染为记录卡片。"
        ),
        "details": (
            "分组选择减少了单页信息密度，并使 Agent 问答区与人工资料核对共享同一就诊数据来源。"
            "缺失字段以“暂无记录”呈现，不在前端进行推断性填充。"
        ),
    },
    {
        "file": "4a646e13ea0dc09dad72c03180b12ab8.png",
        "section": "",
        "title": "4.4 ReAct 分析过程展示",
        "caption": "图 11  Agent 的可折叠分析过程",
        "max_height": 3.4,
        "description": (
            "辅助诊断 Agent 采用 ReAct 流程，根据问题在临床特征提取、病程时间轴、风险预测和医学知识说明工具之间进行选择。"
            "页面接收 phase、Observation 和 final_delta 等事件，将“明确查询内容—整理临床资料—判断下一步—整理回答”"
            "组织为可折叠时间线。"
        ),
        "details": (
            "患者相关工具的 patient_id 由系统覆盖为当前 encounter_key，模型不能自行切换查询对象。"
            "问答记录同步写入项目根目录的 SQLite 数据库，刷新页面或重启服务后仍可恢复；模型生成回答时仅携带当前就诊的有限历史消息。"
        ),
    },
    {
        "file": "26d06d86c8f7900e08e3f2734cdefae9.png",
        "section": "5 病情详情页面",
        "title": "5.1 病情详情整体布局",
        "caption": "图 12  病情详情页面整体结构与患者结果汇总",
        "max_height": 5.15,
        "description": (
            "病情详情先呈现全部可用预测结果的成功与失败统计，再以单次就诊为边界呈现患者结果汇总、患者与就诊选择、分组标签页和风险结果。"
            "views/patient_workspace.py 负责页面编排，并通过 components/patient_navigation.py 与辅助诊断页面共享当前就诊状态。"
        ),
        "details": (
            "页面顶部先展示预测成功率和失败构成，再汇总当前患者的就诊时段、主要诊断、治疗或手术及回顾性目标事件；"
            "中部确认患者及就诊，底部通过标签页逐类浏览真实记录。每次选择变化都会重新调用 get_encounter_detail，"
            "确保结果汇总、时间轴和详情字段来自同一 encounter_key；回顾性 label 不被解释为预测概率或实时风险。"
        ),
        "code_title": "就诊选择与详情分组渲染",
        "code": (
            "detail = get_encounter_detail(selected)\n"
            "tabs = st.tabs([\"完整时间轴\", \"基本信息\", \"诊断信息\",\n"
            "                \"检查与检验\", \"治疗与病程\", \"风险预测\"])\n"
            "with tabs[0]:\n"
            "    _render_timeline(detail)\n"
            "with tabs[5]:\n"
            "    _render_risk(detail)"
        ),
    },
    {
        "file": "97ee94cf1559422b09e22fd2564ce8bc.png",
        "section": "",
        "title": "5.2 预测结果与救治成效推演",
        "caption": "图 13  不同干预时点下的结果对照推演",
        "max_height": 2.35,
        "description": (
            "推演区围绕同一预测风险点并列呈现两种结果路径：事件提前发生而错过干预窗口，以及在风险时点前完成干预并获得救治时间。"
            "前端将节点、状态、天数与解释文字组织为时间线卡片，通过红色和绿色主题帮助使用者比较干预时点对结果理解的影响。"
        ),
        "details": (
            "views/patient_workspace.py 通过 _forecast_outcome 生成稳定的演示分支，再由 _render_forecast_timeline 输出节点结构。"
            "该推演与患者真实病情时间轴及模型结果文件分开处理，只用于解释预测窗口与处置时机之间的关系。"
        ),
    },
    {
        "file": "df154d72d7135cb368ba2bc3f85da5e1.png",
        "section": "",
        "title": "5.3 患者与就诊选择",
        "caption": "图 14  病情详情患者检索与页面联动",
        "max_height": 3.7,
        "description": (
            "病情详情支持直接选择就诊，也可展开筛选器按编号、年龄、性别、日期、诊断、科室和手术名称组合检索。"
            "选择项同时显示风险等级、患者编号、就诊编号、年龄、性别和主要诊断，便于在进入详情前确认分析对象。"
        ),
        "details": (
            "“前往辅助诊断”按钮通过共享的 pending_encounter_key 传递当前就诊，目标页面消费该状态后自动选中同一记录，"
            "实现患者详情与 Agent 问答之间的连续跳转。"
        ),
    },
    {
        "file": "018127eeac2cbc94bbaa03af2d146370.png",
        "section": "",
        "title": "5.4 完整病情时间轴",
        "caption": "图 15  按真实时间排序的就诊事件时间轴",
        "max_height": 4.05,
        "description": (
            "完整时间轴按照工作簿中的真实日期时间排序，将门诊、就诊、诊断、检查、治疗和数据截止等事件组织为纵向节点。"
            "services/workbook_data.py 负责提取和排序事件，components/timeline.py 负责节点、来源标签和展开详情的统一渲染。"
        ),
        "details": (
            "时间缺失时系统不补造事件时点；能够确认的记录才进入时间轴，并保留来源字段。"
            "长文本默认折叠，使用者按需展开，既保证页面可读性，也能查看原始细节。"
        ),
    },
    {
        "file": "c813157af2fe09c5918dfdafcfc42002.png",
        "section": "",
        "title": "5.5 基本信息分组",
        "caption": "图 16  单次就诊基本信息卡片",
        "max_height": 4.5,
        "description": (
            "基本信息页展示患者编号、就诊编号、年龄、性别、入院或就诊时间、出院时间、15 天窗口截止时间和同一患者就诊次数。"
            "字段由 get_encounter_detail 从当前就诊记录中提取，并通过通用记录卡片组件逐项输出。"
        ),
        "details": (
            "患者编号与就诊编号始终同时展示，便于核对多次就诊边界；日期字段统一格式化，缺失值使用明确文字代替空白。"
        ),
    },
    {
        "file": "60fa493d69f1185f94168750ec8cbbab.png",
        "section": "",
        "title": "5.6 诊断信息分组",
        "caption": "图 17  诊断记录与编码信息",
        "max_height": 4.4,
        "description": (
            "诊断信息页集中呈现门诊诊断、诊断名称、诊断时间、科室、备注、主要诊断标识、诊断状态和 ICD 编码。"
            "同一字段存在多个值时保持原有顺序并以统一分隔方式显示，避免在前端进行未经验证的配对。"
        ),
        "details": (
            "标签页仅负责显示当前就诊已经整理出的诊断字段，数据分类逻辑集中在服务层，"
            "因此同一套诊断数据也可以被辅助诊断工具和时间轴复用。"
        ),
    },
    {
        "file": "bde9ee73c91247bb6b823811c07dc8c8.png",
        "section": "",
        "title": "5.7 治疗与病程分组",
        "caption": "图 18  治疗、手术和病程记录切换",
        "max_height": 3.8,
        "description": (
            "治疗与病程页使用 st.segmented_control 在“用药与医嘱、手术信息、病程记录”之间切换，"
            "避免将三类长文本同时堆叠在一个页面。"
        ),
        "details": (
            "用户选择类别后，页面只渲染对应的数据组；卡片仍使用统一字段样式。"
            "这种局部切换方式降低了信息密度，并使治疗记录与完整时间轴形成互补：前者适合分类阅读，后者适合按时间回顾。"
        ),
    },
    {
        "file": "9a8db6c13ee403b68029615723f7c112.png",
        "section": "",
        "title": "5.8 风险预测结果",
        "caption": "图 19  患者级心脏破裂风险结果卡",
        "max_height": 4.9,
        "description": (
            "风险预测页展示风险等级、未来 14 天破裂判断、当前危急度、结果来源、预测结论和核心依据。"
            "services/prediction_api.py 将不同结果格式归一为统一字段，再由 _render_risk 生成状态卡和详情记录。"
        ),
        "details": (
            "风险色只根据已上传结果中的模型标签确定；模型未提供的概率或精确时点不会由页面补充。"
            "原始回答和核心依据可按需展开，既突出结论，也保留复核所需的文本信息。"
        ),
    },
]


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        tag = "w:" + edge
        node = tc_mar.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa: list[int], indent_dxa: int = 120) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.first_child_found_in("w:tblInd")
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            width = widths_dxa[index]
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in("w:tcW")
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(
                cell,
                PRESET["cell_margin_top"],
                PRESET["cell_margin_start"],
                PRESET["cell_margin_bottom"],
                PRESET["cell_margin_end"],
            )


def mark_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = tr_pr.find(qn("w:tblHeader"))
    if tbl_header is None:
        tbl_header = OxmlElement("w:tblHeader")
        tr_pr.append(tbl_header)
    tbl_header.set(qn("w:val"), "true")


def set_run_font(run, *, size=None, bold=None, color=None, italic=None, font=None) -> None:
    font_name = font or PRESET["body_font"]
    run.font.name = font_name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), font_name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), font_name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), PRESET["east_asia_font"])
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = rgb(color)


def set_paragraph_border(paragraph, *, side="bottom", color=LIGHT_GRAY, size=8, space=4) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), str(size))
    border.set(qn("w:space"), str(space))
    border.set(qn("w:color"), color)
    p_bdr.append(border)


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=9, color=MUTED)


def configure_section(section, *, first_page=False) -> None:
    section.page_width = Inches(PRESET["page_width"])
    section.page_height = Inches(PRESET["page_height"])
    section.top_margin = Inches(PRESET["margin"])
    section.bottom_margin = Inches(PRESET["margin"])
    section.left_margin = Inches(PRESET["margin"])
    section.right_margin = Inches(PRESET["margin"])
    section.header_distance = Inches(PRESET["header_distance"])
    section.footer_distance = Inches(PRESET["footer_distance"])
    section.different_first_page_header_footer = first_page


def configure_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = PRESET["body_font"]
    normal._element.rPr.rFonts.set(qn("w:ascii"), PRESET["body_font"])
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), PRESET["body_font"])
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), PRESET["east_asia_font"])
    normal.font.size = Pt(PRESET["body_size"])
    normal.font.color.rgb = rgb(INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(PRESET["body_after"])
    normal.paragraph_format.line_spacing = PRESET["body_line"]

    for style_name, size, before, after, color in (
        ("Heading 1", PRESET["h1_size"], PRESET["h1_before"], PRESET["h1_after"], BLUE),
        ("Heading 2", PRESET["h2_size"], PRESET["h2_before"], PRESET["h2_after"], BLUE),
        ("Heading 3", PRESET["h3_size"], PRESET["h3_before"], PRESET["h3_after"], DEEP_BLUE),
    ):
        style = styles[style_name]
        style.font.name = PRESET["body_font"]
        style._element.rPr.rFonts.set(qn("w:ascii"), PRESET["body_font"])
        style._element.rPr.rFonts.set(qn("w:hAnsi"), PRESET["body_font"])
        style._element.rPr.rFonts.set(qn("w:eastAsia"), PRESET["east_asia_font"])
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = rgb(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    caption = styles["Caption"]
    caption.font.name = PRESET["body_font"]
    caption._element.rPr.rFonts.set(qn("w:ascii"), PRESET["body_font"])
    caption._element.rPr.rFonts.set(qn("w:hAnsi"), PRESET["body_font"])
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), PRESET["east_asia_font"])
    caption.font.size = Pt(9)
    caption.font.italic = False
    caption.font.color.rgb = rgb(MUTED)
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.keep_with_next = True

    for style_name in ("List Bullet", "List Number"):
        style = styles[style_name]
        style.font.name = PRESET["body_font"]
        style._element.rPr.rFonts.set(qn("w:eastAsia"), PRESET["east_asia_font"])
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25


def add_running_header_footer(section) -> None:
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run("智能心盾  |  前端技术实现细节")
    set_run_font(run, size=9, bold=True, color=MUTED)
    set_paragraph_border(p, color=LIGHT_GRAY, size=6, space=3)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(3)
    fr = fp.add_run("西北工业大学 · 灵犀智研团队    |    ")
    set_run_font(fr, size=8.5, color=MUTED)
    add_page_field(fp)


def add_cover(doc: Document) -> None:
    section = doc.sections[0]
    configure_section(section, first_page=True)

    logo_path = PROJECT_ROOT / "assets" / "intelligent-heart-shield-logo.png"
    p_logo = doc.add_paragraph()
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_logo.paragraph_format.space_before = Pt(40)
    p_logo.paragraph_format.space_after = Pt(20)
    cover_logo = p_logo.add_run().add_picture(str(logo_path), width=Inches(0.9))
    add_alt_text(cover_logo, "智能心盾标志", "智能心盾心脏健康辅助分析系统标志")

    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker.paragraph_format.space_after = Pt(14)
    run = kicker.add_run("CLINICAL DECISION SUPPORT · FRONTEND REPORT")
    set_run_font(run, size=10, bold=True, color=BLUE)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(10)
    tr = title.add_run("智能心盾前端技术实现细节")
    set_run_font(tr, size=28, bold=True, color=NAVY)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(24)
    sr = subtitle.add_run("心脏破裂风险辅助分析系统 · 界面、交互与数据绑定说明")
    set_run_font(sr, size=14, color=DEEP_BLUE)

    rule = doc.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rule.paragraph_format.left_indent = Inches(1.05)
    rule.paragraph_format.right_indent = Inches(1.05)
    rule.paragraph_format.space_after = Pt(30)
    set_paragraph_border(rule, color=BLUE, size=14, space=0)

    lead = doc.add_paragraph()
    lead.alignment = WD_ALIGN_PARAGRAPH.CENTER
    lead.paragraph_format.left_indent = Inches(0.55)
    lead.paragraph_format.right_indent = Inches(0.55)
    lead.paragraph_format.space_after = Pt(56)
    lr = lead.add_run(
        "结合当前项目代码与 18 张系统界面截图，对前端模块组织、页面交互、状态管理、"
        "数据展示、Agent 问答和风险结果呈现方式进行说明。"
    )
    set_run_font(lr, size=11.5, color=MUTED)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(4)
    mr = meta.add_run("技术实现说明")
    set_run_font(mr, size=11, bold=True, color=NAVY)
    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_p.add_run("2026 年 9 月")
    set_run_font(date_run, size=10.5, color=MUTED)

    doc.add_page_break()


def add_code_block(doc: Document, title: str, code: str) -> None:
    label = doc.add_paragraph()
    label.paragraph_format.space_before = Pt(7)
    label.paragraph_format.space_after = Pt(3)
    label.paragraph_format.keep_with_next = True
    run = label.add_run(f"关键代码：{title}")
    set_run_font(run, size=9.5, bold=True, color=DEEP_BLUE)

    block = doc.add_paragraph()
    block.paragraph_format.left_indent = Inches(0.12)
    block.paragraph_format.right_indent = Inches(0.12)
    block.paragraph_format.space_before = Pt(0)
    block.paragraph_format.space_after = Pt(7)
    block.paragraph_format.line_spacing = 1.0
    block.paragraph_format.keep_together = True
    set_paragraph_shading(block, "F2F6F9")
    set_paragraph_border(block, side="left", color=BLUE, size=16, space=7)
    code_run = block.add_run(code)
    set_run_font(code_run, size=8.2, color=INK, font="Consolas")


def add_architecture_overview(doc: Document) -> None:
    h = doc.add_heading("1 基于 Streamlit 的模块化多页面系统架构", level=1)
    set_paragraph_border(h, color=BLUE, size=10, space=5)

    p = doc.add_paragraph()
    p.add_run("整体思路。")
    set_run_font(p.runs[0], bold=True, color=NAVY)
    p.add_run(
        "系统以 Streamlit 为页面运行框架，按入口路由、业务视图、公共组件、数据服务和 Agent/模型调用五层组织。"
        "页面通过服务层取得规范化的患者、就诊和预测数据。"
    )
    for run in p.runs[1:]:
        set_run_font(run)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    mark_table_header(table.rows[0])
    headers = ["层次", "主要模块", "职责"]
    for idx, text in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.text = text
        set_cell_shading(cell, LIGHT_BLUE)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for run in cell.paragraphs[0].runs:
            set_run_font(run, size=10, bold=True, color=NAVY)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    rows = [
        ("入口与路由", "app.py、sidebar.py", "页面配置、状态初始化与主页面分发"),
        ("业务视图", "home.py、dashboard.py、clinical_agent.py、patient_workspace.py、about.py", "组织页面布局、控件与业务交互"),
        ("公共组件", "cards.py、timeline.py、records.py、react_chat.py", "复用导航、卡片、时间轴和 Agent 过程样式"),
        ("数据服务", "workbook_data.py、prediction_api.py、chat_store.py", "数据缓存、就诊关联、结果归一化与聊天持久化"),
        ("Agent 与模型", "react_agent.py、tools.py、risk_model.py", "ReAct 调度、就诊范围约束与风险模型调用"),
    ]
    for layer, modules, duty in rows:
        cells = table.add_row().cells
        for idx, text in enumerate((layer, modules, duty)):
            cells[idx].text = text
            cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if idx == 0:
                set_cell_shading(cells[idx], VERY_LIGHT_BLUE)
            for paragraph in cells[idx].paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    set_run_font(run, size=8.4, bold=(idx == 0), color=NAVY if idx == 0 else INK)
    set_table_geometry(table, [1450, 3650, 4260])

    caption = doc.add_paragraph("表 1  前端模块分层与职责", style="Caption")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER

    h2 = doc.add_heading("1.1 状态、数据与页面联动", level=2)
    p2 = doc.add_paragraph()
    p2.add_run("页面状态：")
    set_run_font(p2.runs[0], bold=True, color=NAVY)
    p2.add_run(
        "Session State 保存页面及就诊选择；跨页面跳转通过 pending_page 和 pending_encounter_key 传递目标页面及就诊键。"
    )
    p2.add_run(" 持久化状态：")
    set_run_font(p2.runs[-1], bold=True, color=NAVY)
    p2.add_run(
        "辅助诊断问答写入 SQLite，服务重启后可恢复；界面连续展示消息，模型上下文仍按就诊隔离。"
    )
    for run in p2.runs:
        if run.font.size is None:
            set_run_font(run)

    p3 = doc.add_paragraph()
    p3.add_run("数据更新：")
    set_run_font(p3.runs[0], bold=True, color=NAVY)
    p3.add_run(
        "工作簿以路径、修改时间和大小作为缓存签名，文件更新后自动重新读取；prediction_api 将模型结果统一转换为页面字段。"
    )
    for run in p3.runs[1:]:
        set_run_font(run)

    note = doc.add_paragraph()
    note.paragraph_format.left_indent = Inches(0.15)
    note.paragraph_format.right_indent = Inches(0.15)
    note.paragraph_format.space_before = Pt(8)
    note.paragraph_format.space_after = Pt(8)
    note.paragraph_format.keep_together = True
    set_paragraph_shading(note, VERY_LIGHT_BLUE)
    set_paragraph_border(note, side="left", color=BLUE, size=20, space=8)
    nr = note.add_run("实现边界  ")
    set_run_font(nr, bold=True, color=BLUE)
    nr2 = note.add_run(
        "前端只展示工作簿和模型结果中能够确认的内容；缺失字段、模型不可用和时间无法对齐时均保留明确提示。"
    )
    set_run_font(nr2, color=INK)

    add_code_block(
        doc,
        "统一入口、状态初始化与页面分发",
        "st.session_state.setdefault(\"active_page\", \"首页\")\n"
        "st.session_state.setdefault(\"selected_encounter_key\", None)\n\n"
        "page = render_navigation()\n"
        "ROUTES = {\"首页\": home.render, \"急诊概览\": dashboard.render,\n"
        "          \"辅助诊断\": clinical_agent.render, \"病情详情\": patient_workspace.render}\n"
        "ROUTES.get(page, home.render)()",
    )


def resolve_figure_path(filename: str) -> Path:
    for source_dir in SOURCE_DIRS:
        candidate = source_dir / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"未找到截图：{filename}")

def add_alt_text(inline_shape, title: str, description: str) -> None:
    doc_pr = inline_shape._inline.docPr
    doc_pr.set("title", title)
    doc_pr.set("descr", description)


def add_figure(doc: Document, figure: dict, number: int) -> None:
    if figure["section"]:
        h1 = doc.add_heading(figure["section"], level=1)
        h1.paragraph_format.page_break_before = True
        set_paragraph_border(h1, color=BLUE, size=10, space=5)
        heading = doc.add_heading(figure["title"], level=2)
    else:
        heading = doc.add_heading(figure["title"], level=2)
        heading.paragraph_format.page_break_before = True
    image_path = resolve_figure_path(figure["file"])
    with Image.open(image_path) as image:
        width_px, height_px = image.size

    max_width = 6.35
    max_height = figure["max_height"]
    ratio = width_px / height_px
    width = min(max_width, max_height * ratio)
    height = width / ratio
    if height > max_height:
        height = max_height
        width = height * ratio

    image_p = doc.add_paragraph()
    image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_p.paragraph_format.space_before = Pt(2)
    image_p.paragraph_format.space_after = Pt(0)
    image_p.paragraph_format.keep_with_next = True
    image_p.paragraph_format.keep_together = True
    shape = image_p.add_run().add_picture(str(image_path), width=Inches(width), height=Inches(height))
    add_alt_text(shape, figure["caption"], f"智能心盾系统截图：{figure['title']}")

    caption = doc.add_paragraph(figure["caption"], style="Caption")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.keep_with_next = True

    desc = doc.add_paragraph()
    desc.paragraph_format.keep_together = True
    desc.paragraph_format.space_after = Pt(3)
    desc.paragraph_format.line_spacing = 1.15
    lead = desc.add_run("技术实现：")
    set_run_font(lead, bold=True, color=DEEP_BLUE)
    body = desc.add_run(figure["description"] + figure.get("details", ""))
    set_run_font(body)

    if figure.get("code"):
        add_code_block(doc, figure.get("code_title", "页面实现"), figure["code"])

def add_summary(doc: Document) -> None:
    h = doc.add_heading("7 前端实现总结", level=1)
    h.paragraph_format.page_break_before = True
    set_paragraph_border(h, color=BLUE, size=10, space=5)

    intro = doc.add_paragraph(
        "智能心盾前端的技术实现围绕“单次就诊边界、真实数据展示、模型结果复核和连续交互”展开。"
        "Streamlit 提供统一的 Python 页面运行环境，组件层保证视觉与交互一致，服务层负责数据质量和字段口径，"
        "Agent 与预测模型则以独立模块接入。"
    )
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    items = [
        "统一入口与模块化页面：五个主页面由同一导航和路由状态管理，公共卡片、筛选器、时间轴和页脚组件重复使用。",
        "可靠的就诊关联：患者编号与就诊编号共同构成 encounter_key，筛选、页面跳转、聊天历史和模型上下文均以此为边界。",
        "数据驱动的可视化：工作簿和模型结果分别加载、缓存和规范化，统计卡片、图表、表格及详情页共享统一数据口径。",
        "可追溯的智能问答：ReAct Agent 在当前就诊范围内调用临床资料和风险预测工具，页面同步展示关键过程并持久化问答记录。",
        "明确的应用边界：缺失数据、模型调用失败和无法可靠配对的信息均如实提示，前端不生成工作簿中不存在的患者事实。",
    ]
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.05
        for run in p.runs:
            set_run_font(run, size=9.5)

    h2 = doc.add_heading("7.1 主要代码文件对应关系", level=2)
    mapping = doc.add_table(rows=1, cols=2)
    mapping.style = "Table Grid"
    mapping.rows[0].cells[0].text = "功能"
    mapping.rows[0].cells[1].text = "主要文件"
    for cell in mapping.rows[0].cells:
        set_cell_shading(cell, LIGHT_BLUE)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cell.paragraphs[0].runs:
            set_run_font(run, bold=True, color=NAVY)
    mappings = [
        ("应用入口与路由", "app.py、components/sidebar.py"),
        ("首页与公共样式", "views/home.py、components/styles.py、components/header.py、components/footer.py"),
        ("急诊概览", "views/dashboard.py、components/charts.py、services/prediction_api.py"),
        ("辅助诊断", "views/clinical_agent.py、components/react_chat.py、services/chat_store.py"),
        ("患者详情", "views/patient_workspace.py、components/timeline.py、components/records.py"),
        ("患者数据处理", "services/workbook_data.py、services/clinical_context.py"),
        ("Agent 与模型", "agent/react_agent.py、agent/tools.py、agent/risk_model.py、agent/config.py"),
    ]
    for feature, files in mappings:
        cells = mapping.add_row().cells
        cells[0].text = feature
        cells[1].text = files
        cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cells[0], VERY_LIGHT_BLUE)
        for idx, cell in enumerate(cells):
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    set_run_font(run, size=8.6, bold=(idx == 0), color=NAVY if idx == 0 else INK)
    set_table_geometry(mapping, [2200, 7160])
    cap = doc.add_paragraph("表 2  前端功能与代码文件对应关系", style="Caption")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER


def build_document() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    configure_styles(doc)
    add_cover(doc)

    for index, section in enumerate(doc.sections):
        configure_section(section, first_page=(index == 0))
    add_running_header_footer(doc.sections[0])

    add_architecture_overview(doc)
    for number, figure in enumerate(FIGURES, start=1):
        add_figure(doc, figure, number)

    properties = doc.core_properties
    properties.title = "智能心盾前端技术实现细节"
    properties.subject = "心脏破裂风险辅助分析系统前端技术实现说明"
    properties.author = "智能心盾项目组"
    properties.keywords = "Streamlit, 临床辅助分析, ReAct Agent, 心脏破裂风险, 可视化交互"
    properties.comments = "根据当前项目代码和用户提供的系统截图生成"

    doc.save(OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    print(build_document())
