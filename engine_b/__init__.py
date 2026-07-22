"""Engine B — Signal discovery／intake 的注意力狀態層。

本 package 保存 pending leads 的封閉狀態機與 harvest 紀錄。核心不變式：
lead 狀態只是「研究注意力 metadata」，永遠不影響 evidence tier，也不代表
funded-capital 許可。真正的入圖仍走 lead-intake／source-trace／Research
Action 核准；本層只負責「哪些線索待你判斷、走到哪一步了」。
"""
