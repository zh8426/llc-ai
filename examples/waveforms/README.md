# Phase 6 合成波形示例

这些 CSV 是软件测试夹具，不是示波器实测数据，也不代表真实 LLC 设计、安全结论或器件验证结果。

新增的 `phase6_*.csv` 文件都使用 `sample_rate = 1000000 Hz`、`vds_zvs_threshold = 10 V`、
`vds_hard_switching_threshold = 300 V`。门极阈值可以留空使用自动阈值，或明确填写
`gate_low_threshold = 3 V`、`gate_high_threshold = 9 V`。测试条件可填写
`Vin=400 VDC`、`load=500 W`。

新增文件的周期为 `7 us`，因此 switching frequency 预期约为 `142857.14 Hz`；
原有 `phase6_clean_zvs.csv` 使用 `10 us` 周期，预期约为 `100000 Hz`。

## 覆盖矩阵

| 文件 | 主要覆盖 | 预期结果 |
| --- | --- | --- |
| `phase6_likely_zvs.csv` | 全部周期低 VDS、VDS at turn-on、IRES、周期频率 | `LIKELY_ZVS`，cycle consistency `100%`，dead time `INSUFFICIENT_DATA` |
| `phase6_partial_zvs.csv` | 同一文件内混合 ZVS / 中间 VDS / 硬开关 | `PARTIAL_ZVS`，cycle consistency 约 `33.33%`，3 个证据周期状态依次为 `LIKELY_ZVS`、`PARTIAL_ZVS`、`LIKELY_HARD_SWITCHING` |
| `phase6_likely_hard_switching.csv` | 全部周期高 VDS | `LIKELY_HARD_SWITCHING`，cycle consistency `100%` |
| `phase6_insufficient_data.csv` | 只有一个 Q1 上升沿 | `INSUFFICIENT_DATA`，cycle consistency `0%`，没有 switching frequency 和 VDS 统计 |
| `phase6_dead_time_available.csv` | VGS_Q2 互补门极、周期内 dead-time 配对 | dead time `AVAILABLE`，约 `1000 ns`，有效 `3`、缺失 `1`、拒绝 `0` |
| `phase6_dead_time_missing_cycle.csv` | 某个完整周期缺少 Q2 上升沿 | dead time `AVAILABLE`，有效 `2`、缺失 `2`、拒绝 `0` |
| `phase6_dead_time_rejected_cycle.csv` | 一个周期内出现多个 Q2 上升沿 | dead time `AVAILABLE`，有效 `2`、缺失 `1`、拒绝 `1` |
| `phase6_scaled_units.csv` | `us`、`mV`、`mA` 单位归一化 | 归一化后 `LIKELY_ZVS`，VDS at turn-on 约 `2 V` |

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
cycle_consistency   = 100%
switching_frequency ≈ 100000 Hz
VDS at turn-on      ≈ 2 V
dead_time           = INSUFFICIENT_DATA（示例没有 VGS_Q2）
```

如果要测试 `LIKELY_HARD_SWITCHING`，将 VGS 为高电平的对应行中的 `VDS_Q1` 从 `2` 改为 `400`。
如果只修改其中一个周期的高电平 VDS，例如改为 `100`，可以观察 `PARTIAL_ZVS`。

## 页面上传步骤

1. 在 Waveform Panel 选择一个 CSV。
2. 选择含 `VGS_Q2` 的文件时，勾选“CSV 中包含 VGS_Q2”。
3. 对 `phase6_scaled_units.csv`，将时间单位改为 `us`，并将通道单位改为：
   `VGS_Q1=mV`、`VDS_Q1=mV`、`IRES=mA`。
4. 其他文件使用时间单位 `s`，通道单位分别为 `V`、`V`、`A`。
5. 点击“上传并分析 ZVS”，对照上表检查状态、周期一致性、VDS 和 dead-time 配对计数。
