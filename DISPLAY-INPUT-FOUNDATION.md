# CPU显示、亮度与输入的主机前置核对

2026-10-28，依据官方 `display` 与 `input` 步骤；本轮未操作手机。

## CPU显示

- 当前构建使用的GopFramebuffer源码与已读参考一致，原358槽显示ABI已随完整构建核对。
- 真实 `NativeLegacyRequest.h` 的既有请求状态/边界测试通过。
- 增加1440×3200全尺寸主机缓冲测试：BGRA8888、5760字节目标行跨度、18432000字节帧；
  带padding的源逐像素复制、末端哨兵、短缓冲和非法stride拒绝通过ASan/UBSan。
- `offline-legacy-unit-scale=2` 表示720×1600逻辑点，实际复制仍为1440×3200像素。
  这不是物理密度或Apple机型的测量值。
- CPU路径核对源IOSurface/descriptor边界，完成复制后执行屏障与swap retirement；
  主机像素测试没有执行原版OS的swap队列、完成通知或手机scanout。
- `sheng-vsync=120` 仍是软件请求值。原厂K2/K2b声明有多种时序；
  当前固件选用的模式和实际刷新率仍须测量，不能直接记录成实测120Hz。
  live FDT的默认panel引用仍指向sim-video节点，其声明1080×1920/60Hz；
  这与已有1440×3200 GOP观测不同，不能把DT默认引用直接当成固件当前扫描模式。
- 已知FBSDisplayMode拒绝保持未解决，修正ADT和像素测试不等于OS已接受显示模式。

## 亮度

目标K2/K2b面板声明 `bl_ctrl_dcs`，最大亮度编码2047，并有inverted DBV与首帧后更新策略。
需要在目标DSI命令/所有权基础上实现服务；sheng的KTZ8866 I2C路径不对应此面板。
当前 `sheng-backlight=0`，亮度读取、最低/中间/最高设置和OS UI调光均未验收。

## 真实触控

从固定SHA的本机live FDT解析，而非把参考板参数当作本机：

| 项目 | 原厂声明 |
| --- | --- |
| 节点/协议族 | `/soc/spi@a8c000/fts@0`，`st,spi` |
| 总线 | SPI，CS0，最高7MHz |
| IRQ/reset | TLMM GPIO23 / GPIO22；IRQ flags原值`0x2008` |
| 坐标范围声明 | 1440×3200 |
| 普通/HTP固件名 | `st_fts_k2.ftb` / `st_fts_k2_htp.ftb` |
| 供电provider | touch_avddsource_vreg、PM8350C L3与L2；保留对应phandle和完整路径 |

这些是连接与文件名资料，尚未读取实际芯片ID或解析/加载对应固件。
GENI引擎固件、SPI模式、复位/上电时序、中断与DMA所有权、报告协议及接触ID仍须实现/核对。
当前producer是空接口；离线HID启动成功不代表触控事件已工作。

### 固定版本的ST协议源码

已从已有Venus内核参考的同一提交 `df169d0b934bd8e372c5c5e2ffab5f9c50f3d052`
保留10个ST相关源文件，文件SHA/URL在 `artifacts/venus-touch-source-reference/sources.json`。
`audit-venus-touch-reference.py` 已核对：

- `fts_spi` 分支的 `st,spi`、SPI mode0、8bits、7MHz、4线SPI与CS结束前10µs延时。
  command/read放在同一SPI message中，读取还包含协议dummy字节。
- SPI5.2.4.1分支的触点ID在event[1]高4位；ST4.2.14分支在低4位，坐标字节编码也不同。
  不能因为都叫fts就混用解码。
- 该SPI参考默认SALIXP，源码预期ID36/40、寄存器地址0x20000000。
  **本机芯片ID尚未实测**，此值仅是源码假设。
- SPI参考parser读取 `fts,thp-fw-name`，本机DT声明 `fts,htp-fw-name`；
  参考实现还未对应本机avddold供电路径。必须核对本机原厂驱动/固件代际及供电责任方。

证据 `evidence/touch-reference-audit.json`。本轮只核对协议与接入差异，未启用物理producer。

## 实体按键

- Power：PMK8350 `pon_hlos@1300` 的KPDPWR，Linux code116。
- Volume Down：同一PON的RESIN输入，Linux code114。
- Volume Up：PM8350 GPIO6，active-low，15ms debounce，Linux code115。
- PON还包含长按/组合复位设置；输入移植需核对PMIC访问所有权、IRQ路由和应答，
  保留现有复位行为，再接入HID consumer按下/释放报告。

## 检查与下一阶段

```sh
python3 ports/UniXNU-venus/scripts/check-display-input-foundation.py
```

证据 `evidence/display-input-foundation.json` 保留类型化数值、原始字节和provider路径；
日志/测试在 `artifacts/venus-display-input-foundation/`。
这完成了相应主机侧资料与CPU复制检查。Data跨重启、实际OS画面/swap、DSI亮度与触控/按键
仍有各自实机门槛，按 `ORDERED-BRINGUP.md` 的顺序进行。
