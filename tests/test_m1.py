import pytest,csv,io
from app.pipeline import load_sample
from app.modules.m1_scans.rules import evaluate,decode
from app.config import COLUMNS
from app.errors import DomainError
def test_bom_real_sample(sample):
    "TRAP-02"
    r=evaluate(sample);assert r["metrics"]["encoding"]=="utf-8-sig" and r["rows"][0][COLUMNS[0]].startswith("00")
def test_legacy_encoding_real_sample():
    "TRAP-01"
    r=evaluate(load_sample("legacy.csv"));assert r["metrics"]["encoding"]=="gb18030" and r["metrics"]["accepted"]>=30
def test_bad_columns_real_sample(sample):
    "TRAP-05"
    assert any(r["reason"]=="BAD_COLUMNS" for r in evaluate(sample)["quarantine"])
def test_duplicate_conflict_real_sample(sample):
    "TRAP-14 同键冲突不再隔离，裁决为唯一正式证据"
    r=evaluate(sample)
    assert not any(x["reason"]=="DUPLICATE_CONFLICT" for x in r["quarantine"])
    ruling=next(a for a in r["adjudications"] if a["scan_id"]=="0010")
    assert ruling["adopted"]["event_time"]=="2026-11-02T00:00:00Z"
    assert ruling["rejected"][0]["line"]==43 and ruling["rejected"][0]["reason"]=="LATER_EVENT_TIME"
    winner=next(row for row in r["rows"] if row[COLUMNS[0]]=="0010")
    assert winner["_sources"]==[3,43]
def test_identifier_preserved_real_sample(sample):
    "TRAP-08"
    r=evaluate(sample)["rows"][0];assert r[COLUMNS[0]].startswith("00")
def test_three_empty_states():
    "TRAP-18"
    for raw,code in [(b"","EMPTY_FILE"),(b"\n\r\n","BLANK_ONLY"),((",".join(COLUMNS)+"\n").encode(),"HEADER_ONLY")]:
        with pytest.raises(DomainError) as e:evaluate(raw)
        assert e.value.code==code
def test_intake_conservation_real_sample(sample):
    r=evaluate(sample);m=r["metrics"]
    assert m["input"]==m["accepted"]+m["quarantine"]+m["duplicate"]+m["blank"]+m["repeated_headers"]+m["adjudicated"]
def _csv(extra):
    return (",".join(COLUMNS)+"\n"+"\n".join(extra)+"\n").encode()
CARRIER="0095,0001,妥投,2026-11-04T00:00:00Z,2026-11-06T00:00:00Z,JP,24,200,0,承运商原始"
WAREHOUSE="0095,0001,妥投,2026-11-04T06:00:00Z,2026-11-07T00:00:00Z,JP,24,200,0,国内仓补传"
def test_earliest_upload_wins_regardless_of_file_order():
    "承运商原始扫描上传更早即胜，与文件先后无关；运营的最新补传不采用"
    for rows in ([CARRIER,WAREHOUSE],[WAREHOUSE,CARRIER]):
        r=evaluate(_csv(rows));assert len(r["rows"])==1 and r["metrics"]["disputes"]==1
        ruling=r["adjudications"][0]
        assert ruling["adopted"]["event_time"]=="2026-11-04T00:00:00Z" and ruling["adopted"]["reason"]=="ORIGINAL_SCAN"
        assert ruling["rejected"][0]["reason"]=="LATER_REUPLOAD"
        assert r["rows"][0]["event_time"]=="2026-11-04T00:00:00Z"
def test_identical_reupload_adds_no_scan():
    "同一补传重跑不新增扫描"
    r=evaluate(_csv([CARRIER,CARRIER]))
    assert len(r["rows"])==1 and r["metrics"]["duplicate"]==1 and r["metrics"]["disputes"]==0
def test_adjudication_preserves_all_source_lines():
    "未采用副本不误删：源行并入血缘，行数守恒"
    r=evaluate(_csv([CARRIER,WAREHOUSE]));m=r["metrics"]
    assert r["rows"][0]["_sources"]==[2,3] and m["adjudicated"]==1
    assert m["input"]==m["accepted"]+m["quarantine"]+m["duplicate"]+m["blank"]+m["repeated_headers"]+m["adjudicated"]
def test_quoted_newline_is_one_record(sample):
    "TRAP-03"
    r=evaluate(sample);assert any("\n" in str(x) for row in r["rows"] for x in row.values())
