# 证据优先的锁屏诊断框架

2026-10-29。接续 `LOCKSCREEN-SCALE.md`。本文只调整**诊断方法**，不改显示补丁方向。

最新010实机结果：原链进入正常用户态bootstrap并持续记录日志，watchdogd禁用生效。
SpringBoard19次SIGTRAP，首次拿到5份PID匹配的真实IPS，均为FBSDisplayMode初始化校验BRK。
010-tag的正确解压trace仍有零缩放描述，缓存字节也未改变。下一步聚焦显示缩放来源，
不再用旧日志或长时间等待代替崩溃归因。详见`SHENG-CHAIN-010-RESULT.md`。

## 最新核验纠正（以下历史推断以此为准）

- **缓存完整**：真实文件长度7477B，8192B是APFS分配大小。此前“尾部全零/残件”由取证程序
  未读取DSTREAM.size导致。三份已保存capture严格重读后plist均正常。
- **缓存确有零缩放**：MainScreenStaticInfo的24B值为`[-1,-1,-1,0.0,-1.0,-1]`；
  key ID按`base64(MD5("MGCopyAnswer"+question))`去padding解出。三份缓存完整SHA相同，
  还有旧P3答案。此前以“没有明文scale键”排除缓存的推断撤回。
- **DT=0不是挂树证据**：实际XNU fromPath仅在plane=NULL时解析前缀；004–006的调用形式有误。
  007的mgscale=2只是属性值，未测MG API，不证明镜像行为修好了平台。
- **日志不能硬绑某次启动**：此前没有完成tracev3 chunk/event解码、没有boot UUID/PID关联。
  命中字串证明曾发生零缩放拒绝，不能仅靠文件名或对象地址称003/007仍拿0。

008一次授权启动后的稳定Data只读快照已取回。两个安装文件匹配payload；查询JSON/stderr缺失。
boot args匹配008的launchd原日志记录正常bootstrap与SpringBoard spawn，排除本轮早期SystemOS停滞。
原签名launch cache含561个完整任务定义，无新增查询路径。下一步先验证显式任务执行入口，
不把目录插入当已启动，不把缺报告当MG0。严格tracev3解压23文件/16644152B成功，仍未完成事件归因。
详细收据与复现见`MG-QUERY-OBSERVATION.md`、`evidence/mg-query-readback.json`。
用户提供的haydn同SoC参考已固定版本审阅，见`HAYDN-IAMOJZ-REFERENCE.md`。

009-r2现已准备显式早期任务wrapper：readonly union中的prng_seedctl直接被启动，父进程立即exec原版，
一次mobile查询留下独占journal及JSON/stderr。实际host fork/exec/身份/timeout/去重与mount模型、签名/镜像，
新kernel及重建对照的QEMU SystemOS/AKS/HID通过；QEMU止于Data之前。准确镜像与新kernel资格边界见
`MG-TASK-ACTIVATION.md`，实机仍需单独操作确认和报告。

## 为什么换方法

过去几轮的做法是：改一个显示/缓存假设 → 打包 → RAM boot → 拍照 → 人工抄字段。
002 的结果直接否证了这个闭环里的关键假设，也暴露了闭环本身的问题：

```
002 照片（G:/20261029_085540.JPG，SHA 138604044eddbfe8fbef40ca...）
OS t=113s  root=1  procs=115  MEM totalMiB=6144 free4K=110273
UFS verified=908872  failures=0  integrity=0  published=2
CRASH 1/4 p140 SpringBoard sig5 src=EL0
PC=1a653c744 LR=1a653c744 E=f2000000 F=0 slide=+716c000
MODE w=1440 h=3200 p=0 so=0 hz=405e000000000000 g=1 hdr=0 r=0 v=0
DISPLAY stage=10  SWAP=0  COPY=0  CLIENT calls=2 (IOMobileFramebufferUserClient)
```

**已确认的事实**

1. 启动 ADT 已写入 `display-scale=2`、`display-rotation=0`，但 SpringBoard 拿到的
   `preferredScale` 仍是 0，与未写属性的 6GiB 基线完全一致。
   → “在 `/chosen` 提前写 display-scale 就能修好 preferredScale” 这条**被否证**。
2. 崩溃点仍是 `0x19f3d0744`（PC−slide），即原版 FBSDisplayMode 校验失败的 BRK，
   与 10-28 照片同址。
3. 002 没有缓存改名代码，001 虽带缓存改名但在 SystemOS 入口就停了，
   **缓存刷新从未真正执行过**。因此“旧 MG 缓存导致零值”仍是**未验证假设**，不是结论。

**闭环的问题**：每轮只能得到“是/否”，拿不到崩溃时的错误文本、MG 实际返回值、进程内参数来源；
而屏幕只显示被压缩过的摘要行。继续这样试参数，等于用一次 RAM boot 换一位信息。

## 新框架：四层，按顺序

### 第 1 层 观测优先（当前执行）

从**持久 Data 卷**离线取出系统自己写的证据，不需要新内核、不改手机状态：

| 证据 | 路径 | 能回答什么 |
| --- | --- | --- |
| MobileGestalt 缓存 | `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` | `main-screen-scale` 等答案的真实缓存值 |
| MG 偏好 | `/private/var/mobile/Library/Preferences/com.apple.MobileGestalt.plist` 及小写同名 | 同上，是否有覆盖项 |
| 崩溃报告 | `/private/var/mobile/Library/Logs/CrashReporter/*.ips` | SpringBoard 异常类型、reason 文本、线程回溯 |
| 诊断索引 | `/private/var/db/diagnostics` | 是否有可用的 os_log tracev3 |

这些都写在 Data 上，Data 由 SHNGDATA 覆盖层承载。用 Android root 只读 `dd`
+ 主机端页面重组即可解析，**不需要 XNU 启动，也不需要 root 手机系统**。
工具：`scripts/collect-data-forensics.py`（本文件同期新增）。

### 第 2 层 假设与否证条件

每个假设先写明“什么结果算推翻”，避免再出现“改了没变但继续加码”：

| 假设 | 支持证据 | 否证条件 |
| --- | --- | --- |
| H1 旧 MG 缓存里保存了错误的 scale 答案 | 001/002 都在未刷新缓存的状态下出现 p=0 | 缓存文件里没有 scale 相关键，或键值正常但仍是 p=0 |
| H2 preferredScale 根本不来自 MG `main-screen-scale` | QuartzCore getter 有分支：私有字段非零直接返回；否则才查 MG | `.ips` 回溯显示 preferredScale 来自 CADisplayMode 私有字段路径 |
| H3 拒绝原因是另一个字段（120Hz/gamut/rotation）而非 scale | 校验器同时检查 refresh/scale 等 | `.ips` 的 reason 文本点名具体字段 |

第 1 层取证完成后，H1/H2/H3 至少能排除两个，再决定改什么。

### 第 3 层 参照对比

同 OS（iPadOS 17.7.11 / 21H461）、同身份（iPad7,1，j120ap）的移植是 umi
（SM8250，已到 Hello/设置界面）。它的 minimal `board.toml` 不设 root UUID、
`ipad_identity=false`，完整配置在其仓库 `docs/BUILD.md`。
对比项限定为：ADT 的 `/product`、`/chosen`、`/defaults`、`/buttons` 属性、
`offline-legacy-*` 参数组合、`NativeLegacyDisplay` 的重写槽位。
不对齐 SoC 外设，也不照搬其存储布局。

### 第 4 层 QEMU 用户态复现

目前 QEMU 只到 SystemOS/owner 检查点，用户态问题只能上手机验证。
`--systemos-checkpoint` 之外若要复现 SpringBoard，需要 ramfb + Data ramdisk +
原版 launchd 路径；这一步是**让用户态循环回到主机**，不是新的显示猜测。
优先级低于第 1 层：先把 `.ips` 拿到手，再决定是否值得搭。

## 明确不做

- 在拿到 `.ips` / MG 缓存之前，不再改 display-scale、缓存刷新、`offline-legacy-*`
  参数去试锁屏。
- 不再用“fastboot OKAY / QEMU 通过”当作锁屏证据。
- 不重复 001 那种在 SystemOS 就停住的组合（内核新、仓库未定位停滞前不重试）。

## 第 1 层已执行（2026-10-29）

一次授权只读读取 + 主机离线解析完成：

```
run      G:/UniXNU-Port/artifacts/venus-data-forensics/read-20261029T014826Z
store    LBA[59299519,61396736)  相对 skip 14417855
present  48896 页（上次元数据读取为 47130）  26 段  共读 200278016 B
volume   Data  FCC1EC83-9500-4D4D-AEED-6004A520B3C0（卷根即 /private/var）
```

**得到的真实错误文本（os_log，10 次）**

```
FBSDisplayMode cannot be configured as requested :
<FBSDisplayMode: 0x301e0a350; infxinf@0x (1440x3200/0) 120Hz p3 SDR>
```

- 逻辑尺寸是 `inf`：模式缩放为 0，像素 1440x3200、旋转 0、120Hz、p3。
- 同一描述里 120Hz 与 p3 都存在，**本次报错的字段是缩放**，不是刷新率/色域。
- 关键字命中：SpringBoard 78、FBSDisplayMode 10、IOMobileFramebuffer 1、MobileGestalt 49。
- `GetDotPitch` / `GetMainDisplay` / `GetDisplaySize` / `screen parameters` / `main-screen-scale` / `display-scale` 均无命中。

**MobileGestalt 侧**

- 缓存文件 8192B，SHA `4285efac566d4ec11158d37cbe8079ffbbf5328ce75ae784b17afc35fb1fd373`：
  有 `CacheUUID/CacheData/CacheExtra/CacheVersion`、身份键（`ArtworkDeviceScaleFactor`、
  `CompatibleDeviceFallback`…）与 `iPad7,1`/`21H461`/`xiaomi,venus`；**没有明文 scale 键**，尾部为零，plist 不完整。
- 两个 `com.apple.MobileGestalt.plist` 偏好文件**不存在**。
- CrashReporter 只有 `stacks+com.apple.datamigrator-*`，**没有 SpringBoard .ips**（SIGTRAP 由内核直接投递）。

**据此更新的判断**

| 假设 | 结论 |
| --- | --- |
| H3 拒绝原因是其它字段 | 基本排除：同一描述中 120Hz/p3 正常，异常的是缩放 0→inf |
| H1 旧缓存里存了 scale 答案 | 缓存里没有明文 scale 键；但存在混淆键，能否命中仍未定 |
| H2 preferredScale 不来自 MG | 未证实：MG 确实被调用（CacheData 存在），但未走 dot-pitch 分支 |

下一步唯一廉价判定：一个自签名的自有进程探针，打印
`MGGetFloat32Answer("main-screen-scale", 2.0)`、`IODeviceTree:/chosen` 是否存在、
以及 `display-scale` 属性的原始字节。三种结果分别指向：属性不可见 / 答案为 0 / 调用默认生效。

证据：`evidence/data-forensics-20261029.json`；
`read-20261029T014826Z/{index.json,forensics.json,tracev3-scan.json,extracted/}`。

## A/B 结果：/chosen display-scale 不是来源（2026-10-29）

003（只把 `/chosen` display-scale 由 2 改为 3）开机后回 Android，再只读取证
（run `read-20261029T021027Z`）。最新的 `000000000000000e.tracev3` 里：

```
FBSDisplayMode cannot be configured as requested :
<FBSDisplayMode: 0x30324d090; infxinf@0x (.../0) 120Hz p3 SDR>
```

对象地址与 002（0x301e0a350）不同，是新一轮崩溃；**scale 仍是 0**。

结论：

- 改 `/chosen` display-scale 不改变 `preferredScale`。该属性或被 MG 忽略，或在
  `IODeviceTree:/chosen` 上不可见。
- H1（缓存里有 scale 答案）与“/chosen 直读”两条都不再被支持。
- 剩下两条可测路径：①`IODeviceTree:/chosen` 是否真的可达、属性字节是什么；
  ②MG 的 IOMobileFramebuffer（main display / dot-pitch / display size）分支。

注意：`000000000000000e.tracev3` 尾部是稀疏洞，读取需容忍空洞；不把它当作旧日志。
证据：`evidence/lockscreen-scale-003-phone.json`。

## 007 结果：/chosen 镜像生效，但 SpringBoard 仍拿 0（2026-10-29）

一页诊断（007，kernel `95047fc2…`）显示：

```
12-15  CRASH watchdogd（尚无 SpringBoard 模式行）
30     DT2 root=root kids=2 mir=1
31     DT3 absnull=1 mgscale=2 dp=0
39     OS t=94s … DT=0/ffffffff dp=0 mg=1
```

- `mir=1`、`absnull=1`、`mgscale=2`：镜像挂到注册表根后，**MobileGestalt 形式的绝对
  路径已能解析 `/chosen`，并读到 display-scale=2**。
- 第 39 行的 `DT=0` 只是探针自己「前缀 + 显式 plane」的写法不生效，与 MG 无关。

随后回 Android 只读取证（run `read-20261029T031220Z`，present 50174）：

- 006/007 之后新建的 `000e`、`0013`… 里仍有 7 条
  `infxinf@0x (1440x3200/0) 120Hz p3 SDR` 拒绝行——**模式缩放仍是 0**。
- 说明镜像给出的 2 没有进入 SpringBoard 构造模式时的取值，或更早的内存中 MG 答案（0）胜出。

**结论：`/chosen` 可见性已修好，但它不是 SpringBoard 零缩放的来源。** 剩余可能：
`preferredScale` 来自 CADisplayMode 私有字段或显示模式列表，而不是 MG 的
`main-screen-scale`；下一步只有用自有进程直接调用 `MGGetFloat32Answer` 才能定案。

证据：`evidence/lockscreen-dtmirror-005-phone.json`、`evidence/lockscreen-allinone-007-phone.json`、
`artifacts/venus-data-forensics/read-20261029T031220Z/summary-007.json`。

## 工具用法

```sh
# 1) 主机：只算范围，不碰手机
python tools/python/python.exe ports/UniXNU-venus/scripts/collect-data-forensics.py --plan

# 2) 手机在 Android（已 root）：一次只读读取（无写入、无重启）
python tools/python/python.exe ports/UniXNU-venus/scripts/collect-data-forensics.py --read-android

# 3) 主机离线解析刚才读到的 run
python tools/python/python.exe ports/UniXNU-venus/scripts/collect-data-forensics.py --offline "G:\UniXNU-Port\artifacts\venus-data-forensics\read-<时间戳>"

# 4) 主机：扫描 tracev3（原始段 + 可识别的 LZ4 段）
python tools/python/python.exe ports/UniXNU-venus/scripts/extract-diagnostics-strings.py --offline "G:\UniXNU-Port\artifacts\venus-data-forensics\read-<时间戳>"
```

- 只读：`dd` 读 `unixnu` 的 SHNGDATA 头+位图，再按**已置位页的连续区间**读取；
  不写、不 sync、不改 seed、不重启。
- 页面视图：置位页取 store，未置位页取 `Data.dbr` 种子，只读重组 APFS。
- 输出：`metadata.bin`、`run-*.bin`、`index.json`、`extracted/`、`forensics.json`。
- 边界：只处理文档列出的 MG 路径与 CrashReporter/诊断目录，不整盘导出、
  不读取用户文件内容页以外的东西。

## 验收标准

一次读取 + 离线解析后必须得到：

1. 三个 MG 文件中至少缓存文件可解析，并给出 scale 相关键（有/无、值）。
2. CrashReporter 中与 SpringBoard 相关的 `.ips`，含异常类型与 reason 文本。
3. `forensics.json` 记录字节数、SHA-256、解析错误；缺失项写“不存在”，不写 0 冒充。
