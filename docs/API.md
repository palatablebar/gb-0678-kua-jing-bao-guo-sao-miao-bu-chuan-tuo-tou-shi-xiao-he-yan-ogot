# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。扫描采信阶段另返回adjudications：同键冲突扫描的采用与未采用副本及原因。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV，含裁决明细。
