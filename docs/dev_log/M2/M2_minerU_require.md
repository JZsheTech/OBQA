
## 🧩 MinerU 解析与处理要求总结

### 1. 数据来源与异常处理

* **输入参考文件**
docs/dev_log/M2/ref_data_format

* **错误处理**：`parse_minerU` 接口出错时 **直接抛出异常**，不做静默处理。

---

### 2. 标题（Header）识别逻辑

* **判定条件：**

  * 若 `type == "text"` 且含 `"text_level"` → 一定是标题；
  * 若无 `"text_level"` → 不是标题（普通正文）。
* **层级判断：**

  * 当 `text_level` 不准确时，需启发式识别：

    * 若标题文本包含形如 `1.1.1` 的阿拉伯数字序号 → 推断为分级标题；
    * 若无数字结构或者出现标题跳级的情况(自动推断层级时出错) → 退化为单层标题（整篇只有一个层级）。
* **假设前提**：解析对象为 **学术论文类文档**。

---

### 3. 图片（Image）解析逻辑

* **引用形式：**

  ```json
  "img_path": "images/<hash>.jpg"
  ```
* **匹配规则：**

  * `parse_minerU` 返回中含 `"images"` 字典：

    ```json
    "images": {
        "<hash>.jpg": "data:image/jpeg;base64,<encoded>"
    }
    ```
  * 处理方式：将 `"images/"` 前缀去掉，用文件名 `<hash>.jpg` 作为键，在 `images` 字典中查找对应的 Base64 编码。
    * **编码格式**：
    可以从解析结果中获得`"data:image/...;base64,..."` 这一整段字符串，在将图片内容存入向量数据库前，需要去除 Base64 字符串中的前缀标识：
    ```
    data:image/jpeg;base64,
    ```
    仅保留逗号后的纯 Base64 数据部分，以便统一存储与后续解码。

### 坐标
`bbox` 原始坐标是像素坐标，直接使用minerU解析出的结果即可。

### 4. 公式（Equation）处理逻辑

* 无需区分 `latex` 或 `mathml`，**原样嵌入为字符串** 存储。

---

## 🧱 元素统一化拼装规范（Text / Image / Table / Equation）

### 1. Prefix 格式统一规范

* 结构：

  ```
  prefix = [level_nav] [header_name]
  ```
* 细则：

  * `level_nav` 与 `header_name` **各自带方括号包裹**；
  * `level_nav` 各层级间用 `>` 分隔；
  * 示例：

    ```
    [1 introduction > 1.1 GNN > 1.1.1 message passing] [1.1.1 message passing]
    ```

---

### 2. 各类型元素的处理要求

| 类型           | 内容规范                                                |
| ------------ | --------------------------------------------------- |
| **text**     | 不做段落级清洗，保持原始文本。                                     |
| **header**   | 使用轻量的tf_idf提取 `section_summary`，默认最多 5 句，不足则全取。                |
| **table**    | 保留原始 HTML 存入 `text` 字段。若同时含文本与表格图片 → 采用 **图文融合嵌入**。 |
| **equation** | 若既有 LaTeX 文本又有方程图片 → 采用 **图文融合嵌入**。                 |
| **image**    | 若无 caption，用占位符 `[figure]` 替代。                      |
