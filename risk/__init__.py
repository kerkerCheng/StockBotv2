"""Risk — hard limits only。

**回答一句話：這個曝險撞到哪條硬上限？**
不判斷好壞、不排序、不形成 view——那些分別是 `alpha/` 與 `portfolio/` 的事。

三個硬擋是真實的資本煞車，**重構一項未動**：
5% 單筆 NAV 上限、ETF 槓桿 nominal 20%／effective 40%、總曝險 cap。
numeric SSOT 仍是 `config/investment_policy.json` 與 `config/beta_policy.json`。
"""
