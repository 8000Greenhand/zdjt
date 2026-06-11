# 不用 Codex 也能调整流程

这个项目刻意做成“能打开、能改配置、能分步跑”的形式，不依赖 Codex 全程操作。

---

## 一、目前先固定的原则

第一版只解决截图核心流程：

```text
已登录 AdsPower + 已打开 Temu 商品详情页
→ 识别标题
→ 找主图候选区域
→ 截图
→ 用标题命名
→ 保存本地
→ 写入本地 Excel
```

暂时不做：

```text
查重
腾讯文档登记
标题优化
全自动翻页
自动处理验证码
```

---

## 二、你不用改代码也能调整的东西

打开 `config.json`，可以改这些：

```json
{
  "adspower_api": "http://local.adspower.com:50325",
  "profile_id": "",
  "output_root": "D:/Temu截图/截图结果",
  "registry_path": "D:/Temu截图/登记/截图进度.xlsx",
  "max_filename_length": 120,
  "min_image_width": 250,
  "min_image_height": 250,
  "prefer_left_side_image": true
}
```

### profile_id

AdsPower 环境 ID。程序里点“列出环境”可以看到。

### output_root

截图保存根目录。

### registry_path

本地登记表位置。

### min_image_width / min_image_height

候选截图区域最小尺寸。

如果程序找到了很多小图，把这两个值调大，例如：

```json
"min_image_width": 350,
"min_image_height": 350
```

如果程序找不到图，把它们调小，例如：

```json
"min_image_width": 180,
"min_image_height": 180
```

### prefer_left_side_image

商品详情页主图一般在左侧，所以默认优先左侧大图。

如果 Temu 页面改版，主图不在左边，可以改成：

```json
"prefer_left_side_image": false
```

---

## 三、最常见问题

### 1. 点“连接 AdsPower”失败

检查：

```text
AdsPower 是否已经打开
AdsPower Local API 是否开启
config.json 里的 profile_id 是否正确
端口是否还是 50325
```

先点程序里的“列出环境”，能列出来就说明 API 通。

---

### 2. 标题识别不准

当前版本会尽力自动识别标题，但 Temu 页面结构可能变。

解决方式：

```text
直接在程序标题框里手动改成你要的前 2 行英文标题
再点保存截图
```

后续如果同类页面一直识别不准，再改代码里的 `src/temu_page.py -> extract_title()`。

---

### 3. 图片候选不是主图

先点：

```text
下一张候选图
```

如果候选图太多，多数是小图，就调高：

```json
"min_image_width": 350,
"min_image_height": 350
```

如果完全找不到图，就调低：

```json
"min_image_width": 180,
"min_image_height": 180
```

---

### 4. 保存的截图范围不对

这是当前 v0.1 最大的不确定点。原因是页面里的主图区域可能不是普通 `<img>`，也可能被多层容器包住。

临时处理：

```text
换候选图
缩放页面
确保主图在浏览器可见区域
重新识别
```

后续要改：

```text
src/temu_page.py -> reload_candidates()
```

---

## 四、下一步要加功能时怎么做

建议不要一次加全功能，每次只加一项：

1. 先让当前商品页截图稳定。
2. 再加“从搜索结果点商品”。
3. 再加“进店铺”。
4. 再加“按销量排序”。
5. 再加“销量 ≥5 判断”。
6. 再加“查重”。

每加一步，都先测试 5-10 个商品。

---

## 五、需要我或 Codex 改代码时，重点给这些信息

不要只说“不能用”。要给：

```text
1. 你点了哪个按钮
2. 程序日志里最后 20 行
3. 当前 Temu 页面是什么页面：搜索页 / 店铺页 / 商品详情页
4. 截图保存出来的效果：范围大了、小了、错图、黑图、空图
5. 标题识别结果是什么，正确应该是什么
```

这样可以最快定位。