---
name: tencent-docs-mcp-usage
description: 腾讯文档 MCP（个人版）接口的正确用法与实测踩坑。当需要用 API 创建/写入腾讯文档时使用——智能表格（smartsheet）和在线表格（sheet）都覆盖。包含：智能表格字段与记录写入的真实格式（与 MCP schema 描述不一致）、文本/单选字段写不进去的确认结论、公式字段 formula_model 拼接语法、在线表格 set_range_value 与 value_base64 绕 WAF、命令行参数超长（WinError 206）的 import 调用方案、票据来源、批量写公式、异步重算、clear_range_* 越界（code 608698）与误删公式、公式拼接括号错导致 4 参数 IF 静默失败（Excel 中「文本>=数字」恒为真）、写完公式的全表扫描验收、分块长表的参数常量引用法、read_only=True 读不到表头。
agent_created: true
---

# 腾讯文档 MCP 正确用法与踩坑

## 何时用

需要用 API 操作腾讯文档（个人版 docs.qq.com）的**智能表格**或**在线表格**时。
调用入口是 `tencent-docs-plugin` 里的 `tencentdocs.py`。

---

## 一、载体选型：先看这个

| 需求 | 选谁 | 原因 |
|---|---|---|
| 要写**文本**（款号/名称/判定结论/备注） | **在线表格 sheet** | 智能表格的文本字段**写不进去**（见下） |
| 要写公式 | 两者都可 | 智能表格用 `formula_model`；在线表格用标准 Excel 公式 |
| 要**原生自动化推送** | 智能表格（但受限） | 支持定时/记录变更触发 + 发消息，**创建后默认关闭**，需手动开 |
| 要条件格式/染色 | **在线表格** | 智能表格无对应 API；在线表格可用 `set_cell_style` 动态染色 |
| 要大量行 × 多列 | **在线表格** | `set_range_value` 支持批量，几千格一次 |

**一句话**：只要表里需要写文本，直接用**在线表格**。智能表格只适合"纯数字 + 公式"的场景。

---

## 二、调用方式（两种，**优先第二种**）

### 方式 A：命令行（简单入参可用）
```bash
python3 tencentdocs.py tdoc_call <service> <tool> '<json_args>'
```
service ∈ `tencent-docs`（通用/管理/smartsheet）、`sheet-mcp`（在线表格）、`doc-mcp`、`slide-mcp`。

### 方式 B：import 直接调用（**推荐**，无参数长度限制）
命令行在写入大量单元格或长公式时会撞 **`WinError 206 文件名或扩展名太长`**。
改为以模块方式加载：

```python
import importlib.util, json

SKILL_DIR = r'...\plugins\cache\workbuddy-builtin\tencent-docs-plugin\<ver>\skills\tencent-docs'
spec = importlib.util.spec_from_file_location('_tdoc', SKILL_DIR + r'\tencentdocs.py')
td = importlib.util.module_from_spec(spec)
spec.loader.exec_module(td)

def call(service, tool, args, timeout=300):
    rsp, err = td.call_tool(service, tool, args, timeout=timeout)   # 返回 (dict, err)
    if err:
        raise RuntimeError('TDOC_ERR[%s]: %s' % (tool, err))
    if rsp.get('error'):
        raise RuntimeError('JSONRPC_ERR[%s]: %s' % (tool, rsp['error']))
    res = rsp.get('result') or {}
    sc = res.get('structuredContent')
    if sc is not None:
        return sc
    txt = (res.get('content') or [{}])[0].get('text', '')
    try:
        return json.loads(txt)
    except Exception:
        return {'raw': txt}
```

**票据来源**：宿主网关注入，通过 `~/.codebuddy/mcp.json` 的 gateway 配置请求
`{gateway_url}/internal/tencent-docs/tokens`。**不在环境变量里**，所以别自己去读 `TDOC_*_ACCESS_TOKEN`。

**插件目录探测**（版本号会变，别硬编码）：
```python
base = r'C:\Users\<user>\.workbuddy\plugins\cache\workbuddy-builtin\tencent-docs-plugin'
ver = sorted(os.listdir(base))[-1]
SKILL_DIR = os.path.join(base, ver, 'skills', 'tencent-docs')
```

---

## 三、智能表格（smartsheet）

### 3.1 记录写入：**不要照 schema 写**

MCP schema 描述的是 `records: [{field_values: [{field, text_value, number_value...}]}]`，
但**实测这是错的**，按它写只会创建空记录、值全丢且不报错。

**真实可用的规律**：

| 写法 | 结果 |
|---|---|
| `{field_values: [{field:'标题', text_value:[{'text':'x','type':'text'}]}]}` | ❌ 整条被静默丢弃（total 不变） |
| `{field_values: [{field:'字段ID', text_value:[...]}]}`（用 field_id） | ❌ 同上 |
| `{field_values: [{field:'标题', text_value:'纯串'}]}` | ❌ 同上 |
| `{field_values: [{field:'标题', number_value: 111}]}` | ✅ **成功**（数字可写、能读回） |
| `{field_values: [{field:'标题', string_value: 'x'}]}` | ⚠️ 调用被接受，但文本字段读回为空 |
| `{'标题': [...], '数字': 1}`（顶层字段名做 key） | ⚠️ 记录被创建，但值全空 |

### 3.2 确认结论：文本 / 单选写不进去

`text_value` 试过 6 种变体（裸列表 `['A']`、`[{'text':'B'}]`、`[{'value':'C','type':'text'}]`、
`[{'text':'x','type':'text'}]`、`string_value`、混写）——**全部无法把值写进文本字段**。
`option_value`（单选）同样被拒。

**能可靠写入的只有**：`number_value`（数字/货币/百分比/进度）、`bool_value`（勾选）、
`string_value`（日期/电话/邮箱类型）。

→ **需要文本就用公式字段生成，或改用在线表格。**

### 3.3 公式字段：可用，语法是「顺序拼接」

```python
model = [
    {'type': 1, 'text': 'IF('},          # type1 = 文本片段
    {'type': 2, 'field_id': 'fwr9q0'},   # type2 = 本表列引用
    {'type': 1, 'text': '>5,"大","小")'},
]
call('tencent-docs', 'smartsheet.add_fields', {
    'file_id': fid, 'sheet_id': sid,
    'fields': [{'field_title': '判定', 'field_type': 'formula',
                'property_formula': {'formula_model': model}}]})
```
- type 枚举：1-文本片段，2-列引用，5-`列`，6-`表.列`，9-关联列引用
- 跨表引用要同时给 `table_id`
- 已验证可用：`IF` / 嵌套 `IF` / `AND` / `OR` / `ROUND` / `SUM` / `&` 拼接；除零返回"计算错误"
- `property_formula` 可带 `formatter`（必须同时给 `type` 和对应 `property_xxx`）

### 3.4 读取记录

```python
call('tencent-docs', 'smartsheet.list_records', {
    'file_id': fid, 'sheet_id': sid,
    'field_titles': ['字段A', '字段B'],      # 不传则只返回公式等计算列！
    'include_computed_values': True,          # 公式结果在 computed_value.text
    'limit': 100})
```

### 3.5 其他

- 建文档：`manage.create_file` `{title, file_type:'smartsheet'}`
- 建子表：`smartsheet.add_table` / `create_table_from_plan`（一张表一次调用）
- 自动化：`smartsheet.create_automation_from_plan`（支持 新增记录/修改记录/到达记录时间 触发；
  动作支持 查找记录/新增记录/修改记录/发送消息；**不支持 Webhook/HTTP/脚本**；**创建后默认关闭**）

---

## 四、在线表格（service = `sheet-mcp`）

### 4.1 建文件与子表
```python
call('tencent-docs', 'manage.create_file', {'title': 'xx', 'file_type': 'sheet'})
call('sheet-mcp', 'get_sheet_info', {'file_id': fid})           # 拿 sheet_id
call('sheet-mcp', 'rename_sheet', {'file_id': fid, 'sheet_id': sid, 'name': '每日数据'})
call('sheet-mcp', 'add_sheet', {'file_id': fid, 'name': '参数表', 'append_index': True})
call('sheet-mcp', 'move_sheet', {'file_id': fid, 'src_index': 1, 'dest_index': 0})
call('sheet-mcp', 'insert_dimension', {'file_id': fid, 'sheet_id': sid,
      'dimension_type': 'col', 'index': 26, 'count': 5})         # 默认只有 26 列，不够要补
```

### 4.2 写值 `set_range_value`
```python
values = [
  {'row': r, 'col': c, 'value_type': 'STRING',  'string_value': '文本'},
  {'row': r, 'col': c, 'value_type': 'NUMBER',  'number_value': 1.23},
  {'row': r, 'col': c, 'value_type': 'FORMULA', 'formula': '=IF(A1=0,"",B1/A1)'},
  {'row': r, 'col': c, 'value_type': 'BOOL',    'bool_value': True},
]
call('sheet-mcp', 'set_range_value', {'file_id': fid, 'sheet_id': sid, 'values': values})
```
- row/col 均 **0-based**
- 建议单次 ≤ 300~400 格，请求体 < 1MB

### 4.3 ⚠️ 公式会被 WAF 拦 —— 改用 base64
明文公式（尤其长公式、含 emoji/中文）会触发 **HTTP 501 / `501page` / waf-captcha**。
解决：`value_type='FORMULA'` + **只用 `value_base64`**（公式原文的 UTF-8 Base64，不带 data URI），
不要同时传 `formula`。

```python
import base64
{'row': r, 'col': c, 'value_type': 'FORMULA',
 'value_base64': base64.b64encode(fx.encode('utf-8')).decode()}
```

试算公式（不写盘、用于 dry-run 验证）也用 base64：
```python
call('sheet-mcp', 'calculate_single_formula', {
    'file_id': fid, 'sheet_id': sid, 'anchor_row': 0, 'anchor_col': 0,
    'formula_base64': base64.b64encode('=IF(B4="","",1/B4)'.encode()).decode()})
```
批量试算：`calculate_formulas`（一次最多 100 条）。

### 4.4 读值
```python
call('sheet-mcp', 'get_cell_data', {
    'file_id': fid, 'sheet_id': sid,
    'start_row': 0, 'start_col': 0, 'end_row': 159, 'end_col': 28,
    'return_csv': True})            # csv_data 最省事
```
- 单次范围 ≤ 20000 格（`(end_row-start_row+1)×(end_col-start_col+1)`）
- `include_formula=True` 可同时取公式源串，但**仅 `return_csv=False` 时生效**；
  实测 `return_csv=False + include_formula=True` 有时返回空 `cells`，取数优先用 CSV

### 4.5 样式与尺寸
```python
call('sheet-mcp', 'set_cell_style', {
    'file_id': fid, 'sheet_id': sid, 'start_row': a, 'end_row': b,
    'start_col': c, 'end_col': d,
    'bg_color': 'FFFFC7CE',          # ARGB
    'font_color': 'FF000000', 'bold': True, 'font_size': 14,
    'number_format_pattern': '0.00', # Excel 格式码：@ 文本 / #,##0 / 0% / 0.00 / yyyy-mm-dd
    'horizontal_align': 'center', 'wrap_text': True})

call('sheet-mcp', 'set_dimension_size', {     # 注意是 dimensions 数组（批量）
    'file_id': fid, 'sheet_id': sid,
    'dimensions': [{'dimension_type': 'col', 'index': 0, 'size': 100},
                   {'dimension_type': 'row', 'index': 0, 'size': 34}]})

call('sheet-mcp', 'set_freeze', {'file_id': fid, 'sheet_id': sid,
      'row_count': 1, 'col_count': 2})
```
**没有条件格式 API** → 需要"按值染色"就用脚本算好后调 `set_cell_style` 写静态背景色。

### 4.6 清空（⚠️ 两个坑）

**坑 1：会连公式一起删。**
`clear_range_cells` / `clear_range_all` 清的是**整个矩形区域**，包括里面的公式列。
如果清空范围跨过了公式列，公式会被删掉。**清空要绕开公式列、分段落清。**
（真实事故：冒烟测试清 3–15 列，把第 10 列的公式一起删了，读回该列为空，误判成"公式写不进去"。）

**坑 2：清超出边界会直接报错。**
```python
call('sheet-mcp', 'clear_range_all', {..., 'end_row': 400, 'end_col': 40})
# -> code 608698, operation out of sheet boundary
```
新表默认只有 **200 行 × 31 列**（`get_sheet_info` 返回的 `row_count` / `col_count` 是硬边界）。
**正确顺序**：
```python
info = call('sheet-mcp', 'get_sheet_info', {'file_id': fid})
sh = [s for s in info['sheets'] if s['sheet_id'] == sid][0]
# 1) 先扩到目标尺寸
if sh['col_count'] < need_cols:
    call('sheet-mcp', 'insert_dimension', {'file_id': fid, 'sheet_id': sid,
         'dimension_type': 'col', 'index': sh['col_count'], 'count': need_cols - sh['col_count']})
if sh['row_count'] < need_rows:
    call('sheet-mcp', 'insert_dimension', {'file_id': fid, 'sheet_id': sid,
         'dimension_type': 'row', 'index': sh['row_count'], 'count': need_rows - sh['row_count']})
# 2) 再清（range 必须落在新尺寸内）
call('sheet-mcp', 'clear_range_all', {'file_id': fid, 'sheet_id': sid,
     'start_row': 0, 'start_col': 0, 'end_row': need_rows - 1, 'end_col': need_cols - 1})
```
`insert_dimension` 的 `index` 传当前 `row_count`/`col_count` 表示**追加**在末尾。

---

## 五、踩坑速查

| 现象 | 原因 / 解法 |
|---|---|
| `WinError 206 文件名或扩展名太长` | 命令行传参太长 → 改用 import 方式调 `call_tool` |
| `HTTP 501 / 501page / waf-captcha` | 明文公式被 WAF 拦 → 改用 `value_base64` |
| 写数后立刻读，公式列为空 | **公式重算是异步的**，等 3 秒左右再读；判定逻辑别依赖"写完立刻读" |
| `smartsheet.add_records` 返回 `records: []` 且 total 不变 | 字段值格式错，整条被丢 → 只有 `number_value` 等标量能写 |
| 记录建了但值全空 | 用了 top-level 字段名做 key → 只有 `number_value` 能落地 |
| `list_records` 只返回公式列 | 没传 `field_titles` |
| 子表引用报语法错 | 中文子表名跨表引用写 `参数表!$B$5` |
| 公式里想拼动态文字 | 不能用 `"...参数表!$B$8"`，要写成 `"目标÷"&参数表!$B$8` |
| 补列后列宽/样式没跟进 | 先 `insert_dimension` 再设样式 |
| `set_dimension_size` 报 -32603 | 参数是 `dimensions` 数组，不是单个 `index`/`size` |
| 长数字变科学计数法 | 写入用 `value_type='STRING'`；**事后改 `number_format_pattern='@'` 无效**，必须写入时就是字符串 |
| `clear_range_*` 报 `code 608698 out of sheet boundary` | 范围超了新表默认的 200×31 → **先 `insert_dimension` 扩容再清**（见 4.6） |
| 公式列结果**莫名其妙漂移**（如目标值被逐行除 1.3 直到 0.02） | **括号数量错 → 生成 4 参数 IF → 公式解析失败、单元格退化成文本**。而 Excel 里 `文本 >= 数字` **恒为真**，下游 IF 走了不该走的分支。见 5.1 |
| 写完公式后 `get_cell_data` 某列返回的是公式原文（以 `=` 开头） | 同上，该公式解析失败了。**必须全表扫描一遍** |

### 5.1 公式拼接的两个硬教训

**教训 1：用字符串拼公式时，括号极易少一个，而且失败是静默的。**

错误示范（少一个右括号，`core` 结尾故意留了半个 IF）：
```python
core = 'IF(X{r}="",0,IF(X{r}>=AB{r},'.format(r=x)      # 左括号 2 个
f = '=IF(A{p}<>A{r},' + core + '1,0),' + \             # '1,0),' 只闭合 1 个
    'IF(X{r}="",0,IF(X{r}>=AB{r},AH{p}+1,0)))'.format(...)
```
结果中间那个 IF 吃到 **4 个参数** → 解析失败。

正确写法：**让 `then` 分支单独成串，别把半个 IF 当模板**。
```python
then = '1' if first else 'AH{p}+1'.format(p=prev)
f = ('=IF(OR(X{r}="",F{r}=0),0,IF(X{r}>=AB{r},'
     '{then},0))').format(r=x, then=then)
```

**教训 2：写完公式必须做全表扫描验收。**
```python
rows = read_csv(...)                      # 全表读回
fail = [(i+2, j, v) for i, row in enumerate(rows)
        for j, v in enumerate(row) if str(v).strip().startswith('=')]
assert not fail, fail[:20]                # 有任何以 = 开头的单元格 = 公式解析失败
```
另外对"应当恒定"的列（如初始目标值）做**异常漂移扫描**，比只看几行靠谱得多。

### 5.2 读 Excel 源文件：别用 `read_only=True` 读表头

`openpyxl.load_workbook(p, read_only=True)` 读某些导出文件时 `max_column` / `iter_rows` 只返回 **1 列**，
表头全丢。读表头请用普通模式 `load_workbook(p, data_only=True)`；
只在**逐行流式扫描大文件**时才用 `read_only=True`（并自己按固定列号取，不依赖表头）。

---

## 六、可靠工作流（推荐顺序）

1. **先 dry-run 公式**：`calculate_single_formula` 验证函数/引用语法，再批量写
2. **先建表结构**（子表 + 表头 + 补列），再灌数据
3. **公式最后写，且走 base64**
4. **写完等 3~10 秒再读回校验**，并且：
   - 全表扫描"以 `=` 开头"的单元格 → 有就是解析失败
   - 对应当恒定的列做异常漂移扫描
5. 大表分批（每批 120~350 格），失败自动重试 2 次
6. 染色/数字格式等样式放最后，一次性批量设置
7. **重代码前先做备份**：导出脚本 + 在线表三个子表的 CSV 快照，出错可一键回滚
8. 有判定逻辑的表，**用模拟数据做一次冒烟测试**（灌数 → 读回判定 → 清空还原），
   再交给定时任务跑。只靠"公式不报错"判断不了规则对不对。
9. 建了多块（按分组分块）的长表时，**参数引用用块内常量列字母**（如 L1→`$B$`、L2→`$C$`），
   不要写成 `IF(A=款号, $B$5, $C$5)` 这类逐行判断 —— 块内常量既简单又不会错位，
   并且新增一块时既有块完全不受影响（这就是"留扩容位"的做法）。
