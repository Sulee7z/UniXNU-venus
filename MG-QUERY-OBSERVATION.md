# MG实际查询与缓存取证纠正

2026-10-29。继续既定证据优先框架，不重复单字段照片测试。

## 已验证的新事实

### 1. MG缓存不是残件

原取证程序用了APFS文件extent总长度（分配长度8192），却没有读取inode
`j_dstream_t.size`（真实EOF7477）。bplist尾部零是分配padding，不是文件损坏。

`data_store_view.py`现按92字节inode固定部分、xfield头、8字节对齐/type8 DSTREAM读取EOF；
只在明确稀疏文件或物理地址0的extent中填零。加密extent、漏读capture页、非法范围/CRC/seed均报错。
覆盖此类错误的测试`tests/test_data_store_view.py`通过；真实缓存7477B能被plistlib完整解析。

三份历史读回014826/021027/031220的缓存精确SHA均为：
`661cdb8356befb18dae67ecb839db8d228b513482437db2c820fed68755f16a7`。
纠正后的输出另存`artifacts/venus-mg-recheck/<run-short>/`；旧提取与原始capture保留。

### 2. 缓存中确有旧的零缩放

key标识是`base64(MD5("MGCopyAnswer"+question))`去掉`=`。
ProductType/ProductVersion/BuildVersion/ArtworkTraits等已知键均匹配，
`MainScreenStaticInfo`对应`oBbtJ8x+s1q0OkaiocPuog`。

24B数据按原MG显示采集函数保存的`3i/2f/i`布局解为：

```text
[-1, -1, -1, 0.0, -1.0, -1]
             ^ scale
```

这与`0x1a0215948..5968`的原版结构写入相符。ArtworkTraits仍缓存P3/scale2/iPad7,1，
并没有随board的新sRGB属性变化。没有明文main-screen-scale键**不能排除缓存**。
持久缓存保存旧答案有直接证据；进程是否命中此项仍需实际API查询。

### 3. 004–006的路径推断错误

已读实际XNU `IORegistryEntry::fromPath`：仅在`plane=NULL`时剥离`IODeviceTree:`前缀；
提供`gIODTPlane`时它会把前缀当作路径内容。因此004–006的DT=0是探针调用错误，
不证明原ADT根挂错。007的`absnull=1 / mgscale=2`只证明**属性可读**，不是MG API返回2。
未证明需要新chosen镜像，后续测量候选复用原4b1内核，不含005–007的镜像行为。

### 4. 日志证据的边界

先前tracev3扫描没有成功解压chunk（decoded=0），命中的是压缩块内仍完整的字串。
这些字串支持“曾记录零缩放FBS拒绝”，但缺PID/boot UUID/完整事件解码，
不能仅用新文件名或对象地址断言它属于003、006或007。
同理，未搜到GetDotPitch字串不证明该分支未执行；没有SpringBoard.ips也不证明ReportCrash为何没写。

## 查询程序

`package/MGQueryProbe.c`一次输出JSON：

1. kern.bootsessionuuid、pid/uid。
2. 用户API `IORegistryEntryFromPath`读取chosen与device-tree/chosen原始属性。
3. `MGGetFloat32Answer("main-screen-scale", default)`的实际float32位；default依次1、2、7。
4. `MGCopyAnswerWithError`的main-screen-scale及MainScreenStaticInfo原始结果。
5. 库/API加载是否成功、完整完成标记。

程序不写缓存、不设置属性、不BRK、不复位。原生iOS libSystem/CoreFoundation/IOKit/MG实际执行；
链接时的libSystem.tbd仅声明导入符号，不提供替代实现。

当前Linux`codesign`是`exit0`的构建shim，不能拿来给用户态签名。
本程序改用LLVM ld64.lld ad-hoc签名，逐页检查CodeDirectory：17个4KiB SHA256页，
真实CDHash`ede1079c4b409015e1e34633fa6e7d9ecfd86b9b`。
trustcache只新增该程序自己的CDHash，两个原系统trust模块保持逐字节一致。

执行程序SHA：`04d0ba9947c00ccca84ecc710d9f526cceae6ceeea1bd0455337458fe53c6f3b`。
实际C程序在显式CF/IOKit/MG模型下的ASan/UBSan/JSON/参数/错误处理测试通过，
不是实际API返回值或手机运行的证据。

## 已准备的008手机候选

```text
G:/UniXNU-Port/artifacts/venus-mg-query-008/phone/boot-venus-unixnu.img
SHA256 2ef531b07097c440dc51210548a8a3dfecd46a658c8e783c0e168376d590c71b
168960000 bytes
```

准确SHA与大小见`evidence/mg-query-candidate.json`。
保留已实机进入用户态的kernel4b1ae1c0、6GiB固件、原Data seed。
实际当前board/converter生成ADT，只增加早期scale2/rotation0与GpuAddon占位；随机seed保留。

接入原内核已有的post-Data NGPUADD2安装/LaunchDaemons只读union路径。
只安装两个文件：

- `/private/var/ngpu/bin/venus-mg-query`（0755）
- `/private/var/ngpu/daemons/org.blu-sharky.adrenoprobed.plist`（0644）

后者文件名是原内核固定的daemon-view验收marker；内容是独立label
`org.unixnu.venus.mg-query`的单次任务，UserName=mobile，RunAtLoad=true，KeepAlive=false。
没有GPU插件/Extensions或wallpaper文件，这两个源目录不存在的mount状态是预期；
daemon目录mount独立执行，是否成功启动helper必须由输出确认。
原版launchd仍继续运行。只在本镜像新增`sheng-gpu-addon=1`时执行。

标准输出：`/private/var/tmp/venus-mg-query-008.json`；
标准错误：`/private/var/tmp/venus-mg-query-008.stderr`。
返回Android后可用既有有界Data只读capture与纠正后的解析器取回；不用再拍诊断页。
不存在或不完整的报告不能当作MG返回0。

本轮主机已完成签名、wire解压往返、输入身份、FAT读回、boot roundtrip核验。
复核同kernel6GiB SystemOS/AKS/HID的旧QEMU证据；**未在QEMU执行新helper**，
安装/union挂载/用户态查询仍待准确镜像授权后的实测。

用户随后确认“已回Android，确认008一次”，授权正常Data写入及上述两个文件安装/输出。
ADB5037核venus、fastboot核55870427后一次RAM boot：Sending4.327s、Booting0.193s OKAY，总4.563s。
记录`evidence/mg-query-phone.json`，日志`logs/venus-mg-query-008-phone.txt`。
授权已消费。以下是返回Android后的只读结果。

## 008只读结果：安装通过，查询未完成

用户“已回，允许只读”。快照`artifacts/venus-data-forensics/read-20261029T041826Z`：
50255置位页、31段、205844480B页数据；前后metadata一致，逐段SHA/页覆盖校验通过，checkpoint341。
采集只读，没有手机写入或重启。

- 两个安装文件分别67232B/724B，真实EOF、SHA均匹配008 payload。
- inode mode也核为0755/0644；父目录0755，`/private/var/tmp`为1777。
- `/private/var/tmp/venus-mg-query-008.json`和`.stderr`都无目录记录。
- MG缓存仍是7477B、SHA`661cdb8356befb18dae67ecb839db8d228b513482437db2c820fed68755f16a7`。
- `/private/var/log/com.apple.xpc.launchd/launchd.log`第4行的完整boot args与008完全相同，
  包含`sheng-gpu-addon=1 sheng-build-tag=mg-query-008`；第42行early boot complete，第701–706行
  SpringBoard pid27正常spawn。可据boot args关联本轮，日志本身没有image SHA/boot-session UUID。

### 任务发现接入缺口

当前21H461 OS `/System/Library/xpc/launchd.plist`真实长度1640626B、SHA
`f1b99c4e3e738cb1c2622ad82f5e78cd2fbd1f88c8ced13c423aabf91b2b22eb`。
解析出的`LaunchDaemons`是561项字典，保存完整任务定义，**没有新增查询路径**。
实际launchd二进制有`refusing to read cache protected location from disk`字串；
原`__TEXT,__config`把`launchd_cache_loader`配置为RequireRun/RequireSuccess。
取回的cache-loader日志记录默认路径、原签名可信及缓存成功发送。

原sheng `build-adreno-metal-plugin.py`第99–107行也明确提示新名字可能不被枚举，
另提供已有任务名；但本OS缓存已经包含原FDR的ProgramArguments，因此**仅改overlay文件名
还不足以证明会执行新程序**。

已证明安装持久化和正常launchd启动。目录插入未激活查询是当前接入假设；
union mount stage及具体lookup/refusal分支未捕获，不能单凭无日志证明从未exec。
下一步先验证与该launchd/签名缓存相容的显式单次执行入口，再测MG，不继续修改display参数。

### 日志提取修正

新增严格`tracev3_chunks.py`按16B little-endian preamble、declared size、bv41/LZ4/bv4$与8B对齐
解压，不再猜4KiB边界。23个trace文件解出16644152B，framing/decode错误0；3组边界/损坏测试通过。
其中没有查询任务名。解压成功仍不是完整PID/time/boot事件归因。
原错误scanner和旧输出保留，只作历史材料。

实机收据`evidence/mg-query-readback.json`；快照内`mg-installation`、`mg-launch-logs`、
`mg-trace-chunks`与`forensics-v2`保存原始提取。
OS缓存/原launchd只读检查另存`artifacts/venus-mg-query-008/launch-cache-inspection-v2`。
首次检查的Windows POSIX-parent路径错误已修，旧`launch-cache-inspection`保留，不作缺文件结论。

## 判读

| 实测 | 判断 |
| --- | --- |
| chosen=2，三个返回均0，StaticInfo仍scale0 | API确实返回独立于默认值的旧零答案；缓存/查询计算链待隔离 |
| 三个返回分别1、2、7 | API没有可用答案，返回调用默认；不能用此前属性值推断用户态缩放 |
| 三个返回均2 | 此进程实际MG答案为2；需再对照SpringBoard的进程/模式来源 |
| API/库失败、输出不完整/缺失 | 先修复启动或依赖；不判定缓存或FBS修复效果 |

复现：

```sh
python3 ports/UniXNU-venus/tests/test_data_store_view.py
python3 ports/UniXNU-venus/scripts/build-mg-query-probe.py
python3 ports/UniXNU-venus/scripts/check-mg-query-protocol.py
python3 ports/UniXNU-venus/scripts/prepare-mg-query-phone.py
python3 ports/UniXNU-venus/scripts/prepare-mg-query-phone.py --check
```

haydn参考的固定版本和采用边界见`HAYDN-IAMOJZ-REFERENCE.md`。

## 009执行入口修复已准备

新的readonly `/usr/libexec` union接管原早期prng_seedctl任务；父进程立即exec完整原版任务，
一次supervisor延迟5s后以mobile501运行原查询，30s超时kill/reap，独占journal保存失败阶段。
生产fork/exec/身份/故障与mount环境保留测试、新内核/重建对照的QEMU SystemOS/AKS/HID、签名/FAT/boot校验通过。
准确候选`artifacts/venus-mg-query-009/phone-r2/boot-venus-unixnu.img`，SHA
`34635bc461ec668e87066a3d9bff58c07a7312ef40f8d656e3a989553d9f91c0`。
不是复用008/4b1内核，实际union/任务/查询仍待准确授权实测。详见`MG-TASK-ACTIVATION.md`。

010原链对照已持续运行并取得新日志、19次SpringBoard SIGTRAP和5份真实IPS；
栈明确落在FBS显示模式初始化。MG缓存仍原零缩放字节，010-tag trace仍有infxinf/0描述。
实际MG API答案仍未知，后续缩放源隔离以这些真实报告为基础。
见`SHENG-CHAIN-010-RESULT.md`。

011现在采用官方缓存失效要求：原策略完成后独占备份旧MG文件并同步，
由原系统自行重算，同时保存持久begin/end状态。模型成功/失败测试与真实QEMU Data后
同步拒绝保护已通过；新镜像待具体授权实机测缓存/显示结果。见`SCALE-REFRESH-011.md`。
