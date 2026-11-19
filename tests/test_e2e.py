import csv,io
from app.pipeline import execute,load_sample
from app import store
def test_full_sample_flow(client):
    r=client.post("/api/runs",json={"sample":"dirty.csv"});assert r.status_code==200
    p=r.get_json();assert len(p["stages"])==7
    assert p["stages"][5]["metrics"]["balanced"] is True
def test_idempotent_real_input(sample):
    a=execute(sample);b=execute(sample)
    assert a["run_id"]==b["run_id"] and len(store.history())==1
def test_stale_review_409(client):
    "TRAP-26 陈旧复核不得覆盖新版本"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json();u="/api/runs/"+p["run_id"]+"/review"
    assert client.post(u,json={"version":1,"decision":"已复核"}).status_code==200
    assert client.post(u,json={"version":1,"decision":"退回复核"}).status_code==409
def test_export_has_manifest_and_quarantine(client):
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    r=client.get("/api/runs/"+p["run_id"]+"/archive")
    rows=list(csv.reader(io.StringIO(r.data.decode("utf-8-sig"))))
    assert rows[0][1]=="input_sha256" and any(x[3]=="quarantine" for x in rows[1:])
def test_failed_import_is_atomic(client):
    assert client.post("/api/runs",json={"csv":"bad"}).status_code==422
    assert store.history()==[]
def test_failed_publish_keeps_old_version_readable(client):
    "发布失败保留旧版本并可回读"
    good=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    assert client.post("/api/runs",json={"csv":"bad"}).status_code==422
    assert len(store.history())==1
    back=client.get("/api/runs/"+good["run_id"])
    assert back.status_code==200 and back.get_json()["run_id"]==good["run_id"]
def test_rerun_never_doubles_compensation(client):
    "同一补传重跑不新增扫描、不重复计赔"
    a=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    b=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    assert a["run_id"]==b["run_id"] and len(store.history())==1
    assert a["stages"][0]["metrics"]["accepted"]==b["stages"][0]["metrics"]["accepted"]
    assert a["stages"][5]["metrics"]["expected_total"]==b["stages"][5]["metrics"]["expected_total"]
def test_archive_export_includes_adjudication(client):
    "证据导出载明采用与未采用原因"
    p=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    rows=list(csv.reader(io.StringIO(client.get("/api/runs/"+p["run_id"]+"/archive").data.decode("utf-8-sig"))))
    adjudication=[x for x in rows[1:] if x[3]=="adjudication"]
    assert adjudication and "LATER_EVENT_TIME" in adjudication[0][6]
def test_module_entrances(client):
    from app.config import MODULES
    for slug,name in MODULES:
        assert client.get("/api/"+slug).status_code==200
        assert client.get("/"+slug).status_code==200
def test_missing_run_404(client): assert client.get("/api/runs/missing").status_code==404
