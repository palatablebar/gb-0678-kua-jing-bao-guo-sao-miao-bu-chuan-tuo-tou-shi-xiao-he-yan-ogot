REASONS={"BAD_COLUMNS":"列数不匹配","EMPTY_VALUE":"必填值为空","INVALID_NUMBER":"数字格式错误","INVALID_TIME":"时间缺少偏移或格式错误","DUPLICATE_CONFLICT":"同键取值冲突","UNKNOWN_REFERENCE":"引用不存在","STALE_VERSION":"版本已更新","EMPTY_FILE":"文件为空","HEADER_ONLY":"仅有表头","BLANK_ONLY":"全部为空行","ORIGINAL_SCAN":"上传最早，认定为原始扫描","LATER_REUPLOAD":"补传上传更晚，不采用","LATER_EVENT_TIME":"同批上传发生时刻更晚","UNPROVEN_UPLOAD":"上传时间无法核验","FILE_ORDER":"完全同时按源行序"}
def reject(row, code, detail):
    return {**row,"reason":code,"detail":detail}
def sources(row):
    return row.get("_sources", [row.get("_line",0)])
