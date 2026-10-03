"""Check the held-out grading rules on hand-written answers (no model is called).

Each case: (question id, hypothetical answer, expected verdict). Written before the
held-out run, to make sure the rules accept good answers and reject bad ones.
"""

import sys
from pathlib import Path

from aorus_rag.benchmark import grade, load_cases

CASES = [
    ("h01", "重量約 2.5 kg，電池容量為 99Wh [1][2]。", True),
    ("h01", "重量約 2.5 kg [1]。", False),                                    # missing battery
    ("h02", "與行動辦公相關的有：重量 ~2.5 kg、99Wh 電池、Wi-Fi 7 [1]。", True),
    ("h02", "這台有 RTX 5090 顯示卡 [1]。", False),                           # none of the mobile specs
    ("h03", "BXH 為 RTX 5070 Ti 12GB，BYH 為 RTX 5080 16GB，其餘規格相同 [1]。", True),
    ("h04", "RTX 5070 Ti 對應 AORUS MASTER 16 BXH [1]。", True),
    ("h04", "RTX 5070 Ti 對應 BYH [1]。", False),
    ("h05", "The RTX 5080 is in the AORUS MASTER 16 BYH [1].", True),
    ("h06", "左側為 Thunderbolt™5，右側為 Thunderbolt™4 [1]。", True),
    ("h06", "Thunderbolt™5 位於左側 [1]。", False),                            # only one side
    ("h07", "右側有 1 x Type-A USB3.2 Gen2、1 x Type-C Thunderbolt™4、1 x MicroSD、1 x Audio Jack [1]。", True),
    ("h07", "右側有 Type-A、Thunderbolt™4、MicroSD、耳機孔；右側沒有 HDMI [1]。", True),   # negated HDMI is fine
    ("h07", "右側有 HDMI 2.1、Type-A、Thunderbolt™4、MicroSD、耳機孔 [1]。", False),       # wrong side
    ("h08", "支援，具備 1 x MicroSD（UHS-II）插槽 [1]。", True),
    ("h09", "不是。99Wh 是電池容量，規格資料中未提及續航時間 [1]。", True),
    ("h09", "不是，99Wh 是電池容量，實際約 8 小時 [1]。", False),             # invented battery life
    ("h09", "是的，可以使用 99 小時。", False),
    ("h10", "規格資料中未提及遊戲效能，無法判斷能否流暢執行；本機 GPU 最高為 RTX 5090 [1]。", True),
    ("h10", "搭載 RTX 5090，可以流暢執行《黑神話：悟空》[1]。", False),
    ("h10", "RTX 5090 可達 60 fps 以上 [1]。", False),
    ("h11", "不能。時脈與 TDP 是不同指標，規格資料中未提及 TDP [1]。", True),
    ("h11", "可以推算，TDP 約為 55W [1]。", False),
    ("h12", "可以，有 2 個 SO-DIMM 插槽，最高支援 64GB DDR5 [1]。", True),
    ("h12", "可以擴充，但最高不能超過 64GB [1]。", True),                      # "不能" here is not a no
    ("h12", "不可以，記憶體最高 64GB。", False),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    qs = {c["id"]: c for c in load_cases(Path(__file__).with_name("heldout_qa.jsonl"))}
    failed = 0
    for qid, answer, expected in CASES:
        case = qs[qid]
        g = grade(case, answer, case["gold_chunks"])
        ok = g["correct"] == expected
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'} {qid} expect={str(expected):5} got={str(g['correct']):5} "
              f"violations={g['violations']}  {answer}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} grader checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
