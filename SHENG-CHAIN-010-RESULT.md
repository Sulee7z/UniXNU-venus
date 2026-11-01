# 010结果：启动链持续运行，SpringBoard显示模式仍失败

2026-10-29。用户反馈：“已回，允许只读，不过这次计数一直没停止，我直接重启了”。
这是持续计数及手动返回Android的反馈，没有给出具体计数器、时长或系统界面结果。

## 启动和原策略已取得新实机证据

- 准确镜像SHA `5f9061214acfd829ec893af61904d438844e1fb4ae584122565360653fb9a57d`，原4b1 kernel。
- 新launchd.log第4行完整参数与010一致，包含kt_fixed_zones120/watchdogd-disable1/tagsheng-chain-010。
- 第42行：`Early boot complete. Continuing system boot.`；原早期任务/cache-loader执行并进入bootstrap。
- 新日志1195319B/10007行，末条时间`16:34:42.408932`；日志不是008旧文件。
- disabled.plist1342B，watchdogd键为true；该新日志中watchdogd退出事件0。
- 不据此区分两个新增参数各自贡献，也不把持续日志或计数当界面成功。

用户批准的只读快照：`artifacts/venus-data-forensics/read-20261029T063818Z`。
124248置位页、65段、508919808B页数据，前后metadata稳定，逐段SHA和覆盖通过，checkpoint745。
采集过程中无手机写入、sync或重启。此次页数据已接近512MiB采集上限，后续读回应先核对实际置位页数。

## 19次实际SpringBoard SIGTRAP

新launchd日志有19条SpringBoard SIGTRAP退出记录，显示退出后重启及递增节流。
首次pid27运行45734ms，后续多数运行约0.2–0.4s；最后捕获pid309。
这支持“系统持续运行，但SpringBoard陷入崩溃重启”，不是正常UI完成。

此次首次得到5份真实SpringBoard.ips，pid126/131/136/144/309与010日志退出记录匹配。
报告中的iPad7,1/21H461、FrontBoardServices UUID
`81ef9aac-02b7-30f1-8181-bb60a5115835`一致。
全部PC=`0x1ae954744`，image offset=`0xf744`，报告原始指令字节为BRK#0；
同此前已离线核验的FBS校验位置。原始文件及SHA保留在`forensics-v2/crashes-mobile`。

真实调用栈主线：

```text
SBSystemAppMain
→ FBSystemShellInitialize
→ FBDisplayManager sharedInstance
→ FBSDisplayMonitor / FBSDisplaySource初始化
→ FBSDisplayConfiguration _initWithImmutableDisplay:originalDisplay:assertIfInvalid:
→ FBSDisplayMode _initWithCADisplayMode:scale:rotation:
→ FBSDisplayMode _initWithWidth:height:preferredScale:scaleOverride:...validityCheck:
→ BRK #0
```

问题收敛在系统显示管理器初始化。不能用换启动器或单纯延长等待解释这个实际栈。
报告文件名/header timestamp晚于其captureTime，例如161628文件记录pid144的160233崩溃；
判读使用PID/incident/image映射，不仅看文件名时间。报告的unlocked字段来自离线状态环境，
不作为实际用户解锁或锁屏显示证据。

## 缩放证据与剩余边界

严格解压24个trace文件，31677768B，framing/decode错误0。
其中0018.tracev3包含完整010-tag启动参数与显示拒绝字串：

```text
FBSDisplayMode cannot be configured as requested:
<FBSDisplayMode: ...; infxinf@0x (1440x3200/0) 120Hz p3 SDR>
```

同文件内多处描述仍是零缩放。字串已正确解压，但没有完整firehose事件PID/time/boot解码；
当前崩溃归因以PID匹配的IPS为主，不以对象地址强绑进程。
MG缓存仍7477B/SHA661cdb8356befb18dae67ecb839db8d228b513482437db2c820fed68755f16a7，
保存的MainScreenStaticInfo.scale0未改变；实际MG API返回值仍未测得。
下一步应隔离显示缩放的缓存/计算来源，保留已经获得正常启动证据的原链。

skip-Setup偏好复查：三份之前缺失的文件已由OS创建，但配方键仍未设置；
SpringBoard偏好从144B变300B。迁移配置仍缺LastSystemVersion，尚不能据此认定显示失败原因。
报告在本次快照`sheng-startup-prefs/report.json`。

主收据`evidence/sheng-chain-control-readback.json`；
分析`sheng-chain-analysis/report.json`及`trace-context.json`。
分析器严格校验IPS的两个JSON对象、incident、PID、image offset、UUID和原始BRK指令。
