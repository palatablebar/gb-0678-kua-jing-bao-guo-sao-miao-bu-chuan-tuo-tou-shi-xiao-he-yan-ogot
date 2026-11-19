import csv,io
from datetime import datetime,timezone
from app.config import COLUMNS
from app.errors import DomainError
from app.reasons import reject
from app.values import instant
FAR=datetime.max.replace(tzinfo=timezone.utc)
def decode(raw):
    for encoding in ("utf-8-sig","gb18030"):
        try: return raw.decode(encoding),encoding
        except UnicodeDecodeError: continue
    raise DomainError("ENCODING","无法识别文件编码")
def sortable(value):
    try: return instant(value)
    except DomainError: return FAR
def rank(row):
    return (sortable(row["received_time"]),sortable(row["event_time"]),row["_line"])
def adjudicate(copies):
    "同一扫描号多份取值时裁定唯一正式证据：上传最早的已认定承运商原始扫描优先，补传不改写已认定时刻。"
    winner=min(copies,key=rank)
    adopted_upload=sortable(winner["received_time"])
    if adopted_upload==FAR: detail="各副本上传时间均无法核验，按发生时刻与源行次序定案"
    else: detail="上传时间最早，认定为已认定承运商原始扫描，结算以此为准"
    adopted={"line":winner["_line"],"node":winner["node"],"event_time":winner["event_time"],"received_time":winner["received_time"],"reason":"ORIGINAL_SCAN","detail":detail}
    rejected=[]
    for row in copies:
        if row is winner: continue
        received=sortable(row["received_time"])
        if received==FAR: reason,why="UNPROVEN_UPLOAD","上传时间无法核验，不能认定为原始扫描"
        elif received>adopted_upload: reason,why="LATER_REUPLOAD","补传上传更晚，结算以原始扫描为准，不采用最新补传"
        elif sortable(row["event_time"])>sortable(winner["event_time"]): reason,why="LATER_EVENT_TIME","同一上传批次内发生时刻更晚，不改写已认定时刻"
        else: reason,why="FILE_ORDER","上传与发生时刻一致，按源行先后定案"
        rejected.append({"scan_id":row[COLUMNS[0]],"line":row["_line"],"node":row["node"],"event_time":row["event_time"],"received_time":row["received_time"],"reason":reason,"detail":why})
    winner["_sources"]=sorted(line for copy in copies for line in copy["_sources"])
    return winner,{"scan_id":winner[COLUMNS[0]],"adopted":adopted,"rejected":rejected}
def evaluate(raw,context=None):
    text,encoding=decode(raw)
    if not text: raise DomainError("EMPTY_FILE","文件为空")
    if not text.strip(): raise DomainError("BLANK_ONLY","全部为空行")
    stream=csv.reader(io.StringIO(text,newline=""));header=next(stream,None)
    if header!=COLUMNS: raise DomainError("BAD_HEADER","表头不匹配")
    rows=[];bad=[];adjudications=[];groups={};duplicate=blank=repeated=merged=count=0
    try:
        for cells in stream:
            count+=1;line=stream.line_num
            if not cells or not any(c.strip() for c in cells): blank+=1;continue
            if cells==header: repeated+=1;continue
            row={"_line":line,"_sources":[line],"_raw":cells}
            if len(cells)!=len(header): bad.append(reject(row,"BAD_COLUMNS","列数不匹配"));continue
            row.update(dict(zip(header,[x.strip() for x in cells])))
            if not row[header[0]]: bad.append(reject(row,"EMPTY_VALUE","业务键为空"));continue
            groups.setdefault(row[header[0]],[]).append(row)
    except csv.Error: raise DomainError("BAD_CSV","引号未闭合或文件损坏")
    if count==0: raise DomainError("HEADER_ONLY","仅有表头")
    for key in groups:
        distinct=[]
        for row in groups[key]:
            if any(row["_raw"]==kept["_raw"] for kept in distinct): duplicate+=1
            else: distinct.append(row)
        if len(distinct)==1: rows.append(distinct[0]);continue
        winner,ruling=adjudicate(distinct)
        merged+=len(distinct)-1;adjudications.append(ruling);rows.append(winner)
    if not rows and not bad: raise DomainError("BLANK_ONLY","全部为空行")
    return {"rows":rows,"quarantine":bad,"adjudications":adjudications,"metrics":{"input":count,"accepted":len(rows),"quarantine":len(bad),"duplicate":duplicate,"blank":blank,"repeated_headers":repeated,"adjudicated":merged,"disputes":len(adjudications),"encoding":encoding}}
