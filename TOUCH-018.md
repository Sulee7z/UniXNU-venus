# 017启动报告：ST识别失败；018对齐官方GENI路径

## 017实机结果

只读快照`read-20261029T192825Z`完整：171115页/93段，含两次metadata共701419520B，
checkpoint1159，metadata稳定、SHA/覆盖通过。launchd完整参数为touch-017/venus-st-report=1。
启动报告`/private/var/db/venus-st-017/startup.jsonl` 362B：

```json
{"stage":5,"status":-19,"clock_cmd":0,"clock_cfg":1048577,
 "geni_protocol":1,"fifo_disabled":0,"chip_id":0,"fw":0,
 "messages":1,"opcode":251,"transfer":0,"cs":0,
 "frames":0,"hid_phase":6,"hid_match":0,"hid_meta":0,
 "hid_start":0,"hid_ready":1,"hid_report":-1,"hid_reports":0}
```

HID发现/元类/启动和原IOHIDEventDriver匹配都成功；唯一失败是ST阶段5：
仅一次0xFB读，GENI transfer/CS返回0，但芯片ID读为0，VST_E_ID(-19)。
这不是HID问题，也不是“没有加载触摸驱动”。

## 官方文档与主线核对

重读`https://unixnu.com/zh/porting/`、`porting/bring-up`、`porting/input`、
`drivers/xnu-drivers`、`drivers/sheng-hid-input`，并核对主线
`https://github.com/UniXNU/UniXNU-sheng`固定提交
`08cde20edc3254ed6f7df8d0f5384fb887786e8f`的`package/TouchProbe.cpp`和
`package/TouchBoard.h`。主线要点：

- 分阶段报告，失败先停在资源/时钟/引擎/识别；
- 先取GENI engine identity，再配置SPI时钟、引脚和复位；
- 官方`busXfer`用`geni_spi_transfer(..., keep_cs=0)`，不手工发第二个CS opcode；
- 本机`fifo_disabled=0`，不需要主线在FIFO禁用时使用的SMMU bypass DMA；
- 主线从S4 DFS表选择时钟并投GPLL0；Venus报告显示XO/SE11分支已运行，时钟不是当前
  已证实失败点；
- 识别应记录实际芯片ID并允许重试，不能把FTB target 0x3936直接当成芯片ID。

## 018修改

- ST消息改用控制器管理的CS（`keep_cs=0`），删除未定义的手工CS opcode9；
- 复位低电平保持300ms，复位释放后等待，识别最多8次、每次25ms；
- 芯片ID接受SALIXP 0x4036和FTB target 0x3936，0/0xffff仍失败并记录；
- startup报告增加`id_attempts`、`cs_manual=0`，用于区分“传输成功但ID0”和CS/复位问题；
- HID匹配、延迟元类注册、原版codeless bundle保持不变；
- 新报告目录`/private/var/db/venus-st-018`，root0700/文件0600/独占，不覆盖旧报告。

生产kernel `b5d81d5b55834ad8cc469c128367b877d7b76b653ab4db464d26d5e54cd1da37`。
本次G:清理已删除`artifacts/venus-deployment/OS.raw`/`SystemOS.raw`，无法重跑
QEMU SystemOS；不声称018 QEMU通过。017 HID匹配测试、生产HID对象一致性、FAT/
ADT/trust/FD/EFI/boot roundtrip/`--check`仍通过。018没有phone实测。

## 候选

`G:/UniXNU-Port/artifacts/venus-touch-018/phone/boot-venus-unixnu.img`
168960000B，SHA256
`43b574316bfeae5212bf0fee0db576c90b9632aa1ead9610aab3a5487045b531`。

018已启动并只读取回`read-20261030T014937Z`：报告仍stage5/status-19/chip_id0，
messages8/id_attempts8/transfer0/cs0，HID ready1。控制器CS/复位/重试没有解决ID0。
下一步见[TOUCH-019.md](TOUCH-019.md)：先做GENI内部loopback和MISO输入使能，
再按报告决定是否检查PM8350C L2/L3供电。
