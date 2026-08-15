# Phase 6 合成波形示例

这些 CSV 是软件测试夹具，不是示波器实测数据，也不代表真实 LLC 设计、安全结论或器件验证结果。

## `phase6_clean_zvs.csv`

上传页面时使用以下元数据：

```text
sample_rate = 1000000 Hz
time_unit = s
VGS_Q1: unit=V, probe_ratio=1, polarity=1
VDS_Q1: unit=V, probe_ratio=1, polarity=1
IRES: unit=A, probe_ratio=1, polarity=1
vds_zvs_threshold = 10 V
vds_hard_switching_threshold = 300 V
gate_low_threshold = 3 V
gate_high_threshold = 9 V
test_condition: Vin=400 VDC, load=500 W
```

预期结果：

```text
zvs_status          = LIKELY_ZVS
confidence          = 100%
switching_frequency ≈ 100000 Hz
VDS at turn-on      ≈ 2 V
dead_time           = INSUFFICIENT_DATA（示例没有 VGS_Q2）
```

如果要测试 `LIKELY_HARD_SWITCHING`，将 VGS 为高电平的对应行中的 `VDS_Q1` 从 `2` 改为 `400`。
如果只修改其中一个周期的高电平 VDS，例如改为 `100`，可以观察 `PARTIAL_ZVS`。
