# Welcome012之后：A660 Metal13与自有ST触摸14

2026-10-29，用户确认012进入系统欢迎页。该镜像`38245b0e...`保留为UI基线。

## Metal实际实现

- 用户指定none24smu/UniXNU-zeta，固定`eb489285a1d9153872f00c93ebb519a269b249b5`，36个参考文件按Git blob/长度/SHA核验。
- UniXNU base35c384e / NativeMetal ff0c70d / metal2vulkan720ef1c；26个zeta图形补丁和17个translator补丁在独立工作副本应用。
- `package/Metal13/venus-ios17-runtime.patch`保留iPadOS17、536B私有_MTLDevice ABI；固定地址显示内存实验默认关闭。
- 自有Venus插件入口保留原`initWithAcceleratorPort:`与NativeAdrenoMetal运行时标识，通过原Metal发现路径返回真实Metal前端；只允许列出的backboardd，发布文件缺失时返回nil。
- Rust1.98运行时、Objective-C前端、Mesa85fda3b Turnip/native Darwin后端已实际交叉编译/链接为普通ARM64/iOS17。SDK仅用于声明/stub，运行时链接原17系统框架。
- 修正工具SDK的IOKit `Versions/A`安装名为iOS平面路径，使用同一Turnip对象重链，保留失败/未签名输出；不打包Apple框架代码。
- 插件22,067,760B，SHA`ab37f4967aa46547a3e63125cb9134ba2055f2efec78a04c632fe1d2b021127b`，CDHash`2b99e6b9b8793408ac5d6936d262374fcdd095c5`。
- Turnip17,059,744B，SHA`e6f1002553b506cc2a5b960bcc26ad3a4bb9cbc3f243ede388d5f9d87b664fbf`，CDHash`6c43d9c9581477078b7226f996c2ba127e02d2d5`。两文件4KiB CodeDirectory逐页独立验证。
- addon5文件：bundle Info/插件/Turnip和publish/clients；12,207,648B，SHA`78926fe0...`；追加own trust模块，原012两个模块逐字节保留。
- 实际Metal/AIR C API在主机软件Vulkan执行，compute_bad/render_bad/import_bad均0。没有测试原系统QuartzCore库(qc0)，没有把软件Vulkan计作A660硬件结果。

## 自有ST实现

Android返回和只读范围已单独确认。真实驱动fts_touch_spi5.2.4.1，spi1.0/a8c000，10点，X0..1439/Y0..3199。
正常FTB118,356B/SHA7d0994ea...，HTP108,064B/SHA34809628...；目标0x3936，当前缓存FW/config为84.48，与正常文件匹配。
本机FTB目标不是旧参考默认SALIXP0x4036；原始芯片寄存器ID仍待XNU读验证。
新FDT SHAeca50c15...声明：SPI mode0/CS0/≤7MHz，GPIO23低电平IRQ、22reset、132高电平AVDDsource，SE11/S3、wrapperAC0000，GPIO48–51 qup11。
未声明super-resolution/翻转，因此采用已核对12-bit编码和本机方向，不使用zeta/Novatek矩阵。

`package/VenusStTouch/`是自写ST协议/触点/HID/backend：

- 固定3936 FTB格式/长度/section校验，SPI0xFB chip/fw读取、0x87 FIFO、dummy1、同CS消息和10µs尾延时。
- 10点稳定硬件ID、高nibble ID/低nibble类型、完整快照、多点/抬起/复用ID显式lift，归一化到HID32767；palm confidence与hover tip分别处理。
- GENI共用组件仅负责控制器，ST message/解码/状态/板级策略自写；FIFO PIO、SE完成轮询、CS_DEASSERT9、不引入DMA地址假设。
- 19.2MHz XO/SE11时钟vote、6.4MHz SPI、pinmux/AVDDsource/reset和volatileIER/scan；保留现存芯片flash固件，没有烧写/NVM/calibration/lockdown命令。
- 原17 IOHIDDevice208B/207slots ABI下独立Venus digitizer；显示集成属性、同步快照、回调引用及停止时工作循环寿命处理；原键盘/Home保持其服务。
- 真正C核心ASan/UBSan与实际FTB、异常长度/ID、10点、复用/lifts、坐标/dummy/IO失败通过；新C/C++/HID/GENI按真实10063编译配方编译/归档/重链通过。
- LDO/GENI固件/PIO可用性仍属于实际板级交接验证；不把FTB目标或GPIO配置计作实测芯片/触摸事件。3次连续IO错误释放contacts并停止，不自动reset重试。

## 独立候选

共同kernel SHA`5c982406cc2474c1be96a7378440baf1fc1139690804a68e3b3d1c72c0e76a90`。
原012BootPolicy/RamBlock/GPU/显示成员保留，只有HidInputProbe成员替换并新增ST归档。
新内核default-off QEMU SystemOS/APFS/6GiB/AKS/HID通过。两个候选FAT、FD/EFI、boot roundtrip和--check通过。

| 候选 | 镜像SHA256 | 范围 |
| --- | --- | --- |
| Metal013 | `82f242ac57b6b214898c9e88d3f6aa6d01dd59efc334c9426df4d9f44015e9bd` | A660mode9、Metal发布、own5文件addon和追加trust、normalData/cache；ST关闭 |
| Touch014 | `7f5f335a822dc70d22c9ac9a0a9d3eea7bf9d6edf84de4933198592f5bf75a48` | ownSTmode3、GPIO/XO/GENI/MCUreset/volatile扫描/HID；GPU关闭 |

均168,960,000B，路径`artifacts/venus-{metal-013,touch-014}/phone/boot-venus-unixnu.img`。
没有再次失效MG缓存，没有重置Data/刷写。

用户先批准Metal013一次，Sending4.343s/Booting0.193s OKAY，总4.587s。
随后反馈“gpu驱动疑似没生效，有点卡但是不确定，来测试触摸吧”；GPU效果/Metal发现/像素仍未确认。
用户手动返回Android并准确批准Touch014一次，Sending4.342s/Booting0.193s OKAY，总4.584s。
两次授权均已消费，日志及phone收据保留。Touch014随后停在早期`PE_lockdown_iokit`：
QEMU复现为`VenusHidTouch.o`自动`__mod_init_func`提前注册metaclass，与手动初始化重复。
按官方ShengHidInput模式用`macho-late-init.py`延期后，Touch015/Metal016重建；
QEMU default-off与mode1通过。详见[`TOUCH-015-FIX.md`](TOUCH-015-FIX.md)。
当前尚未实机启动015/016；014/013镜像和失败日志保留。

证据：`evidence/metal13-source-review.json`、`st-touch-identity.json`、`metal013-candidate.json`、`touch014-candidate.json`，各artifact保留编译/签名/模型/主机runtime/QEMU收据。
